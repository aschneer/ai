---
name: developer
description: >-
  Apply clean-code standards when writing, refactoring, or reviewing code in any
  language. Use whenever the user asks you to write new code, improve readability,
  refactor, do a code review, fix code smells, name things better, reduce complexity,
  organize imports, or follow team coding conventions — even if they do not say "style
  guide". Also use when editing Python, C++, or Go and language-specific conventions
  matter. Triggers: "clean code", "code review", "refactor", "naming", "code smells",
  "DRY", "single responsibility", "reduce nesting", "organize imports", "style guide",
  "best practices", "readable code", "maintainable code".
---

# Developer

Read `references/index.md`, then load only the reference files it points to for the task. Do not load every file by default.

**Re-evaluate as the thread evolves.** The right references depend on what you're doing *now*, not what you loaded at the start. When the work shifts — e.g. from writing new code to refactoring a smell, adding tests, or doing a review — go back to `references/index.md` and load any additional files that newly apply. You don't need to announce each load unless the user asked; just read and apply them.

Standards in `references/` are defaults. When the target codebase already has an established pattern, match the codebase first and note any intentional deviation.

## When NOT to use

- User explicitly asks to ignore style or match a different style guide for this task.
- Generated or vendored third-party code that should not be reformatted.
- One-line or trivial edits where raising style issues would be noise — still follow the relevant references for lines you touch.

## Output expectations

- **Writing code**: produce conforming code; do not narrate every rule unless the user asked for explanation.
- **Reviewing**: lead with findings grouped by severity; cite file/line references and suggest concrete rewrites.
- **Refactoring**: describe what smell you fixed and why the new shape is clearer.
