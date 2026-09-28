<!-- sdlc stage=intent model=deepseek-v4.1-flash:cloud from=idea@fc02723 -->
# Intent: Consolidate pytest tests into a structured tests/ directory

**Owner:** @ly2xxx · **Status:** proposed (approving the review gate approves it)

## Problem
The repository currently keeps its pytest suites as loose `test_*.py` files at the repository root, sitting alongside packaging, docs and shell/PowerShell scripts. Contributors cannot tell at a glance which tests cover which part of `md_mcp`, and the root directory grows noisier with every new test. This makes the suite harder to navigate, review and extend.

## Outcome
Every pytest test module lives under a single, predictable `tests/` directory at the repository root, with subfolders that make the area under test obvious (for example mirroring the `md_mcp` modules). Running `pytest` from the repository root still collects the same set of tests as before the move, and all of them pass. No test behaviour, assertion or coverage changes — only location and the path configuration needed to find them.

## Done when
- All pytest test modules that previously sat at the repository root live under a `tests/` directory, organised so the subject of each test is evident from its path.
- No `test_*.py` pytest module remains at the repository root.
- Test path configuration (`pyproject.toml` / `pytest.ini` / any equivalent) reflects the new layout, so a plain `pytest` from the repository root collects the suite without manual path arguments.
- The set of collected tests is unchanged from before the move — nothing lost, nothing silently skipped, nothing added.
- `pytest` completes with 100% of collected tests passing.
- The existing tests still pass.

## Not in scope
- Rewriting, merging, deleting or adding test cases, fixtures or assertions.
- Improving coverage, changing test frameworks, or converting any test style.
- Moving `test_install.ps1`, which is an installer script check rather than a pytest module.
- Restructuring `sample-client/tests` (its own `pytest.ini`, BDD features and step definitions).
- Renaming or reorganising `md_mcp` production modules, or any non-test source change.
- Build, release or CI workflow redesign beyond the minimum path updates needed for pytest to keep working.

## Open questions
- Does "all pytest tests" include the separate `sample-client/tests` suite? *Assumption: no — it is a self-contained client test project with its own config, so it stays where it is.*
- What exact internal layout should `tests/` use? *Assumption: subfolders mirroring the `md_mcp` package areas they exercise, with any cross-cutting tests at `tests/` root.*
- Should a shared `conftest.py` or helper module be introduced during the move? *Assumption: only if an existing test file genuinely cannot import after relocation; no new fixture design work.*
- Does `test_install.ps1` count as a pytest test? *Assumption: no, and it is left untouched.*
