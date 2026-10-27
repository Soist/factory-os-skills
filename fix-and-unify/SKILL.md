---
name: fix-and-unify
description: "fix-and-unify skill"
---

## Fix & Unify

## 触发条件

**USER TRIGGER**：用户说「fix everywhere」「unify」「统一修」「全局修」「同样的问题」，或调用 `/fix-and-unify`。
**AUTO TRIGGER**：Claude 完成任何修复（代码、文档、措辞、命名、配置）后，判断被修复的是一个可重复的模式（而非一次性 typo 或刻意独特的设计），则自动触发 Phase 1 提取规则并评估是否需要全局扫描。
**DO NOT TRIGGER**：用户明确说「只改这一处」；或修复的是字面值 typo 无规则可泛化。

---

### Core Principle

**EVERY FIX IS A POLICY, NOT A PATCH.**

When you fix one instance of a problem, you are implicitly defining a rule about how things _should_ work. A single fix without checking the right context is an incomplete fix — it leaves the same violation lurking nearby, waiting to become the next bug report.

**But "right context" ≠ "entire codebase."** Audit smart, not wide. Scope the search to where violations actually live.

### The Four-Phase Framework

#### Phase 1: Extract the Rule

Before writing any code, explicitly name the principle being violated.

1. **Identify the symptom** — What exactly is wrong with the code the user pointed at?
2. **Generalize to a rule** — Ask: _"What general principle, if followed everywhere, would have prevented this?"_
3. **State it crisply** — Write a one-sentence rule in imperative form (e.g., "All alert/modal dialogs must use the shared `<Modal>` component instead of ad-hoc implementations").
4. **Validate with the user** — Present the extracted rule and confirm scope before proceeding. The user may want a narrower or broader scope than you inferred.

**Rule quality checklist:**
- Is it grep-able? (Can you search the codebase for violations?)
- Is it unambiguous? (Would two developers apply it the same way?)
- Is it scoped? (Does it say where it applies — e.g., frontend only, server routes only?)

#### Phase 2: Smart-Scope Audit

**Don't grep the whole codebase. Audit the right context — no more, no less.**

##### Step 1: Determine the blast radius

> 注：下文 `frontend/src/...`、`.interface-design/` 等路径是 React + 设计系统项目的示例，按当前仓库实际结构替换；仓库没有对应物就跳过该项。

Use the rule from Phase 1 and the location of the original fix to pick the tightest scope that could contain violations:

| Signal | Scope to audit | Example |
|---|---|---|
| Rule is about a specific component's API/props | That component's file + its direct consumers (grep for imports) | "Use `variant` prop instead of custom className on `<Badge>`" → `Badge.tsx` + files importing `Badge` |
| Rule is about a UI pattern (modals, alerts, toasts) | `frontend/src/components/` + `frontend/src/pages/` | "All alerts must use `<InlineAlert>`" |
| Rule is about a backend convention (error handling, response shape) | `servers/routes/` or `servers/services/` | "All routes must use `raise AppError()` not raw `HTTPException`" |
| Rule is about data modeling / types | `src/models/` + consumers of those models | "All price fields must be `Decimal`, not `float`" |
| Rule is about config / env access | `config.py` + files that read env vars directly | "Use `config.X` not `os.getenv()`" |
| Rule is about CSS / styling | `frontend/src/index.css` + components using raw values instead of tokens | "Use `--color-*` tokens, not hex literals" |
| Rule is about a single file's internal consistency | Just that file | "All handler functions in this router follow the same try/catch shape" |
| Rule crosses layers (frontend + backend) | Ask user to confirm cross-cutting scope before proceeding | Rare — flag it |

**Heuristic**: Start at the narrowest plausible scope. If you find 0 violations, widen one level. If violations are clustered in one area, don't widen further.

##### Step 2: Execute the search

1. **Pick 1–2 search strategies** appropriate for the scope:
   - Text patterns (e.g., `className="alert"`, raw hex colors)
   - Import/usage patterns (e.g., files importing or not importing a module)
   - Structural patterns (e.g., inline implementations of something that should be shared)
2. **Search within the scoped paths only** — pass the right `path` and `glob` to `Grep`/`Glob`. Do not search docs, generated/vendored code, or unrelated layers unless the rule specifically applies there.

##### Step 3: Catalog violations

Build a concrete list with file:line references:
```
Violation #1: frontend/src/components/Foo.tsx:42 — ad-hoc alert div
Violation #2: frontend/src/components/Bar.tsx:118 — duplicated modal logic
Violation #3: frontend/src/pages/Baz.tsx:205 — inline confirm dialog
```

Classify each:
- **Identical** — Same anti-pattern, straightforward to refactor
- **Analogous** — Similar spirit but different shape; needs judgment
- **Borderline** — Might be intentionally different; flag for user decision

##### Step 4: Present findings before acting

Show the user the violation list and the scope you searched. Let them exclude borderline cases, adjust scope, or say "just fix the original one."

**Audit red flags — stop and reassess if:**
- You find 15+ violations → likely an architecture change; discuss scope with user
- Violations leak into a layer you didn't expect → confirm cross-cutting refactor with user
- The "canonical" implementation doesn't exist yet → you need to create it first (Phase 3)

#### Phase 3: Refactor in a Single Pass

Fix everything at once — no "we'll get to the rest later."

1. **Establish the canonical implementation** — If a shared component/utility/pattern doesn't exist yet, create it first. This becomes the source of truth.
2. **Refactor all violations** — Work through the catalog from Phase 2. For each:
   - Replace the ad-hoc implementation with the canonical one
   - Preserve any _intentional_ local variations (convert them to props/options on the canonical implementation if needed)
   - Verify the refactored code compiles / renders correctly
3. **Handle edge cases** — Some violations may need the canonical implementation to be extended. Do this by adding parameters/variants to the shared component, not by keeping one-off implementations.
4. **Verify holistically** — After all changes:
   - Run the test suite / build
   - Spot-check UI for visual regressions (if frontend)
   - Confirm no imports are broken
5. **Summarize what was done** — Provide a concise change log:
   ```
   Rule: "All confirmation dialogs must use <DeleteConfirmModal>"
   Fixed: 6 files, 4 ad-hoc implementations replaced
   Extended: Added `variant` prop to DeleteConfirmModal for non-delete confirmations
   New: n/a
   ```

#### Phase 4: Mandatory Cleanup Followthrough

Extraction/unification is **not complete** when the new canonical implementation exists. It is only complete after a targeted cleanup pass removes the displaced code and verifies that no second path remains.

1. **Invoke `/cleanup-followthrough` on the touched scope** — at minimum the canonical implementation, all migrated callers, and nearby tests/fixtures.
2. **Delete leftovers, don’t just bypass them**:
   - stale fallback / compatibility branches
   - duplicate transforms / duplicate validation
   - old props / params / refs / state / helper wrappers
   - tests, names, comments, fixtures that still describe the old path
3. **Do not declare success if both paths still exist** — a wrapper/helper extraction that leaves the old implementation alive is an incomplete refactor.
4. **Report net simplification** — call out what code/branches/paths were actually removed, not just what abstraction was added.

### Decision Tree: When NOT to Unify

Not every fix warrants a full audit. Skip Phase 2–3 if:

- **Typo / data fix** — The fix is a literal value correction with no pattern to generalize
- **One-off by design** — The code is intentionally unique (e.g., a migration script, a one-time hack with an expiry)
- **User explicitly requests a point fix** — They say "just fix this one" — do it, but mention that other instances exist

In all other cases, default to the full three-phase flow.

### Anti-Patterns

| Anti-Pattern | Why It's Bad | Do This Instead |
|---|---|---|
| Fix one, leave the rest | Creates inconsistency; the next person copies the wrong version | Audit and fix all |
| Create a new "correct" component but don't migrate old ones | Two competing patterns; codebase diverges | Migrate in the same PR, then run `/cleanup-followthrough` |
| Extract a helper but keep the old logic around "for safety" | Complexity moves instead of shrinking | Delete the displaced path unless a real compatibility requirement remains |
| Refactor without stating the rule | No one knows _why_ things changed; drift resumes | State the rule explicitly in the PR/commit |
| Audit by memory ("I think that's the only place") | You're wrong ~60% of the time | Grep the right scope. Always grep. |
| Grep the entire repo for a component-level rule | Wastes time, floods results with noise | Scope to the layer/directory where violations can live |
| Fix 20 files without user alignment | Scope creep; user may not want all changes | Present the audit, get approval, then refactor |

### Integration with Other Skills

- **bug-fix** → Use Phase 0-1 of that skill to find root cause; then feed the root cause into Phase 1 of this skill to extract the rule
- **frontend-audit** → If the audit phase reveals widespread tech debt, consider running a full `frontend-audit` to prioritize
- **ui-design**（仅当仓库有）→ When the rule involves UI patterns, consult `.interface-design/system.md` and `.claude/skills/ui-design/SKILL.md` to ensure the canonical implementation aligns with the design system
- **update-practices** → If the extracted rule is broadly applicable and should be followed going forward, add it to `PROJECT.md` or `frontend-coding-practices.md`
- **cleanup-followthrough** → Mandatory final step after Phase 3. `fix-and-unify` is not done until the cleanup pass confirms the old path is truly gone.

### Checklist — Before Declaring "Done"

- ☐ Rule is stated in one sentence, in imperative form
- ☐ User approved the rule and audit scope
- ☐ Audit scope justified (not too wide, not too narrow)
- ☐ All violations cataloged with file:line references
- ☐ Borderline cases flagged for user decision
- ☐ Canonical implementation exists (created or identified)
- ☐ All violations refactored to use the canonical implementation
- ☐ `/cleanup-followthrough` completed on the touched scope
- ☐ Old paths / fallback branches / duplicate helpers actually removed
- ☐ Build / tests pass after refactor
- ☐ Change summary provided to user
