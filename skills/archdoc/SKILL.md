---
name: archdoc
description: >-
  Principles and rules for writing and maintaining an architecture document — the durable record of how a system is
  built and why. Load this whenever the user asks to create, draft, write, update, revise, or review an architecture
  doc, or mentions "architecture", "arch doc", "architecture.md", "system design", "tech stack decision", or "how
  should we structure this" — even casually ("write up how this thing is put together", "document why we chose
  Postgres", "let's nail down the architecture first"). Also load it before you would otherwise start writing up a
  system's structure, stack choices, or component breakdown, so the document follows architecture-doc conventions from
  the first line. It is the sibling of `prd.md` and `decisions.md` in a project's `design_docs/` folder. Do NOT use this
  skill for a PRD or requirements list (use the `prd` skill), a README, deployment runbooks, or implementation/phase
  plans — none of those are architecture.
---

# Writing an architecture doc

An architecture doc is the system-level **"how"** of what is being built: the significant implementation and
engineering decisions, each stated *with its reasoning*. It is the durable record of how the system is built and why it
is built that way.

It is the mirror image of a PRD. A PRD holds requirements and no implementation; an architecture doc holds
implementation decisions and no requirements. If you find yourself writing "the product must let the user…", you've
drifted into PRD territory — that belongs in the PRD, and the architecture doc's job is to explain how the system
satisfies it.

This skill loads the rules for producing a good architecture doc. It does **not** launch an interview or a fixed
workflow. When the user asks to create or update an architecture doc, do that task normally, following the principles
below. Only run a structured design exercise if the user asks for one.

## Where it sits: the design_docs family

The architecture doc is one of three sibling documents in a project's `design_docs/` folder, written in this order:

- **`prd.md`** — *what* we want, decided first. Requirements, no implementation. Locked down once agreed (see the `prd`
  skill).
- **`architecture.md`** — *how* we build it, decided second, derived from the PRD. Major engineering decisions. This
  document.
- **`decisions.md`** — *what changed along the way*, appended during the build. A timestamped log of major decisions,
  inflection points, and changes of approach, with reasoning.

Knowing the siblings exist is what keeps the architecture doc from bloating, because each has a job this one doesn't:

- A requirement showing up here belongs in `prd.md`. Reference it instead — cite the requirement number (`PRD 4.1`) to
  explain *why* a decision was made. That's what the PRD's numbering is for, and a decision anchored to a requirement
  is far easier to re-evaluate later.
- The *history* of how a decision evolved belongs in `decisions.md`. This doc states the design as it stands now (see
  "Reflect the current state" below). When you rewrite a section because the approach changed, that's often the moment
  to suggest a `decisions.md` entry capturing the pivot and its reasoning — the two docs are complements: current state
  here, the path and the reasoning for changes there.

**Open with a scope statement that names the siblings.** After the one-line description of the system, say explicitly
what this document covers and what lives elsewhere. It orients the reader in a sentence and, more importantly, it keeps
the author honest about the boundary while writing:

> How the Schedule skill is **built** — engineering structure and implementation choices. What the product does and the
> rules it enforces are in `prd.md`; how a user runs it is in `README.md`. This document covers code.

If the project doesn't use this layout, the principles all still hold — just adapt the pointers to whatever documents
actually exist, and don't invent siblings that aren't there.

## What an architecture doc captures

Three kinds of thing, all at the *significant* altitude:

- **An approach chosen over an alternative approach** — event-driven vs. polling, server-rendered vs. SPA,
  monolith vs. services.
- **A framework, library, language, or technology chosen over another** — the canonical architectural decision.
- **Structural decisions about how the major pieces fit together** — what the components are, what each owns, and how
  they talk to each other.

The altitude matters more than the topic. An architecture doc is **not a line-by-line description of the code** and not
a specification of how to write each function. If a reader could get the same information by reading the code in five
minutes, the doc is describing rather than deciding. What the code cannot tell them is *why this and not that* — that's
what only the doc holds, and it's the reason the doc exists.

## The two discriminating tests

Most "does this belong?" questions collapse into these. Apply them to any candidate section.

**Test 1 — engineering or content?** Is this a decision about *how the system is engineered*, or about *what the
product happens to contain*? Engineering → architecture doc. Content, or how it's shipped and run → somewhere else
(PRD, README, content docs).

The failure mode this catches: a slide deck's architecture doc listing the ordered slides. Which slides exist, and in
what order, is a presentation decision — the rendering pipeline, the build step, the templating engine are all
identical regardless. That list is content, and it belongs in a content doc.

**Test 2 — would the architecture change?** If this detail changed, would the architecture change with it? If no, it
isn't architecture. Swapping copy, reordering a menu, retuning a threshold: the system is engineered the same way
before and after. Swapping the ORM, moving from batch to streaming: the architecture is genuinely different.

When a section survives both tests but you're still unsure whether the user wants it in this document, **ask them**
rather than guessing. That judgment is theirs.

## What belongs in the doc

Not every doc needs every section, and the order can follow whatever the system's natural shape is. Include a section
when the system actually has something to say there — an empty heading is worse than no heading.

**Stack / technology choices.** The layers of the system and the chosen technology for each, each with its reasoning.
Name the major rejected alternatives and why they lost. This is the highest-value section in most architecture docs,
because it is the part future readers most often try to reconstruct and cannot.

**Code layout.** A *map*, not an inventory: which files or directories hold which major pieces of functionality. The
purpose is orientation — a new reader should know where to go looking. The exact tree doesn't matter and listing every
file actively hurts, because an inventory goes stale immediately and buries the few pointers that mattered.

**Component design.** The major components, what each is responsible for, and the significant design decisions inside
each. Keep this current with the code; a component's stated responsibility that no longer matches what it does is a
worse-than-useless doc.

**Cross-cutting decisions.** Decisions that shape a whole subsystem rather than living in one component — a
latency-versus-throughput trade-off, a consistency model, an error-handling or retry philosophy. State the trade-off
explicitly: what was gained, what was given up. A trade-off recorded as a one-sided win is a trade-off that will be
re-argued later.

**Risks and mitigations.** Real architectural risks — where the design is load-bearing, fragile, or betting on an
assumption — and how the design addresses each. Not a generic risk register.

**Future enhancements.** Architectural directions deliberately deferred or ruled out of scope, with enough reasoning
that the decision isn't relitigated from scratch later.

## What does not belong

**Implementation plans, phases, or commit sequences.** The order in which a system was built is not a property of the
system. A build schedule is project management; put it in a plan document. (Describing architecture that isn't built
yet is fine — see below. Describing *when* it will be built is not.)

**Requirements.** What the product must do for the customer is the PRD's job. The architecture doc may reference a
requirement to explain why a decision was made, but it does not state requirements of its own.

**Deployment and run instructions.** How to install, configure, and start the thing belongs in the README. Duplicating
it here creates two copies that will disagree.

**Content and product decisions that don't change the engineering.** See Test 1 above.

**Brainstorming artifacts, outlines, and drafts.** Don't reference or depend on scratch planning documents. The
architecture doc stands on its own — a reader with only this doc and the code should never need to go find a
brainstorm to understand a decision.

## Every decision carries its reasoning

A choice without a "why" is not architecture — it's a fact already visible in the code, restated. The reasoning is the
entire payload, because it's what lets a future reader (or agent) decide whether the decision still holds when
circumstances change.

**Weak — states the choice, no reasoning:**
> The backend is written in Go. The database is Postgres. Caching uses Redis.

**Strong — decision, reasoning, rejected alternative:**
> **Backend — Go.** The ingest path is I/O-bound across thousands of concurrent feed fetches, and Go's goroutines make
> that natural without an async framework. Python was the default choice given the team's familiarity, but the fetch
> fan-out would have meant asyncio throughout, and the CPU-bound parsing step would have contended on the GIL.

The second is longer and worth it. The first tells a reader what they could have learned from `go.mod`.

Where a decision was genuinely forced (only one option, or an external constraint), say so — "forced by the existing
auth provider" is useful reasoning and stops someone from re-evaluating a non-choice.

## Structure and style

- **Plain Markdown headings.** `##` for sections, `###` for components or individual decisions where that reads better.
- **Short overview, then the scope statement.** A line on what the system is, then what this doc covers versus its
  siblings (see the design_docs section above).
- **Numbering is optional, unlike in a PRD.** An architecture doc isn't an addressable list of atomic claims, so it
  needs no hierarchical scheme. Number sections (`## 1. Design principles`) when the doc is long enough that people
  will want to cite parts of it; leave them unnumbered when it isn't. Either is fine — be consistent within a document.
- **A "Design principles" section near the top is often worth it.** A handful of numbered principles that govern the
  whole system ("minimal code — prefer instructing the agent unless correctness requires library code", "read-only
  engine", "validate before compute"). These are the decisions that explain many of the smaller ones, so stating them
  once up front stops the same rationale from being repeated in every section below.
- **Lead each decision with a bolded name, then the reasoning.** `**Backend — Go.**` followed by why. This makes the
  doc scannable: a reader hunting for one decision finds it without reading the whole document.
- **Use a table when a decision is applied repeatedly across many items.** A recurring split — which capabilities are
  agent versus deterministic code, which layer owns which concern — reads far better as `| item | choice | why |` than
  as a dozen paragraphs. The `why` column is not optional; it's what makes it architecture rather than an inventory.
- **Prose for reasoning, bullets for enumerations.** Rationale and trade-offs need a couple of sentences to be
  intelligible; lists of files, components, or layers do not. Don't force reasoning into telegraphic bullets — it's
  precisely the part that needs room.
- **Concise; every section earns its place.** Cut anything that restates the code, restates another section, or exists
  only to fill a template heading.

## The completeness invariant

**There must be no major architectural property or decision in the system that the doc doesn't capture.** If the code
holds a significant decision the doc never mentions, the doc is wrong — not merely incomplete.

This is what makes the doc trustworthy. A reader who finds one unmentioned major decision can no longer rely on the doc
for any of them, because they now have to verify everything against the code anyway. Completeness is the property that
gives the whole document its value.

Note this runs the opposite direction from a PRD, which is deliberately a *superset* of what's built. An architecture
doc describes the system as it is.

## Reflect the current state, not the history

The doc describes how the system is built **now**. It is not a changelog, not a record of the path taken, and not a log
of superseded decisions. When a decision is replaced, rewrite the section to describe the new design and its reasoning
— don't stack a new paragraph on top of the old one. A doc that accumulates history becomes a doc where the reader
can't tell which parts are still true.

Two things that look like exceptions but aren't:

- **Architecture planned ahead of the code.** While a project is still being built, the doc may describe the intended
  architecture before it exists. That's the normal case for a design-first project, not drift.
- **Rejected alternatives.** Recording that Python was considered and why it lost is *reasoning for the current
  design*, not history. Keep it. What doesn't belong is the narrative of having tried Python first and migrated.

The history isn't lost — it goes in `decisions.md`, the sibling built for exactly this: timestamped entries recording
what changed, why, and what trade-offs were weighed. That division is what lets the architecture doc stay a clean
description of the present without anyone having to throw away the reasoning behind a pivot.

## Notice drift and flag it — proactively

The doc goes stale during ordinary development, not during doc-writing. Someone swaps a library, restructures a
component, or adds a subsystem, and the architecture doc isn't touched — because the change is happening in code. Each
such gap chips away at the completeness invariant, and it happens silently.

So watch for it as you work, not only when you're editing the doc. When you or the user make a change, ask: *does this
change a decision the architecture doc records, or add one it doesn't?* Cases worth catching:

- A **new component, subsystem, or dependency** the doc doesn't mention.
- A **replaced technology or approach** that now contradicts what the doc says.
- A **component whose responsibilities have shifted** away from its documented role.

When you notice one, **tell the user** — something like "This swaps the queue from SQS to Redis Streams, which
contradicts the Stack section of the architecture doc. Want me to update it, and log the switch in `decisions.md`?"
Then let them decide. Flag and ask; the user authorizes the edit.

A change of approach mid-build usually wants both: the architecture doc rewritten to describe the new design, and a
`decisions.md` entry recording why the approach changed. Offer both rather than silently picking one.

Small, purely local changes don't need flagging. The bar is the same as for inclusion: if the architecture didn't
change, there's nothing to sync.
