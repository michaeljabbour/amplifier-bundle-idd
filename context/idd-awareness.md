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
