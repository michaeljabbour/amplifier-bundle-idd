# IDD-Aware Session

This session uses Intent-Driven Design (IDD). Every interaction is decomposed
into five orthogonal primitives before execution:

| Primitive | Question | Purpose |
|-----------|----------|---------|
| **Agent** | WHO | Identity, capability, persona, constraints |
| **Context** | WHAT | Knowledge, state, memory, references |
| **Behavior** | HOW | Interaction patterns, protocols, quality standards |
| **Intent** | WHY | Goal, success criteria, definition of done |
| **Trigger** | WHEN | Conditions, sequences, events, timing |

## How It Works

1. **Layer 1 (Voice):** You express intent in natural language.
2. **Layer 2 (Grammar):** The system decomposes your input into five primitives
   and presents a structured plan for confirmation.
3. **Layer 3 (Machinery):** On approval, agents execute the plan. Progress is
   reported against your original intent and success criteria, not internal state.

## Mid-Flight Correction

You can adjust the plan at any time by speaking at the intent level:
- "Skip mobile for now" (adjusts scope)
- "Add a review step" (adjusts behavior)
- "Use the explorer instead" (adjusts agent)

The system updates the Grammar and resumes without restarting.

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
