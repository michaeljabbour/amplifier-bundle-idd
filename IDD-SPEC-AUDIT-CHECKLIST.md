# IDD Spec Audit Checklist

**Purpose:** Pass the Amplifier expert audit (ecosystem, foundation, kernel) for the IDD specification.
**Spec version under review:** v0.4 (amplifier-idd-spec3.docx)
**Audit date:** 2026-02-18
**Auditors:** amplifier:amplifier-expert, foundation:foundation-expert, core:core-expert

---

## Verdict: PASS

All P0 and P1 items pass. The spec is ready for implementation as `amplifier-bundle-idd`.
P2 items are explicitly deferred to the build phase per the Document Scope section (lines 999-1019).

---

## P0 — Must Pass (Blocks Everything)

### P0-1: coordinator.mount("agents") Correction — PASS

- [x] **P0-1a:** All references to `coordinator.mount("agents", ...)` removed. Line 790: "Mechanism already exists for tools/providers. coordinator.mount('tools', ...) and coordinator.mount('providers', ...) work for runtime changes. Agent delegation uses coordinator.get_capability('session.spawn')." Line 869: "Critical: coordinator.mount('agents', ...) does NOT work."
- [x] **P0-1b:** Actual delegation mechanism documented. Line 868: "coordinator.get_capability('session.spawn') returns a function registered by the app layer (amplifier-app-cli/session_runner.py) that creates a child AmplifierSession."
- [x] **P0-1c:** Two distinct operations clearly distinguished. Lines 867-869: Tool/provider changes via mount(), agent delegation via session.spawn.
- [x] **P0-1d:** Architecture Placement table corrected. Lines 789-792: "Tools/providers: kernel. Agent spawn: app layer."
- [x] **P0-1e:** P1 action updated. Line 978: "For agent delegation: use coordinator.get_capability('session.spawn') to create child sessions. For runtime tool changes: use coordinator.mount('tools', ...)."

---

### P0-2: Recipe Format Reconciliation — PASS

- [x] **P0-2a:** Relationship explicitly stated. Line 452: "IDD markdown is a human-readable design layer that gets compiled to YAML by the Layer 1-to-2 parser. It is not a replacement for YAML recipes and not a parallel format."
- [x] **P0-2b:** Side-by-side example provided. Lines 454-494: Same recipe shown in IDD markdown (left) and compiled YAML (right) with steps, depends_on, context.include with template expressions, and approval gates.
- [x] **P0-2c:** All YAML features addressed:
  - `{{steps.X.result}}` template expressions: Lines 486-487, 512-513
  - `foreach` loops: Lines 517-519
  - `while_condition` / `break_when`: Lines 515-516
  - `approval` gates: Lines 494, 507
  - `depends_on`: Lines 483, 490, 493, 509-510
  - `parallel` execution: Lines 509-510
- [x] **P0-2d:** Compilation rules specified. Lines 496-520: Full table mapping IDD markdown elements to YAML recipe fields with compilation rules. Line 521: Bidirectional (YAML to IDD markdown also supported).

---

### P0-3: Behaviors vs. Hooks Conflation — PASS

- [x] **P0-3a:** Behaviors now list `.md` convention bundles. Lines 356-358: `agents.md`, `careful-mode.md`, `review-before-ship.md`.
- [x] **P0-3b:** Clarifying note present. Line 365: "Behaviors are convention bundles (markdown files) that describe patterns, protocols, and interaction norms -- they belong to the Grammar layer (Layer 2). Runtime capabilities like logging, streaming, and redaction are hook modules (Python code with lifecycle event handlers) -- they belong to Layer 3 (Machinery)."

---

## P1 — Should Pass Before Implementation

### P1-1: Agent Definition Format Accuracy — PASS

- [x] **P1-1a:** Agent definition uses actual `meta:` frontmatter. Lines 529-534: Shows `---`, `meta:`, `name: zen-architect`, `description:`, `---` followed by markdown body.
- [x] **P1-1b:** Relationship between IDD sections and format explained. Lines 541-551: "## Capabilities and ## Constraints sections are conventions that the IDD parser reads for agent matching during dynamic composition. Existing agents without these sections still load and work."

---

### P1-2: IDD Orchestrator Relationship to Existing Orchestrators — PASS

- [x] **P1-2a:** Relationship stated as option (b) — wraps. Lines 877-882: "The IDD orchestrator wraps an inner orchestrator. It handles Layer 1-to-2 decomposition and Layer 2-to-1 reporting at the outer level, then delegates the actual LLM loop to an existing orchestrator (typically loop-streaming)."
- [x] **P1-2b:** Inner orchestrator selection specified. Lines 882-891: Configurable in bundle.md frontmatter. Shows `orchestrator: idd` and `idd-inner-orchestrator: loop-streaming`.
- [x] **P1-2c:** execute() signature documented. Line 893: `async def execute(self, prompt, context, providers, tools, hooks, **kwargs) -> str`.

---

### P1-3: Grammar State Propagation to Child Sessions — PASS

- [x] **P1-3a:** State serialization pattern documented. Lines 898-906: Shows `[IDD GRAMMAR STATE]`, `json.dumps(grammar_state)`, `[YOUR TASK]`, `[SUCCESS CRITERIA]` instruction format.
- [x] **P1-3b:** Limitation acknowledged. Line 908: "Child sessions cannot send Grammar updates back to the parent during execution. Results return only when the child completes."
- [x] **P1-3c:** App-layer capability with graceful degradation documented. Line 909: "session.spawn is an app-layer capability (registered by amplifier-app-cli), not a kernel method. The IDD orchestrator must check for its availability via coordinator.get_capability('session.spawn') and fall back to single-agent execution if not registered."

---

### P1-4: Dynamic Composition Engine Specification — PASS

- [x] **P1-4a:** Parser spec present. Lines 915-917: Input (natural language string), Output (structured decomposition with five fields: intent, agents, context, behaviors, trigger), Method (LLM call with Grammar schema as structured output), Prompt structure (presents framework, lists available agents from coordinator.config["agents"]).
- [x] **P1-4b:** Agent resolution specified. Lines 918-919: "Natural language agent descriptions are matched against available agent names and their ## Capabilities sections. If no match, the parser surfaces this as a gap for the human to resolve." Advisory note: context/behavior resolution could be more explicit (minor, non-blocking).
- [x] **P1-4c:** Confirmation flow defined. Lines 920-921: Five-step protocol: parser outputs decomposition -> reporter renders human-readable plan -> human approves/modifies/rejects -> compiler generates YAML -> orchestrator executes.

---

### P1-5: Key Modules Not Referenced — PASS

- [x] **P1-5a:** tool-delegate referenced. Line 926: "tool-delegate (tool-task): The primary mechanism for agent spawning."
- [x] **P1-5b:** tool-mcp referenced. Line 927: "tool-mcp: Model Context Protocol integration. MCP tools are available to agents composed by IDD in the same way they are available to any agent."
- [x] **P1-5c:** Scheduling addressed. Line 928: "Amplifier currently has no built-in scheduler. Temporal triggers like scheduled-weekly assume an external scheduler (cron, CI pipeline, GitHub Actions) that invokes Amplifier with the appropriate context. Building a scheduling module is out of scope for the initial IDD implementation."

---

### P1-6: Context Manager Interaction During Correction — PASS

- [x] **P1-6a:** Full correction mechanics specified. Lines 931-936: Four-step sequence: (1) Update Grammar state internally, (2) Inform LLM via injection hook, (3) Resume execution with updated recipe graph, (4) Emit idd:correction event.
- [x] **P1-6b:** Context manager methods specified. Lines 934-935: Uses per-turn injection hook (ephemeral), NOT add_message() (permanent history), NOT set_messages() (silently ignored).

---

### P1-7: IDD Orchestrator Return Value — PASS

- [x] **P1-7a:** Return strategy specified as option (c). Line 893: "The return type is str per the Orchestrator Protocol -- the IDD orchestrator returns a human-readable summary of the completed intent. Structured results (success criteria status, correction history, resolved primitives) are emitted via the idd:intent_resolved hook event."
- [x] **P1-7b:** idd:intent_resolved payload documented with field names and types. Lines 838-854: JSON schema with intent_name (str), status (enum), success_criteria (array of {name, pass, evidence}), corrections (array of {timestamp, primitive, change}), agents_used (str[]), steps_completed (int), steps_skipped (int), elapsed_seconds (int), summary (str).

---

### P1-8: Hook Priority for IDD Events — PASS

- [x] **P1-8a:** Priorities specified. Lines 938-964: Telemetry at 1 (existing), IDD Grammar injection at 3, tool-policy at 5 (existing), IDD event emission at 10, IDD Layer 2-to-1 reporter at 15. Ordering dependencies clear.
- [x] **P1-8b:** Blocking vs non-blocking documented. Lines 944-966: Grammar injection (priority 3) is blocking. Event emission (priority 10) and reporter (priority 15) are non-blocking observers. Line 966: "A bug in an IDD telemetry hook should never crash the orchestrator."

---

## P2 — Address Before Publishing as Open Spec

### P2-1: Testing Strategy — DEFERRED

Explicitly deferred to build phase. Line 1009: "Detailed testing strategy and test cases."

---

### P2-2: Security Considerations — DEFERRED

Explicitly deferred to build phase. Lines 1010-1011: "Security model (prompt injection, privilege escalation, context leakage mitigations)."

---

### P2-3: Governance and Procedural Requirements — PASS

- [x] **P2-3a:** Governance section present. Lines 992-996: Repos affected (amplifier-bundle-idd, amplifier-foundation, bundle repos), push ordering (core -> foundation -> bundle -> docs), review requirements (per REPOSITORY_RULES.md, cross-team review for foundation changes).
- [x] **P2-3b:** No core changes confirmed. Line 993: "No changes to amplifier-core required."

---

### P2-4: Concurrency and Session Isolation — DEFERRED

Explicitly deferred to build phase. Line 1012: "Concurrency and session isolation semantics."

---

### P2-5: Error Propagation Specifics — DEFERRED

Explicitly deferred to build phase. Line 1013: "Error propagation specifics (tool:error -> Grammar report)."

---

### P2-6: Nested Bundle Compatibility — DEFERRED

Explicitly deferred to build phase. Line 1014: "Nested bundle compatibility (idd:true + non-IDD bundles)."

---

### P2-7: Capability Registration — DEFERRED

Explicitly deferred to build phase. Line 1015: "Capability registration (idd.parse, idd.report, idd.correct)."

---

## Verification Matrix

| # | Item | Auditor | Status |
|---|------|---------|--------|
| P0-1 | coordinator.mount("agents") correction | core-expert | PASS |
| P0-2 | Recipe format reconciliation | foundation-expert | PASS |
| P0-3 | Behaviors vs hooks conflation | amplifier-expert | PASS |
| P1-1 | Agent definition format | amplifier-expert | PASS |
| P1-2 | Orchestrator relationship | foundation-expert | PASS |
| P1-3 | Grammar state to child sessions | core-expert | PASS |
| P1-4 | Dynamic composition engine | foundation-expert | PASS |
| P1-5 | Missing module references | amplifier-expert | PASS |
| P1-6 | Context manager during correction | core-expert | PASS |
| P1-7 | Orchestrator return value | core-expert | PASS |
| P1-8 | Hook priorities | core-expert | PASS |
| P2-1 | Testing strategy | all | DEFERRED |
| P2-2 | Security considerations | all | DEFERRED |
| P2-3 | Governance / procedural | amplifier-expert | PASS |
| P2-4 | Concurrency / isolation | core-expert | DEFERRED |
| P2-5 | Error propagation | core-expert | DEFERRED |
| P2-6 | Nested bundle compatibility | foundation-expert | DEFERRED |
| P2-7 | Capability registration | core-expert | DEFERRED |

**Totals: 12 PASS, 0 FAIL, 6 DEFERRED (all P2, all explicitly scoped to build phase)**

---

## Advisory Notes (Non-Blocking)

1. **Behavior file extensions:** The spec lists behaviors as `.md` files (correct for IDD), but actual foundation behaviors may use different extensions. Minor — resolve during build.
2. **Context/behavior resolution in dynamic composition:** Agent resolution has explicit fallback (surface gap to human). Context and behavior resolution could benefit from the same explicit fallback pattern. Minor — refinement during build.

---

## Next Steps

The spec is approved for implementation. Recommended sequence:
1. Initialize git repo for `amplifier-bundle-idd`
2. Scaffold bundle structure (agents/, behaviors/, context/, recipes/, bundle.md)
3. Begin P0 actions: build the IDD orchestrator, Layer 1-to-2 parser, Layer 2-to-1 reporter
4. Address P2 deferred items as the bundle stabilizes
