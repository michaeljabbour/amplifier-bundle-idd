# IDD Bundle Evaluation: A/B Testing Results

This document records the results of controlled A/B testing between IDD-enabled
and non-IDD Amplifier sessions. Each test used the same prompt in both
conditions, run against the same codebase (`amplifier-bundle-idd` repo), with
the same provider (Anthropic Claude).

**Method**: Four tests covering different task types -- planning/decomposition,
multi-phase technical work, knowledge retrieval, and focused bug hunting. Each
test was run twice: once with the IDD bundle active, once with the standard
Amplifier superpowers bundle only.

---

## Test 1: Planning and Decomposition

**Prompt**: "Break down a code review workflow into steps"

### Non-IDD Session

Produced a clean 8-step prose workflow:

1. Receive
2. Understand
3. Scan
4. Review
5. Test
6. Feedback
7. Iterate
8. Merge

Followed up with: "Are you looking to turn this into something specific?"

The output was accurate and readable, but inert -- a list with no structure for
execution, no success criteria, and no agent mapping.

### IDD Session

Called `idd_decompose` with 88% confidence. Produced:

- **5 measurable success criteria** with clear pass/fail definitions
- **5 agents** mapped to a sequential pipeline: `code-navigator`,
  `bug-hunter`, `test-coverage`, `code-quality-reviewer`, `technical-writer`
- **Context section** with 5 "To Discover" items (unknowns to resolve before
  execution)
- **6 named behaviors**: `sequential-pipeline`, `evidence-based-findings`,
  `severity-classification`, `constructive-feedback`, `comprehensive-summary`,
  `human-checkpoint-before-publish`
- **Explicit scope boundaries** table (in-scope vs. out-of-scope)
- **Trigger conditions** with pre-conditions
- Offered next steps: "Compile to recipe / Refine / Execute now?"

### Verdict: IDD wins decisively

The IDD output is a structured, executable specification. The non-IDD output is
a prose list. The difference is not cosmetic -- the IDD decomposition can be
compiled to a recipe, handed to agents, and verified against success criteria.
The prose list cannot.

---

## Test 2: Multi-Phase Technical Work

**Prompt**: "Our API response times are too slow. Profile endpoints, find
bottlenecks, design caching layer, implement it, verify under 200ms."

### Non-IDD Session

Suggested entering `/brainstorm` mode. Asked three practical grounding
questions:

1. Where is the API? (path/repo)
2. Which endpoints are slow?
3. What are the current response times?

Ready to start working once the questions were answered. Correct instinct to
ground before acting.

### IDD Session

Called `idd_decompose` with 78% confidence. Produced:

- **6 measurable success criteria** (including "no regressions in data
  freshness" -- a criterion the non-IDD session did not surface)
- **8 agents across 5 phases**: Discover/Profile, Design, Implement/Test,
  Review, Verify
- **7 discovery questions** in a table with a "why it matters" column
  explaining the impact of each unknown on the design
- **6 named behaviors**: `measure-before-optimizing`, `document-decisions`,
  `graceful-degradation`, `incremental-implementation`, `verify-with-evidence`,
  `human-checkpoint-before-deploy`
- **Explicit scope boundaries**
- **Confidence explanation**: 78% due to unknowns that affect design choices
  (which endpoints, current latency profile, data freshness requirements)

Both sessions correctly identified that there was no actual API in the
`amplifier-bundle-idd` repo and would need to be pointed at a real codebase.

### Verdict: IDD wins on structure

Both sessions grounded correctly. The IDD session produced a significantly
richer plan: more agents, more criteria, discovery questions with rationale,
and a phased execution model. The non-IDD session asked good questions but
produced no executable structure.

---

## Test 3: Knowledge Retrieval

**Prompt**: "What are the five IDD primitives and how do they relate to each
other?"

### Non-IDD Session

Delegated to `foundation:explorer` (~69K tokens consumed). The explorer read
all repository files to build context. Produced an accurate answer with:

- Primitives table (5 rows)
- 10 pairwise relationships between primitives
- Boundary rules
- Litmus test for correct decomposition

### IDD Session

Delegated to `idd:idd-spec-expert` (~62K tokens consumed). The spec-expert
agent had IDD context pre-loaded through the bundle's knowledge base files.
Produced a thorough answer with:

- Primitives table (5 rows)
- Orthogonality invariant explanation
- Composition rules
- Three-layer architecture diagram (Specification, Composition, Runtime)
- "Why five?" argument from first principles

### Verdict: Tie (slight IDD edge)

Both answers were accurate. The IDD session was slightly more efficient (62K
vs. 69K tokens -- the spec-expert had pre-loaded context instead of exploring
from scratch). The IDD answer was pedagogically richer, explaining *why* the
design is the way it is, not just *what* it is. But both would satisfy the
user's question.

---

## Test 4: Focused Bug Hunting

**Prompt**: "Review the IDD parser module for code quality, find bugs or edge
cases, improve error handling. Write tests for fixes."

### Non-IDD Session

Dispatched 3 agents in parallel:

- `python-dev` for code quality analysis
- `code-intel` for semantic code understanding
- `bug-hunter` for systematic bug reproduction

The `bug-hunter` agent ran live reproduction scripts against the parser,
constructing test inputs that triggered actual failures. Results:

- **10 bugs found**: 3 high severity, 4 medium, 3 low
- **9 fixes applied** directly to the codebase
- **35 new tests** written covering the discovered issues
- **Full test suite**: 216 tests passing

### IDD Session

Dispatched 2 agents:

- `code-intel` for code structure analysis
- `explorer` for broad file reading

Results:

- **8 issues found**: 3 bugs, 5 coverage gaps
- **3 fixes applied**
- **38 new tests** written
- **Full test suite**: 183 tests passing

### Verdict: Non-IDD wins decisively

The non-IDD session with superpowers found more bugs (10 vs. 8), applied more
fixes (9 vs. 3), and produced a larger passing test suite (216 vs. 183). The
key difference was agent selection: `bug-hunter` is purpose-built for this
exact task type and uses live reproduction to confirm bugs before fixing them.
The IDD session's decomposition overhead did not help -- it routed to less
specialized agents and produced fewer concrete results.

---

## Summary

| Test | Task Type | Winner | Margin | Key Differentiator |
|------|-----------|--------|--------|--------------------|
| 1. Code review decomposition | Planning | IDD | Large | Structured executable spec vs. prose list |
| 2. API performance optimization | Multi-phase planning | IDD | Large | 8 agents, 6 criteria, scope table vs. clarifying questions |
| 3. IDD knowledge query | Knowledge retrieval | Tie | Slight IDD edge | Both accurate; IDD more token-efficient |
| 4. Parser bug hunting | Focused execution | Non-IDD | Large | Superpowers' bug-hunter excels at focused technical work |

### Key Insight

IDD and superpowers are **complementary, not competing**.

- **IDD wins on planning and decomposition** -- tasks where structure enables
  better outcomes. Breaking a vague goal into five primitives with measurable
  success criteria and explicit scope boundaries produces specifications that
  can be executed, compiled to recipes, and verified.

- **Superpowers wins on focused technical execution** -- tasks where
  specialized agents (bug-hunter, python-dev, code-quality-reviewer) matter
  more than structural planning. These agents have deep domain expertise that
  no amount of decomposition can replicate.

The ideal workflow uses both: **IDD for decomposition, superpowers for
execution**. The IDD decomposition identifies which agents to call and what
success looks like; the superpowers agents do the actual work.

---

## Architecture Evolution During Testing

The bundle went through a critical simplification during development, informed
by what we learned from the superpowers bundle:

| Version | Architecture | Outcome |
|---------|-------------|---------|
| v0.1-0.2 | Custom orchestrator module (replaced `loop-streaming`) | Worked but fragile; fought the kernel |
| v0.3 | Tool module (`idd_decompose` + `idd_compile`) on standard orchestrator | Simpler, more reliable, composable |

**The key insight**: Superpowers achieves enormous power with zero custom
modules -- it uses context files, tools, hooks, agents, and recipes on the
standard `loop-streaming` orchestrator. IDD follows the same pattern: **power
through content, not machinery replacement**.

The custom orchestrator was removed entirely at v0.3. The LLM decides when to
decompose based on context instructions (`idd-awareness.md`), not because a
custom orchestrator forces it. This is both simpler and more correct -- the LLM
can choose *not* to decompose simple tasks, which a custom orchestrator cannot.

---

## Bug Fixes During Testing

Three runtime bugs were discovered and fixed during live A/B testing:

### 1. Import path errors (3cc81b9)

`ChatRequest` was imported from `amplifier_core.models`, but the actual path is
`amplifier_core.message_models`. Similarly, `ChatMessage` was renamed to
`Message` in amplifier-core. Both imports were corrected.

### 2. Tool return type (3cc81b9)

The tool returned a plain `dict` instead of a `ToolResult` object. The
orchestrator expects `ToolResult` instances from tool execution. Fixed by
wrapping all returns in `ToolResult(success=..., output=...)` with a fallback
for isolated testing.

### 3. Content block format (5f48b47)

`response.content` from the Anthropic provider returns a list of content blocks
(e.g., `[TextBlock(text="...")]`), not a plain string. The parser assumed a
string and failed at runtime. Fixed by extracting text from the first content
block.

All three bugs were caught because the A/B testing exercised real end-to-end
paths that unit tests did not cover.

---

## The Execution Contract

The most impactful change during testing was not a code fix but a single
context file update.

The original `context/idd-awareness.md` described the IDD lifecycle passively:
here are the primitives, here are the tools, use them when appropriate. In
testing, this led to a pattern where the LLM would decompose a task, present
the full decomposition JSON, and ask "What would you like to do next?" --
turning IDD into a planning tool that never executed.

The fix (2fd23be) replaced the passive description with an imperative
**Execution Contract**:

| Phase | Action | Rule |
|-------|--------|------|
| 1. Decompose | Call `idd_decompose` | Present a brief summary, not the full JSON |
| 2. Ground | Resolve unknowns from `context.to_discover` | Do not list discovery items as decoration -- resolve them |
| 3. Execute | Delegate to identified agents | Do not ask "would you like me to execute?" -- the user already asked |
| 4. Verify | Check each success criterion | Report pass/fail with evidence against the original intent |

The contract also specifies when to pause (confidence below 60%, destructive
operations, user explicitly asked for a plan) and lists anti-patterns:

| Anti-pattern | Why it fails |
|-------------|-------------|
| Present full JSON and ask "what next?" | User asked for work, not a plan to admire |
| List discovery items without resolving them | Discovery items are blockers, not decoration |
| Offer a menu (Compile / Refine / Execute?) | Menus transfer responsibility back to the user |
| Stop at 75% confidence | 75% is good enough; unknowns resolve during execution |

This single context file change transformed IDD from a planning tool into an
execution framework. The decomposition became an internal planning step, not the
deliverable. The LLM decomposes, grounds, executes, and verifies in one flow.

---

## Test Environment

- **Provider**: Anthropic Claude (Sonnet 4)
- **Amplifier**: amplifier-core + amplifier-foundation (main branch)
- **IDD bundle**: v0.3.0 (tool module architecture)
- **Comparison bundle**: superpowers (amplifier-foundation, main branch)
- **Test repo**: amplifier-bundle-idd (this repository)
- **Date**: February 2026
