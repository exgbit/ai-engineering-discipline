# Loop Template

## Loop Name

Example: `feature-slice-loop`, `bugfix-loop`, `dependency-upgrade-loop`

## Goal

What outcome should this loop produce?

## Inputs

- Spec:
- Issue / backlog item:
- Relevant memory files:
- Allowed repositories / directories:

## Scope

Allowed:

- 

Forbidden:

- 

Requires approval:

- 

## State Model

| State | Description | Next States |
|---|---|---|
| load_context | Read spec and memory | plan, stop |
| plan | Produce small-step plan | implement, stop |
| implement | Change code or docs | verify, stop |
| verify | Run checks and collect evidence | implement, escalate, done |
| escalate | Ask for human review | implement, stop |
| done | Produce PR evidence and memory update |  |

## Verify Gates

- [ ] 

## Exit Conditions

Success:

- 

Failure:

- 

## Retry Policy

- Max retries:
- What may change between retries:
- What requires escalation:

## Budgets

- Token budget:
- Wall-time budget:
- Cost budget:
- Failure budget:

## Memory Writes

What should be written after completion?

- [ ] project rule
- [ ] pitfall
- [ ] module boundary
- [ ] reusable prompt / loop lesson
