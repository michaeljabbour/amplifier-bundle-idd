---
bundle:
  name: idd
  version: 0.2.0
  description: Intent-Driven Design - compositional grammar for agent systems

includes:
  - bundle: git+https://github.com/microsoft/amplifier-foundation@main
  - bundle: git+https://github.com/microsoft/amplifier-bundle-modes@main
  - bundle: idd:behaviors/idd-core
---

# Intent-Driven Design (IDD)

IDD decomposes every agentic interaction into five orthogonal primitives:
**Agent** (WHO), **Context** (WHAT), **Behavior** (HOW), **Intent** (WHY), **Trigger** (WHEN).

## Agents

| Agent | Role | When to Use |
|-------|------|-------------|
| `idd:idd-composer` | Decompose and compose | Creating or refining IDD compositions |
| `idd:idd-reviewer` | Audit and validate | Verifying compositions against the spec |
| `idd:idd-spec-expert` | Knowledge and teaching | Questions about IDD itself |

## Recipes

| Recipe | Workflow |
|--------|----------|
| `idd-decompose` | Natural language to IDD decomposition |
| `idd-full-cycle` | Decompose, review, approve, execute |
| `idd-audit` | Audit existing artifacts for IDD compliance |
| `idd-teach` | Interactive IDD onboarding |

@idd:context/idd-awareness.md
