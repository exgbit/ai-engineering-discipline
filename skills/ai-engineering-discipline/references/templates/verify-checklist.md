# Verify Checklist

## P0: Must Pass

- [ ] Code compiles
- [ ] Unit tests pass
- [ ] Lint passes
- [ ] Typecheck passes
- [ ] No secrets or credentials committed
- [ ] Critical path regression covered
- [ ] Error handling reviewed
- [ ] Rollback path documented

## P1: Required for Review

- [ ] Spec or issue linked
- [ ] Acceptance criteria mapped to tests
- [ ] PR explains AI usage
- [ ] Risk and impact documented
- [ ] Config / migration changes documented
- [ ] Monitoring or logging impact considered

## P2: Recommended

- [ ] Integration tests
- [ ] Performance benchmark
- [ ] Security scan
- [ ] Manual validation screenshots or logs
- [ ] Release checklist

## Anti-Rationalization Questions

- What evidence proves this works?
- What edge case would break this?
- What did AI assume that may be false?
- What test would fail if the implementation is wrong?
- What is the rollback path?
