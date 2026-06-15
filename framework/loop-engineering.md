# Loop Engineering

## 1. Core Idea

Prompt engineering focuses on writing better instructions for an agent. Loop engineering focuses on designing the system that repeatedly prompts, checks, retries, stops, and learns around the agent.

In this framework:

- `Spec` defines what the loop is allowed to do.
- `Verify` defines how the loop proves progress.
- `Memory` defines what the loop can reuse.
- `Loop` defines how the agent is orchestrated over time.

The unit of design moves from a single prompt to a controlled execution loop.

## 2. Loop Anatomy

Every production-grade AI coding loop should define:

| Part | Question |
|---|---|
| Goal | What outcome should the loop produce? |
| Scope | Which files, services, commands, and environments can it touch? |
| State | What does the loop know at each step? |
| Policy | What actions are allowed, forbidden, or require approval? |
| Verify Gate | What evidence allows the loop to continue? |
| Exit Condition | When must the loop stop? |
| Retry Strategy | What can be retried, how often, and with what changes? |
| Memory Update | What should be persisted after completion or failure? |
| Budget | Token, wall-time, cost, and failure-rate limits. |

## 3. Reference Loop

```text
Backlog Item
  -> Load Spec
  -> Load Memory
  -> Plan
  -> Implement Small Step
  -> Run Verify Gate
      -> pass: continue or exit
      -> fail: diagnose and retry within budget
      -> unsafe: stop and request human review
  -> Update Memory
  -> Produce PR Evidence
```

## 4. Loop Levels

### L0: Manual Prompting

The engineer manually prompts the agent. Useful for exploration, but not reliable for repeated production work.

### L1: Checklist Loop

The engineer follows a repeatable checklist: read spec, implement, test, update memory. This is the minimum viable discipline.

### L2: Scripted Loop

Commands, tests, linters, and review checks are wired into a repeatable script or agent workflow. Failures are explicit.

### L3: Governed Agent Loop

The agent can run multi-step work, but only inside defined scope, policies, budgets, and approval gates.

### L4: Organizational Loop Platform

Teams standardize reusable loops for common work: bug fix, feature slice, migration, refactor, dependency upgrade, incident follow-up.

## 5. Safety Rules

- A loop must be stateless with respect to authority: it cannot grant itself new permissions.
- A loop must be stateful with respect to evidence: every continuation needs a reason.
- A loop must have dual exit conditions: success criteria and failure budget.
- A loop must never treat generated explanations as verification.
- A loop touching production data or infrastructure must require explicit human approval.

## 6. Loop SLA

For vendor evaluation or internal platform design, define a Loop SLA:

| Metric | Description |
|---|---|
| token_budget | Maximum tokens per loop run |
| wall_time_budget | Maximum elapsed time |
| retry_budget | Maximum retries before escalation |
| failure_rate | Failed loops divided by total loops |
| verification_rate | Loops with attached evidence |
| human_escalation_rate | Loops requiring review or approval |
| memory_write_rate | Loops that update durable project memory |

The goal is not full autonomy. The goal is controlled, measurable autonomy.
