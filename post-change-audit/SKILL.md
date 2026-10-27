---
name: post-change-audit
description: "Umbrella post-change closeout skill. After a substantial feature/refactor, inspect the diff, catch anti-patterns and missing follow-through, then drive the change to an elegant, regression-safe final state. USER TRIGGER: 'post change audit', 'next skill', 'what did I miss after this change', '改完后检查', '大改后审计'. AUTO TRIGGER: do not auto-trigger."
---

# Post-Change Audit

Use this after a substantial feature, refactor, deploy-related change, or shared-infra update.

This skill is not a router. It owns closeout.

## Goal

Find what the change left incomplete, fix what should be fixed now, and leave the code in a cleaner, safer, more elegant state.

Success means:

- the changed surface has believable regression protection
- anti-patterns introduced by the change are removed or justified
- stale branches / duplicate paths / incomplete cleanup are gone
- relevant follow-through is actually done, not merely recommended

This is an incremental closeout skill, not a restart-from-zero skill.

## Priority

1. test coverage on the changed surface
2. test quantity on the changed surface
3. test quality
4. implementation path / ownership correctness
5. stale fallback / duplicate path / dead branch cleanup
6. deploy / API / security / frontend best-practice alignment when relevant

Worst case is a fake test suite that passes while missing the real regression.

## Trigger

- USER TRIGGER: `post change audit`, `next skill`, `what did I miss after this change`, `改完后检查`, `大改后审计`
- AUTO TRIGGER: do not auto-trigger
- DO NOT TRIGGER: tiny point fixes, docs-only edits, or cases where one explicit narrow audit is clearly sufficient

## Workflow

1. Reuse what is already known from the current conversation:
   - accepted scope
   - root cause already identified
   - tests already added
   - validations already run
   - fixes already confirmed good
2. Inspect the current diff with `git status --short`, `git diff --stat`, and targeted `git diff`.
2. Issue a regression protection status first:
   `Must add tests | Must strengthen tests | Sufficient`
3. Build a short closeout checklist for this diff only:
   - missing or weak regression tests
   - wrong owner / wrong layer / multiple implementation paths
   - stale fallback / dead branch / duplicate helper / old path still alive
   - deploy / API / security / frontend follow-through
   - missing runbook / practice update
4. Execute only the missing follow-through. Use narrow skills as tools when helpful:
   - `/test-guard` or `/test-guard:audit`
   - `/implementation-path-audit`
   - `/code-placement`
   - `/api-audit`
   - `/deploy-audit`
   - `/security-audit`
   - `/error-handling-audit`
   - `/frontend-audit`
   - `/negative-code-audit`
   - `/fix-and-unify`
   - `/cleanup-followthrough`
   - `/update-practices`
   - `/e2e`
5. Re-check the changed surface and stop only when closeout is genuinely complete or the remaining issue is a real blocker.

## Hard rules

- Do not stop at a recommendation list.
- Do not run a full audit buffet; only act on issues that the current diff actually introduced or exposed.
- Do not redo work that was already completed and already validated in the current thread unless new evidence suggests it is insufficient.
- Prefer gap-filling over repetition: verify prior work briefly, then move to what is still missing.
- If the regression protection status is not `Sufficient`, test remediation is mandatory and comes first.
- Prefer deleting stale code over layering another abstraction on top of it.
- If a new canonical path displaced an old one, cleanup is mandatory.
- If a new canonical usage now exists, update practices.

## Output

```text
## Post-Change Audit

### Change summary
- [surface] — [what changed]

### Regression Protection Status
- [Must add tests | Must strengthen tests | Sufficient] — [reason]

### Findings and actions
- [High/Medium/Low] [problem] — [what was wrong]
  Action: [what was fixed / checked / delegated]

### Closeout status
- Reused from prior work: [what was already done and accepted]
- Done: [what is now fixed / cleaned / verified]
- Remaining: [only true blockers or intentionally deferred items]

### Final state
- [why the changed surface is now in a stronger, cleaner, more elegant state]
```

If this skill changes shared profile assets (skills / memory / instructions), sync them the way the owning repo defines (order-ocr: `venv/bin/python scripts/agent_profile.py migrate-live`; team-skills: `./install.sh`).

Tell the user if a new session is needed for picker/discovery refresh.
