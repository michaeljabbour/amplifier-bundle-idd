# The Five Primitives of Intent-Driven Design

Intent-Driven Design (IDD) decomposes every agent interaction into exactly
five orthogonal primitives. Each primitive answers one question and one
question only. Together, the five primitives form a complete grammar for
describing any AI-assisted workflow. Orthogonality is the central invariant:
changing one primitive never requires changing any other. If a change to one
primitive forces a change elsewhere, the decomposition contains a conflation
and must be refined.

The primitives are **Agent**, **Context**, **Behavior**, **Intent**, and
**Trigger**. They map, respectively, to the questions WHO, WHAT, HOW, WHY,
and WHEN. No sixth question is needed; no subset is sufficient. This document
is the definitive reference for all five.

Throughout this document, an "employee onboarding redesign" project serves as
the running example. In that project a product team uses multiple agents to
reduce new-hire drop-off from 40% to under 20%, redesigning the sign-up flow,
first-day checklist, and welcome sequence.

---

## 1. Agent (WHO)

### Definition

An Agent is the entity that performs work. It encompasses identity, capability
boundaries, persona, role description, and constraints. The Agent primitive
answers a single question: **WHO does this?**

An Agent is not a behavior, a goal, or a piece of knowledge. It is a bounded
identity with a clear statement of what it can and cannot do.

### Mapping

In Amplifier bundles, agents live in the `agents/` directory. Each agent is
declared in YAML or referenced from a bundle manifest.

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | yes | Unique identifier for this agent. |
| `role` | string | yes | Human-readable description of the agent's function. |
| `instruction` | string | yes | Core directive that defines the agent's operating identity. |
| `capabilities` | list of strings | no | What this agent CAN do. |
| `constraints` | list of strings | no | What this agent MUST NOT do. |
| `tools` | list of strings | no | Tool names available to this agent. |

### Boundary Rules

Agent defines IDENTITY, not behavior. The statement "careful code reviewer"
conflates WHO with HOW. The agent is "code reviewer"; "careful" is a Behavior
that should be declared separately and composed in. Likewise, an agent does
not define goals (that belongs to Intent) or knowledge (that belongs to
Context).

The litmus test: if you remove an adjective or adverb from the agent
description and the identity still makes sense, the removed word likely
belongs in Behavior.

### Examples

**Good decompositions:**

1. A "UX researcher" agent with capabilities: `[user interviews, heuristic
   evaluation, usability testing]`. The identity is clear; the capabilities
   describe capacity, not style.

2. A "senior frontend engineer" with constraints: `[no backend changes,
   follow design system]`. Seniority here narrows capability scope, not
   behavior. The constraint "follow design system" bounds what the agent
   touches, not how it works.

3. In the onboarding redesign, three agents are defined: `ux-designer`,
   `frontend-engineer`, and `qa-tester`. Each has clear, non-overlapping
   boundaries. The UX designer produces wireframes and prototypes. The
   frontend engineer implements components. The QA tester validates against
   acceptance criteria.

**Bad decompositions (conflation):**

1. "The agent should carefully review code using best practices." This mixes
   WHO (code reviewer) with HOW (carefully, best practices). Extract the
   agent as "code-reviewer" and the behavioral norms into a Behavior.

2. "Research agent who knows about our codebase." This mixes WHO (researcher)
   with WHAT (codebase knowledge). The agent is "researcher"; the codebase
   is Context provided to it.

3. "Agent that runs after deployment." This mixes WHO with WHEN. The agent's
   identity should stand on its own; "after deployment" is a Trigger.

### Orthogonality Test

Can you swap the agent without changing the Intent? If the answer is yes, the
Agent-Intent boundary is clean. Can you change an agent's constraints without
altering any Behavior? If yes, the Agent-Behavior boundary is clean.

---

## 2. Context (WHAT)

### Definition

Context is the knowledge, state, memory, references, working data, and
environmental facts available to agents. It answers: **WHAT do they know and
have?**

Context is passive. It does not prescribe action, dictate style, or trigger
execution. It is the raw material agents consume.

### Mapping

In Amplifier bundles, context lives in the `context/` directory: knowledge
base files, reference documents, system descriptions, and configuration.

### Three Types of Context

| Type | Gathered By | Lifecycle | Examples |
|------|-------------|-----------|----------|
| **Auto-Detected** | System inspection | Refreshed automatically | Working directory structure, git history, dependency manifests, file contents. |
| **Provided** | Human or configuration | Stable across session | User goals, team conventions, brand guidelines, design system tokens, architectural decision records. |
| **Discovered** | Agent activity at runtime | Accumulated during execution | API responses, test results, build output, interview transcripts, analytics queries. |

### Fields

Each context item carries:

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Identifier for this piece of context. |
| `type` | enum: `auto`, `provided`, `discovered` | How this context was obtained. |
| `content` or `reference` | string or path | The knowledge itself, or a pointer to it. |
| `scope` | list of agent names | Which agents can see this context. An empty list means all agents. |

### Boundary Rules

Context is KNOWLEDGE, not action. "Analyze the codebase" is an Intent carried
out by an Agent; the codebase itself is Context. Context does not prescribe
behavior: "follow TDD" is a Behavior, not Context. A testing framework
reference guide is Context; the instruction to use it is Behavior.

### Examples

**Good decompositions:**

1. "Current onboarding flow screenshots and metrics" -- provided context
   scoped to the UX designer and QA tester.

2. "Design system component library" -- provided context scoped to the
   frontend engineer and UX designer.

3. "User drop-off analytics from last quarter" -- provided context that
   informs the Intent's success criteria. The analytics are data; the goal
   of reducing drop-off is Intent.

**Bad decompositions (conflation):**

1. "The context is to review the PR." That is an Intent (review the PR), not
   Context. The PR diff is Context; the directive to review it is Intent.

2. "Context: be thorough." Thoroughness is a Behavior, a standard of work.
   Context would be the materials the agent needs to be thorough about.

3. "Context: after the build passes." Timing conditions are Triggers, not
   Context. The build output log may be Context, but the condition "after it
   passes" belongs to Trigger.

### Orthogonality Test

Can you change what agents know without changing who they are? Can you add a
new reference document without altering when things trigger? If both answers
are yes, the boundaries are clean.

---

## 3. Behavior (HOW)

### Definition

Behavior encompasses interaction patterns, protocols, quality standards,
communication norms, and stylistic conventions. It answers: **HOW should
agents work?**

Behaviors are reusable across agents and compositions. They are convention
bundles expressed in Markdown, not executable code.

### Mapping

In Amplifier bundles, behaviors live in the `behaviors/` directory as
Markdown files that describe patterns, rules, and standards.

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `pattern` | string | A concise name for the behavioral norm. |
| `applies_to` | list of strings | Agent names or roles this behavior governs. |
| `rules` | list of strings | Specific guidelines that operationalize the pattern. |

### Boundary Rules

Behavior is PATTERN, not identity. "Senior engineer" is an Agent; "code
review with line-by-line comments" is a Behavior. Behavior is also not a
goal: "achieve 90% coverage" is Intent (a success criterion), while "write
tests before implementation" is Behavior (a working method).

The key differentiator: behaviors tell agents how to carry out their work,
but they do not say what the work is (Intent), who does it (Agent), what
knowledge is available (Context), or when it starts (Trigger).

### Examples

**Good decompositions:**

1. "Mobile-first design approach" -- applies to all designer agents. This
   is a method, not an identity or a goal.

2. "TDD red-green-refactor cycle" -- applies to all engineer agents. The
   cycle is a protocol for how code gets written, independent of what is
   being built or who is building it.

3. "Present three options before committing to a direction" -- applies to
   all agents. This is a collaboration protocol.

4. In the onboarding redesign: "Follow Material Design guidelines" and
   "Accessibility-first approach" are Behaviors assigned to the UX designer
   and frontend engineer. They describe how design and implementation
   proceed, not what the project aims to achieve.

**Bad decompositions (conflation):**

1. "The careful reviewer agent." This fuses Agent identity with Behavior.
   Separate into agent "code-reviewer" and behavior "thorough line-by-line
   review."

2. "When tests pass, deploy." This is a Trigger (condition-based activation),
   not a Behavior.

3. "Achieve 90% coverage." This is Intent (a success criterion). The
   corresponding Behavior might be "write unit tests for every public
   function."

### Orthogonality Test

Can you change HOW agents work without changing WHO they are? Can the same
behavior apply to different agents without modification? If both are true,
the boundary is clean.

---

## 4. Intent (WHY)

### Definition

Intent captures the goal, success criteria, purpose, values, scope
boundaries, and definition of done. It answers: **WHY are we doing this?**

Intent is the primitive that gives a composition its reason to exist. Without
a declared Intent, agents have capability but no direction. Intent currently
lives in recipe definitions but is a first-class IDD primitive that can be
referenced and reused independently.

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `goal` | string | The objective stated in outcome terms. |
| `success_criteria` | list of strings | Measurable conditions that define "done." |
| `scope_in` | list of strings | What is explicitly included in this effort. |
| `scope_out` | list of strings | What is explicitly excluded. |
| `values` | list of strings | Principles that constrain trade-off decisions. |

### Boundary Rules

Intent is PURPOSE, not method. "Reduce onboarding drop-off by 20%" is
Intent. "Use A/B testing" is method -- either a Behavior or an Agent
activity, but not the reason the work exists. Intent is also not a trigger:
"when the sprint starts" is WHEN, not WHY.

An Intent without `scope_out` is a scope-creep risk. Explicitly listing
what is excluded is as important as listing what is included.

### Examples

**Good decompositions:**

1. The full onboarding redesign Intent:

   ```yaml
   goal: "Reduce new-employee onboarding drop-off from 40% to under 20%"
   success_criteria:
     - "Drop-off rate below 20%"
     - "Time-to-completion under 15 minutes"
     - "Accessibility score AA or above"
   scope_in:
     - "Sign-up flow"
     - "First-day checklist"
     - "Welcome sequence"
   scope_out:
     - "Admin dashboard"
     - "Payroll integration"
     - "Desktop app"
   values:
     - "Accessibility over aesthetics"
     - "Simplicity over feature-richness"
   ```

   Every field answers WHY: why this goal, why these criteria, why these
   boundaries, why these trade-off principles.

2. A code review Intent: `goal: "Ensure PR meets production quality
   standards"`. Success criteria might include passing CI, no unresolved
   comments, and documented API changes.

3. A migration Intent: `goal: "Move from REST to GraphQL without service
   disruption"`. Scope-out might exclude mobile clients in v1.

**Bad decompositions (conflation):**

1. "Make it better." No measurable criteria, no scope, no trade-off
   guidance. This is not an actionable Intent.

2. "The goal is to carefully review the code." This mixes WHY with HOW.
   The goal is to "ensure code quality"; the adverb "carefully" belongs
   in Behavior.

3. An Intent with no `scope_out`. Without explicit exclusions, every
   adjacent concern becomes a candidate for scope creep. Always declare
   what the work is not.

### Orthogonality Test

Can you change the goal without changing who does it? Can you revise success
criteria without altering behavior protocols? If yes, Intent is properly
isolated.

---

## 5. Trigger (WHEN)

### Definition

A Trigger defines conditions, sequences, events, dependencies, parallelism
constraints, and timing rules. It answers: **WHEN does this happen?**

Triggers govern activation and ordering. They say nothing about what happens,
who does it, or how it is done. Like Intent, Triggers currently live in
recipe definitions but are a first-class IDD primitive.

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `activation` | string | What starts this: `"user request"`, `"PR opened"`, `"schedule:daily"`, etc. |
| `pre_conditions` | list of strings | What must be true before activation can proceed. |
| `confirmation` | enum: `auto`, `human`, `none` | Whether human approval is required before execution. |

### Boundary Rules

Trigger is TIMING, not action. "Deploy the app" is an Agent performing an
Intent, not a Trigger. "After tests pass" is a Trigger -- it defines when
something activates. Triggers do not define what happens; they only define
when it may begin.

A composition with no explicit Trigger has an implicit "start immediately"
activation. IDD prefers explicit over implicit: declare the Trigger even
when it seems obvious.

### Examples

**Good decompositions:**

1. "User requests onboarding redesign" -- a manual trigger with
   `confirmation: "human"`. The human must approve before agents begin work.

2. "After design review is approved" -- a trigger with a pre-condition.
   The activation event is approval; the pre-condition is that a design
   review exists and has been submitted.

3. "Run design and engineering in parallel; QA after both complete." This
   shows parallelism (design and engineering share no ordering dependency)
   and a sequential dependency (QA waits on both). These are all timing
   concerns, cleanly separated from what design, engineering, or QA
   actually do.

**Bad decompositions (conflation):**

1. "Trigger: review the code." Reviewing code is an Intent/Agent action,
   not a timing condition. The trigger might be "PR opened" or "review
   requested."

2. "When the agent is careful." Carefulness is a Behavior, not a temporal
   condition. Triggers deal in events and states, not qualities.

3. No explicit trigger at all. An undeclared trigger makes activation
   implicit, which violates the IDD principle of explicit-over-implicit
   and makes compositions harder to reason about.

### Orthogonality Test

Can you change when something triggers without changing what it does? Can
you change the activation event without changing which agent responds? If
both answers are yes, the Trigger is properly orthogonal.

---

## The Full Decomposition Test

When building or reviewing an IDD composition, apply this procedure:

1. **Classify.** For every element in the composition, ask: does this answer
   WHO, WHAT, HOW, WHY, or WHEN?

2. **Decompose.** If any element answers more than one question, split it.
   "Careful code reviewer who runs after deployment" answers WHO, HOW, and
   WHEN. Decompose into agent "code-reviewer", behavior "thorough review",
   and trigger "after deployment completes."

3. **Verify pairwise orthogonality.** There are ten unique pairs among five
   primitives. For each pair, confirm that changing one does not force a
   change in the other.

### The Ten Orthogonality Pairs

| # | Pair | Question | Pass Example | Fail Example |
|---|------|----------|-------------|--------------|
| 1 | Agent -- Context | Can you change WHO without changing WHAT they know? | Replacing the UX designer with a product designer does not alter the onboarding metrics provided as context. | The agent definition embeds specific file paths, so swapping agents requires rewriting context references. |
| 2 | Agent -- Behavior | Can you swap agents and keep behaviors? | Assigning "mobile-first design" to either UX designer or frontend engineer works without modifying the behavior. | The behavior says "as a senior engineer, always..." -- changing the agent requires editing the behavior text. |
| 3 | Agent -- Intent | Can you change WHO without changing WHY? | Replacing the frontend engineer with a full-stack engineer does not alter the goal of reducing drop-off. | The intent says "the UX designer will reduce drop-off" -- agent identity is embedded in the goal statement. |
| 4 | Agent -- Trigger | Can you change WHO without changing WHEN? | Swapping the QA tester for an automated test runner does not change the trigger "after design and engineering complete." | The trigger says "when the QA tester is available" -- agent identity is embedded in the timing rule. |
| 5 | Context -- Behavior | Can you add knowledge without changing protocols? | Adding brand color guidelines to context does not change the "accessibility-first" behavior. | The behavior says "apply the colors from context document X" -- adding a new document requires rewriting the behavior. |
| 6 | Context -- Intent | Can you change WHAT they know without changing WHY? | Updating analytics data does not change the goal of reducing drop-off to under 20%. | The intent references a specific data file by name; changing the data source requires editing the intent. |
| 7 | Context -- Trigger | Can you add context without changing timing? | Adding a competitor analysis document does not alter the trigger "after design review is approved." | The trigger condition checks for a specific context file's existence; adding context changes trigger evaluation. |
| 8 | Behavior -- Intent | Can you change HOW without changing WHY? | Switching from "waterfall" to "iterative prototyping" does not change the goal of reducing drop-off. | The intent says "achieve 90% coverage using TDD" -- method is embedded in the goal, so changing behavior means rewriting intent. |
| 9 | Behavior -- Trigger | Can you change protocols without changing timing? | Switching from "present three options" to "present one recommendation" does not change the trigger "after user request." | The trigger says "when the agent finishes its careful review" -- behavioral quality is embedded in the timing condition. |
| 10 | Intent -- Trigger | Can you change WHY without changing WHEN? | Changing the success criterion from "20% drop-off" to "15% drop-off" does not change the trigger "user requests redesign." | The trigger says "when drop-off exceeds 40%" -- goal metrics are embedded in the activation condition. |

If any pair fails, the composition has a conflation. Refactor until all ten
pairs pass.

---

## Quick Reference

| Primitive | Question | Maps To | Key Fields | Common Conflation |
|-----------|----------|---------|------------|-------------------|
| **Agent** | WHO does this? | `agents/` | name, role, instruction, capabilities, constraints, tools | Embedding behavioral adjectives ("careful reviewer") or knowledge ("knows the codebase") in identity. |
| **Context** | WHAT do they know? | `context/` | name, type (auto/provided/discovered), content/reference, scope | Stating actions as context ("context is to review the PR") or embedding behavioral norms ("be thorough"). |
| **Behavior** | HOW should they work? | `behaviors/` | pattern, applies_to, rules | Fusing behavior with identity ("the careful agent") or with goals ("achieve 90% coverage"). |
| **Intent** | WHY are we doing this? | recipes (first-class IDD primitive) | goal, success_criteria, scope_in, scope_out, values | Embedding methods in goals ("carefully review") or omitting scope_out. |
| **Trigger** | WHEN does this happen? | recipes (first-class IDD primitive) | activation, pre_conditions, confirmation | Embedding actions in timing ("trigger: review the code") or leaving activation implicit. |

---

## Applying the Primitives: Onboarding Redesign Complete Example

The following shows the full decomposition for the employee onboarding
redesign project, demonstrating that every element maps to exactly one
primitive.

**Agents (WHO):** `ux-designer` (wireframes, prototypes, user flows),
`frontend-engineer` (component implementation, integration), `qa-tester`
(acceptance testing, accessibility audits).

**Context (WHAT):** Current onboarding flow screenshots, user drop-off
analytics, design system component library, Material Design reference docs,
WCAG 2.1 AA guidelines.

**Behaviors (HOW):** Mobile-first design approach, accessibility-first
development, present three options before committing, TDD red-green-refactor
cycle for all engineering work.

**Intent (WHY):** Reduce new-employee onboarding drop-off from 40% to under
20%. Success criteria: drop-off below 20%, completion under 15 minutes,
accessibility score AA or above. Scope includes sign-up flow, first-day
checklist, welcome sequence. Scope excludes admin dashboard, payroll
integration, desktop app. Values: accessibility over aesthetics, simplicity
over feature-richness.

**Triggers (WHEN):** Activation on user request with human confirmation.
Design and engineering run in parallel after approval. QA triggers after both
design and engineering complete. Final review triggers after QA passes.

Each element answers exactly one question. No element references another
primitive's concern. All ten orthogonality pairs pass. The composition is
clean.
