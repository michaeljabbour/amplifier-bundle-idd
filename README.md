# Intent-Driven Design (IDD)

A compositional grammar for agent systems. IDD decomposes every agentic
interaction into five orthogonal primitives before execution, producing
structured specifications that can be verified, compiled to recipes, and
handed to agents.

## What IDD Does

IDD provides a formal grammar with **five primitives** and **three layers**.

### Five Primitives

| Primitive | Question | Purpose |
|-----------|----------|---------|
| **Agent** | WHO | Identity, capability, persona, constraints |
| **Context** | WHAT | Knowledge, state, memory, references |
| **Behavior** | HOW | Interaction patterns, protocols, quality standards |
| **Intent** | WHY | Goal, success criteria, definition of done |
| **Trigger** | WHEN | Conditions, sequences, events, timing |

### Three Layers

1. **Specification Layer** -- The five primitives define the grammar. Each
   primitive is orthogonal: changing one does not require changing the others.
2. **Composition Layer** -- Primitives are combined into executable
   specifications with scope boundaries, discovery items, and agent pipelines.
3. **Runtime Layer** -- Compositions execute through Amplifier's orchestrator,
   with hooks observing state and recipes automating multi-step workflows.

## Quick Start

Add the IDD bundle to your Amplifier installation:

```bash
amplifier bundle add /path/to/amplifier-bundle-idd/bundle.md --name idd
amplifier bundle use idd
amplifier
```

Or run directly:

```bash
amplifier run --mode chat --bundle idd
```

Once active, the LLM gains two IDD tools (`idd_decompose`, `idd_compile`),
three specialist agents, four hook modules, and four recipes. It will
automatically decompose complex tasks into the five primitives before
executing them.

## What You Get

### Tools

| Tool | Description |
|------|-------------|
| `idd_decompose` | Decompose natural language into five IDD primitives. Returns structured JSON with agents, success criteria, scope boundaries, and confidence score. |
| `idd_compile` | Compile a decomposition into executable Amplifier recipe YAML (schema v1.7.0). |

### Agents

| Agent | Role | When to Use |
|-------|------|-------------|
| `idd:idd-composer` | Decompose and compose | Creating or refining IDD compositions |
| `idd:idd-reviewer` | Audit and validate | Verifying compositions against the spec |
| `idd:idd-spec-expert` | Knowledge and teaching | Questions about IDD itself |

### Hooks

| Hook | Purpose |
|------|---------|
| `hooks-idd-events` | Emits IDD lifecycle events (`idd:intent_parsed`, etc.) |
| `hooks-idd-grammar-inject` | Injects Grammar state into the LLM context |
| `hooks-idd-reporter` | Reports execution results against success criteria |
| `hooks-idd-confirmation` | Non-blocking confirmation gate for high-impact operations |

### Recipes

| Recipe | Workflow |
|--------|----------|
| `idd-decompose` | Natural language to IDD decomposition with validation |
| `idd-full-cycle` | Decompose, review, approve, execute |
| `idd-audit` | Audit existing artifacts for IDD compliance |
| `idd-teach` | Interactive IDD onboarding |

## When to Use IDD

**Use IDD for:**

- Complex multi-step tasks that benefit from structured breakdown
- Tasks where explicit success criteria should be defined before execution
- Multi-agent workflows requiring coordination across phases
- Work that should be compilable to repeatable recipes

**Do not use IDD for:**

- Simple single-step requests (the LLM handles these directly)
- Focused technical execution where a specialized agent (e.g., bug-hunter)
  is the right tool for the job

## When IDD Complements Other Bundles

IDD and superpowers are complementary, not competing. A/B testing showed:

- **IDD wins on planning and decomposition** -- structured specifications with
  measurable success criteria, agent pipelines, and scope boundaries.
- **Superpowers wins on focused technical execution** -- specialized agents
  like bug-hunter and code-quality-reviewer have domain expertise that
  decomposition cannot replicate.

The ideal workflow: **IDD decomposes the problem, superpowers agents execute
the solution.** IDD identifies which agents to call and what success looks
like; the superpowers agents do the work.

## Architecture

IDD uses **no custom orchestrator**. It follows the same pattern as superpowers:
power through content, not machinery replacement.

```
bundle.md
  includes: amplifier-foundation + behaviors/idd-core

behaviors/idd-core.yaml
  tools:    tool-idd (idd_decompose, idd_compile)
  hooks:    events, grammar-inject, reporter, confirmation
  agents:   idd-composer, idd-reviewer, idd-spec-expert
  context:  idd-awareness.md (the Execution Contract)
```

The standard `loop-streaming` orchestrator drives the session. The LLM
decides when to decompose based on the context instructions in
`idd-awareness.md`. This means it can choose *not* to decompose simple
tasks -- something a custom orchestrator cannot do.

The `idd-awareness.md` context file contains the **Execution Contract**:
decompose, ground unknowns, execute, verify. The LLM drives through all
four phases without stopping to ask permission.

## Testing

```bash
python -m pytest tests/ -v
```

216 tests covering the parser, compiler, grammar model, tools, and hooks.

## Evaluation

See [docs/EVALUATION.md](docs/EVALUATION.md) for detailed A/B testing results
comparing IDD-enabled sessions against standard Amplifier sessions across four
task types.

## Based On

The IDD Specification v0.4 by Michael J. Jabbour (Microsoft Corp / MADE
Explorations).
