# Project Memory Example

## Project Rules

- All payment-related changes require integration tests and rollback notes.
- API handlers must not call external services directly; use service-layer ports.
- Any new background job must define idempotency behavior.

## Module Map

| Module | Owner | Boundary |
|---|---|---|
| api | Platform Team | Request validation, auth, response mapping |
| service | Domain Team | Business orchestration |
| repository | Data Team | Persistence and transaction boundaries |
| worker | Platform Team | Async jobs and retry behavior |

## Pitfalls

### 2026-06-01: Missing idempotency in retry job

Retry logic created duplicate downstream requests. Future worker changes must document idempotency keys and duplicate handling in the spec.

### 2026-06-08: AI generated direct DB access in handler

The implementation bypassed service-layer boundaries. Add boundary checks to review and mention this rule in `AGENTS.md`.
