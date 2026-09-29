# Build log: 005-put-all-pytest-tests-into-an

## Phase 1: Relocate root pytest modules into tests/
**Status:** done. **Builder:** Claude Code (sdlc-github skill).
**Files changed:** `pyproject.toml`; moved with `git mv`, bytes unchanged: `test_chunking.py`, `test_chunking_simple.py` and `test_strategy_param.py` to `tests/chunking/`, `test_file_watching.py` to `tests/scanner/`, `test_semantic.py` to `tests/semantic/`, `test_read_file.py` and `test_search_natural_language.py` to `tests/server/`.

The seven root-level pytest modules now live under `tests/`, grouped by the area they exercise, and `pyproject.toml` ends with `[tool.pytest.ini_options]` (`testpaths = ["tests"]`, `pythonpath = ["."]`), so a plain `pytest` from the root collects them. No workflow or `pypi-build` script named a root-level test path, so none changed.

- `sdlc_stage.py verify --feature 005-put-all-pytest-tests-into-an --phase 1 --test-command 'python -m pytest -q --ignore=sample-client'`: PASSED on the uncommitted work and again after the commit (scope inside the targets, no frozen file touched, contract matches the approved tag).
- Phase 1 Verify block: exit 0. `python -m pytest --collect-only -q`: 13 tests collected, all under `tests/`.
- `python -m pytest -q --ignore=sample-client`: 13 passed, 1 skipped, the same as before the move. The skip is `tests/semantic/test_semantic.py`, which skips itself at module level without the optional `semantic` extra, as it did at the root.
- The collected tests, compared by file and test name, are the same 13 before and after the move.

**Deviations:** none.
