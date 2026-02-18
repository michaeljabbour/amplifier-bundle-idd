---
name: idd-review
description: >
  Per-primitive audit checklists for Intent, Agent, Context, Behavior, and
  Trigger. Cross-primitive orthogonality checks, layer separation validation,
  verdict rubric (PASS/CONDITIONAL/FAIL). Use when reviewing or auditing IDD
  compositions. See references/anti-patterns.md for the 11 common anti-patterns
  catalog.
version: 1.0.0
metadata:
  category: idd
---

> **Companion file:** See [references/anti-patterns.md](references/anti-patterns.md) for the catalog of 11 common IDD anti-patterns.

# IDD Composition Review Checklist

## Purpose

This checklist is a structured protocol for auditing IDD compositions. Use it after decomposition and before execution. It ensures every composition meets IDD quality standards: correct classification, full orthogonality, proper layer separation, and compositional completeness.

A composition that passes this checklist can be executed with confidence. One that fails should be corrected at the Grammar layer before any agent touches a tool.

---

## Per-Primitive Checklist

### Intent Audit (WHY)

The Intent primitive is the foundation of the entire composition. If the goal is unclear, every downstream decision inherits that ambiguity.

| # | Check | Pass? |
|---|-------|-------|
| I-1 | Is the goal statement clear and unambiguous? | |
| I-2 | Are success criteria measurable (not vague)? | |
| I-3 | Is `scope_in` explicitly listed? | |
| I-4 | Is `scope_out` explicitly listed (prevents creep)? | |
| I-5 | Are values stated as priority orderings (X over Y)? | |
| I-6 | Does the intent avoid prescribing method (no HOW leakage)? | |

A good Intent says "reduce onboarding drop-off from 40% to under 20%" -- not "rewrite the signup form in React." The moment an Intent names a technology, a tool, or a sequence of steps, it has leaked into Behavior or Agent territory.

### Agent Audit (WHO)

Agents are identities with capabilities and constraints. They are not behavior descriptions wearing a name tag.

| # | Check | Pass? |
|---|-------|-------|
| A-1 | Is each agent defined by identity/role, not by behavior? | |
| A-2 | Are capabilities listed (what they CAN do)? | |
| A-3 | Are constraints listed (what they MUST NOT do)? | |
| A-4 | Are agents loaded by reference, not redefined inline? | |
| A-5 | Is no agent a "god agent" doing everything? | |

An agent named "Explorer" with a capability of "codebase navigation" is correct. An agent described as "the agent that carefully and thoroughly explores the codebase, taking notes and summarizing findings" has absorbed Behavior into its identity.

### Context Audit (WHAT)

Context is the knowledge agents need to do their work. It is not a dumping ground for goals, instructions, or behavioral norms.

| # | Check | Pass? |
|---|-------|-------|
| C-1 | Is all context explicitly listed (no assumptions)? | |
| C-2 | Is each item classified (auto-detected, provided, discovered)? | |
| C-3 | Is context scope defined (which agents see what)? | |
| C-4 | Does context contain only knowledge, not actions or goals? | |
| C-5 | Are context flow dependencies between agents declared? | |

If an agent needs access to the existing codebase, that must appear in Context -- not assumed because "obviously the code reviewer needs to see code." Implicit context breaks composition portability.

### Behavior Audit (HOW)

Behaviors are reusable interaction patterns. They attach to agents at composition time, not at definition time. A behavior that can only apply to one agent is likely a misclassified agent trait.

| # | Check | Pass? |
|---|-------|-------|
| B-1 | Are behaviors expressed as patterns/protocols, not as agent traits? | |
| B-2 | Can each behavior apply to more than one agent? | |
| B-3 | Are behaviors declared once, not duplicated per agent? | |
| B-4 | Do behaviors avoid prescribing goals (no WHY leakage)? | |
| B-5 | Are conflicting behaviors resolved by specificity? | |

"Review-before-ship" is a behavior: any agent can follow it. "The reviewer is careful" is an agent trait masquerading as a behavior -- it cannot be detached and applied elsewhere.

### Trigger Audit (WHEN)

Every composition must have an explicit activation condition. Compositions without triggers default to "just do it now," which makes timing invisible and removes the confirmation gate.

| # | Check | Pass? |
|---|-------|-------|
| T-1 | Is at least one trigger defined? | |
| T-2 | Is activation condition explicit? | |
| T-3 | Are pre-conditions listed? | |
| T-4 | Is confirmation mode set (auto/human/none)? | |
| T-5 | Is parallelism vs sequencing explicitly stated? | |
| T-6 | Are dependencies declared (not assumed from ordering)? | |

Even an immediate, manual trigger should be declared: `activation: on-demand, confirmation: human`. This makes the composition auditable and self-documenting.

---

## Cross-Primitive Checks

### Orthogonality Check

Run the 10-pair decomposition test. For each pair of primitives, confirm you can change one without changing the other. Any entanglement indicates primitive conflation.

| Pair | Can change independently? | Notes |
|------|--------------------------|-------|
| Intent / Agent | | |
| Intent / Context | | |
| Intent / Behavior | | |
| Intent / Trigger | | |
| Agent / Context | | |
| Agent / Behavior | | |
| Agent / Trigger | | |
| Context / Behavior | | |
| Context / Trigger | | |
| Behavior / Trigger | | |

If swapping the Explorer agent for a different research agent forces you to rewrite the Intent, those two primitives are entangled.

### Layer Separation Check

Each of IDD's three layers has a strict boundary. Content from one layer must not leak into another.

| Layer | Boundary Rule | Violation Example |
|-------|---------------|-------------------|
| Voice (Layer 1) | Natural language only -- no syntax, no YAML | User input containing `depends_on:` keys |
| Grammar (Layer 2) | Primitives only -- no execution details | Grammar specifying `tool: grep` or `provider: anthropic` |
| Machinery (Layer 3) | Execution only -- no goal definitions or norms | Tool implementation that encodes success criteria |

### Completeness Check

| # | Check | Pass? |
|---|-------|-------|
| CC-1 | All five primitives present? | |
| CC-2 | Intent has at least one success criterion? | |
| CC-3 | At least one Trigger defined? | |
| CC-4 | All agents have at least one capability? | |
| CC-5 | Context covers what agents need to do their work? | |

---

## Verdict Rubric

### PASS

All five primitives are present and correctly classified. All 10 orthogonality pairs pass. No primitive conflation detected. Scope boundaries are explicit in both directions (`scope_in` and `scope_out`). Layer separation is clean -- Voice contains no syntax, Grammar contains no execution details, Machinery contains no goal definitions.

### CONDITIONAL PASS

Minor orthogonality concerns exist but are documented and acknowledged. One or two classifications have low confidence and are flagged for user clarification. Optional fields (`scope_out`, `values`) are missing but justified -- for example, a quick exploratory task where explicit exclusions add no value.

### FAIL

Any of the following constitutes a failure: a missing primitive (especially Intent or Trigger), primitive conflation (WHO+HOW, WHY+HOW, or any other merge), implicit context dependencies, no explicit trigger, layer boundary violations, or a "god agent" that absorbs all responsibilities. A failed composition must be corrected before execution.

---

## Example Walkthrough: Onboarding Redesign

Consider the employee onboarding redesign composition from `recipes/examples/onboarding-redesign.md`. Here is an abbreviated audit.

**Intent Audit.** The goal is "make the onboarding flow significantly faster for new users." Success criteria are measurable: setup under 2 minutes, works on web and mobile, no new dependencies. `scope_in` lists onboarding screens, auth flow, and profile setup. `scope_out` excludes post-onboarding and billing. Values are not explicitly stated as priority orderings -- this is a minor gap worth flagging but not a failure. The Intent does not prescribe method. Verdict: I-1 through I-4, I-6 pass. I-5 is a minor gap.

**Agent Audit.** Four agents are defined by role: Explorer, Researcher, Zen Architect, Builder. Each has a clear capability boundary. No agent is a god agent. They are referenced by name, not redefined inline. Verdict: all Agent checks pass.

**Context Audit.** Context lists `context/project` as auto-detected. Flow dependencies are declared: Explorer and Researcher feed into Architect, Architect feeds into Builder. Context scope could be more explicit about what each agent sees beyond these flows. Verdict: C-1, C-2, C-5 pass. C-3 is a minor gap.

**Behavior Audit.** Two behaviors are declared by reference: `review-before-ship` and `log-all-decisions`. Both are reusable patterns, declared once, and do not encode goals. Verdict: all Behavior checks pass.

**Trigger Audit.** Activation is on-demand with human confirmation. Pre-conditions require access to both codebases. Parallelism is explicit: Explorer and Researcher run in parallel at step 1, then sequencing takes over. Verdict: all Trigger checks pass.

**Orthogonality.** Swapping Explorer for a different research agent does not change the Intent, Context structure, Behaviors, or Trigger. Changing the Trigger from on-demand to scheduled does not alter agents or behaviors. All 10 pairs pass.

**Layer Separation.** The composition is expressed in natural language at the Voice layer, structured into primitives at the Grammar layer, and defers all execution details to Machinery. Clean.

**Overall Verdict: CONDITIONAL PASS.** Two minor gaps (I-5: no explicit value ordering, C-3: agent-level context scope could be sharper). Neither blocks execution. Both should be addressed if the composition is promoted to a reusable template.
