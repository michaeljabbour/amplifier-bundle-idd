---
name: idd-philosophy
description: >
  Why IDD exists, the core insight (orthogonal decomposition enables composition),
  relationship to Amplifier, design principles. Use when explaining IDD, justifying
  decomposition, or teaching the approach. See references/three-layers.md for the
  Voice/Grammar/Machinery layer model.
version: 1.0.0
metadata:
  category: idd
---

> **Companion file:** See [references/three-layers.md](references/three-layers.md) for the Voice/Grammar/Machinery layer model.

# Intent-Driven Design: Why It Exists

This document explains the philosophical foundations of Intent-Driven Design (IDD) --
why it was created, what problem it solves, and how it relates to the broader Amplifier
ecosystem. It is self-contained and assumes no prior knowledge of IDD's internals.

---

## The Problem

Today's agent systems accept raw natural language and proceed directly to execution.
There is no intermediate representation between "what the user said" and "what the
machine does." No inspectable artifact. No editable structure. No way to verify intent
before action is taken.

This is not a new category of problem. The history of software is a history of
introducing structured intermediate layers where none existed:

| Domain           | Before                        | Intermediate Layer | After                          |
|------------------|-------------------------------|--------------------|--------------------------------|
| Web development  | Spaghetti scripts             | MVC                | Separated concerns             |
| Databases        | Ad-hoc file access            | SQL                | Declarative data queries       |
| Styling          | Inline presentation in HTML   | CSS                | Content separated from layout  |
| Compilation      | Direct machine code           | IR / AST           | Portable, optimizable programs |
| Agent systems    | Raw natural language          | **IDD**            | Structured, composable intent  |

Without an intermediate layer, agent interactions suffer from five compounding failures:

**Unpredictable behavior.** The same natural language prompt produces different results
depending on model version, temperature, system prompt length, and conversation history.
There is no stable contract between what you ask and what you get.

**No verification.** You cannot inspect what the agent "understood" before it acts. The
first time you learn your intent was misinterpreted is when the wrong thing has already
been done.

**No composition.** Two agent configurations cannot be meaningfully combined. If one
person sets up an agent for code review and another sets one up for security auditing,
there is no operation that merges them into a single coherent system.

**No sharing.** You cannot hand someone your "agent setup" in a form they can read,
understand, modify, and use. The knowledge lives in prompt fragments, memory, and
implicit conventions.

**No versioning.** If your agent interaction worked well last Tuesday, there is no
artifact to commit, diff, or roll back to. The interaction is ephemeral.

IDD exists because these are not annoyances -- they are structural impossibilities
without an intermediate representation.

---

## The Core Insight

Orthogonal decomposition enables composition.

If any agent interaction can be decomposed into exactly five independent dimensions,
and those dimensions are truly independent -- changing one does not force changes to
the others -- then composition follows as a mathematical consequence.

The five dimensions are:

| Dimension   | Question    | Controls                              |
|-------------|-------------|---------------------------------------|
| **Agent**   | WHO?        | Identity, capabilities, role          |
| **Context** | WHAT?       | Knowledge, data, domain understanding |
| **Behavior**| HOW?        | Norms, style, constraints, process    |
| **Intent**  | WHY?        | Goals, success criteria, purpose      |
| **Trigger** | WHEN?       | Activation conditions, timing, events |

The power of orthogonality is substitution without side effects. Consider an employee
onboarding redesign project. You can:

- Swap the **Agent** from a generalist to a UX specialist without changing the goal,
  the context, the behavioral norms, or the trigger conditions.
- Add new **Context** (competitive analysis, user research data) without redefining
  who does the work or why.
- Change the **Trigger** from "run on demand" to "run every Monday at 9am" without
  touching the agent, the knowledge, the behavior, or the intent.
- Tighten the **Behavior** (enforce accessibility standards, require mobile-first
  approach) without altering what the agent knows or what it is trying to achieve.

Each substitution is local. Each combination is valid. This is what orthogonality buys
you: the number of meaningful configurations is the *product* of options per dimension,
not the sum.

---

## IDD as Grammar

IDD is a grammar in the linguistic sense.

Natural language has a finite set of syntactic categories -- nouns, verbs, adjectives,
adverbs, sentence structure -- yet from these finite rules, speakers construct an
infinite variety of meaningful sentences. The categories do not limit expression. They
*enable* it. Without grammar, communication is not free; it is chaotic.

IDD operates on the same principle. Its five primitives -- Agent, Context, Behavior,
Intent, Trigger -- are syntactic categories for agent interaction. From five finite
categories, users construct an infinite variety of meaningful agent configurations.

Consider how grammar works in the onboarding redesign example:

```
INTENT:    Reduce onboarding drop-off by 20%
AGENT:     UX design specialist with prototyping capability
CONTEXT:   Current onboarding funnel data, design system tokens, competitor flows
BEHAVIOR:  Mobile-first, WCAG AA compliant, present options before committing
TRIGGER:   When sprint planning completes for Q3
```

Each line is a "word" in a different syntactic category. Together they form a
"sentence" -- a complete, parseable, meaningful expression of agent work. Change any
single line and you have a different valid sentence. Combine lines from two different
sentences and the result is still grammatically correct.

The key insight is that grammar does not constrain expression. It is the precondition
for compositional expression. Before grammar, you have isolated utterances. After
grammar, you have a language.

---

## The Paradigm Shift

> MVC structured how to build the solution. IDD structures how to express the problem.

This distinction matters. MVC tells you to separate model, view, and controller *when
building software*. It is architecture for builders -- an organizational principle for
code. IDD tells you to separate WHO, WHAT, HOW, WHY, and WHEN *when expressing what
you want agents to do*. It is grammar for expressers -- an organizational principle for
intent.

These operate at fundamentally different levels of abstraction:

| Property         | MVC                              | IDD                                  |
|------------------|----------------------------------|--------------------------------------|
| Organizes        | Implementation code              | Problem expression                   |
| Audience         | Developers building systems      | Anyone directing agent work          |
| Artifact         | Source files in a project        | A declaration of structured intent   |
| Composability    | Limited (frameworks are rigid)   | Native (orthogonal primitives)       |
| Verification     | Tests, type checks               | Human review of intent before action |

MVC was a breakthrough because it imposed structure on the *solution space*. IDD is a
breakthrough because it imposes structure on the *problem space*. The solution space is
where machines work. The problem space is where humans think.

---

## Relationship to Amplifier

Amplifier's foundational philosophy is "mechanism not policy." The kernel provides
primitives -- sessions, providers, tools, hooks, modules -- and bundles provide policy:
how to use those primitives for a specific purpose.

IDD is pure policy. It is a bundle, not a kernel change. It adds no new mechanism to
Amplifier. Instead, it uses every mechanism Amplifier already provides:

| Amplifier Mechanism | IDD Usage                                          |
|---------------------|---------------------------------------------------|
| Bundles             | Define Agent identities and capabilities            |
| Context files       | Provide the WHAT -- knowledge, data, domain rules   |
| Behavior files      | Encode the HOW -- norms, constraints, style guides   |
| Recipes             | Orchestrate multi-step Intent execution             |
| Hooks               | Implement Trigger conditions and event responses    |
| Sessions            | Scope the lifecycle of an intent-driven interaction |

The relationship is analogous to language and alphabet. Amplifier provides the alphabet
-- a set of powerful, composable symbols. IDD provides the grammar -- rules for
combining those symbols into meaningful expressions. You need both: an alphabet without
grammar gives you characters but no sentences; a grammar without an alphabet gives you
rules but no symbols to apply them to.

Or, more concretely: Amplifier says "here are Lego bricks." IDD says "here is a
language for describing what to build with them."

This separation is intentional and load-bearing. IDD never needs Amplifier to change.
Amplifier never needs to know IDD exists. Each can evolve independently, which is itself
a demonstration of the orthogonality principle that IDD is built on.

---

## Audience Expansion

The most consequential effect of IDD is expanding who can direct agent work.

Without IDD, configuring an agent system requires understanding bundles, YAML syntax,
provider configuration, hook lifecycle, and context file conventions. The audience is
developers. With IDD, expressing what you want requires understanding five intuitive
questions: Who should do this? What do they need to know? How should they work? Why
are we doing this? When should it happen?

Return to the onboarding redesign. A product manager can express:

> "Redesign the onboarding flow to reduce drop-off by 20%, using our design system,
> with a mobile-first approach, reviewed by the design team before shipping."

IDD decomposes this into the five primitives:

| Primitive    | Extracted Value                                          |
|--------------|----------------------------------------------------------|
| **Intent**   | Reduce onboarding drop-off by 20%                        |
| **Context**  | Current onboarding metrics, design system documentation  |
| **Behavior** | Mobile-first approach, design team review gate            |
| **Agent**    | Design specialist with prototyping tools                 |
| **Trigger**  | On request (implicit: now)                               |

The product manager did not write YAML. They did not choose a provider. They did not
configure hooks. They expressed intent in natural language, and the grammar decomposed
it into a structure that Amplifier can execute and -- critically -- that both humans
and machines can inspect before execution begins.

The grammar is the bridge between human intent and machine execution. It does not
replace natural language; it gives natural language a skeleton.

---

## Design Principles

Five principles guide every design decision in IDD. They are ordered by priority: when
two principles conflict, the higher-ranked principle wins.

### 1. Orthogonality Over Convenience

It is tempting to create combined primitives -- an "AgentWithContext" that bundles
identity and knowledge, or a "TriggeredBehavior" that merges timing with norms. Every
such combination destroys one axis of independent variation and reduces the total
configuration space. IDD resists this even when the separated form feels verbose.
Orthogonality is not a nice-to-have; it is the structural property that makes
composition possible.

### 2. Explicit Over Implicit

All context flow is declared. All trigger conditions are visible. All scope boundaries
are named. IDD never infers a dimension that the user did not express. If the behavior
is unspecified, the behavior is empty -- not defaulted. This makes IDD configurations
auditable: what you see is exactly what will execute. There are no hidden defaults
producing surprising behavior on the fifteenth run.

### 3. Grammar Over Code

The design layer -- the five-dimensional expression of intent -- is human-readable, not
executable. It is closer to a specification than to a program. This is deliberate:
the grammar layer exists to be *read by humans*, not parsed by compilers. Execution is
Amplifier's job. Expression is IDD's job. Keeping them separate means the expression
can be reviewed, shared, and versioned by people who do not write code.

### 4. Composition Over Configuration

When you need more capability, you combine simple primitives rather than configuring
complex ones. Need a code-reviewing security auditor? Compose a code-review agent
with a security-audit behavior, not a monolithic "secure-code-review" agent with
thirty configuration flags. Simple primitives composed freely will always outperform
complex primitives configured carefully, because the composition space grows
multiplicatively while the configuration space grows linearly.

### 5. Verification Before Execution

The grammar layer exists so that humans can inspect what will happen before it happens.
Every IDD configuration produces a readable artifact -- the decomposed five-dimensional
intent -- that a human can review, modify, or reject before any agent takes action.
This is not a safety feature bolted on after the fact. It is the reason the
intermediate representation exists at all.

---

## Summary

IDD is an intermediate representation for agent interaction. It decomposes the
unstructured space between human intent and machine execution into five orthogonal
dimensions -- Agent, Context, Behavior, Intent, and Trigger -- that are independently
variable, freely composable, and human-readable. It is implemented as a pure-policy
bundle on top of Amplifier's mechanism layer, expanding the audience for agent-directed
work from developers to anyone with something to accomplish.

The simplest way to understand IDD: it is a grammar for talking to agents the way SQL
is a grammar for talking to databases. Both impose structure. Both enable composition.
Both expand who can do the work.
