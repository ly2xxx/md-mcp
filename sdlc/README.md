# AI-native SDLC pipeline (proof of concept)

Each stage of the lifecycle is a GitHub Actions run that reads the previous
stage's Markdown artifact and writes the next one, using Ollama Cloud. People
approve by merging, never by reading every line the model wrote.

```text
Run workflow: one-line idea
  └─▶ intent stage ──PR──▶ you review, edit, merge
                                  │
      spec stage   ◀──────────────┘ ──PR──▶ you review, edit, merge
                                                   │
      plan stage   ◀───────────────────────────────┘ ──PR──▶ you review, edit, merge
                                                                    │
      build stage  ◀────────────────────────────────────────────────┘
        writes code, runs the tests (the gate) ──PR──▶ you review, merge;
                                  CI, BDD eval and the delta summary take over
```

| Stage | Reads | Writes | Who approves |
| :-- | :-- | :-- | :-- |
| Intent | your one-line idea | `intent.md` | you, by merging the intent PR |
| Design | intent | `spec.md` | you, by merging the spec PR |
| Plan | intent, spec, the files they name | `plan.md` with a `## Files` list | you, by merging the plan PR |
| Build | intent, spec, plan, the listed files | code, new tests, `build-report.md` | you, by merging the build PR |
| Test | the build | pass/fail | the test command's exit code, not the model |
| Review | the diff | a PR comment | `commit-delta-summary.yml`, a different model from the builder |

## Start a feature

**Actions → SDLC Pipeline → Run workflow**, type a one-line **idea**, leave the
rest empty, and run it. The intent stage creates the next numbered folder (for
example `002-extract-gfm-tables-as-lists-of`) and opens a PR with a drafted
`intent.md`. Edit it on the branch if needed and merge; that starts **spec**.
Each merge after that starts the next stage: spec → plan → build.

The build PR carries the code, new tests and `build-report.md`. It is a draft
titled `[gate failed]` if the tests never passed.

You can still write `intent.md` yourself: push a new folder with one to `main`.

## Change a feature

Run the workflow with an **idea** and the **feature** folder, e.g. "also accept
tables without a header row" and `002-extract-gfm-tables-as-lists-of`. The run
warns that the feature already has an intent, and the PR is titled
`intent (revision)`: its Files changed tab shows exactly what changes, and it
lists the artifacts that merging will regenerate. Close it to keep the current
intent. Merge it and spec, plan and build run again, each as a new PR.

A merge starts the stage after the earliest artifact it changed, so this works
at any level: edit `spec.md` on `main` and plan and build re-run.

## Run one stage by hand

Run the workflow with the **feature** folder and a **stage**. `next` runs the
first stage whose artifact is missing.

## Guard rails

- **The job that runs model-written code can't write to the repo.** `generate`
  has a read-only token and runs the tests with a scrubbed environment. A
  separate `propose` job holds the write token, runs nothing from the model,
  re-checks every path and opens the PR.
- **The build may only touch files in the plan's `## Files` list**, which you
  approved. Nothing under `.github/` or `.git/`, and no path outside the repo.
- **Existing tests are frozen.** The build may add test files, not edit old ones,
  so it can't make the suite pass by weakening it. The exception is a test this
  feature's own earlier build wrote (listed in its `build-report.md`), so a
  revised feature can update its own tests.
- **"The tests passed" is an exit code.** An empty test run (pytest exit 5)
  counts as a failure.
- Each artifact records the stage, model and commit it was generated from.

## Setup

`OLLAMA_API_KEY` is already a repository secret. Then either:

- enable **Settings → Actions → General → Allow GitHub Actions to create and
  approve pull requests**, or
- add a `SDLC_PR_TOKEN` secret: a fine-grained token with contents and pull
  requests write on this repo. PRs opened with it also trigger CI; PRs opened
  with the default token don't.

Optional variables: `OLLAMA_MODEL` (spec and plan) and `OLLAMA_BUILD_MODEL`.

## Known limits of the proof of concept

- One feature per push. Two ideas started before either intent PR is merged
  get the same number (their names still differ).
- The Run workflow form has single-line inputs only, so the idea is one line
  and the model drafts the rest. Edit the intent PR for anything longer.
- The build writes whole files, so it suits small modules better than large ones.
- Model-written test code can still read the runner's Ollama key from process
  memory. Use a key with a spending limit.
- The action lives here for now. It is written to move unchanged to
  `ly2xxx/.github/actions/sdlc-stage`, next to `commit-delta-summary`.
