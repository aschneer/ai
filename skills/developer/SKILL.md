---
name: developer
description: >-
  Clean-code standards for writing, refactoring, and reviewing code in any language (Python, C++, Go, TypeScript,
  and others). Load this proactively whenever a task involves producing or reworking a non-trivial amount of code —
  roughly multiple functions, or at least a file's worth — such as implementing a feature, writing a module or class,
  adding a component, refactoring existing code, or reviewing a diff or PR. Trigger even when the user doesn't name a
  style guide or say "clean code": if they ask you to build, implement, add, rewrite, or refactor something of that
  size, load this first so the code conforms from the start. Skip it only for genuinely trivial work — a one-to-few-line
  script, a tiny snippet, a config tweak, or a single throwaway command — where applying full standards would be noise.
  Also skip when the user explicitly asks to ignore style or match a different guide, or for generated/vendored code.
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
