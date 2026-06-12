# Core Principles

## Function Design

- Functions should do exactly one thing (single responsibility)
- Prefer many small, focused functions over fewer, larger ones
- Target ~20-30 lines, but prioritize single responsibility over length
- Functions should have minimal side effects
- Limit parameters to 3-4 maximum (use objects/structs for related parameters)
- Each function should operate at a single level of abstraction

## Class Design

- Only include functions in a class if they operate on the class's state
- Prefer standalone functions when possible
- Favor composition over inheritance
- Keep classes small and focused on a single responsibility

## Comments & Documentation

- Avoid comments that describe what the code does (code should be self-documenting)
- Use comments to explain "why" not "what"
- Document design decisions, business rules, and non-obvious behavior
- Remove commented-out code before committing

## Naming

- Use intention-revealing names that clearly convey purpose
- Functions: verb phrases describing action (`calculate_tax`, `send_email`, `process_order`)
- Variables: nouns describing content (`user_count`, `order_total`, `customer_address`)
- Booleans: questions or predicates (`is_valid`, `has_permission`, `can_edit`)
- Classes: nouns describing concept (`OrderProcessor`, `PaymentGateway`, `UserValidator`)
- Avoid abbreviations unless they're widely understood
- Be consistent with naming patterns within the codebase
- Use pronounceable names
- Names should eliminate need for explanatory comments

## Code Complexity

- Limit nesting depth to 3 levels maximum (use early returns/guard clauses)
- Break complex conditionals into well-named functions or variables
- Avoid deeply nested loops (extract to functions)
- Keep cyclomatic complexity low (< 10 per function)

## Code Duplication

- Follow DRY (Don't Repeat Yourself) principle
- Extract repeated logic to shared functions
- Use parameters to handle variations in similar code
- Don't duplicate; refactor to reusable components
