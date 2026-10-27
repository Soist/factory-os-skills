---
name: triage
description: "Unified entry point for all coding work. Auto-classifies work type (bug, new feature, change feature, refactor), scopes the task, assesses risk, designs TDD plan, and routes to downstream skills. For UI features (new or change) with vague requirements, runs inline UI context gathering and generates a Feature Brief before architecture/TDD phases. USER TRIGGER: user describes any coding task, or says '/triage'. AUTO TRIGGER: when user's request is a non-trivial coding task (bug report, feature request, change request). DO NOT TRIGGER: pure investigation ('why does X happen'), documentation-only changes, or when user gives a precise 1-line instruction."
---

> 注：下文 `frontend/src/...`、`.interface-design/` 等路径是 React + 设计系统项目的示例，按当前仓库实际结构替换；仓库没有对应物就跳过该项。

# Triage — Scope, Architecture, Risk, TDD, Route

Single entry point for all coding work. Classifies what the user wants, scopes it, decides the architecture boundary, assesses risk with the full picture, designs tests against the right layer, then routes to the right execution skills.

**Philosophy**: Think before you code. Every coding task — bug or feature — gets a boundary decision and a test plan before implementation starts. The depth of analysis scales with task complexity.

---

## Output Principle: Stay at Architecture + Behavior Level

The user owns architecture and product-behavior decisions; they do not read the code. The AI handles the code-level translation once architecture and behavior are aligned. Triage output reflects that division of labor.

**What belongs in the output:**
- The decision/rule/state transition the system makes, in product terms ("when X happens, the system should Y").
- The architectural placement: which layer/module/page/flow owns the responsibility, and why.
- At most **one file name or class/component name per item**, used as an anchor so the user can locate the area on a map — not as a code spec.

**What does NOT belong in the output:**
- Function names, parameter signatures, return types, code snippets.
- Framework helper names or idioms (`success_response`, `Annotated[...]`, `OrderServiceDep`, `AdminUser`, hook names, decorator names, etc.).
- "Internal" API shape details (request body keys, ORM field names) unless the user explicitly asked about them.
- Test function names or `pytest::nodeids` — describe what the test *verifies in product terms* instead.

**Why**: once architecture and behavior are confirmed, writing the code is a near-mechanical translation step. There is nothing left for the user to weigh in on at the code level, so surfacing code-level details only adds noise and pushes the conversation away from the decisions the user actually owns. If a question genuinely requires picking between two code-level implementations, lift it back up to the architecture or behavior question that decides it.

---

## Calibration: Scale the Depth

Match analysis depth to task complexity. Read this first — it determines how much of the following phases to run.

| Task scale | Triage depth | Example |
|-----------|-------------|---------|
| **Trivial** (1 file, obvious fix) | Phase 0 + one-liner risk + one-liner TDD + go | "Fix typo in error message" |
| **Small** (2-3 files, clear scope) | Full phases, concise output | "Add validation for negative quantities" |
| **Medium** (cross-layer, multiple files) | Full phases, detailed output | "Add customer management page" |
| **Large** (architectural, many subsystems) | Full phases + recommend splitting into sub-tasks | "Redesign the review flow" |

For **trivial** tasks: collapse output to ~5 lines. Skip Phase 2 (Architecture). Don't produce a wall of text for a one-line fix.

For **large** tasks: recommend breaking into smaller tasks, each triaged separately.

---

## Phase 0: Classify Work Type

Read the user's message and classify into one of:

| Type | Signal words | Key question |
|------|-------------|--------------|
| **Bug** | "broken", "报错", "不对", "regression", error logs, "fix", stack traces | What's wrong and what should happen instead? |
| **New feature** | "add", "新增", "I want", "create a", "build" | What doesn't exist yet that should? |
| **Change feature** | "改", "update", "move", "换成", "change X to Y", "make X do Y" | What exists but should behave differently? |
| **Refactor** | "重构", "clean up", "extract", "split", "consolidate", "rename" | What should stay the same behaviorally but improve structurally? |

**If ambiguous**: state your classification and ask the user to confirm before proceeding.

**UI vagueness check** — after classifying, ask: does this task involve UI (New feature or Change feature), and is the request underspecified (missing layout, interaction, or scope decisions)? If yes, set flag `[UI: vague]`. This triggers UI Context Gathering in Phase 1 before proceeding to Phase 2.

The classification drives which phases are heavy vs. lightweight:

| Phase | Bug | New feature | Change feature | Refactor |
|-------|-----|-------------|----------------|----------|
| Scope | Symptoms + repro | Requirements + affected layers | Current vs. desired behavior | What to restructure |
| Architecture | Where does the fix live? | Where should new logic live? | Does the change reveal a boundary problem? | This IS the boundary work |
| Risk | Change risk + diagnostic confidence | Change risk + solution confidence | Change risk + regression surface | Low (tests must stay green) |
| TDD | Red test that catches the bug | Acceptance tests that define "done" | Tests for changed + unchanged behavior | Verify existing tests pass first |

---

## Phase 1: Scope & Investigate

Consult `docs/investigation-runbook.md` + `CLAUDE.md` to locate relevant files — don't explore blindly.

### For Bug:

1. Clarify **symptoms**, **expected behavior**, **trigger conditions**
2. If description is unclear, **ask immediately** — don't guess
3. Trace the code path, identify root cause
4. State root cause to user

### For New Feature:

1. Identify affected layers at a high level: UI-only? UI + API? Full-stack?
2. Check existing patterns in the codebase that this should follow
3. Identify dependencies and integration points
4. If `[UI: vague]` flag is set → run **UI Context Gathering** (see below) before Phase 2

*(Phase 2 will go deeper on exactly where the logic should live — don't pre-decide the boundary here.)*

### For Change Feature:

1. Document **current behavior** (what it does now)
2. Document **desired behavior** (what it should do)
3. Identify all callers/consumers of the code being changed
4. Assess regression surface: what else could break?
5. If `[UI: vague]` flag is set → run **UI Context Gathering** (see below) before Phase 2

### For Refactor:

1. Document the structural change (before → after)
2. Verify existing test coverage — list which tests cover the code being refactored
3. If coverage is thin, flag it (tests need to be added BEFORE refactoring)

### UI Context Gathering `[UI: vague]`

Runs when `[UI: vague]` is set on New Feature or Change Feature. Think from the user's perspective — what UX would serve them best? — before deciding architecture.

**Step 1 — Detect scope** (silent):
- **UI-only**: Pure frontend change, no new data, no new API calls
- **UI + API**: Needs new or changed endpoints, but no schema change
- **Full-stack**: Needs new UI + API + service logic + possibly DB model changes

**Step 2 — Gather context** (silent — no output to user):

Always read (frontend):
1. `.claude/skills/ui-design/SKILL.md` — design principles, patterns A-H
2. `.interface-design/system.md` — canonical tokens and components
3. `frontend/src/index.css` — existing component classes in `@layer components`
4. List `frontend/src/components/` — existing reusable components
5. List `frontend/src/pages/` — existing pages for pattern reference
6. Relevant existing page — if the request relates to one, read it

Also read when scope is UI + API or Full-stack (backend):
7. List `servers/routes/` — read the most relevant route file for idioms
8. List `servers/services/` — read the most relevant service
9. `servers/dependencies.py` — DI aliases (`OrderServiceDep`, `AdminUser`, etc.)
10. `servers/exceptions.py` — `AppError`, `success_response`, `collection_response` patterns
11. `servers/database.py` — existing models if DB change may be needed

**Step 3 — Calibrate brief size**:

| Task Scale | Brief Format |
|-----------|-------------|
| **Micro** (add a button, tweak layout) | 3-5 bullet points |
| **Small** (new component, new interaction) | Short brief (1-2 sections) |
| **Medium** (new page or workflow, may need API) | Full brief — frontend + backend sections if needed |
| **Large** (redesign, multi-page, major schema change) | Output 2-3 scoping questions only — do NOT proceed to Phase 2 yet |

**Step 4** — Feature Brief is output as an additional section in Phase 6. Template there. Then continue to Phase 2 as normal.

**This phase is investigation only — no code changes.**

---

## Phase 2: Architecture Decision

Establish where the core logic should live. The output of this phase feeds directly into Phase 3 (which areas of the system change → blast radius) and Phase 4 (which layer to test at → test strategy). Getting the boundary right has three compounding benefits:
- **Readability**: a single named place that captures the behavior, so the user (and future readers) can point at one spot to understand the rule
- **Maintainability**: one place to update when requirements change, no hunting through components or layers
- **Testability**: logic at the right layer can be tested cheaply and exhaustively

**Step 1 — Identify the core logic:**
What is the pure computation, decision, validation, or state transition at the heart of this task? (Strip away rendering, events, API calls — what is the actual decision being made?)

**Step 2 — Find the right home:**

| If the core logic is... | It belongs in... | Test at... |
|-------------------------|-----------------|------------|
| Stateless computation / validation / mapping | Pure TS/Python function | Unit test (vitest / pytest) |
| Field-level keyboard routing, advance rules | `src/lib/*.ts` pure function | Unit test |
| Stateful multi-step flow, context-aware | Custom hook | Hook test (vitest RTL) |
| Cross-component wiring / form state machine | Vitest integration | Vitest integration |
| True browser behavior (focus, clipboard, login cookie, cross-page) | Must be E2E | Playwright E2E |

**Step 3 — Identify the gap:**
Where would this logic naturally end up without deliberate extraction? (Inline in component? Buried in event handler?) If there's a gap between "natural home" and "right home", evaluate:

- **Gap is trivial (< 30 min extraction)**: Extract first. Gives you a named boundary that's readable, maintainable, and cheaply testable. Add extraction as the first step of the implementation plan. TDD targets the extracted boundary.
- **Gap is moderate (1-2 hours)**: Flag the tradeoff to the user. Recommend extraction if the behavior has many edge cases or is likely to be updated independently.
- **Already at the right layer / must be E2E**: State why, proceed.

**Output format — REQUIRED, include verbatim in Phase 6 plan (skip only for trivial tasks):**

Per the Output Principle: describe the boundary as a *decision the system makes*, not a function. Each line may use at most one file/component/module name as an anchor so the user can locate the area on a map — no function names, no signatures, no helper names.

```
**Boundary**: [the decision / rule / state transition this captures, in product terms — e.g. "when to auto-advance to the next field while a reviewer types crease-type values"]
**Natural home**: [where this would land by default if nobody thought about it — e.g. "buried inside the blind input form component"]
**Right home**: [the architectural layer that should own it — e.g. "a dedicated frontend rule module separate from the form"; one file/component name as anchor optional] — extraction cost: trivial / moderate / significant
**→ Plan**: [extract first, then test the rule directly | test at component level because the rule is trivially small and only meaningful in context | must E2E because the behavior only exists in a real browser]
```

---

## Phase 3: Risk & Confidence Assessment

### Change Risk (Low / Medium / High)

| Dimension | Evaluation |
|-----------|-----------|
| **Blast radius** | How many files/subsystems? Include any new files from Phase 2's extraction plan. Cross frontend-backend? |
| **Critical path** | Touches OCR pipeline, LLM extraction, review submission, WeChat callback, ERP? Critical path = +1 risk level |
| **Change nature** | Pure addition → Low; Modify existing logic → Medium; Restructure/change data model/state flow → High |
| **Reversibility** | Easy rollback → Low; Affects stored data or API contracts → High |

### Confidence (High / Medium / Low)

**For Bug** — Diagnostic Confidence:

| Level | Meaning | Typical evidence |
|-------|---------|-----------------|
| **High** | Root cause has direct evidence | Logs/stack trace reproducible, code path clear |
| **Medium** | Root cause from reasonable inference | Code analysis + domain knowledge, no direct repro |
| **Low** | Root cause is a guess | Can't reproduce locally, external system/timing/concurrency involved |

**For Feature/Change/Refactor** — Solution Confidence:

| Level | Meaning | Typical evidence |
|-------|---------|-----------------|
| **High** | Solution follows established codebase pattern | Direct precedent exists, reusing existing components |
| **Medium** | Solution is reasonable but involves new patterns | Industry best practice, no direct codebase precedent |
| **Low** | Solution has significant assumptions | Vague requirements, untouched subsystem, multiple valid approaches |

### Output format (concise):

```
Risk: [Low/Medium/High] — [one-line reason]
Confidence: [High/Medium/Low] — [evidence type]
```

### Escalation rules:

- **High risk OR Low confidence** → explicitly warn user, suggest narrowing scope or more investigation
- **Medium + Medium** → normal flow, but TDD coverage must be thorough
- **Low risk + High confidence** → fast-track, lightweight TDD

---

## Phase 4: TDD Design

Every task starts with "what does done look like in test form?" Design the test plan targeting the boundary identified in Phase 2.

### For Bug:

1. **Regression test**: Describe in product terms what input the test sets up and what correct behavior it asserts
2. **Test layer**: unit / API / integration / frontend component / E2E — pick the cheapest layer that can prove the behavior
3. The test must **fail with the bug present** and **pass after the fix**

*(Test file paths and function names are an implementation detail — leave them to the AI when writing the test.)*

### For New Feature:

1. **Acceptance tests**: What tests, when passing, prove the feature is complete?
2. **Layer-appropriate tests** (use the boundary from Phase 2):
   - New API endpoint → API test (request → response contract)
   - New service logic → Unit test (core logic + edge cases)
   - Extracted lib function → Unit test covering all branches + 1 E2E smoke
   - New UI interaction → Integration test or E2E spec
3. **Prioritize**: Which 1-2 tests are the most important to write first?

### For Change Feature:

1. **Behavior preservation tests**: What existing tests must stay green? List them.
2. **Changed behavior tests**: What new/modified tests capture the desired change?
3. **Regression surface**: Any adjacent behaviors that should be explicitly tested?

### For Refactor:

1. **Pre-refactor verification**: List existing tests that must pass before AND after
2. **Coverage gaps**: If existing coverage is thin, which tests to add BEFORE refactoring?
3. No new behavioral tests needed (behavior shouldn't change)

### Output format:

Describe each test as a *behavior the system must satisfy*, in product terms. No `pytest::nodeids`, no test function names. Test layer (unit / API / integration / component / E2E) goes in parentheses so the user sees how the behavior is being pinned down. At most one file/area name as an anchor.

```
## TDD Plan

### Write first (RED):
- [ ] [behavior, in product terms — e.g. "negative quantity is rejected with the Chinese error 「数量必须为正」"] (layer: unit / API / integration / component / E2E)
- [ ] [behavior] (layer)

### Must stay green:
- [ ] [existing behavior that must keep working, in product terms — anchor with the test area if helpful, e.g. "review submission flow"]

### Run after implementation:
- [ ] [test command] — [scope]
```

---

## Phase 5: Skill Route

Based on classification, scope, and architecture decision, determine which skills to invoke and in what order.

### Routing table:

| Work type | Skill chain |
|-----------|------------|
| **Bug** | `/bug-fix` (execution: red → green → report) → `/test-guard` (verify no regression) |
| **Bug (UI interaction/state machine)** | `/bug-fix:walkthrough` (interactive behavior alignment → test → fix) → `/e2e` (visual verify) |
| **New feature (has UI)** | `/ui-design` (reference) → implement → `/test-guard` → `/e2e` |
| **New feature (backend only)** | implement with TDD plan → `/test-guard` |
| **Change feature (has UI)** | implement with TDD plan → `/test-guard` → `/e2e` |
| **Change feature (backend only)** | implement with TDD plan → `/test-guard` |
| **Refactor** | verify existing tests green → refactor → `/test-guard` |

**If Phase 2 recommended extraction**: prepend an extraction step to any chain above. Example: "extract the field-advance rule into a dedicated frontend rule module → then `/bug-fix`". The extraction is implementation step 0, before the main chain begins. Describe what is being extracted in product/architectural terms, not by function name.

### Conditional skills (evaluate and include if applicable):

| Condition | Skill |
|-----------|-------|
| Phase 2 recommended extraction (new file created) | `/code-placement` |
| Fix could be a repeating pattern | `/fix-and-unify` |
| Changed shared infrastructure | `/update-practices` |
| New route file or API shape change | `/api-audit` |
| Wrote or modified tests | `/test-guard:audit` (auto-audit quality) |

### Output format:

```
## Skill Route

0. Extract [the rule / decision, in product terms] into [the architectural layer it belongs in; one file/module name as anchor optional] — from Phase 2
1. `/bug-fix` — red-green execution
2. `/test-guard` — anti-regression + coverage check
3. `/fix-and-unify` — pattern detected, check for siblings
```

*(Step 0 only present if Phase 2 recommended extraction.)*

---

## Phase 6: Present Plan & Checkpoint

Present the full triage result to the user in this format:

```
## Triage: [brief title]

**Type**: [Bug / New feature / Change feature / Refactor]
**Risk**: [Low/Medium/High] — [reason]
**Confidence**: [High/Medium/Low] — [evidence]

### Scope
[2-3 sentences: what's being done and why]

### Root Cause / Approach
[For bug: root cause. For feature/change: approach summary. Keep to 3-5 lines max.]

### Boundary
[From Phase 2 — required for non-trivial tasks. Four lines: the decision in product terms, natural home, right home + extraction cost, → plan. Stay at architecture/behavior level per the Output Principle.]

### Feature Brief
[Only present when [UI: vague] flag was set in Phase 0. Append after Boundary — does not replace it.]

#### Inferred from Codebase (confirm or override)
- **Layout**: [e.g., "full-width table like AdminOrdersPage"]
- **Pattern**: [e.g., "Pattern H (Table) with Pattern D (Batch)" — reference ui-design §4]
- **Reuse**: [existing components/classes — be specific]
- **Density**: [Condensed/Regular/Relaxed]
- **Role**: [who uses this — from ui-design role matrix]

#### Key States
- **Loading**: [skeleton or spinner]
- **Empty**: [empty state copy in Chinese]
- **Error**: [inline alert, toast, or both]

#### Backend (omit for UI-only tasks)

Describe in product/responsibility terms. No framework helper names, no DI jargon, no Pydantic/SQLAlchemy field signatures.

- **Operations**: [what the backend must be able to do, in product terms — e.g. "list customers for a factory, create a pricing rule, delete a rule"]
- **Responsibility**: [new area of responsibility, or extends an existing one — name the service or module as an anchor if it helps]
- **Schema impact**: [new entity / new field on existing entity / no change — describe what it represents, not column names]
- **Who can call it**: [admin only / operator / public]

### TDD Plan
[From Phase 4]

### Skill Route
[From Phase 5]

### Open Questions
[Only if genuinely ambiguous. For each question, include:
- the recommended answer
- a 1-3 line rationale grounded in the user's context, codebase evidence, and industry best practice
- what would change if the user chooses differently
Omit section if none.]
```

**Then wait for user confirmation before executing.**

Rules for the checkpoint:
- **Low risk + High confidence + no open questions** → still present the plan, but say "Ready to execute, confirm?" rather than asking for detailed review
- **High risk OR Low confidence** → explicitly recommend the user review carefully
- **Open questions exist** → do not just list them neutrally; give a recommendation for each one first, then ask the user to confirm or override
- **If a recommendation is strong** (clear codebase precedent or strong industry best practice) → say so explicitly instead of presenting all options as equally good
- **If multiple options are viable** → explain the tradeoff briefly, but still pick one as the default recommendation

---

## Phase 7: Post-Implementation — Execute Skill Chain

**This phase is MANDATORY. Do not report "done" until every skill in the Skill Route has been invoked.**

After implementation is complete:

1. Walk through the Skill Route from Phase 5 **in order**
2. For each skill: invoke it via the Skill tool (e.g. `/test-guard`, `/e2e`)
3. If a skill finds issues → fix them before moving to the next skill
4. Only after ALL skills in the route have run and passed → report completion to the user

**Mandatory three-goal test verdict for Medium/High risk (or Low confidence)**: when Phase 3 rated the change **Risk ∈ {Medium, High}** or **Confidence = Low**, the closeout MUST include and return to the user `/test-guard`'s 三目标自省 (its Phase 4) — not just "tests pass":
- **① prev behavior 未回归** — existing tests green *and* proven to actually exercise the changed path (call out any fake-green where a passing test never reaches the change).
- **② new behavior 正确** — new behavior has behavioral assertions, checked against ANTI_PATTERNS.
- **③ future 不回归** — a mutation / negative-control on the highest-value new test (break the implementation → the test must fail → revert → green), with the evidence shown.

Do not declare "done" on a Medium/High-risk change without this verdict. Delegate to `/test-guard`; do not reinvent it here.

**Why this exists**: The Skill Route is a binding execution plan, not a suggestion. Skipping downstream skills (e.g. `/test-guard`) leads to coverage gaps — such as writing only unit tests when integration tests are needed, or trusting a green suite that never touches the changed path. The whole point of the chain is that each skill catches what the previous one missed.

**Anti-pattern to avoid**: Implementing code, running tests manually, declaring "done" — without invoking the skills that would have caught gaps (missing integration tests, anti-patterns, coverage holes).

**Exception**: If the user explicitly says "skip test-guard" or "that's enough", you may skip. But never skip on your own judgment.

---

## Rules

1. **Never skip Phase 4 (TDD Design)**. Even for trivial tasks, state which test verifies the change — even if it's "existing tests cover this, just run them."

2. **Never start coding before Phase 6 confirmation**. The whole point is to align before execution.

3. **Don't duplicate downstream skills**. Triage scopes and plans; `/bug-fix` executes the red-green cycle; `/test-guard` runs tests + audits quality post-implementation. Don't redo their work.

4. **Consult runbook first**. Use `docs/investigation-runbook.md` and `CLAUDE.md` to locate files. Don't spawn broad exploration agents when the runbook has a map.

5. **Conclusion first**. Lead with the classification and risk, then details. Don't bury the verdict.

6. **Recommendations, not punts**. When triage uncovers open design questions, do not simply bounce them back to the user. Use the codebase context and industry best practice to recommend a default, explain why, and only ask the user to confirm or override when the consequence is meaningful.

7. **Chinese for user-visible content**. Triage output can be English (it's developer-facing), but any user-visible text referenced in the plan (labels, error messages) should be noted in Chinese.

8. **Structurally sound solutions, not patches**. For any code change, propose solutions that are architecturally correct — proper placement, clean abstractions, consistent with existing patterns. Never propose quick-and-dirty patches that "just make it work." Additionally:
   - **Opportunistic cleanup**: If you spot adjacent code that's messy, duplicated, or inconsistent and fixing it carries no risk (same file, covered by tests, obvious improvement), clean it up as part of the change.
   - **Risky but high-ROI cleanup**: If you spot something worth fixing but it's risky (touches other behavior, crosses module boundaries, no test coverage), flag it to the user for approval before including it in scope.

9. **Output stays at architecture + behavior level** (see Output Principle at the top). The user owns architecture and product-behavior decisions; the AI handles the code-level translation once these are aligned. In every phase output:
   - Describe *what the system decides/does* in product terms, and *where the responsibility lives* at the architectural layer.
   - Anchor with at most one file/class/component/module name per item.
   - No function names, no parameter signatures, no code snippets, no framework helper names (e.g. `success_response`, `OrderServiceDep`, `AdminUser`, `Annotated[...]`), no test nodeids.
   - If a question seems to require choosing between two code-level implementations, lift it back up to the architecture or behavior question that decides it, and ask *that*.
