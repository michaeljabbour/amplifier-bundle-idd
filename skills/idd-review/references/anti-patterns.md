# IDD Anti-Patterns

## Purpose

This catalog describes the most common mistakes made when composing IDD primitives. Each anti-pattern follows a consistent structure: what it is, what it looks like in practice, why it violates IDD principles, and how to fix it. Use this as a diagnostic reference during composition and as a companion to the review checklist.

The running example throughout is an employee onboarding redesign composition.

---

## 1. Primitive Conflation

**What it is.** Two or more primitives are merged into one, destroying orthogonality.

**Looks like.** An agent description that includes behavioral instructions: "The code reviewer agent should carefully review each file line-by-line, leaving detailed comments on every function." This fuses WHO (code reviewer) with HOW (carefully, line-by-line, detailed comments).

**Why it's wrong.** Orthogonality is the backbone of IDD. When WHO and HOW are merged, you cannot swap the agent without rewriting the behavior, and you cannot reuse the behavior with a different agent. The composition becomes monolithic even though it looks decomposed.

**Fix.** Separate the identity from the pattern. Define "code reviewer" as an Agent with capabilities (static analysis, style checking). Define "careful line-by-line review" as a Behavior that any agent can follow. They combine at composition time, not definition time.

**Example.** In the onboarding redesign, writing "Explorer carefully and thoroughly maps the codebase" conflates Agent and Behavior. Instead: Agent is "Explorer" (capability: codebase navigation). Behavior is "thorough-exploration" (protocol: map all entry points before diving into details).

---

## 2. Implicit Triggers

**What it is.** The composition has no explicit WHEN -- it assumes "just do it now."

**Looks like.** A composition with Intent, Agents, Context, and Behaviors fully specified, but no Trigger section. The author assumes the composition fires immediately upon creation.

**Why it's wrong.** Without an explicit trigger, timing is invisible. There is no confirmation gate, no pre-condition check, and no way to audit when or why execution started. The composition also cannot be reused in a scheduled or event-driven context.

**Fix.** Always declare at least one Trigger, even for immediate execution. The minimal valid trigger is `activation: on-demand, confirmation: none`. For compositions that need human approval, use `confirmation: human`. This costs one line and makes the composition self-documenting.

**Example.** The onboarding redesign declares its trigger explicitly: on-demand activation, human confirmation required, pre-condition of access to both codebases. Removing this section would make it impossible to know whether the composition was meant to run immediately, on a schedule, or in response to an event.

---

## 3. Vague Intent

**What it is.** The goal is stated in terms no one could measure or verify.

**Looks like.** "Make the onboarding experience better." "Improve code quality." "Optimize performance." These are aspirations, not intents. They provide no definition of done and no way to know when to stop.

**Why it's wrong.** Without measurable success criteria, scope creep is guaranteed. Agents have no termination condition. Reviewers have no acceptance standard. The composition will either run indefinitely or stop at an arbitrary point that satisfies no one.

**Fix.** Replace vague aspirations with measurable criteria. "Reduce onboarding drop-off from 40% to under 20%." "New users complete setup in under 2 minutes." "Zero new runtime dependencies added." Each criterion must be something a reviewer -- human or automated -- can objectively evaluate.

**Example.** The onboarding redesign states three measurable criteria: setup under 2 minutes, works on web and mobile, no new dependencies. Any reviewer can check all three. Compare this to "make onboarding better," which could mean anything.

---

## 4. Scope Creep (Missing scope_out)

**What it is.** Intent specifies what is in scope but never states what is excluded.

**Looks like.** An Intent with `scope_in: onboarding screens, auth flow, profile setup` but no `scope_out`. The author assumes exclusions are obvious.

**Why it's wrong.** Without explicit exclusions, work expands to fill available time and agent capacity. An agent exploring the auth flow may wander into the billing integration because "it's connected." Another may redesign the admin dashboard because "admins onboard too." Every unstated boundary is a boundary that will eventually be crossed.

**Fix.** Always define `scope_out` alongside `scope_in`. Be specific about what is deliberately excluded and why. "NOT including: post-onboarding experience, billing integration, admin dashboard, desktop application."

**Example.** The onboarding redesign explicitly excludes post-onboarding experience and billing. Without this, the Zen Architect might reasonably propose changes to the first-run tutorial (post-onboarding) or the payment setup step (billing), expanding the work far beyond what was intended.

---

## 5. Behavior-as-Agent

**What it is.** An interaction pattern is described as if it were an agent identity.

**Looks like.** Agents named "the careful agent," "the thorough researcher," or "the meticulous reviewer." The name encodes a behavioral quality rather than a role or capability.

**Why it's wrong.** Behaviors are reusable across agents. When you embed "careful" into an agent's identity, that quality cannot be applied to other agents, and the agent cannot operate in a different mode (fast, exploratory, approximate) without being redefined. You have lost composability.

**Fix.** Name agents by role: "reviewer," "explorer," "architect." Define thoroughness, carefulness, or meticulousness as Behaviors that attach to agents at composition time. The same "careful-review" behavior can then apply to any agent that needs it.

**Example.** Writing "the thorough Explorer" in the onboarding redesign bakes a behavioral expectation into the Agent primitive. Instead, define Explorer by capability (codebase navigation, dependency mapping) and attach a "thorough-exploration" Behavior separately. If a quick exploratory pass is needed later, you swap the Behavior, not the Agent.

---

## 6. Context Assumptions

**What it is.** Agents are expected to "just know" things that are never listed in Context.

**Looks like.** A composition where the Architect agent is expected to know about the existing design system, the Builder agent is expected to know the project's testing conventions, and neither piece of knowledge appears in the Context section.

**Why it's wrong.** Implicit dependencies break composition portability. The composition works in the original project because agents happen to have access to the right files, but it fails when reused elsewhere. It also makes auditing impossible -- a reviewer cannot verify that agents have what they need if requirements are unstated.

**Fix.** List all context explicitly. Classify each item by type: auto-detected (project structure), provided (design system documentation), or discovered (Explorer output). Scope each item to the agents that need it.

**Example.** In the onboarding redesign, the Explorer's output feeds into the Architect's input -- this is declared. But if the Architect also needs the company's design system guidelines, that must appear in Context as a provided item scoped to the Architect, not assumed.

---

## 7. Monolithic Composition

**What it is.** A single agent is assigned all responsibilities.

**Looks like.** One "super agent" with a massive instruction: explore the codebase, research best practices, design the solution, implement it, and review its own work. The composition technically has one Agent, one Context blob, and one Behavior section that reads like a novel.

**Why it's wrong.** No parallelism is possible. No specialization is leveraged. No part of the composition can be swapped independently. If the implementation is poor, you cannot replace the Builder without also replacing the Researcher, Architect, and Reviewer -- because they are all the same agent.

**Fix.** Decompose into specialist agents with clear capability boundaries. The onboarding redesign uses four agents: Explorer and Researcher work in parallel, Architect synthesizes, Builder implements. Each can be replaced independently, and the first two run concurrently.

---

## 8. Over-Decomposition

**What it is.** A task that needs two or three agents is split into a dozen.

**Looks like.** Separate agents for "reading code," "understanding code," "summarizing code," and "commenting on code." Or distinct agents for "opening the file," "parsing the AST," and "traversing the tree."

**Why it's wrong.** Coordination overhead scales with agent count. Every additional agent introduces a context handoff, a potential failure point, and a sequencing decision. When the overhead exceeds the benefit of specialization, the composition is slower and more fragile than a monolithic alternative.

**Fix.** Consolidate related capabilities into natural role boundaries. "Reading, understanding, and summarizing code" is one agent's capability set (Explorer), not three agents. Apply the test: would a human organization create separate job titles for these? If not, they belong in one agent.

---

## 9. Layer Bleed

**What it is.** Content from one IDD layer appears in another where it does not belong.

**Looks like.** Voice input (Layer 1) containing YAML syntax: "Create a composition with `depends_on: [step_1]`." Grammar (Layer 2) specifying execution details: "Use the `grep` tool with provider `anthropic`." Machinery (Layer 3) encoding goal definitions in tool implementations.

**Why it's wrong.** Layer separation exists so that each layer can evolve independently. When a user must write YAML to express intent, the Voice layer has failed. When Grammar prescribes tool choices, it has absorbed Machinery concerns and cannot be executed on a different infrastructure.

**Fix.** Keep each layer in its lane. Voice is natural language only -- no syntax, no structure. Grammar is the five primitives -- no tool names, no provider choices, no API endpoints. Machinery is execution -- no goal definitions, no behavioral norms.

**Example.** A user saying "have the Explorer use grep to search for auth handlers" is leaking Machinery into Voice. The correct Voice-layer statement is "understand how authentication is currently implemented." The choice of grep, LSP, or manual file reading belongs to Machinery.

---

## 10. Orphaned Context

**What it is.** Context is declared but never consumed by any agent.

**Looks like.** A Context section listing the project's CI/CD configuration, deployment history, and infrastructure topology for a composition whose agents only need the source code and design system.

**Why it's wrong.** Orphaned context is noise. It increases the cognitive load on auditors who must determine whether each context item is actually used. It also wastes token budget when context is injected into agent sessions -- agents receive information they will never act on.

**Fix.** Every context item should be scoped to at least one agent. If no agent needs it, remove it. During review, trace each context item to a consumer. If the trace dead-ends, the context is orphaned.

**Example.** If the onboarding redesign's Context section included "infrastructure/deployment-config" but no agent has a capability related to deployment, that context is orphaned. Remove it, or add an agent that needs it.

---

## 11. Circular Dependencies

**What it is.** Agent A depends on output from Agent B, which depends on output from Agent A.

**Looks like.** The Architect needs the Builder's implementation estimate to finalize the design, but the Builder needs the Architect's finalized design to produce an estimate. Neither can start.

**Why it's wrong.** Circular dependencies create deadlocks. No valid execution order exists. The composition cannot be compiled into a recipe because recipe steps require a directed acyclic graph. Even if execution is forced by running one agent with incomplete context, the result is unreliable.

**Fix.** Break the cycle by restructuring into stages or introducing a mediating step. In the example above, the Architect produces a draft design first (stage 1), the Builder estimates against the draft (stage 2), and the Architect revises based on the estimate (stage 3). The cycle becomes a linear sequence with a feedback loop.

**Example.** If the onboarding redesign had Explorer depending on Architect's design priorities and Architect depending on Explorer's findings, neither could start. The fix is clear: Explorer runs first with broad scope, Architect synthesizes after. If the Architect needs a second pass, that becomes a declared stage, not an implicit dependency.

---

## Quick Reference

| # | Anti-Pattern | Violates | Key Signal |
|---|-------------|----------|------------|
| 1 | Primitive Conflation | Orthogonality | Agent descriptions contain behavioral instructions |
| 2 | Implicit Triggers | Completeness | No Trigger section in composition |
| 3 | Vague Intent | Measurability | Goal has no success criteria |
| 4 | Scope Creep | Boundaries | `scope_in` present but no `scope_out` |
| 5 | Behavior-as-Agent | Composability | Agent named by quality, not role |
| 6 | Context Assumptions | Portability | Agents expected to "just know" things |
| 7 | Monolithic Composition | Parallelism | Single agent does everything |
| 8 | Over-Decomposition | Efficiency | More agents than natural roles |
| 9 | Layer Bleed | Layer separation | YAML in Voice, tools in Grammar |
| 10 | Orphaned Context | Clarity | Context declared but unconsumed |
| 11 | Circular Dependencies | Executability | Mutual agent dependencies |
