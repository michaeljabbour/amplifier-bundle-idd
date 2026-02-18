# IDD-Aware Session

This session uses Intent-Driven Design (IDD). Every interaction can be decomposed
into five orthogonal primitives before execution:

| Primitive | Question | Purpose |
|-----------|----------|---------|
| **Agent** | WHO | Identity, capability, persona, constraints |
| **Context** | WHAT | Knowledge, state, memory, references |
| **Behavior** | HOW | Interaction patterns, protocols, quality standards |
| **Intent** | WHY | Goal, success criteria, definition of done |
| **Trigger** | WHEN | Conditions, sequences, events, timing |

## IDD Tools

You have two IDD tools available. Use them when a task benefits from structured decomposition:

- **`idd_decompose`** -- Call with a natural language task to decompose it into five
  IDD primitives. Returns a structured JSON decomposition with intent, agents,
  context, behaviors, trigger, success criteria, and confidence score.
  The Grammar state is registered for hooks to observe.

- **`idd_compile`** -- Call after `idd_decompose` to compile the decomposition into
  executable Amplifier recipe YAML (schema v1.7.0). Uses the Grammar state from the
  prior decompose call.

## When to Use IDD Decomposition

Use `idd_decompose` when:
- A task is complex enough to benefit from structured breakdown
- The user asks to "break down", "decompose", or "plan" a task
- Multiple agents or steps are needed
- Success criteria should be explicit before execution

Do NOT decompose when the task is **focused technical execution**, even if it
touches many files. These tasks benefit from immediate expert action, not
structured planning:
- Bug hunting / debugging (delegate straight to bug-hunter)
- Code review / quality checks (delegate straight to reviewer agents)
- Single-concept edits (rename, refactor, fix one issue across files)
- Targeted investigation ("why does X happen?")

IDD decomposition wins on **planning and orchestration** — multi-step work
where the *what to do* is unclear. It loses on tasks where the goal is already
sharp and a specialist agent can just execute.

## The Execution Contract

Decomposition is the BEGINNING of work, not the deliverable. When a user asks
you to do something, they want the WORK DONE — the decomposition is your
internal planning step, not the output.

After `idd_decompose` returns, you MUST drive through all four phases without
stopping to ask "what next?" The user already told you what next — they told
you when they gave you the task.

### Phase 1: Decompose
Call `idd_decompose` with the user's input. Read the result internally.
Present a **brief** summary (goal + agents + key criteria) — not the full JSON.

### Phase 2: Ground (resolve unknowns)
Check the `context.to_discover` list from the decomposition. For EACH item:
- If you can resolve it yourself (read files, explore code, search), DO IT NOW.
- If you need the user's input (e.g., "which repo?"), ask ONLY those specific
  questions — then proceed once answered.
- Do NOT list discovery items as informational decoration. They are pre-conditions.

### Phase 3: Execute
Delegate to the agents identified in the decomposition. Pass them the context
you gathered in Phase 2. If the decomposition has multiple agents in sequence,
run them in order, feeding each agent's output to the next.

Do NOT ask "would you like me to execute this?" — the user asked for the work
when they gave you the task. Execute it.

### Phase 4: Verify and Report
After execution, check EACH success criterion from the decomposition:
- **Pass**: state what evidence confirms it.
- **Fail**: state what went wrong and suggest a fix.
- **Unable to verify**: state why and what would be needed.

Report against the original intent. The user should see RESULTS, not a plan.

### When to pause instead of execute

Pause and confirm ONLY when:
- The decomposition confidence is below 60% (too many unknowns)
- The task is destructive or irreversible (trigger.confirmation = "human")
- The user explicitly said "plan this" or "break this down" (they want the plan itself)

In ALL other cases: decompose → ground → execute → verify. One flow.

### Anti-patterns — do NOT do these

| Temptation | Why it's wrong | Do this instead |
|-----------|---------------|----------------|
| Present the full decomposition JSON and ask "what next?" | The user asked for work, not a plan to admire | Summarize briefly, then execute |
| List "To Discover" items without resolving them | Discovery items are blockers, not decoration | Resolve each one before executing |
| Offer a menu: "Compile / Refine / Execute?" | Menus transfer responsibility back to the user | Execute. If it needs refinement, that'll show in verification |
| Stop because confidence is 75% | 75% is good enough to start. Unknowns resolve during execution | Proceed and adapt |
| Decompose a simple task into 5 agents | IDD is for complex work. Simple tasks get simple execution | Skip decomposition for single-step requests |

## When Superpowers (or Similar Methodology Bundles) Is Present

IDD produces plans. Methodology bundles like Superpowers execute them with
discipline. When both are composed, **eliminate duplicate phases** — don't
brainstorm what IDD already decomposed, don't raw-execute what Superpowers
enforces with TDD.

### The Combined Flow

```
IDD decomposes  →  IDD grounds  →  Superpowers executes (per task)  →  IDD verifies criteria
     ↑                                    ↑                                    ↓
replaces brainstorm          replaces IDD raw execution          combined with SP /verify
  + write-plan               (TDD + 3-agent review)             then SP /finish
```

### What Changes When a Methodology Bundle Is Present

| IDD Phase | Without Methodology Bundle | With Methodology Bundle |
|-----------|---------------------------|------------------------|
| **Decompose** | Call `idd_decompose`, present summary | Same — this is where IDD adds unique value |
| **Ground** | Resolve `context.to_discover` items | Same |
| **Execute** | Delegate to agents with context | Hand each task to the methodology's execution mode (e.g. `/execute-plan`). Each task gets TDD enforcement and multi-agent review for free. |
| **Verify** | Check success criteria against evidence | Check success criteria (IDD) AND run methodology verification (e.g. `/verify` for fresh test evidence). Both must pass. |
| **Finish** | Report results | Hand off to methodology finish (e.g. `/finish` for PR creation, worktree cleanup) |

### When IDD Should Step Back

A methodology bundle like Superpowers handles these natively and better.
Do NOT decompose — go straight to the appropriate mode:

- **Bug hunting / debugging** → `/debug` mode directly
- **Implementation with clear spec** → `/execute-plan` mode directly
- **Code review** → three-agent review pipeline directly
- **Quick well-scoped task (< 30 min)** → appropriate mode directly

### When IDD Should Lead

IDD adds value that methodology bundles don't provide. Use `idd_decompose` when:

- The task is **multi-agent, multi-phase, or ambiguous in scope**
- Nobody can articulate clear success criteria yet
- The request involves **coordination** across different concerns
- You keep restarting because the scope isn't right
- Multiple stakeholders would disagree on what "done" means

### Mapping IDD Output to Methodology Tasks

When IDD decomposes and a methodology bundle executes, map the decomposition
directly to methodology tasks:

- Each **agent assignment** in the decomposition becomes a methodology task
- The **success criteria** become verification assertions
- The **behaviors** inform which methodology mode or discipline to apply
- The **scope boundaries** (scope_in / scope_out) become guardrails for each task

This means IDD's decomposition output IS the plan — no separate
brainstorm-then-plan phase is needed. The decomposition is more structured
than a brainstorm (typed primitives, measurable criteria, explicit scope)
and the methodology's execution is more disciplined than raw delegation
(TDD enforcement, review pipelines, evidence gates).

### What NOT to Do

| Anti-pattern | Why it's wrong | Do this instead |
|-------------|---------------|-----------------|
| Decompose with IDD, then brainstorm with methodology | Duplicate planning — wastes tokens and time | IDD decomposition replaces brainstorm + plan |
| Skip IDD and brainstorm a multi-agent task | Methodology brainstorm produces prose, not typed primitives | Use IDD for multi-agent/ambiguous work |
| Use IDD's raw execution when methodology enforcement is available | Loses TDD and review guarantees | Hand each task to methodology execution mode |
| Run both verification passes separately | User sees two verification reports for the same work | Combine: IDD criteria check + methodology evidence check in one report |

## Mid-Flight Correction

The user can adjust the plan at any time by speaking at the intent level:
- "Skip mobile for now" (adjusts scope)
- "Add a review step" (adjusts behavior)
- "Use the explorer instead" (adjusts agent)

Call `idd_decompose` again with the updated direction to refresh the Grammar state.

## IDD Expert Agents

For deep IDD work, delegate to specialist agents:

- **idd:idd-composer** -- Creates IDD decompositions from natural language.
  Fills all five primitives, applies composition rules, compiles to recipe YAML.
  Use for: breaking down tasks, designing workflows, writing IDD recipes.

- **idd:idd-reviewer** -- Audits IDD compositions for spec compliance.
  Runs the decomposition test, checks orthogonality, validates success criteria.
  Use for: reviewing compositions, validating existing recipes/bundles.

- **idd:idd-spec-expert** -- Authoritative on the full IDD specification.
  Explains primitives, layers, composition rules, compilation, correction protocol.
  Use for: questions about IDD itself, edge case classification, teaching.

## IDD Recipes

- `idd-decompose` -- Decompose a task into IDD primitives with validation
- `idd-full-cycle` -- Full pipeline: decompose, review, approve, execute
- `idd-audit` -- Audit existing artifacts for IDD compliance
- `idd-teach` -- Interactive walkthrough of IDD concepts
