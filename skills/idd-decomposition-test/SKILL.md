---
name: idd-decomposition-test
description: >
  Three-step quality gate for IDD decompositions: primitive classification,
  completeness check, orthogonality verification (10 pairs). Use after
  decomposing to validate quality before execution.
version: 1.0.0
metadata:
  category: idd
---

# The Decomposition Test

## Purpose

The Decomposition Test is the quality gate for IDD Grammar. It verifies that a composition has clean primitive boundaries -- no conflation, no missing primitives, full orthogonality. Every Grammar decomposition must pass this test before proceeding to execution.

A composition that fails the Decomposition Test will produce agents that are brittle, difficult to reconfigure, and resistant to reuse. The test exists to catch these structural defects early, when they are cheap to fix.

## The Test Procedure

The test has three sequential steps. A composition must pass all three.

### Step 1: Primitive Classification

For each element in the composition, ask: "Does this answer WHO, WHAT, HOW, WHY, or WHEN?" Classify every element into exactly one primitive. If an element answers more than one question, it must be decomposed further.

Consider the sentence: "The careful code reviewer checks PRs after they're opened."

This single description contains all five primitives tangled together:

| Fragment | Question It Answers | Primitive |
|----------|-------------------|-----------|
| "code reviewer" | Who does the work? | Agent |
| "careful" | How should they work? | Behavior |
| "checks PRs" | Why are we doing this? | Intent (partially -- the goal) |
| "PRs" | What do they know about? | Context |
| "after they're opened" | When does this happen? | Trigger |

If this sentence were left as a single agent description, it would be a conflation violation. Each fragment must be separated into its own primitive definition.

### Step 2: Completeness Check

Verify that all five primitives are present. A composition missing any primitive is incomplete. Default behaviors are acceptable for simple compositions, but the remaining four primitives must always be explicitly stated.

| Missing Primitive | The Question It Leaves Unanswered |
|-------------------|----------------------------------|
| No Agent | Who does the work? |
| No Context | What do they know? |
| No Behavior | How should they work? |
| No Intent | Why are we doing this? |
| No Trigger | When does this happen? |

A composition with a missing primitive is not merely incomplete -- it is ambiguous. The missing information will be filled in by implicit assumptions, and implicit assumptions are where miscommunication hides.

### Step 3: Orthogonality Verification

Test every combination of primitive pairs. For each pair, ask: "Can I change one without changing the other?" If the answer is no, the two primitives are entangled and must be refactored.

There are exactly 10 unique pairs to test. All 10 must pass.

## The 10 Pair Combinations

The following table uses the employee onboarding redesign as a running example. Each row tests one pair of primitives for independence.

| Pair | Test Question | Pass Example | Fail Example |
|------|--------------|--------------|--------------||
| Agent-Context (WHO-WHAT) | Can you swap the agent without changing the context? | Replacing the UX designer with a different designer does not change the onboarding metrics data. | Agent is defined as "the agent who knows our codebase" -- identity depends on context. |
| Agent-Behavior (WHO-HOW) | Can you apply the same behavior to a different agent? | "Mobile-first approach" applies to both the designer and the engineer. | Agent named "careful-reviewer" -- behavior is baked into identity. |
| Agent-Intent (WHO-WHY) | Can you change who does it without changing the goal? | Swapping the frontend engineer for a full-stack engineer does not change "reduce drop-off by 20%." | Agent defined as "the agent whose goal is to reduce drop-off" -- identity depends on intent. |
| Agent-Trigger (WHO-WHEN) | Can you change who without changing when? | Replacing the QA tester does not change "after implementation completes." | Agent defined as "the agent that runs after deploys" -- identity depends on timing. |
| Context-Behavior (WHAT-HOW) | Can you add context without changing how they work? | Adding more analytics data does not change "mobile-first approach." | Behavior is "follow the context guidelines" -- behavior depends on context content. |
| Context-Intent (WHAT-WHY) | Can you change knowledge without changing goals? | Updating the design system docs does not change "reduce drop-off by 20%." | Intent is "understand the codebase" -- the goal IS the context. |
| Context-Trigger (WHAT-WHEN) | Can you add context without changing timing? | Adding accessibility guidelines does not change "after design review." | Trigger is "when new data arrives" and context IS that data -- entangled. |
| Behavior-Intent (HOW-WHY) | Can you change methods without changing goals? | Switching from "mobile-first" to "responsive" does not change the drop-off target. | Intent says "achieve 90% test coverage using TDD" -- goal and method conflated. |
| Behavior-Trigger (HOW-WHEN) | Can you change protocols without changing timing? | Switching from "TDD" to "BDD" does not change "after design approval." | Behavior is "review when ready" -- behavior and trigger conflated. |
| Intent-Trigger (WHY-WHEN) | Can you change goals without changing timing? | Changing the target from 20% to 15% drop-off does not change "user requests redesign." | Trigger is "when we need to improve onboarding" -- trigger IS the intent. |

## Common Orthogonality Violations and Fixes

These are the most frequently encountered violations. Learn to recognize the patterns.

| Violation | What It Looks Like | Fix |
|-----------|-------------------|-----|
| Identity-Behavior conflation | "The meticulous senior engineer" | Agent: "senior-engineer". Behavior: "meticulous attention to detail." |
| Intent-Method conflation | "Improve test coverage using TDD" | Intent: "improve test coverage to 90%." Behavior: "use TDD methodology." |
| Agent-Context conflation | "Domain expert" | Agent: "analyst." Context: domain documentation, domain rules. |
| Trigger-Intent conflation | "When quality drops, fix it" | Intent: "maintain code quality above threshold." Trigger: "quality metric falls below threshold." |
| Behavior-Trigger conflation | "Review code promptly when PRs open" | Behavior: "review code promptly." Trigger: "when PR is opened." |

The underlying principle in every fix is the same: separate the concern into two independent declarations. Each primitive should be a self-contained statement that makes sense on its own.

## When Low Confidence Is Acceptable

Not every decomposition maps cleanly to five crisp primitives. Confidence below 0.9 on a classification is acceptable in the following cases:

1. **Genuine ambiguity in the Voice input.** The original phrasing is unclear and could reasonably map to multiple primitives. Flag the ambiguity for user clarification rather than guessing.
2. **Intentional span across two primitives.** A phrase deliberately bridges two concerns. Decompose it into both parts and note the relationship.
3. **Domain-specific terminology.** A term from the problem domain does not map cleanly to the primitive vocabulary. Add a clarification note explaining the mapping.

Low confidence is NOT acceptable in these situations:

1. **Unrecognized conflation.** Two primitives are tangled together and the author has not noticed. This is a test failure, not an ambiguity.
2. **Lazy decomposition.** The classification was left vague because further analysis seemed difficult, not because the input was genuinely ambiguous.
3. **Missing primitive.** A primitive is absent entirely. This is always a completeness failure regardless of confidence.

## Real-World Walkthrough: Employee Onboarding Redesign

Start with a raw Voice input:

> "I want to redesign our employee onboarding to cut drop-off in half. Use our design system, mobile-first. Get design and engineering working in parallel, then QA validates. I want human approval before we start building."

### Primitive Classification (Step 1)

Walk through each phrase:

| Phrase | Classification | Primitive |
|--------|---------------|-----------||
| "redesign our employee onboarding" | The overarching goal | Intent |
| "cut drop-off in half" | Measurable success criterion | Intent (refines the above) |
| "our design system" | Knowledge the agents need | Context |
| "mobile-first" | A working methodology | Behavior |
| "design and engineering working in parallel" | Two agents with a coordination pattern | Agent (x2) + Trigger (parallel) |
| "then QA validates" | A third agent with sequential timing | Agent + Trigger |
| "human approval before we start building" | A gate condition on timing | Trigger (approval gate) |

### Completeness Check (Step 2)

- **Agent:** Design agent, engineering agent, QA agent. Present.
- **Context:** Design system documentation, current onboarding flow, drop-off metrics. Present.
- **Behavior:** Mobile-first methodology. Present.
- **Intent:** Reduce employee onboarding drop-off by 50%. Present.
- **Trigger:** Design and engineering start in parallel; QA starts after implementation; human approval gate before build phase. Present.

All five primitives are accounted for. The composition passes Step 2.

### Orthogonality Verification (Step 3)

Spot-check the critical pairs:

- **Agent-Behavior:** Can "mobile-first" apply to a different agent? Yes -- it applies to both the design and engineering agents. Pass.
- **Agent-Intent:** Can we swap the design agent without changing the 50% drop-off target? Yes. Pass.
- **Behavior-Intent:** Can we switch from "mobile-first" to "responsive-first" without changing the drop-off goal? Yes. Pass.
- **Context-Trigger:** Can we update the design system docs without changing the parallel execution timing? Yes. Pass.
- **Intent-Trigger:** Can we change the target from 50% to 30% without changing the approval gate? Yes. Pass.

All 10 pairs pass. The remaining pairs follow the same pattern -- each primitive can be modified independently.

### Final Clean Grammar Output

- **Intent:** Reduce employee onboarding drop-off by 50%.
- **Agents:** design-agent, engineering-agent, qa-agent.
- **Context:** Design system documentation, current onboarding flow data, drop-off analytics.
- **Behavior:** Mobile-first design and implementation methodology.
- **Triggers:** Design and engineering execute in parallel on start. QA executes after implementation completes. Human approval gate before build phase begins.

This composition is clean: fully classified, complete, and orthogonal. It is ready for execution.
