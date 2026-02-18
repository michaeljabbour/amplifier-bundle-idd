---
name: idd-recipe-compilation
description: >
  Compilation rules between IDD decompositions and Amplifier recipe YAML.
  Template expressions, foreach, while/break_when, parallel execution,
  approval gates, bidirectional compilation. Use when compiling decompositions
  to recipes or understanding the mapping.
version: 1.0.0
metadata:
  category: idd
---

# IDD Markdown to Recipe YAML Compilation

This document specifies how IDD (Intent-Driven Design) markdown compiles to
Amplifier recipe YAML and how YAML decompiles back to IDD markdown. These
rules form the deterministic bridge between the human-readable design layer
and the machine-executable workflow layer.

---

## IDD Markdown Format

IDD markdown is the human-readable design layer -- the Grammar in document
form. It uses natural language with structured conventions. It is NOT freeform
prose. It is a constrained natural language format that maps deterministically
to YAML. Think of it as the "source code" that compiles to recipes.

An IDD markdown document contains one section per primitive, expressed in
natural language but structured enough to parse unambiguously. Each section
heading corresponds to a Grammar primitive (Intent, Agents, Context,
Behaviors, Triggers), and the content within each section follows conventions
that the compiler can translate without guessing.

### Running Example: Employee Onboarding Redesign

```markdown
## Intent
Reduce employee onboarding drop-off from 40% to under 20%.
Success criteria: drop-off below 20%, completion time under 15 minutes, AA accessibility.
Scope: sign-up flow, first-day checklist, welcome sequence.
Out of scope: admin dashboard, payroll integration.
Values: accessibility over aesthetics, simplicity over features.

## Agents
- UX Designer: creates wireframes and prototypes
- UX Researcher: conducts usability studies and heuristic analysis
- Frontend Engineer: implements the designs
- QA Tester: validates against success criteria

## Context
- Current onboarding flow and drop-off metrics
- Design system component library
- Accessibility guidelines (WCAG 2.1)

## Behaviors
- Mobile-first design approach
- Present three options before committing
- TDD for all implementation work

## Triggers
- Activation: user requests onboarding redesign
- Confirmation: human approval required before implementation begins
- Sequence: design and research in parallel; implementation after design approval; QA after implementation
```

Every keyword in this document has a defined compilation target. The next
section enumerates those mappings.

---

## Compilation Rules

The following table defines the exhaustive set of mappings from IDD markdown
elements to recipe YAML fields. These rules are applied top-down during
compilation and reversed during decompilation.

| IDD Element | YAML Field | Compilation Rule |
|---|---|---|
| Intent goal statement | `intent:` top-level key | Direct map -- the goal sentence becomes the recipe intent string |
| Success criteria list | `success_criteria:` list | Each criterion becomes a YAML list item |
| Scope items | `scope:` list | Each scope item becomes a list entry |
| Out of scope items | `constraints:` list | Negative-scope items become constraint entries |
| Values ranking | `values:` list | Each "X over Y" pair becomes a values entry |
| Agent definition | `steps[].agent:` | Agent name maps to an agent reference path |
| Agent responsibility | `steps[].instruction:` | The role description becomes the step instruction |
| Context items | `context:` list | Each context source becomes a context entry |
| Behavior rules | `behaviors:` list | Each behavior becomes a behavioral constraint |
| "in parallel" / "and" / "simultaneously" | No `depends_on` | Steps without ordering keywords receive no depends_on field |
| "after X" / "once X completes" | `depends_on: [X]` | Dependency keywords generate depends_on references |
| "reviews against criteria" | `while:` / `break_when:` | Review-loop phrasing compiles to a convergence loop |
| "for each" / "iterate over" | `foreach:` | Collection iteration compiles to a foreach block |
| Confirmation: "human" | `approval: required` | Human confirmation triggers an approval gate on the stage |
| Confirmation: "auto" | _(no gate)_ | Step executes without pause |
| Activation trigger | `trigger:` top-level key | The activation condition becomes the recipe trigger |

These rules are intentionally unambiguous. If an IDD markdown element does not
match any row in this table, compilation fails with a diagnostic error rather
than guessing.

---

## Side-by-Side Example

The following demonstrates a complete compilation from the onboarding redesign
IDD markdown to its equivalent recipe YAML.

### IDD Markdown (Source)

```markdown
## Intent
Reduce onboarding drop-off to under 20%.
Success criteria: drop-off below 20%, completion under 15 min, AA accessibility.

## Agents
- UX Designer: creates wireframes and prototypes
- UX Researcher: conducts usability studies
- Frontend Engineer: implements designs
- QA Tester: validates against criteria

## Sequence
Design and research run in parallel.
Implementation begins after design review approval.
QA reviews implementation against success criteria.
Iterate until all criteria pass.
```

### Compiled Recipe YAML (Target)

```yaml
name: onboarding-redesign
intent: "Reduce onboarding drop-off to under 20%"
success_criteria:
  - "Drop-off rate below 20%"
  - "Completion time under 15 minutes"
  - "Accessibility score AA"

steps:
  - name: design
    agent: "@agents/ux-designer"
    instruction: "Create wireframes and prototypes for the onboarding flow"
    # no depends_on -- runs in parallel with research

  - name: research
    agent: "@agents/ux-researcher"
    instruction: "Conduct usability studies on current onboarding flow"
    # no depends_on -- runs in parallel with design

  - name: design-review
    depends_on: [design, research]
    approval: required
    # "human approval" in triggers compiles to approval gate

  - name: implementation
    agent: "@agents/frontend-engineer"
    depends_on: [design-review]
    instruction: "Implement the approved designs"

  - name: qa
    agent: "@agents/qa-tester"
    depends_on: [implementation]
    while: "criteria not met"
    break_when: "all success criteria pass"
    instruction: "Validate implementation against success criteria"
```

Note how parallel execution is expressed by the _absence_ of depends_on, not
by an explicit parallel keyword in YAML. The recipe engine treats any steps
without mutual dependencies as eligible for concurrent execution.

---

## Advanced Compilation Patterns

### foreach Loops

When IDD markdown describes iteration over a collection, the compiler emits a
`foreach` block. The collection reference and the per-item agent are extracted
from the natural language phrasing.

IDD markdown:
> For each component in the design system, verify accessibility compliance.

Compiles to:

```yaml
- name: accessibility-check
  foreach: "components"
  agent: "@agents/qa-tester"
  instruction: "Verify accessibility compliance for this component"
```

The `foreach` key tells the recipe engine to instantiate the step once per item
in the named collection, passing the current item as context to the agent.

### while / break_when (Convergence Loops)

Phrases like "review until all criteria pass" or "iterate until convergence"
compile to a while-loop structure. The break condition maps directly to the
success criteria or an explicit exit condition.

IDD markdown:
> QA reviews implementation against success criteria. Iterate until all criteria pass.

Compiles to:

```yaml
- name: qa
  agent: "@agents/qa-tester"
  while: "criteria not met"
  break_when: "all success criteria pass"
```

The recipe engine re-executes the step on each loop iteration, providing the
previous result as context, until the break condition evaluates to true.

### Parallel Execution

Any agents or steps described without ordering keywords ("and",
"simultaneously", "in parallel", or simply listed without sequence markers)
compile WITHOUT `depends_on` fields. This enables parallel execution by the
recipe engine. Ordering is introduced only when the IDD markdown explicitly
states temporal dependencies with words like "after", "once", "then", or
"following".

### Approval Gates

The trigger primitive's confirmation field controls whether a stage requires
human approval. When the IDD markdown specifies `Confirmation: human`, the
compiler emits `approval: required` on the corresponding stage boundary. This
maps to Amplifier's staged recipe format, where execution pauses at stage
boundaries until a human approves or denies continuation.

When confirmation is "auto" or omitted, no gate is generated and the stage
transitions automatically.

---

## Bidirectional Compilation

YAML can also decompile back to IDD markdown. This reverse path supports three
workflows:

1. **Importing existing recipes.** A team with existing Amplifier recipe YAML
   can generate IDD markdown to bring their workflows into the design layer.

2. **Human-readable summaries.** Complex YAML recipes can be presented to
   non-technical stakeholders as natural language IDD documents.

3. **Round-trip editing.** A workflow that starts as YAML can be decompiled to
   IDD markdown, edited by a designer, and recompiled back to YAML.

Decompilation rules reverse the compilation table:

| YAML Field | IDD Markdown Output |
|---|---|
| `depends_on: [X]` | "after X completes" |
| No `depends_on` among sibling steps | "in parallel" |
| `while:` / `break_when:` | "reviews against criteria until [break condition]" |
| `foreach:` | "for each item in [collection]" |
| `approval: required` | Confirmation: "human" |
| `success_criteria:` list | Success criteria listed after Intent goal |

Round-trip fidelity is a design goal: compiling and then decompiling (or vice
versa) should produce semantically equivalent documents, though surface-level
wording may differ.

---

## Parser Pipeline: Voice to YAML

The compilation rules documented here sit at a specific point in the IDD
parsing pipeline. The full path from user input to executable recipe is:

```
Voice (natural language) --> Grammar (five primitives) --> IDD Markdown --> Recipe YAML
```

The parser does not go directly from Voice to YAML. The Grammar extraction
phase identifies the five primitives in the user's natural language input. The
IDD markdown phase structures those primitives into the constrained format
shown above. The compilation phase applies the rules in this document to
produce valid recipe YAML.

The same rules work in reverse when presenting recipes back to users:

```
Recipe YAML --> IDD Markdown --> Natural language summary
```

This two-hop decompilation ensures that users always see their workflows in
the design language they authored, not in raw YAML.

---

## Compilation Errors

When the compiler cannot produce valid YAML from an IDD markdown document, it
emits a diagnostic error rather than generating a best-guess recipe. The
following are the most common failure modes:

**No Intent found.** Every IDD markdown document must contain an Intent
section. Without a goal statement, the recipe has no purpose and compilation
is rejected.

**Ambiguous sequencing.** Words like "then" can imply sequential ordering or
conditional branching depending on context. When the compiler cannot determine
which interpretation is correct, it halts and requests clarification from the
user.

**Unresolvable agent.** If the IDD markdown references an agent (e.g., "Data
Scientist") that has no matching bundle in the Amplifier configuration, the
compiler emits an error listing the referenced agent and available bundles.

**Missing trigger.** Every recipe needs an activation condition. If the
Triggers section is absent or contains no activation entry, the compiler
reports the omission.

**Circular dependencies.** If sequencing keywords create a dependency cycle
(A after B, B after A), the compiler detects and reports the cycle rather than
producing an invalid recipe.

These errors are designed to be actionable: each diagnostic tells the user
exactly what to fix in their IDD markdown to achieve successful compilation.
