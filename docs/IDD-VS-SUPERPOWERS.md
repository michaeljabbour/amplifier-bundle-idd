# IDD vs Superpowers: Feature Comparison

## 1. Executive Summary

IDD (Intent-Driven Development) and Superpowers are complementary bundles that address different phases of the software development lifecycle. IDD structures **what** to do: it decomposes complex, ambiguous tasks into five orthogonal primitives (WHO/WHAT/HOW/WHY/WHEN), produces structured specifications with measurable success criteria, and grounds work before execution begins. Superpowers structures **how** to do it: it enforces TDD discipline through tool-policy restrictions, runs a three-agent review pipeline on every implementation task, and manages the full branch lifecycle from worktree creation to merge. Neither bundle replaces the other. IDD produces plans that Superpowers can execute with rigor, and Superpowers produces verified code that IDD can measure against its success criteria. A/B testing confirms this division: IDD won decisively on decomposition tasks, Superpowers won decisively on execution tasks, and neither excelled at the other's specialty.

---

## 2. At a Glance

| Dimension | IDD | Superpowers |
|-----------|-----|-------------|
| Primary focus | Task decomposition and planning | Task execution and quality assurance |
| Core question answered | "What should we build?" | "How should we build it?" |
| Architecture approach | Tools + hooks + context | Modes + agents + recipes |
| Orchestrator | Inherited (loop-streaming) | Inherited (loop-streaming) |
| Modules added | 5 | 2 |
| Agents | 3 | 5 |
| Modes | 0 | 6 |
| Recipes | 4 | 7 |
| Context files | 9 | 5 |
| Skills | 0 | 6+ (local + external source) |
| Enforcement mechanism | Context instructions (Execution Contract) | Tool policy (write\_file BLOCKED in most modes) |
| Test coverage | 216 tests | Not measured in our evaluation |

---

## 3. What Each Does Well

### IDD Excels At

**Decomposing complex, ambiguous tasks into structured specifications.** When given "optimize API response times," IDD produced an 8-agent plan across 5 phases with 6 measurable success criteria and 7 discovery questions to ground unknowns. Superpowers, given the same prompt, suggested entering brainstorm mode and asked 3 clarifying questions. IDD's output was actionable before a single line of code was written.

**Mapping agents to roles with measurable success criteria.** Every IDD decomposition assigns specific agents to specific roles, defines what "done" means in quantifiable terms, and scopes boundaries explicitly (in-scope vs. out-of-scope). This eliminates ambiguity about completion.

**Explicit scope boundaries.** The five-primitive grammar forces scope declaration. WHO defines responsibilities, WHAT defines deliverables, HOW defines approach, WHY defines success criteria, and WHEN defines sequencing. Nothing is implicit.

**Confidence scoring.** IDD decompositions include confidence percentages (e.g., 88% confidence on the code review task). When confidence is low, the system surfaces grounding questions before execution, preventing wasted effort on under-specified work.

**Grammar-level reporting.** IDD's reporter hook tracks progress against intent primitives, not against internal machinery. Reports answer "are we building what we said we'd build?" rather than "did the tools run?"

### Superpowers Excels At

**Enforced TDD discipline.** Superpowers uses tool-policy enforcement at the mode level: `write_file` is BLOCKED in most modes. This is not a suggestion the LLM might ignore -- it is a physical constraint. The LLM cannot write production code outside of execute-plan mode, and within that mode, the three-agent pipeline enforces test-first development.

**Three-agent review pipeline.** Every implementation task passes through implementer (writes code with TDD), spec-reviewer (verifies the implementation matches the specification), and code-quality-reviewer (assesses code quality independent of spec compliance). This separation of concerns catches different classes of defects.

**Systematic debugging.** Superpowers' debug mode implements a 4-phase scientific method: observe, hypothesize, test, conclude. In the parser bug-hunting A/B test, Superpowers found 10 bugs, produced 9 fixes, wrote 35 new tests, and performed live reproduction of failures. IDD found 8 issues with 3 fixes and 38 new tests but lacked the structured debugging methodology.

**Branch lifecycle management.** The workflow spans the full git lifecycle: worktree setup, implementation, verification (fresh test runs with evidence), and finish (merge or PR creation). The `finish` recipe automates the cleanup that developers routinely forget.

**Evidence-based completion.** The verify mode requires fresh proof -- re-running tests, checking coverage, confirming no regressions -- before any completion claim is accepted. Claims without evidence are rejected.

---

## 4. Where Each Falls Short

### IDD Weaknesses

**No tool-policy enforcement.** IDD relies on context instructions (the Execution Contract: Decompose, Ground, Execute, Verify) to govern LLM behavior. The LLM is told to decompose before executing, but nothing physically prevents it from skipping decomposition and writing code directly. In adversarial or high-pressure scenarios, context instructions are weaker than tool-policy blocks.

**No mode system.** Without modes, IDD cannot create distinct operational phases with different tool permissions. There is no equivalent of Superpowers' ability to say "in this phase, you may only read files and run tests."

**Does not enforce TDD or review pipelines.** IDD can decompose a task that includes TDD as a step, but it has no mechanism to enforce that the implementer actually writes tests first, or that reviews happen before merge.

**Less effective for focused technical execution.** The A/B test on parser bug hunting showed this clearly: IDD's decomposition-first approach added overhead to a task where the right move was to start reading code, reproducing bugs, and writing fixes. Superpowers' debug mode was purpose-built for this.

### Superpowers Weaknesses

**Does not decompose tasks into structured primitives.** Superpowers' brainstorm mode produces a conversational plan through dialogue with the user. The output is prose, not a structured specification with typed primitives. This works well for clear tasks but leaves ambiguity in complex multi-phase work.

**No formal success criteria before execution.** Superpowers defines "done" implicitly through test passage and review approval, not through explicit, measurable criteria declared before work begins. You know the code is correct, but you may not know whether it solves the right problem.

**No explicit scope boundaries.** There is no formal in-scope/out-of-scope declaration. Scope is managed conversationally during brainstorm mode, which works for experienced users but provides no structured artifact to reference later.

**No confidence scoring or grounding phase.** Superpowers does not assess whether enough information exists to begin work. It does not surface discovery questions or estimate confidence in the plan. If requirements are ambiguous, this surfaces during implementation rather than during planning.

**Plans are conversation-driven, not structured.** The write-plan mode produces a plan through dialogue, which is flexible but less reproducible. Two runs of the same task may produce structurally different plans. IDD's five-primitive grammar produces consistent, comparable decompositions.

---

## 5. The Complementary Pattern

IDD and Superpowers address orthogonal concerns. IDD owns the planning layer: what to build, who builds it, what success looks like, and what questions must be answered first. Superpowers owns the execution layer: how to build it with TDD, how to review it with a three-agent pipeline, and how to verify and ship it with evidence.

The ideal integration uses IDD to produce the specification and Superpowers to execute against it.

### Hypothetical Combined Workflow

Consider the prompt: **"Optimize API response times to under 200ms for the top 10 endpoints."**

**Phase 1 -- IDD Decomposes**

IDD's `idd_decompose` tool produces a structured plan:
- **WHO**: 8 agents (profiler, cache-architect, query-optimizer, load-tester, 4 endpoint specialists)
- **WHAT**: Response time reduction for 10 specific endpoints
- **HOW**: Profile first, then optimize (caching, query optimization, connection pooling), then verify
- **WHY**: 6 success criteria (p95 < 200ms per endpoint, no regression in correctness, cache hit rate > 80%, etc.)
- **WHEN**: 5 phases (profile, design, implement, verify, deploy)
- **Scope**: In-scope: the 10 endpoints. Out-of-scope: database schema changes, infrastructure scaling.
- **Confidence**: 72% -- needs profiling data before implementation phases are reliable.

The 15-second confirmation gate fires. The user reviews and approves.

**Phase 2 -- IDD Grounds**

IDD executes the profiling phase to answer its discovery questions. Confidence rises to 91%. The implementation plan is now concrete: 3 endpoints need caching, 4 need query optimization, 2 need connection pooling, 1 needs algorithmic changes.

**Phase 3 -- Superpowers Executes**

For each implementation task, Superpowers enters `/execute-plan` mode:
1. The **implementer** agent writes tests first (asserting p95 < 200ms for the target endpoint), then writes the optimization code to pass those tests.
2. The **spec-reviewer** agent verifies the implementation matches the IDD-defined specification for that phase.
3. The **code-quality-reviewer** agent checks for maintainability, performance anti-patterns, and style compliance.

Tool policy enforcement ensures no production code is written without tests. The three-agent pipeline ensures no code merges without both spec and quality review.

**Phase 4 -- IDD Verifies**

IDD's reporter checks each of the 6 success criteria against evidence:
- p95 < 200ms for endpoint /users? Measured: 142ms. PASS.
- Cache hit rate > 80%? Measured: 87%. PASS.
- No correctness regressions? 847 tests pass. PASS.

**Phase 5 -- Superpowers Finishes**

Superpowers enters `/finish` mode: runs a final verification pass, creates the PR with evidence summary, and cleans up the worktree.

### Why This Works

IDD prevents the "build the wrong thing" failure mode. Superpowers prevents the "build the right thing badly" failure mode. Together, they cover both.

---

## 6. Recommendation: When to Use Which

| Situation | Recommended | Rationale |
|-----------|-------------|-----------|
| Complex multi-step task with unclear scope | IDD | Five-primitive decomposition clarifies what to build before any code is written. Confidence scoring surfaces unknowns early. |
| Implementation task with clear requirements | Superpowers | TDD enforcement and three-agent review pipeline ensure quality execution. Requirements are already known; decomposition adds overhead. |
| Bug hunting or debugging | Superpowers | Bug-hunter agent + systematic 4-phase debugging methodology. A/B test: Superpowers found more bugs, produced more fixes, and performed live reproduction. |
| Designing a new agent workflow | IDD | WHO/WHAT/HOW/WHY/WHEN primitives map directly to agent role assignment, deliverable definition, and success criteria. |
| Full feature from idea to merge | Both | IDD for planning and success criteria, Superpowers for TDD execution and branch lifecycle. The complementary pattern described in Section 5. |
| Code review | Superpowers | Three-agent review pipeline (implementer, spec-reviewer, code-quality-reviewer) is purpose-built for this. |
| Auditing existing recipes or bundles | IDD | IDD reviewer checks orthogonality and completeness against the five-primitive grammar. Detects missing primitives and structural gaps. |
| Quick, well-scoped task (< 30 min) | Superpowers | Overhead of full decomposition is not justified. Superpowers' mode system provides just enough structure. |
| Multi-team coordination or handoff | IDD | Structured specifications with explicit scope boundaries and success criteria are the correct artifact for cross-team communication. |

---

## 7. Can They Be Composed?

Yes. Both bundles are designed for composition within the Amplifier ecosystem.

### Technical Compatibility

Both bundles inherit from foundation and use the `loop-streaming` orchestrator without replacing it. Neither bundle assumes exclusive control of the agent loop. This is the baseline requirement for composition.

A combined bundle configuration would include both behavior sets:

```yaml
includes:
  - foundation
  - superpowers:behaviors/superpowers-methodology
  - idd:behaviors/idd-core
```

### Layer Interaction

IDD's contributions (5 modules: tools, hooks, context) and Superpowers' contributions (2 modules: hooks, tool-policy modes) operate at different layers:

- **IDD adds tools** (`idd_decompose`, `idd_query`) that return structured data. These tools do not write files.
- **IDD adds hooks** (grammar-inject, reporter, confirmation gate) that observe and annotate the conversation.
- **Superpowers adds modes** (brainstorm, write-plan, execute-plan, debug, verify, finish) with tool-policy enforcement.
- **Superpowers adds agents** (brainstormer, plan-writer, implementer, spec-reviewer, code-quality-reviewer) that perform delegated work.

### Potential Friction

**Superpowers modes block `write_file`, but IDD tools do not write files.** IDD's `idd_decompose` and `idd_query` tools return data structures; they do not create or modify files on disk. This means IDD's tools function normally even when Superpowers' most restrictive modes are active. There is no tool-policy conflict.

**Mode transitions need coordination.** In a composed bundle, the user would use IDD's decomposition (no mode required) to produce a plan, then enter Superpowers' `/execute-plan` mode to implement each phase. The transition is explicit and natural, but there is no automated handoff mechanism today. A future recipe could automate this: run `idd_decompose`, present the plan, then invoke the Superpowers execution pipeline for each phase.

**Context budget.** IDD contributes 9 context files and Superpowers contributes 5, plus skills. In a composed configuration, total context injection increases. Both bundles should be evaluated for context efficiency in combination, though neither is excessively large individually.

### Net Effect

IDD decomposition followed by Superpowers' mode-enforced execution. The planning layer gains structure and measurability. The execution layer gains discipline and verification. The A/B test results predict this: IDD's decisive wins on decomposition tasks (code review, API optimization) combine with Superpowers' decisive win on execution tasks (parser bug hunting) to cover the full lifecycle without gaps.

---

## Appendix: A/B Test Results

These results are from controlled tests where identical prompts were given to both bundles.

| Test | IDD Result | Superpowers Result | Winner | Margin |
|------|-----------|-------------------|--------|--------|
| Code review decomposition | 5 agents, 5 criteria, scope table, 88% confidence | 8 prose steps, asked "what next?" | IDD | Large |
| API performance optimization | 8 agents across 5 phases, 6 criteria, 7 discovery questions | Suggested /brainstorm, asked 3 grounding questions | IDD | Large |
| IDD knowledge query | Delegated to spec-expert (62K tokens) | Explorer read files (69K tokens) | Tie | -- |
| Parser bug hunting | 8 issues, 3 fixes, 38 new tests | 10 bugs, 9 fixes, 35 new tests, live reproduction | Superpowers | Large |

**Key takeaway**: Each bundle won decisively on tasks aligned with its core purpose and was outperformed on tasks outside its specialty. This is the strongest evidence for complementary use rather than replacement.
