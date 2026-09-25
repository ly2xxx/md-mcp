# AI-native SDLC pipeline (proof of concept)

Each stage of the lifecycle is a GitHub Actions run that reads the previous
stage's Markdown artifact and writes the next one, using Ollama Cloud. People
approve by merging, never by reading every line the model wrote.

```text
intent.md ──merge──▶ spec stage ──PR──▶ you review, edit, merge
                                            │
                     plan stage ◀───────────┘
                         │
                         └──PR──▶ you review, edit, merge
                                     │
                     build stage ◀───┘  writes code, runs the tests (the gate)
                         │
                         └──PR──▶ you review, merge; CI, BDD eval and the delta summary take over
```

| Stage | Reads | Writes | Who approves |
| :-- | :-- | :-- | :-- |
| Intent | an idea | `intent.md` | you, by committing it to `main` |
| Design | intent | `spec.md` | you, by merging the spec PR |
| Plan | intent, spec, the files they name | `plan.md` with a `## Files` list | you, by merging the plan PR |
| Build | intent, spec, plan, the listed files | code, new tests, `build-report.md` | you, by merging the build PR |
| Test | the build | pass/fail | the test command's exit code, not the model |
| Review | the diff | a PR comment | `commit-delta-summary.yml`, a different model from the builder |

## Try it

1. Merge the PR that adds this folder. Its `features/001-word-count/intent.md`
   lands on `main` and starts the **spec** stage.
2. A PR `sdlc(001-word-count): spec` appears. Read `spec.md`, edit it on the
   branch if needed, and merge. That starts **plan**.
3. Same for `plan.md`. Merging it starts **build**.
4. The build PR carries the code, new tests and `build-report.md`. It is a
   draft titled `[gate failed]` if the tests never passed.

A new feature is a new folder with an `intent.md`, pushed to `main`. To run or
re-run any stage by hand: **Actions → SDLC Pipeline → Run workflow**, with the
folder name and a stage.

## Guard rails

- **The job that runs model-written code can't write to the repo.** `generate`
  has a read-only token and runs the tests with a scrubbed environment. A
  separate `propose` job holds the write token, runs nothing from the model,
  re-checks every path and opens the PR.
- **The build may only touch files in the plan's `## Files` list**, which you
  approved. Nothing under `.github/` or `.git/`, and no path outside the repo.
- **Existing tests are frozen.** The build may add test files, not edit old ones,
  so it can't make the suite pass by weakening it.
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

- One feature per push, with stages strictly in order. Editing `intent.md`
  after its spec exists does not re-run the spec.
- The build writes whole files, so it suits small modules better than large ones.
- Model-written test code can still read the runner's Ollama key from process
  memory. Use a key with a spending limit.
- The action lives here for now. It is written to move unchanged to
  `ly2xxx/.github/actions/sdlc-stage`, next to `commit-delta-summary`.
