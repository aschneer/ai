# Best Practices

## Writing New Code

1. **Start Simple**
   - Write the simplest solution that works
   - Don't over-engineer or add unnecessary abstraction
   - YAGNI (You Aren't Gonna Need It) - don't code for imagined future needs

2. **Self-Documenting Code**
   - Code should read like prose
   - Use descriptive names instead of comments
   - Break complex logic into well-named functions
   - Comments should explain "why", not "what"

3. **Early Returns**
   - Use guard clauses to handle edge cases early
   - Reduce nesting by returning early
   - Make the "happy path" clear and unindented

4. **Avoid Premature Optimization**
   - Clarity first, performance second
   - Measure before optimizing
   - Optimize only when profiling shows need

5. **Consistency**
   - Follow existing patterns in the codebase
   - Don't mix styles within same project
   - Use automated formatters to enforce consistency

## Code Readability

- Code is read far more often than it's written
- Optimize for the reader, not the writer
- If you need to explain it, simplify it
- Less code is not always better; clarity is better

## When to Extract a Function

Extract code into a function when:

- It's repeated in multiple places
- A block needs a comment to explain what it does
- The logic can be described with a clear, concise name
- The function is doing multiple things at different abstraction levels
- It improves testability

Don't extract when:

- It makes the code harder to understand
- The function would only be called once and is self-evident
- It creates artificial abstraction with no benefit

## Continuous Improvement

- Regularly update dependencies
- Refactor code to improve clarity and maintainability
- Remove dead code and unused imports
- Keep the codebase clean and consistent
- Learn from code reviews and feedback
- Apply the Boy Scout Rule: leave code better than you found it
