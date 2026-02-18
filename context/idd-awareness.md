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

You do NOT need to decompose simple, single-step requests.

## The Flow

1. **Layer 1 (Voice):** User expresses intent in natural language.
2. **You call `idd_decompose`** with the user's input.
3. **Present the plan** to the user. A 15-second confirmation window opens
   automatically -- the user can adjust direction or let it auto-proceed.
4. **Execute** by delegating to agents or running the compiled recipe.
5. **Report completion** against the original intent and success criteria.

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
