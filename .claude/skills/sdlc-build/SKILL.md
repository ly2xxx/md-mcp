---
name: sdlc-build
description: Build one phase of an approved SDLC feature plan (sdlc/features/<feature>/plan.md) on its feature/<feature> branch - implement only that phase's targets, never touch its frozen files, run its Verify commands and the phase check, log the result, then stop for review. Use when asked to build, implement or continue a phase or a feature from the SDLC pipeline.
---

# Build one phase of an SDLC plan

The SDLC Pipeline workflow wrote and got approval for `intent.md`, `spec.md` and
`plan.md` in `sdlc/features/<feature>/`, on the branch `feature/<feature>`. It is
now waiting at **"4 · ✋ Build it, then approve"**. You build the plan with the
developer one phase at a time. When every phase is done and pushed, they approve
that job, and the workflow verifies the branch and opens the pull request.

## Before the first phase

1. `git fetch origin && git switch feature/<feature>` (pull if it exists locally).
2. Read `intent.md`, `spec.md` and `plan.md`. The plan is the contract. If it is
   wrong or can't be built as written, say so and stop: fixing the plan is the
   developer's call, not an edit you make to get unstuck.
3. Make sure the project is installed: `uv sync` or `uv venv && uv pip install -e . pytest`.

## For each phase (only the one asked for)

1. Read the phase's markers: `<!-- targets: ... -->` is the only set of files you
   may create, modify, move or delete. `<!-- frozen: ... -->` must not change at
   all. `*` does not cross `/`; `**` does.
2. Implement the phase and write the tests its **Definition of done** names.
3. Run the phase's **Verify** block exactly as written. Iterate until it passes,
   within the phase's attempt budget. If the budget runs out, stop and write down
   which assumption in the plan was wrong. Never edit a frozen file or weaken a
   test to get to green; that is an escalation, not a fix.
4. Run the mechanical check on the uncommitted work:
   ```bash
   python .github/actions/sdlc-stage/sdlc_stage.py verify --feature <feature> --phase <n> --test-command "uv run pytest -q --ignore=sample-client"
   ```
   It fails on any file outside the phase's targets, any frozen file touched, a
   failing Verify command or a failing suite.
5. Append to `sdlc/features/<feature>/build-log.md`:
   - `## Phase <n>: <name>`, status, and the files changed.
   - What was built, in two or three sentences.
   - The exact verification command and its result.
   - Any deviation from plan.md, and whether plan.md was amended or the
     deviation stands. One or the other, never neither.
6. Commit (`sdlc(<feature>): phase <n>`) and push. Then stop and ask the
   developer to review before the next phase.

## After the last phase

Tell the developer to approve **"4 · ✋ Build it, then approve"** in the waiting
workflow run (Review deployments). The run then checks the whole branch against
the plan and opens the pull request, as a draft if anything failed.
