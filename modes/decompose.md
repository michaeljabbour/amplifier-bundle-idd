---
mode:
  name: decompose
  description: IDD decomposition mode — structured task breakdown into five primitives before any execution
  shortcut: decompose

  tools:
    safe:
      - read_file
      - glob
      - grep
      - LSP
      - web_search
      - web_fetch
      - load_skill
      - todo
      - memory
      - delegate
      - mode
      - centaur_predict
      - errorcache
      - recipes
    warn:
      - bash

  default_action: block
---

# Decompose Mode

You are in **IDD decomposition mode**. Your job is to break the task into
the five IDD primitives before any code is written or any action is taken.

## What You Must Do

1. **Call `idd_decompose`** with the user's task to produce a structured
   decomposition (Agent/WHO, Context/WHAT, Behavior/HOW, Intent/WHY,
   Trigger/WHEN).

2. **Present a brief summary** — goal, agents, success criteria, scope
   boundaries, confidence. Not the full JSON.

3. **Identify unknowns** — review `context.to_discover` items. These are
   pre-conditions that must be resolved before execution.

4. **Exit this mode** when the decomposition is approved (or auto-approved
   by the confirmation gate). Transition to:
   - `/ground` if there are unresolved discovery items
   - `/execute-plan` (Superpowers) if the plan is ready and that mode is available
   - Clear mode and execute directly if no methodology bundle is present

## What You Cannot Do

- **No writing files** — `write_file`, `edit_file`, `apply_patch` are blocked.
  You are planning, not implementing.
- **No running code** — `bash` requires justification (warn policy). Read-only
  investigation commands are acceptable.
- **No implementation** — Do not write code, create files, or make changes.
  The decomposition IS the deliverable in this mode.

## When to Use This Mode

- Complex multi-step tasks where the scope is unclear
- Multi-agent coordination where roles need explicit assignment
- Tasks where success criteria should be defined before work begins
- When the user says "plan this", "break this down", "decompose"

## When to Exit

- After the decomposition is complete and the confirmation gate has passed
- If the user says "go", "execute", "proceed"
- Suggest the appropriate next mode based on what's available

## Delegate for Exploration

You CAN delegate to exploration agents (`foundation:explorer`,
`python-dev:code-intel`, etc.) to gather information that improves the
decomposition. Use `context_depth="none"` for independent investigation.
Exploration results inform the decomposition — they are not execution.

## Anti-Patterns

| Temptation | Do This Instead |
|-----------|-----------------|
| Skip decomposition for a "simple" multi-step task | If it has multiple agents or unclear scope, decompose it |
| Present full JSON and ask "what next?" | Summarize briefly, let the confirmation gate handle approval |
| Start writing code "just to explore" | Use read_file, grep, delegate to explorer — no code writing |
| Decompose a single focused task | Exit mode — single-focus tasks don't need IDD |
