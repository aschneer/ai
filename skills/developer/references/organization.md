# Code Organization

## Imports/Includes

- **All import statements must be at the top of the file** (after module docstring if present)
- **Organize imports in exactly three sections, separated by blank lines:**
  1. Standard library/native packages (e.g., `os`, `sys`, `pathlib` for Python)
  2. Third-party packages (e.g., `pytest`, `requests`, `numpy`)
  3. Local packages from the same repository (e.g., `from src.module import ...`)
- Sort imports alphabetically within each section
- One import per line for clarity
- Remove unused imports
- **Exception:** Imports may be placed elsewhere in the file only if there is a specific functional reason that makes it impossible to place them at the top (e.g., avoiding circular imports). In such cases, document why the import cannot be at the top.

## File and Directory Naming

- Prefer `snake_case` for file and directory names
- Defer to idiomatic conventions when they differ — e.g. follow the existing repo layout, or language norms like Go package naming — and stay consistent within the project

## File Structure

- Keep files focused and small (< 500 lines when possible)
- Split large files into smaller, logical modules
- Group related functionality together
- Order: constants, data structures, helper functions, main functions, entry points
- Related functions should be close to each other

## Libraries and Entry Points

- Put reusable logic in library modules; keep binaries, CLI scripts, and other entry points thin — they should call into libraries or orchestrate pieces of them, not hold core logic
- Name library modules with an `_lib` suffix when no language or repo convention already defines a pattern (e.g. `validate_lib.py`, `compute_lib.py`)
- Entry-point files name the action or tool (`validate.py`, `compute_schedule.py`), not the domain logic they delegate to

## Error Handling

- Handle errors at the appropriate level of abstraction
- Include context with errors (what failed and why)
- Don't swallow errors silently
- Fail fast with clear error messages
- Validate inputs early

## Function Organization

- Order functions by level of abstraction (high-level first, helpers below)
- Keep related functions together
- Extract blocks with comments into named functions
