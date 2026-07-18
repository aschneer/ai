---
name: prd
description: >-
  Principles and rules for writing and maintaining a Product Requirements Document (PRD). Load this whenever the user
  asks to create, draft, write, update, revise, review, or add to a PRD, or mentions "product requirements", "requirements
  doc", "requirements document", or "prd.md" — even casually ("let's spec this out", "turn this into requirements",
  "add a requirement for X"). Also load it before you would otherwise start writing a requirements list or product spec,
  so the document follows PRD conventions from the first line. Do NOT use this skill for design docs, architecture docs,
  data models, implementation plans, or code — those are derived from the PRD, not part of it.
---

# Writing a PRD

A PRD (Product Requirements Document) is a concise, numbered list of requirements. Each requirement describes a product
feature or capability — **what we want for the customer** — not how to implement it.

This skill loads the rules for producing a good PRD. It does **not** launch an interview or a fixed workflow. When the
user asks to create or update a PRD, do that task normally, but follow the principles below. Only run a structured
requirement-gathering exercise if the user asks for one.

## What belongs in a PRD (and what doesn't)

The dividing line is **control**, not technical depth. Put something in the PRD when the designer explicitly wants to
**require and control** that aspect of the product. Leave it out when you're willing to let the implementer decide the
best approach.

This means a PRD *can* contain a technical or even architectural requirement — but only when the designer deliberately
wants to lock that choice down (e.g. "must use tree-sitter for parsing" because they want language-aware parsing
guaranteed). Absent that intent, keep implementation and architecture out. State each requirement from the customer's
perspective, at the altitude of *what the product does*, and go no lower than the requirement itself demands.

Litmus test for a line: **Is this something we're choosing to require, or an implementation detail that snuck in?** If
it reads like a design decision the implementer should own, it belongs in a design doc, not here.

When you're unsure whether a given requirement belongs in the PRD or somewhere else, **ask the user** rather than
guessing. That judgment call is theirs.

## Requirements are requirements, not implementations

Write each item as a statement of what the product must do, observable from outside. Good requirements describe
capabilities, guarantees, inputs, outputs, and constraints. They avoid prescribing the mechanism unless the mechanism
*is* the requirement.

**Example — leaking implementation:**
> The skill must loop over every file, call `tree.walk()`, and append each node to an array in `index.json`.

**Example — stated as a requirement:**
> The skill must extract every function, method, and class in the target directory, using a language-aware parser.

The second says what's required (complete symbol extraction, language-aware) and controls the one aspect the designer
cares about (language-awareness), without dictating the loop, the data structure, or the file layout beyond what's
actually required.

## Structure

- **Hierarchical numbering.** Requirements are numbered in a nested structure: top-level sections (`1`, `2`, `3`), then
  requirements (`1.1`, `1.2`), then sub-requirements (`1.1.1`) as needed. The numbering is the addressing system —
  design docs, tickets, and reviews cite requirements by number, so numbers must be stable and unambiguous.
- **One requirement per line, separated by a blank line.** Write each numbered requirement on its own line, and
  separate every requirement from the next with a blank line, so each renders as its own line in Markdown. Markdown
  collapses single newlines: consecutive requirement lines with no blank line between them render as one run-on
  paragraph. Do **not** rely on the `N.M` numbering to produce line breaks — `5.1.` is not a valid Markdown
  ordered-list marker (only `1.`/`2.`-style integer markers are), so it yields no automatic line breaks. The blank
  line is what forces each requirement onto its own rendered line.
- **One requirement per number — atomicity.** Each numbered item must state exactly one requirement. The test: could you
  drop or change this claim without affecting any other claim in the line? If a single line contains two things that
  could be changed, removed, or satisfied independently, it's actually two requirements wearing one number, and it must
  be split. For example, "The tool is a command-line program started with a single command that runs until stopped by the
  user" is three independent requirements — the CLI form factor, the single-command invocation, and the run-until-stopped
  lifecycle — each of which could change without touching the others; it should be three numbered items. This matters
  because the number is the addressing system: a compound line can't be cited, revised, or deleted as a unit without
  disturbing unrelated requirements bundled beside it. Split independent claims into sibling requirements; use a
  sub-requirement (`1.1.1` under `1.1`) only when the child genuinely *elaborates or narrows* its parent, not when the two
  are merely adjacent peers.
- **Logical sections.** Group requirements into sections that reflect the natural structure of the product (e.g.
  Inputs, a major capability, Reporting, Output). Order sections so the document reads top to bottom as a coherent
  description of the product.
- **A short Overview** at the top: one or two sentences on what the product is.
- **Concise and structured — not prose.** A PRD reads as a scannable, numbered list, not paragraphs of narrative. Each
  requirement is one short, self-contained statement: capture every detail that's actually necessary, and nothing beyond
  that. If a requirement is running long, it's usually either carrying implementation detail that doesn't belong or
  bundling several independent claims that should be split (see atomicity above). No filler, no restating the same
  requirement twice.

## The PRD must capture the whole product — the reconstruction test

The relationship is one-directional: **the PRD is a superset of what's built.** Every feature the product has must map to
a PRD requirement, but the PRD may also contain requirements not yet implemented.

This matters because of how a PRD is normally used: it's typically written in full *before* any code, then implemented in
stages. Early on the PRD deliberately describes far more than exists yet — that's the plan, not drift. So do **not**
delete requirements just to make the PRD match current progress, and do not add requirements only as you build them.

The rule runs the other way: **the product must never have a feature, capability, or behavior that isn't captured as a
PRD requirement.** Unimplemented requirements are fine; unrequirement-ed features are not.

The test to hold in mind: **take the PRD alone into a fresh, empty git repository, hand it to an agent, and it should be
able to rebuild the product with all the same capabilities and features** (once fully implemented). Implementation
details may differ, but no functionality should be missing. If a feature exists in the product but not in the PRD, the
PRD is incomplete and must be reconciled. (A requirement in the PRD with no matching feature yet is not a defect — it's
just not built yet.)

## Notice drift and flag it — proactively

The dangerous phase is *after* the initial PRD and MVP, during ongoing development and maintenance. Requirements drift
quietly here: while implementing, the user changes how a feature works, adds a new capability, or drops one — and the PRD
is not touched, because the change is happening in code, not in the doc.

Because the PRD is the source of truth downstream work relies on, this silent drift is exactly what breaks the
reconstruction test. So watch for it as you work, not only when editing the PRD. When the user makes a design change,
requests a new feature, or alters existing behavior on the fly, ask yourself: *is this captured in the PRD?* Two cases
worth catching:

- **New functionality** the PRD doesn't mention yet.
- **Changed behavior** that now contradicts an existing PRD requirement.

When you notice either, **proactively tell the user** — something like "This changes how X works, which contradicts
requirement 3.2 / isn't in the PRD yet. Want to update the PRD so it stays the source of truth?" Then let them decide.

This does not conflict with the lock-down rule below: you are *flagging* drift and *asking*, never silently patching the
PRD. The user still explicitly authorizes every change to the document. Your job is to make sure drift never goes
unnoticed, so the PRD keeps matching the product.

## Deferred / out-of-scope requirements

If a requirement is deliberately out of scope for now but worth preserving, don't delete it — move it to a clearly
labeled "Deferred — Implement Later" section at the bottom, keeping its full text and a stable identifier. This records
the decision so it isn't rediscovered or relitigated later.

## The PRD is not a living document

This is the most important operating rule, and it changes how you edit.

A PRD is created through careful collaboration with the user and then **locked down**. Every other artifact —
architecture docs, data models, design docs, code — is derived *from* it. Because so much hangs off the PRD, it is not
edited casually.

Do **not** update the PRD unless one of these is true:

1. The user **explicitly** asks for the update, or
2. You hit a contradiction or gap in the PRD that suggests it needs revision — in which case you **report it to the
   user and let them decide**, rather than fixing it yourself.

Never update the PRD unilaterally during normal implementation work. If you're building from the PRD and something
seems off, surface it; don't silently patch the requirements to match what you wrote. The whole value of the lock-down
is that downstream work can trust the PRD is intentional.

When the user *does* ask for an update, make the requested change surgically and preserve the existing numbering where
possible, since other artifacts reference those numbers.
