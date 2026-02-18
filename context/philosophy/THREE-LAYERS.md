# The Three Layers of Intent-Driven Design

Intent-Driven Design organizes all interaction into three distinct layers:
**Voice**, **Grammar**, and **Machinery**. Each layer has a single responsibility,
a clear contract with its neighbors, and a different audience. Understanding this
separation is prerequisite to working with IDD effectively.

The model is not a suggestion. It is the structural invariant that every IDD
component must respect. When a violation occurs -- when concerns from one layer
leak into another -- the system becomes harder to reason about, harder to debug,
and harder to trust.

---

## Layer 1: Voice (Natural Language Input)

Voice is what the user says. There is no syntax, no schema, no formatting
requirement. The user expresses intent in natural language, and the system
receives it without demanding structural compliance.

Examples of Voice input:

- "Redesign the employee onboarding flow to reduce drop-off."
- "Add dark mode to the settings page."
- "The checkout process takes too long -- fix it."

Voice is the accessibility layer. Anyone who can describe what they want can
participate. No knowledge of bundles, YAML, providers, or agent architecture is
required. This is deliberate: the barrier to entry is the ability to articulate
a goal.

Voice is not a prompt. A prompt is a formatted instruction optimized for a
specific model. Voice is richer than a command and less structured than a spec.
It carries nuance, implicit constraints, and contextual assumptions that a
well-designed parser must extract rather than ignore.

**What makes Voice effective:**

| Quality | Description | Example |
|---|---|---|
| Clear goal | The desired outcome is unambiguous | "Reduce onboarding drop-off" not "Make onboarding better" |
| Stated constraints | Boundaries or success criteria are present | "Without changing the existing API surface" |
| Sufficient specificity | Enough detail to disambiguate among interpretations | "Employee onboarding" not just "onboarding" |

Voice that lacks these qualities still works -- IDD does not reject input -- but
it produces lower-confidence Grammar decompositions and requires more
confirmation cycles before execution can begin.

---

## Layer 2: Grammar (Structured Decomposition)

Grammar is the core product of IDD. It is the intermediate representation that
sits between what the user said and what the system does. Voice enters; Grammar
emerges. Grammar is inspected, confirmed, and then handed to Machinery.

Every Voice input is decomposed into five orthogonal primitives:

| Primitive | Role | Question it answers |
|---|---|---|
| **Agent** | WHO does the work | Which agent or role is responsible? |
| **Context** | WHAT information is needed | What knowledge, files, or state are relevant? |
| **Behavior** | HOW the work is performed | What constraints, style, or methodology apply? |
| **Intent** | WHY the work matters | What is the goal, and what does success look like? |
| **Trigger** | WHEN execution begins or proceeds | What condition activates the next step? |

These five primitives are orthogonal by design. Changing the Agent does not
change the Intent. Changing the Trigger does not change the Behavior. This
orthogonality is what makes Grammar composable: you can swap one primitive
without disturbing the others.

**Properties of Grammar artifacts:**

Grammar is not an opaque internal data structure. It is designed to be handled
directly by humans and machines alike.

- **Inspectable** -- you can read the decomposition and understand what the system intends to do.
- **Editable** -- you can modify any primitive before execution begins.
- **Shareable** -- you can hand a Grammar artifact to a colleague, a different agent, or a different system.
- **Versionable** -- you can track changes to Grammar over time, producing a legible history of intent evolution.
- **Composable** -- you can combine two Grammar artifacts into a larger one, merging or chaining their primitives.

**The three roles of Grammar:**

Grammar serves a triple function within IDD, and understanding all three roles
is essential:

1. **Interpretation surface (Layer 1 to Layer 2).** The parser translates Voice
   into the five primitives. This is the analytical role: taking unstructured
   language and producing structured form.

2. **Feedback surface (Layer 2 to Layer 1).** The structured form is presented
   back to the user in readable language. The user sees what the system
   understood and confirms, edits, or rejects the interpretation. This is the
   verification role.

3. **Protocol layer (agent to agent).** When agents communicate with each other,
   they exchange Grammar -- not natural language, not raw tool calls. Grammar is
   the lingua franca of multi-agent coordination within IDD.

### The Confirmation Gate

The confirmation gate sits between Grammar and Machinery. After the Layer 1 to
Layer 2 decomposition completes, the system presents the Grammar back to the
user. Execution does not begin until the user confirms. This is where the
principle of verification before execution is enforced structurally, not by
convention.

The gate is not optional. It is the mechanism that prevents misinterpretation
from reaching Machinery, where the cost of error is highest.

---

## Layer 3: Machinery (Execution)

Machinery is how confirmed Grammar maps to running agents, tools, and workflows.
In the Amplifier ecosystem, this mapping is concrete:

| Grammar Primitive | Amplifier Mechanism |
|---|---|
| Intent | Recipe top-level goal |
| Agent | Bundle loading and agent selection |
| Context | Context file mounting |
| Behavior | Behavior file application |
| Trigger | Recipe steps with activation conditions |

Machinery is invisible to the user. They should never need to know about
bundles, YAML structure, provider configuration, or hook lifecycle. If Machinery
details surface in the user's experience, it is a layer violation.

Machinery handles the operational concerns that Grammar deliberately ignores:
bundle resolution, provider selection, tool mounting, session lifecycle
management, error recovery, and progress reporting.

---

## Layer Transitions

The boundaries between layers are not passive. Each transition is an active
process with its own module, event, and contract.

**Voice to Grammar (Layer 1 to Layer 2):**
The IDD parser module decomposes natural language into the five primitives. Upon
completion, it emits an `idd:intent_parsed` event carrying the full Grammar
artifact and a confidence score indicating how certain the decomposition is. Low
confidence triggers clarification requests back to the user rather than
proceeding with an uncertain interpretation.

**Grammar to Voice (Layer 2 to Layer 1):**
The IDD reporter hook presents the Grammar back to the user in readable,
natural-language form. This is the feedback step that precedes the confirmation
gate. The user sees a human-readable summary of what the system understood, not
the raw primitive structure.

**Grammar to Machinery (Layer 2 to Layer 3):**
The composition engine maps resolved primitives to Amplifier mechanisms. It emits
an `idd:composition_ready` event when all primitives have been resolved to
concrete Amplifier constructs. Only after this event does execution begin.

---

## Data Flow: Employee Onboarding Redesign

To make the three-layer model concrete, here is a single request flowing through
every layer with representative data at each stage.

**Layer 1 -- Voice:**
> "Redesign the employee onboarding flow to reduce drop-off. Keep the existing
> API contracts intact. Focus on the first-week experience."

**Layer 2 -- Grammar (after parsing):**

| Primitive | Resolved Value |
|---|---|
| Agent | `design-intelligence:layout-architect` + `foundation:zen-architect` |
| Context | Current onboarding flow docs, drop-off analytics, API contract specs |
| Behavior | Preserve API surface; optimize for first-week retention |
| Intent | Reduce employee onboarding drop-off rate |
| Trigger | Immediate; single-pass redesign with review gate |

The user sees this decomposition, confirms the agent selection and context
scope, and approves execution.

**Layer 3 -- Machinery (after confirmation):**
The composition engine loads the specified bundles, mounts the onboarding
documentation as context files, applies the API-preservation constraint as a
behavior file, creates a recipe with the redesign goal, and begins execution.
The user sees progress and results. They do not see bundle resolution, provider
negotiation, or YAML generation.

---

## What Makes Each Layer Work Well

Each layer has its own quality criteria. Applying the wrong criteria to the wrong
layer is a common mistake.

| Layer | Key Qualities | Failure Mode |
|---|---|---|
| Voice | Clarity, specificity, stated constraints | Vague input produces low-confidence Grammar |
| Grammar | Orthogonality, completeness, no conflation of primitives | Tangled primitives produce fragile compositions |
| Machinery | Correct mapping, graceful error handling, progress reporting | Silent failures or leaked abstractions |

---

## Separation Discipline

The three-layer model is only useful if the boundaries are maintained. Each
layer has fundamentally different concerns:

- **Voice** is about human expression. Its quality is measured by how well the user's intent is captured.
- **Grammar** is about structural correctness. Its quality is measured by orthogonality and completeness.
- **Machinery** is about execution fidelity. Its quality is measured by whether the right things happen reliably.

Mixing concerns across layers is an anti-pattern. Two common violations:

**Violation: execution details in Voice.** When a user writes "Load the
zen-architect bundle and run a staged recipe with approval gates," they are
bypassing Grammar entirely and speaking Machinery. The system should still
accept this input, but the parser should extract the intent ("I want a
carefully reviewed architectural redesign") rather than pass through the
mechanism names.

**Violation: execution details in Grammar.** When a Grammar primitive contains
"use anthropic provider with claude-sonnet" or "mount file at
~/.amplifier/context/," it has absorbed Machinery concerns. Grammar describes
what and why. Machinery decides how, with which provider, and where files live.

Maintaining this discipline is what allows each layer to evolve independently.
Voice can improve its parsing without touching Machinery. Machinery can swap
providers without altering Grammar. Grammar can add new primitives without
requiring users to change how they speak.
