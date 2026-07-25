# Feed Reader — Architecture

A service that polls RSS/Atom feeds, normalizes entries, and serves them over a JSON API.

## Stack

**Backend — Go.** The ingest path fans out thousands of concurrent feed fetches, and goroutines handle that without an
async framework. Python was the familiar choice, but the CPU-bound parse step would have contended on the GIL.

**Storage — Postgres.** Entries need de-duplication by URL and range queries by publish date; both are ordinary
indexed-relational work. Considered and rejected: a document store, which would have meant hand-rolling the uniqueness
constraint.

**Job queue — Amazon SQS.** Fetch jobs are enqueued per feed. SQS was chosen over running our own broker purely to
avoid operating one.

## Code layout

- `cmd/api/` — HTTP server entrypoint
- `cmd/worker/` — fetch worker entrypoint
- `internal/ingest/` — feed fetching, parsing, normalization
- `internal/store/` — Postgres access layer

## Components

### Fetch worker

Owns pulling jobs off the queue, fetching the feed, parsing it, and writing normalized entries. Delivery is
at-least-once: entries are idempotent on URL, so a duplicate fetch costs a wasted request rather than a duplicate row.

### API server

Read-only. Serves entry lists and single entries. No write endpoints, which keeps all mutation confined to the worker
and means the API can be scaled independently without coordination.

## Risks and mitigations

**Slow or hanging feeds stall workers.** Every fetch carries a hard timeout, and a feed that fails repeatedly is backed
off exponentially so one bad publisher can't consume the worker pool.
