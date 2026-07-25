---
name: archdoc
description: >-
  Principles and rules for writing and maintaining an architecture document — the durable record of how a system is
  built and why. Load this whenever the user asks to create, draft, write, update, revise, or review an architecture
  doc, or mentions "architecture", "arch doc", "architecture.md", "system design", "tech stack decision", or "how
  should we structure this" — even casually ("write up how this thing is put together", "document why we chose
  Postgres", "let's nail down the architecture first"). Also load it before you would otherwise start writing up a
  system's structure, stack choices, or component breakdown, so the document follows architecture-doc conventions from
  the first line. Do NOT use this skill for a PRD or requirements list (use the `prd` skill), a decision log/changelog,
  a README, deployment runbooks, or implementation/phase plans — none of those are architecture.
---

# Writing an architecture doc

An architecture doc is the system-level **"how"**: the significant engineering decisions, each stated *with its
reasoning*. Three kinds of thing qualify:

- An approach chosen over an alternative — event-driven vs. polling, monolith vs. services.
- A technology chosen over another — the canonical architectural decision.
- Structural decisions about how the major pieces fit together.

**Think of it as an onboarding doc for engineers.** Its goal is to get a new engineer, in the least time possible, to
(1) understand every major design decision and why it was made, and (2) hold a map of the project — where things live,
what the major components are, how they interact. Every choice about what to include and how to present it serves
that.

This skill loads the principles below. It doesn't launch an interview or a fixed workflow — when the user asks for an
architecture doc, write it normally, thinking this way.

## What it is not

- **Not a requirements doc.** What the product must do for the customer is the PRD's job, decided first and independent
  of this. If you're writing "the product must let the user…", you've drifted. When a requirement motivates a decision,
  *reference* it — "batched because the PRD requires sub-second reads (PRD 4.1)". A pointer stays correct when the
  requirement is revised; a copy goes stale.
- **Not a historical record.** Not a timeline, not a changelog, not a log of decisions made, not a record of the order
  things were built. None of that is a property of the system — it's a property of the project that produced it. What
  it is instead: **a summary of the actual architectural state right now**, which a reader can trust without working
  out which parts have been superseded.
- **Not a description of the code.** Not line-by-line, not a spec for how to write each function. If a reader could
  learn the same thing by reading the code for five minutes, the doc is describing rather than deciding. What the code
  can't tell them is *why this and not that* — that's what only the doc holds, and the reason it exists.
- **Not a plan, a runbook, or a content doc.** Build order and phases are project management. Install and run
  instructions belong in the README; duplicating them here creates two copies that will disagree. And don't reference
  scratch outlines or brainstorms — the doc stands on its own.

Two things look like history and aren't:

- **Architecture designed but not yet built.** Writing the architecture before the code is the normal case, and the doc
  legitimately describes the intended design ahead of it. Forward-looking, not historical.
- **Rejected alternatives.** "Postgres over a document store, because de-duplication is a uniqueness constraint we'd
  otherwise hand-roll" is *reasoning for the current design*. Keep it. The narrative — tried the document store first,
  migrated off it after two months — is what doesn't belong.

Where a project keeps a decision log (commonly a `decisions.md` alongside), that's where the narrative goes: what
changed, why, what trade-offs were weighed. Current state here, path taken there. If the project has no such log, the
history is simply out of scope — don't smuggle it in for lack of a better home.

## Two tests for "does this belong?"

1. **Engineering, or content?** Is this a decision about *how the system is engineered*, or about *what the product
   happens to contain*? The failure this catches: a slide deck's architecture doc listing its twelve slides in order.
   Which slides exist is a presentation decision — the parser, templating, and rendering are identical regardless.
2. **Would the architecture change?** If this detail changed, would the architecture change with it? Reordering a menu,
   retuning a threshold: engineered the same way before and after, so not architecture. Swapping the ORM, moving batch
   to streaming: genuinely different.

When something passes both but you're unsure the user wants it here, ask. That judgment is theirs.

## Every decision carries its reasoning

A choice without a "why" is not architecture — it's a fact already visible in the code, restated. The reasoning is the
entire payload: it's what lets a future reader decide whether the decision still holds when circumstances change.

**Weak:**
> The backend is written in Go. The database is Postgres.

**Strong — decision, reasoning, rejected alternative:**
> **Backend — Go.** The ingest path is I/O-bound across thousands of concurrent feed fetches, and goroutines make that
> natural without an async framework. Python was the default given team familiarity, but the fan-out would have meant
> asyncio throughout, and the CPU-bound parse step would have contended on the GIL.

The second is longer and worth it. The first tells a reader what they'd have learned from `go.mod`. Where a decision
was genuinely forced, say so — "forced by the existing auth provider" is useful reasoning and stops someone
re-evaluating a non-choice.

## Sections: ideas, not a template

How the doc is organized is entirely up to the nature of the project. The list below is a source of ideas — not a
required set, not an exhaustive one, and not an order. Take what the project needs, invent what it needs that isn't
here, and skip the rest; an empty heading is worse than none.

- **Design principles** — a handful of rules governing the whole system ("prefer instructing the agent unless
  correctness requires code", "read-only engine"). Stating them once up front stops the same rationale repeating below.
- **Stack** — the layers and the chosen technology for each, with reasoning and the major rejected alternatives.
  Usually the highest-value section, because it's what future readers most often try to reconstruct and can't.
- **Code layout** — a *map*, not an inventory: which files hold which major pieces. Listing every file goes stale
  immediately and buries the few pointers that mattered.
- **Component design** — the major components, what each owns, and the significant decisions inside each.
- **Cross-cutting decisions** — things shaping a whole subsystem rather than one component: a latency-vs-throughput
  trade-off, a consistency model, a retry philosophy. State what was gained *and* given up; a trade-off recorded as a
  one-sided win gets re-argued later.
- **Risks and mitigations** — where the design is load-bearing, fragile, or betting on an assumption, and how it copes.
  Not a generic risk register.
- **Future enhancements** — directions deliberately deferred, with enough reasoning that they aren't relitigated.

## Form follows the goal

The doc is not just a list of decisions in prose. Reach for whatever conveys the architecture fastest:

- A block diagram of how components connect.
- A flow chart of a request or data path.
- A table mapping functionality to the module that owns it, or splitting responsibilities across layers.
- Prose, for reasoning and trade-offs — these need a couple of sentences to be intelligible, so don't compress them
  into telegraphic bullets.

Use judgment: pick the form that gets a new engineer to understanding quickest.

## Style

Plain Markdown headings; `###` for individual components or decisions where that reads better. Open with a line or two
on what the system is. Numbering is optional, unlike in a PRD — an architecture doc isn't an addressable list of atomic
claims, so number sections only if people will cite parts of it, and be consistent either way.

Lead each decision with a bolded name, then the reasoning (`**Backend — Go.**` …), so a reader hunting one decision
finds it without reading everything. In any table of decisions, a `why` column is what keeps it architecture rather
than an inventory.

Cut anything that restates the code, restates another section, or fills a template heading.

## Completeness, and the drift that erodes it

**No major architectural decision in the system may be missing from the doc.** If the code holds a significant decision
the doc never mentions, the doc is wrong, not merely incomplete — a reader who finds one gap has to verify everything
against the code anyway, and the document's value collapses. (Note this runs opposite to a PRD, which is deliberately a
*superset* of what's built.)

Completeness erodes during ordinary development, not doc-writing: someone swaps a library or adds a subsystem, and the
doc isn't touched because the change is happening in code. So watch as you work, not only when editing the doc. Worth
catching:

- A new component, subsystem, or dependency the doc doesn't mention.
- A replaced technology or approach that now contradicts it.
- A component whose responsibilities have drifted from its documented role.

Small local changes don't need flagging — same bar as for inclusion: if the architecture didn't change, there's nothing
to sync.

When you notice one, **tell the user and let them decide** — "This swaps the queue from SQS to Redis Streams, which
contradicts the Stack section. Want me to update it?" Where the project keeps a decision log, a mid-build change of
approach usually wants both the architecture section rewritten and a log entry recording why; offer both rather than
silently picking one.

**When you do update, rewrite in place.** Don't append a paragraph beneath the old one, leave the previous approach
with a note that it changed, or add a "Previously…" subsection. Each turns one clear statement into two competing ones
with no way to tell which is live — the same failure as an incomplete doc, arriving by a different route.
