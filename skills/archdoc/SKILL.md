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

## What it is, and what it is not

Two documents get confused with the architecture doc. Naming both is the fastest way to see what this one actually is.

**It is not a requirements doc.** Requirements — what the product must do for the customer — are the PRD's job, decided
before the architecture and independent of it. When a requirement is what motivates a decision, *reference* it rather
than restating it: "batched because the PRD requires sub-second reads (PRD 4.1)". A pointer explains the decision and
stays correct when the requirement is revised; a copy silently goes stale.

**It is not a historical record.** This is the more common failure, so be blunt about it: the architecture doc is not a
timeline, not a changelog, not a log of decisions made, and not a record of the order in which things were built. None
of that is a property of the system — it's a property of the project that produced it.

What it is instead: **a summary of the actual architectural state of the project right now.** A reader should be able
to open it and see how the system is built today, without having to work out which parts have been superseded.

The one thing that isn't "right now": **architecture that is designed but not yet implemented.** Writing the
architecture before the code is the normal case, and the doc legitimately describes the intended design ahead of it.
That's forward-looking, not historical — it never conflicts with the rule above.

Rejected alternatives also aren't history. "Postgres over a document store, because entry de-duplication is a
uniqueness constraint we'd otherwise hand-roll" is *reasoning for the current design*, and it belongs here. What
doesn't belong is the narrative — that a document store was tried first, ran for two months, and got migrated away
from.

Where a project keeps a decision log (commonly a `decisions.md` alongside the architecture doc), that's where the
narrative goes: timestamped entries recording what changed, why, and what trade-offs were weighed. The two are
complements — current state here, the path taken there. When you rewrite a section because the approach changed,
that's usually the moment to suggest a log entry capturing the pivot. If the project has no such log, the history is
simply out of scope; don't smuggle it in here for lack of a better home.

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
yet is fine. Describing *when* it will be built is not.)

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
- **Short overview at the top.** A line or two on what the system is and its overall shape.
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

## Editing: rewrite in place, never stack

This is what "a summary of the current state" means in practice when you're editing rather than authoring.

When a decision is superseded, **rewrite the section** so it describes the new design and its reasoning. Do not append
a new paragraph beneath the old one, do not leave the previous approach in place with a note that it changed, and do
not add a "Previously…" or "Update:" subsection. Each of those turns one clear statement into two competing ones, and
the reader has no way to tell which is live — which is exactly the failure that makes a doc untrustworthy.

The reasoning that motivated the change isn't lost by rewriting; it goes in the project's decision log, where it stays
findable without clouding the description of the present.

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
contradicts the Stack section of the architecture doc. Want me to update it?" Then let them decide. Flag and ask; the
user authorizes the edit.

Where the project keeps a decision log, a change of approach mid-build usually wants both: the architecture section
rewritten to describe the new design, and a log entry recording why the approach changed. Offer both rather than
silently picking one.

Small, purely local changes don't need flagging. The bar is the same as for inclusion: if the architecture didn't
change, there's nothing to sync.
