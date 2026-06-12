# Code Review Guidelines

## Check for

- Single responsibility principle (functions doing one thing)
- Meaningful, descriptive names
- No code duplication (DRY)
- Appropriate error handling with context
- Test coverage for new functionality
- Nesting depth (≤ 3 levels)
- Parameter count (≤ 4 per function)
- Complex conditionals (should be simplified)
- Performance implications

## Ask

- Is this the simplest solution?
- Will this be easy to understand in 6 months?
- Are there any edge cases not covered?
- Could any functions be broken down further?
- Are there any code smells (duplication, long functions, deep nesting)?
- Does the code follow existing conventions?
