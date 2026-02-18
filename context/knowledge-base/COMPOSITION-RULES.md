# Composition Rules

## What Composition Means in IDD

A composition is a complete unit of work expressed in IDD Grammar. It binds
together specific instances of all five primitives — Intent, Trigger, Agent,
Context, and Behavior — into a coherent, executable specification. The word
"composition" is deliberate: you are *assembling* primitives that already exist,
not defining new ones inline. Each primitive retains its identity and can
participate in other compositions independently.

Think of a composition as a sentence constructed from a shared vocabulary. The
vocabulary (primitives) is defined once and reused everywhere. The sentence
(composition) gives those words meaning in a particular situation. Two
compositions may share the same Agent or the same Behavior, but each composition
is its own self-contained unit of executable intent.

Throughout this document, we use a running example: an **employee onboarding
redesign** project whose Intent is to reduce new-hire drop-off during the first
week.


## The Six Composition Rules

### Rule 1: Every Composition Must Reference Exactly One Intent

A composition without an Intent has no purpose. It is an assembly of parts with
nothing to aim at. Conversely, if a composition contains two Intents, it is
actually two compositions forced into one — split them.

The Intent anchors everything else. Agents serve the Intent. Context supports
it. Behaviors constrain it. Triggers activate it. There is no primitive in a
composition that does not trace back to the Intent.

In the onboarding redesign, the single Intent is "reduce new-hire drop-off
during the first week." If a stakeholder also wants to "modernize the tech
stack," that is a separate composition with its own agents, context, behaviors,
and triggers. Combining them would conflate two scopes and make both harder to
reason about.

### Rule 2: Every Composition Must Reference at Least One Trigger

Nothing happens without a WHEN. Even "do it now" is a trigger — it simply has
`activation: "immediate"` and `confirmation: "none"`. Making timing explicit
keeps execution auditable and prevents compositions from firing silently.

A composition may have multiple triggers. The onboarding redesign might activate
when a stakeholder requests it (manual trigger) *and* when quarterly drop-off
metrics exceed a threshold (metric trigger). Both are declared; both are
auditable.

### Rule 3: Agents Are Loaded, Not Redefined

In Amplifier, agents ARE bundles. You reference them by identity — you do not
inline their definition inside a composition. This enables reuse: the same
`@agents/ux-designer` bundle can serve the onboarding redesign today and a
checkout flow optimization tomorrow.

You can customize an agent's participation through composition-specific Context
and Behavior, but the agent's core identity stays stable. Its capabilities,
tools, and base instructions live in its bundle, not in your composition.

**Bad:** Defining a new agent inline for every composition, duplicating
capability declarations and tool lists.

**Good:** Referencing `@agents/ux-designer` and attaching composition-specific
context (the onboarding flow data) and behavior (prioritize accessibility).

### Rule 4: Context Flows Explicitly

No implicit sharing. If Agent A produces context that Agent B needs, that data
flow must be declared in the composition. Hidden dependencies between agents are
composition errors — they make the system fragile and unauditable.

In the onboarding redesign, the UX designer produces wireframes (discovered
context) that the frontend engineer needs as input. The composition declares
this explicitly:

```
ux-designer.output.wireframes → frontend-engineer.input.wireframes
```

This declaration means the composition engine knows to wait for the UX
designer's wireframes before activating the frontend engineer. It also means
anyone reading the composition can trace every data dependency without
inspecting agent internals.

### Rule 5: Behaviors Are Inherited, Not Duplicated

If a behavior applies to all agents in a composition — such as "follow WCAG 2.1
accessibility standards" — declare it once at the composition level. Do not copy
it into each agent's definition. Duplication creates drift: when the standard
changes, you update one copy and forget the others.

Behaviors stack additively. A composition declares defaults, and individual
agents may carry additional behaviors. The stacking order is described in detail
in the Behavior Stacking section below. Where behaviors conflict, the more
specific one wins.

### Rule 6: Sequence Is Explicit About Parallelism and Dependencies

Never assume sequential execution. If two agents CAN work in parallel, the
composition must say so. If one depends on the other, the composition must say
so. Ambiguity in sequencing is a composition error.

For the onboarding redesign:

```
parallel: [ux-designer, user-researcher]
after: [ux-designer, user-researcher] → frontend-engineer
after: [frontend-engineer] → qa-engineer
```

This declares that design and research happen concurrently, engineering starts
only after both complete, and QA follows engineering. Anyone reading the
composition knows the execution topology without guessing.


## Merge Semantics

When two bundles are loaded together, their IDD primitives merge according to
deterministic rules. The table below covers the common scenarios.

| Scenario | Merge Rule | Example |
|---|---|---|
| Different Intents | Union — both available as separate compositions | Bundle A: "redesign onboarding", Bundle B: "add dark mode" — both compositions coexist |
| Same-named Intent | Last-loaded wins; warning emitted | Both bundles define a "code-review" intent — the later bundle's version is used |
| Triggers | Union with deduplication by identity | Both bundles trigger on "PR opened" — a single trigger instance, no duplicate firing |
| Agents | Union by bundle reference; no duplication of same bundle | Both reference `@agents/ux-designer` — one instance loaded |
| Behaviors | Union; conflicts resolved by specificity then load order | Both declare "follow accessibility standards" — deduplicated to one behavior |
| Compositions | Union; name collisions resolved by last-loaded wins with warning | Two compositions named "onboarding-flow" — later one overrides, warning emitted |

Warnings are not silent. They surface in the composition log so that operators
can detect unintentional overrides and resolve them.


## Orthogonality Enforcement

After assembling primitives into a composition, verify orthogonality. For every
pair of primitives, confirm that you can change one without being forced to
change the other. This is the practical test.

If an Agent and a Behavior are entangled — for instance, naming an agent "the
careful reviewer" where "careful" is actually a behavior trait — the composition
fails the orthogonality check. The agent's identity should describe *what it
is*, not *how it behaves*. Behavior is a separate primitive for a reason.

Orthogonality failures are composition errors, not warnings. They must be
resolved before execution.


## Confidence Scoring

When decomposing Voice (natural language) into Grammar (structured primitives),
each primitive assignment receives a confidence score between 0.0 and 1.0. The
score reflects how certain the parser is that a given phrase maps to a specific
primitive.

| Range | Label | Action |
|---|---|---|
| >= 0.9 | High | Proceed without annotation |
| 0.7 – 0.89 | Medium | Proceed with an advisory note attached to the primitive |
| < 0.7 | Low | Halt and request clarification from the user |

Low confidence means the parser cannot reliably determine which primitive a
phrase belongs to. Rather than guess and propagate ambiguity, the system asks.
This is a deliberate design choice: precision over speed.


## Scope Boundaries

Every Intent defines `scope_in` and `scope_out`. These are explicit boundaries
that govern what the composition is allowed to touch.

Everything listed in `scope_in` is in play — agents may act on it, context may
reference it, behaviors may constrain it. Everything listed in `scope_out` is
explicitly excluded — no agent should pursue work in that territory, and any
drift toward it is flagged.

Anything not mentioned in either list is implicitly out of scope, but should be
made explicit in `scope_out` as soon as it is discovered. This prevents the
common failure mode of "while we're at it, let's also..." — scope creep gets
checked against `scope_out` before it can take hold.

For the onboarding redesign: `scope_in` includes the first-week experience,
onboarding emails, and the setup wizard. `scope_out` includes the hiring
pipeline, benefits enrollment, and payroll integration.


## Values as Constraints

`Intent.values` is a priority ordering that constrains decisions throughout
execution. Values are not aspirational — they are operational. When a design
choice forces a trade-off, the value ordering decides.

"Accessibility over aesthetics" means that if a visual treatment harms screen
reader usability, accessibility wins. "Speed over completeness" means shipping a
focused MVP before a comprehensive solution. Values flow from the Intent to
every agent in the composition and influence how Behaviors are applied.


## Agent Matching

When a composition references an agent role (e.g., "needs a UX designer"), the
composition engine matches against available agent bundles. Matching evaluates
three criteria:

1. **Capabilities overlap** — the agent's declared capabilities cover what the composition requires.
2. **Constraints compatibility** — the agent's constraints do not conflict with composition-level behaviors.
3. **Tool availability** — the tools the agent needs are present in the runtime environment.

If no agent bundle satisfies all three criteria, the composition fails with an
`unresolvable_agent` error. This is a hard failure — the composition does not
execute with a degraded agent set.


## Behavior Stacking

Multiple behaviors can apply to a single agent within a composition. They
combine in a defined stacking order:

1. **Composition-level defaults** — behaviors declared at the composition root, applying to all agents.
2. **Role-specific behaviors** — behaviors scoped to a role (e.g., all designers follow brand guidelines).
3. **Agent-specific overrides** — behaviors attached to a particular agent instance in this composition.

Conflicts are resolved by specificity: more specific wins. An agent-specific
override takes precedence over a role-level behavior, which takes precedence
over a composition default. If two behaviors at the same specificity level
conflict, the later-declared one wins and a warning is emitted.


## Full Example: Employee Onboarding Redesign

The following composition references all six rules.

```yaml
composition:
  name: onboarding-redesign
  version: "1.0"

  # Rule 1: Exactly one Intent
  intent:
    objective: "Reduce new-hire drop-off during the first week from 23% to under 10%"
    scope_in: [first-week experience, onboarding emails, setup wizard]
    scope_out: [hiring pipeline, benefits enrollment, payroll integration]
    values: [accessibility over aesthetics, clarity over cleverness]

  # Rule 2: At least one Trigger
  triggers:
    - activation: "stakeholder-request"
      confirmation: "team-lead-approval"
    - activation: "quarterly-metrics"
      condition: "drop_off_rate > 0.20"
      confirmation: "none"

  # Rule 3: Agents loaded by reference, not redefined
  agents:
    - ref: "@agents/ux-designer"
    - ref: "@agents/user-researcher"
    - ref: "@agents/frontend-engineer"
    - ref: "@agents/qa-engineer"

  # Rule 4: Context flows declared explicitly
  context_flows:
    - from: "user-researcher.output.findings"
      to: "ux-designer.input.research"
    - from: "ux-designer.output.wireframes"
      to: "frontend-engineer.input.wireframes"
    - from: "frontend-engineer.output.build"
      to: "qa-engineer.input.artifact"

  # Rule 5: Behaviors inherited at composition level
  behaviors:
    composition:
      - "Follow WCAG 2.1 AA accessibility standards"
      - "Document all decisions with rationale"
    agent_specific:
      frontend-engineer:
        - "Use the existing design system; do not introduce new components"

  # Rule 6: Sequence explicit about parallelism and dependencies
  sequence:
    - parallel: [ux-designer, user-researcher]
    - after: [ux-designer, user-researcher] → frontend-engineer
    - after: [frontend-engineer] → qa-engineer
```

This composition is self-contained. A reader can determine the goal, the
activation conditions, who participates, how data flows between participants,
what constraints govern behavior, and in what order work proceeds — all without
consulting any other document.
