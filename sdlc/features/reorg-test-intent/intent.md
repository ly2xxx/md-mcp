<!-- sdlc stage=intent model=deepseek-v4.1-flash:cloud from=idea@8df5a06 -->
# Intent: Organize pytest tests into a dedicated folder with README

**Owner:** @ly2xxx · **Status:** proposed (merging this PR approves it)

## Problem
Developers and contributors find the repository root cluttered with scattered pytest test files, making the test suite hard to discover, understand, and run. This slows onboarding and increases the chance that tests are overlooked or executed incorrectly.

## Outcome
All pytest test files currently at the repository root live under a dedicated top-level `tests/` directory (with subfolders if appropriate), and that directory contains a `README.md` explaining the layout and how to run the tests. The root directory no longer contains pytest test files. The test suite remains fully runnable and passes as before.

## Done when
- The repository root contains no files matching `test_*.py` (excluding intentional non-pytest files such as `test_install.ps1`).
- All relocated pytest test files reside under `tests/` (or a clearly named subdirectory within it).
- `tests/README.md` exists and documents the folder structure and the command to run the tests.
- Running the command from `tests/README.md` collects and executes the same set of tests that existed before the move.
- The existing tests still pass.

## Not in scope
- Rewriting, refactoring, or adding test logic; only moving files and adding documentation.
- Reorganizing `sample-client/tests/`, which already has its own structure.
- Changing the test framework, dependencies, or CI workflows beyond any path updates required for test discovery.

## Open questions
- What exact folder hierarchy should be used? Assumption: a top-level `tests/` directory is sufficient; subfolders are optional and can be introduced only if the tests naturally group (e.g., by module).
- Should `sample-client` tests be merged into the new structure? Assumption: no, they remain separate because they are integration/LLM-based tests with their own `pytest.ini` and dependencies.
- Should the main `README.md` be updated to point to the new `tests/README.md`? Assumption: not required by this idea, but a link may be added if it improves discoverability.
