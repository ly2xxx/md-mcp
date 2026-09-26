# AI-native SDLC pipeline (proof of concept)

One GitHub Actions run takes a feature from a one-line idea to a pull request.
Ollama Cloud writes the design documents; a person approves each one, builds
the code phase by phase, and the run checks the build against the plan before
it opens the only pull request.

```text
Run workflow: one-line idea
  │
  ├─ 1 · Write intent.md   ─▶ ✋ Review intent.md   (read, edit on the branch, approve)
  ├─ 2 · Write spec.md     ─▶ ✋ Review spec.md
  ├─ 3 · Write plan.md     ─▶ ✋ Review plan.md      phases, each with targets, frozen
  │                                                  files, a Definition of done and
  │                                                  Verify commands
  ├─ 4 · ✋ Build it, then approve                   you build each phase locally
  │                                                  (Claude Code + sdlc-build skill)
  ├─ 5 · Verify the build   scope, frozen files, every phase's Verify, the test suite
  └─ 6 · Open the pull request                       a draft if verification failed
```

Everything lands on one branch, `feature/<feature>`, in
`sdlc/features/<feature>/`. The ✋ jobs wait on a GitHub environment with a
required reviewer, so the run pauses there until you approve. Waiting jobs use
no runner minutes, and a pause can last up to 30 days.

## Setup (once)

1. **Settings → Environments → New environment** `sdlc-review`. Tick
   **Required reviewers** and add yourself. (Leave "Prevent self-review" off.)
2. **Settings → Actions → General → Allow GitHub Actions to create and approve
   pull requests**, or add an `SDLC_PR_TOKEN` secret (a fine-grained token with
   contents and pull requests write). With the token, CI also runs on the PR.
3. `OLLAMA_API_KEY` is already a secret. Optional variables: `OLLAMA_MODEL`
   (default `deepseek-v4-flash:cloud`) and `OLLAMA_THINK` (`false` to stop a
   reasoning model thinking for minutes).

## Run a feature

1. **Actions → SDLC Pipeline → Run workflow.** Type the idea, leave the rest
   empty. The run is named `SDLC · <idea> · from auto`.
2. **At each ✋ Review job**, open the run. The job before it shows the new
   document in its summary with **View** and **Edit on the branch** links. Edit
   it there if it needs changing, then **Review deployments → Approve**. The next
   stage reads the branch after you approve, so it sees your edits. **Reject**
   stops the run.
3. **At "4 · ✋ Build it, then approve"**, build the plan locally:

   ```bash
   git fetch origin && git switch feature/<feature>
   claude    # then: "use sdlc-build to build phase 1 of <feature>"
   ```

   The `sdlc-build` skill implements one phase, keeps to its targets, runs its
   Verify commands and this check, logs the phase in `build-log.md`, commits and
   stops for your review:

   ```bash
   python .github/actions/sdlc-stage/sdlc_stage.py verify --feature <feature> --phase 1 \
     --test-command "uv run pytest -q --ignore=sample-client"
   ```

   Push each phase. When all are done, approve the Build job.
4. **Verify** checks the whole branch against the plan. **Open the pull request**
   then opens one PR with the phase checklist and the verification report. If a
   check failed the PR is a draft: push the fix and **Re-run failed jobs**.

## Other ways to start

| Run workflow with | Does |
| :-- | :-- |
| idea | a new feature, numbered after the highest existing one |
| idea + feature | revises that feature's intent (with a warning), then spec and plan again |
| feature | the first missing document, or straight to the Build gate if all three exist |
| feature + start | that stage onwards: `spec`, `plan`, or `build` to verify an existing build |

## What the plan must contain

`plan.md` uses the markers from `deterministic-coding/phase_check.py`:

```markdown
## Phase 1: word count on MarkdownFile
<!-- phase: 1 -->
<!-- targets: md_mcp/scanner.py, tests/test_word_count.py -->
<!-- frozen: tests/test_read_file.py -->
**Definition of done:**
- [ ] `tests/test_word_count.py::test_frontmatter_excluded`: spec behaviour 1
**Verify:**
    uv run pytest tests/test_word_count.py -v   (in a bash fence)
```

It also needs a **Coverage** table with one row per "Done when" item in
`intent.md`, so a plan can't quietly drop part of the intent: an item it can't
deliver is marked `NOT COVERED` for you to see at the review. If the model
leaves out a marker, a checklist, a Verify block or a coverage row, the stage
asks it once more, then flags what is still missing in the run summary.

## Guard rails

- **No model-written code runs in Actions.** The model writes documents; people
  approve them and build the code.
- **Scope is mechanical.** Verify fails if the branch changes a file outside
  every phase's `targets`, or any `frozen` file.
- **"Tests pass" is an exit code**, from each phase's Verify block and the whole
  suite, never anyone's opinion.
- **Permissions per job.** Document jobs can push to the feature branch only;
  Verify is read-only; only the last job can open a pull request.

## Known limits

- Environments with required reviewers need a public repository or a paid plan.
- An approval comment doesn't reach the next stage. To steer a stage, edit the
  document on the branch before approving.
- The Verify commands come from the approved plan and run on the runner, so
  read them at the plan review like any other code.
