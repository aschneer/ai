# Edge-Case Taxonomy

Walk this checklist explicitly for every function/method analyzed. For each category, ask: *does an instance of this category exist for this function's inputs?* If yes, it is a cell in the behavior matrix. Do not free-associate — go through the list in order.

## 1. Boundary values
- 0, 1, -1
- Type-max, type-min (e.g., `INT_MAX`, `INT_MIN`)
- Off-by-one around any explicit threshold (if `x >= 18`, test 17, 18, 19)
- Inclusive/exclusive boundary distinctions

## 2. Empty and degenerate inputs
- Empty string `""`
- Empty collection `[]`, `{}`, `set()`, `tuple()`
- `None` / `null` / `nil` / `undefined`
- Single-element collection
- Single-character string
- Zero-iteration loops (empty input causing the loop body to never run)

## 3. Type variants (dynamic languages)
- Wrong primitive type (`int` where `str` expected, `str` where `bytes` expected)
- Subclasses (does it work? should it?)
- Duck-typed equivalents (a `dict`-like vs a real `dict`)
- `None` where a value is expected

## 4. Invalid / out-of-domain inputs
- Out-of-range numbers (negative when only positive valid, etc.)
- Malformed structures (unclosed brackets in a parser, broken JSON, bad UTF-8)
- Values violating documented preconditions
- Sentinel-value collisions (does `-1` mean "not found" *and* a real value?)

## 5. Boundary structural cases
- Very large inputs (10⁶+ elements, multi-MB strings)
- Very small (length 1, length 2 — often where pairwise logic breaks)
- Deeply nested structures (recursion depth limits)
- Self-referential / cyclic structures (infinite loop risk)

## 6. Numerical edge cases
- `NaN`
- `+Inf`, `-Inf`
- `-0.0` vs `+0.0`
- Floating-point precision (`0.1 + 0.2 != 0.3`)
- Integer overflow / underflow
- Division by zero
- Very small floats near zero (denormals)
- Mixed-sign arithmetic

## 7. String edge cases
- Unicode (multi-byte, combining characters, RTL, emoji)
- Whitespace-only
- Leading/trailing whitespace (does the function strip? should it?)
- Very long strings
- Escape characters, control characters
- Different encodings (UTF-8, UTF-16, latin-1)
- Mixed line endings (`\n`, `\r\n`, `\r`)
- Null bytes embedded in strings

## 8. Collection edge cases
- Duplicates (does the function dedupe? should it?)
- Ordering dependencies (does input order matter?)
- Mutation during iteration (modifying a collection while iterating it)
- Heterogeneous element types (in dynamic langs)
- Sparse collections (e.g., dict with non-contiguous integer keys)
- Already-sorted vs reverse-sorted vs random (for sort/search functions)

## 9. Concurrency (where applicable)
- Reentrance — calling the function from within itself
- Race conditions — two threads/coroutines calling it simultaneously
- Lock ordering — does it acquire locks in a consistent order?
- Interrupt safety (signal handlers, async cancellation)

## 10. State and side effects
- Idempotency — does calling twice produce the same result as calling once?
- Ordering — does `f(a); f(b)` behave the same as `f(b); f(a)`?
- Failure mid-operation — partial state left behind on exception
- Resource cleanup — files/sockets/locks released on every exit path
- Side effects in the "happy path" vs error path

## 11. Error paths
- **Every `raise` / `throw` / error return must have a test.**
- Each distinct exception type is a separate cell
- Each distinct error message/code is a separate cell if the message is part of the contract

## 12. Time and ordering (if relevant)
- Timezone handling (naive vs aware datetimes; DST boundaries)
- Leap years (Feb 29)
- Leap seconds
- Daylight-saving transitions
- Year 2038 / Unix epoch boundaries
- Past dates, future dates, the unix epoch itself

## 13. I/O and external state (if relevant)
- File does not exist
- File exists but is empty
- File exists but is unreadable (permissions)
- Network unreachable
- Partial reads/writes
- Encoding/decoding failures on disk content
- Concurrent file modification during operation

## 14. Class-specific dimensions (for methods)
- Method called in each valid state of the object (state machine cells)
- Method called in invalid state (e.g., `send()` on a closed connection)
- Method called before construction completes (in languages where this is possible)
- Method called after destruction/close
- Inheritance: subclass overrides interacting with base behavior

## Application

For each function, produce a list like:

```
parse_date(s: str) -> date:
  ✓ Boundary: empty string ""             → ValueError
  ✓ Empty: None                           → TypeError
  ✓ Invalid: malformed "not-a-date"       → ValueError
  ✓ String: leading/trailing whitespace   → unspecified (clarify)
  ✓ Time: Feb 29 non-leap year            → ValueError
  ✓ Time: Feb 29 leap year                → date(YYYY, 2, 29)
  ✓ Time: DST transition date             → date(YYYY, M, D)
  ✓ Error path: ValueError                → covered separately above
```

Only include cells that actually apply to this function's input domain. A function taking only `int` does not need string edge cases. A pure function does not need state/side-effect cells.
