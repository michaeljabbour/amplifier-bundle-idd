---
bundle:
  name: idd
  version: 0.1.0
  description: Intent-Driven Design - compositional grammar for agent systems

includes:
  - bundle: git+https://github.com/microsoft/amplifier-foundation@main
  - bundle: idd:behaviors/idd-core
---

# Intent-Driven Design (IDD)

IDD decomposes every agentic interaction into five orthogonal primitives:
**Agent** (WHO), **Context** (WHAT), **Behavior** (HOW), **Intent** (WHY), **Trigger** (WHEN).

@idd:context/idd-awareness.md
