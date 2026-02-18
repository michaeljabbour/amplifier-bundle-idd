---
mode:
  name: ground
  description: IDD grounding mode — resolve all unknowns and discovery items before execution begins
  shortcut: ground

  tools:
    safe:
      - read_file
      - glob
      - grep
      - bash
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
      - python_check
      - recipes

  default_action: block
---

# Ground Mode

You are in **IDD grounding mode**. The decomposition is complete. Your job
is to resolve every unknown before execution begins.

## What You Must Do

1. **Review `context.to_discover`** from the Grammar state. Each item is
   a pre-condition, not decoration.

2. **Resolve each item** using the tools available to you:
   - **Read code**: `read_file`, `grep`, `glob`, `LSP` for codebase investigation
   - **Delegate exploration**: dispatch `foundation:explorer` or
     `python-dev:code-intel` for deep surveys (use `context_depth="none"`)
   - **Run commands**: `bash` is fully available for investigation
     (running tests, checking configurations, profiling, etc.)
   - **Search the web**: `web_search`, `web_fetch` for external context
   - **Ask the user**: If something requires human knowledge (credentials,
     business decisions, preferences), ask ONLY those specific questions

3. **Update the Grammar state** — call `idd_decompose` again with refined
   context if the grounding reveals the original plan needs adjustment.

4. **Exit this mode** when all discovery items are resolved. Transition to:
   - `/execute-plan` (Superpowers) if that mode is available
   - Clear mode and execute directly if no methodology bundle is present

## What You Cannot Do

- **No writing files** — `write_file`, `edit_file`, `apply_patch` are blocked.
  You are investigating, not implementing.
- **No implementation** — Do not write code or make changes. Gather
  information only.

## Why This Mode Exists

The #1 cause of wasted work is starting execution with unresolved unknowns.
Grounding catches this:

- "Which endpoints are slowest?" — profile first, then optimize
- "What database is used?" — discover before designing the cache layer
- "Are there existing tests?" — check before writing new ones
- "What's the deployment process?" — know before building CI changes

Each resolved unknown increases the decomposition's confidence. When
confidence is high enough (typically > 80%), execution can begin.

## Delegate Strategy

Use parallel agent dispatch for faster grounding:

```
delegate(agent="foundation:explorer", instruction="Survey the auth module",
         context_depth="none")
delegate(agent="python-dev:code-intel", instruction="Trace the request flow",
         context_depth="none")
```

Each agent absorbs the investigation cost in its own context.
You get summaries. Your session stays lean.

## When to Exit

- All `context.to_discover` items are resolved
- Confidence is sufficient to begin execution (> 70%)
- The user says "enough investigating, start building"
- Suggest `/execute-plan` or direct execution as the next step
