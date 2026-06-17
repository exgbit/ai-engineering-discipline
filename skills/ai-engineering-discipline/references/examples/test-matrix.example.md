# Test Matrix Example

| Requirement ID | Requirement | Unit Test | Integration Test | Manual / Release Check | Status |
|---|---|---|---|---|---|
| R1 | User can submit an order | `order_service_test.go::TestSubmitOrder` | `order_flow_test.go::TestOrderHappyPath` | Submit order in staging | done |
| R2 | Duplicate submit is idempotent | `order_service_test.go::TestDuplicateSubmit` | `order_flow_test.go::TestRetryDoesNotDuplicate` | Check idempotency logs | done |
| R3 | Unauthorized user cannot submit | `auth_test.go::TestSubmitDenied` |  | Verify 403 response | todo |
