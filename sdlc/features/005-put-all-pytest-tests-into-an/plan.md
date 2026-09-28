<!-- sdlc stage=plan model=deepseek-v4.1-flash:cloud from=intent.md,spec.md@f5fa854 -->
## Approach
Move the seven root-level `test_*.py` modules byte-for-byte into the prescribed `tests/` tree, then add `[tool.pytest.ini_options]` to `pyproject.toml` with `testpaths = ["tests"]` and `pythonpath = ["."]`. Update any CI workflow that names an old root-level test path, and prove the suite is unchanged by comparing bytes against `HEAD`, checking collection only under `tests/`, and running the full suite without `sample-client`.

## Coverage

| Done when (intent.md) | Spec behaviours | Phase |
| :-- | :-- | :-- |
| All pytest test modules that previously sat at the repository root live under a `tests/` directory, organised so the subject of each test is evident from its path. | 2, 3, 12, 15 | Phase 1 |
| No `test_*.py` pytest module remains at the repository root. | 1 | Phase 1 |
| Test path configuration (`pyproject.toml` / `pytest.ini` / any equivalent) reflects the new layout, so a plain `pytest` from the repository root collects the suite without manual path arguments. | 4, 5, 8 | Phase 2 |
| The set of collected tests is unchanged from before the move — nothing lost, nothing silently skipped, nothing added. | 5, 12 | Phase 2 |
| `pytest` completes with 100% of collected tests passing. | 6, 7 | Phase 2 |
| The existing tests still pass. | 6, 7, 11, 13 | Phase 1, Phase 2 |

## Phase 1: Move all root pytest modules into the tests/ tree
<!-- phase: 1 -->
<!-- targets: test_chunking.py, test_chunking_simple.py, test_strategy_param.py, test_file_watching.py, test_semantic.py, test_read_file.py, test_search_natural_language.py, tests/chunking/test_chunking.py, tests/chunking/test_chunking_simple.py, tests/chunking/test_strategy_param.py, tests/scanner/test_file_watching.py, tests/semantic/test_semantic.py, tests/server/test_read_file.py, tests/server/test_search_natural_language.py -->
<!-- frozen: pyproject.toml, sample-client/pytest.ini, test_install.ps1, md_mcp/**, .github/workflows/** -->

**Goal:** Every root-level `test_*.py` module exists at its prescribed `tests/` path, no root-level `test_*.py` remains, and each moved module is byte-identical and still passes when run explicitly.

**Changes:**
- Create these directories: `tests/chunking/`, `tests/scanner/`, `tests/semantic/`, `tests/server/`.
- Move exactly these files using `git mv` so history and bytes are preserved:
  - `test_chunking.py` → `tests/chunking/test_chunking.py`
  - `test_chunking_simple.py` → `tests/chunking/test_chunking_simple.py`
  - `test_strategy_param.py` → `tests/chunking/test_strategy_param.py`
  - `test_file_watching.py` → `tests/scanner/test_file_watching.py`
  - `test_semantic.py` → `tests/semantic/test_semantic.py`
  - `test_read_file.py` → `tests/server/test_read_file.py`
  - `test_search_natural_language.py` → `tests/server/test_search_natural_language.py`
- Do not edit any moved file. Do not add `__init__.py`, `conftest.py`, `pytest.ini`, or any new helper. If an import fails, stop and revise this plan; do not add a shim in Phase 1 because Phase 2 supplies `pythonpath = ["."]`.
- `tests/scanner/test_file_watching.py` will keep its existing `Path(__file__).parent / "test_data"` behaviour, so a runtime directory `tests/scanner/test_data/` may appear. That is an unchanged test artifact, not a test module.

**Definition of done:**
- [ ] `tests/chunking/test_chunking.py`, `tests/chunking/test_chunking_simple.py`, `tests/chunking/test_strategy_param.py`, `tests/scanner/test_file_watching.py`, `tests/semantic/test_semantic.py`, `tests/server/test_read_file.py`, and `tests/server/test_search_natural_language.py` exist.
- [ ] `test_chunking.py`, `test_chunking_simple.py`, `test_strategy_param.py`, `test_file_watching.py`, `test_semantic.py`, `test_read_file.py`, and `test_search_natural_language.py` no longer exist at repository root.
- [ ] Each moved file is byte-identical to the pre-move file in `HEAD`. The `cmp` checks in Verify prove spec behaviours 2 and 3.
- [ ] `python -m pytest tests/chunking/test_chunking.py tests/chunking/test_chunking_simple.py tests/chunking/test_strategy_param.py tests/scanner/test_file_watching.py tests/semantic/test_semantic.py tests/server/test_read_file.py tests/server/test_search_natural_language.py -v` exits 0. This proves the moved modules import and their tests pass (spec 6, 15).
- [ ] `test_install.ps1`, `sample-client/pytest.ini`, and every file under `md_mcp/` are unchanged (`git diff --exit-code -- test_install.ps1 sample-client/pytest.ini md_mcp/` exits 0). This proves spec behaviours 9, 10, 11.

**Verify:**
```bash
python -m pytest tests/chunking/test_chunking.py tests/chunking/test_chunking_simple.py tests/chunking/test_strategy_param.py tests/scanner/test_file_watching.py tests/semantic/test_semantic.py tests/server/test_read_file.py tests/server/test_search_natural_language.py -v
test ! -e test_chunking.py
test ! -e test_chunking_simple.py
test ! -e test_strategy_param.py
test ! -e test_file_watching.py
test ! -e test_semantic.py
test ! -e test_read_file.py
test ! -e test_search_natural_language.py
git show HEAD:test_chunking.py | cmp - tests/chunking/test_chunking.py
git show HEAD:test_chunking_simple.py | cmp - tests/chunking/test_chunking_simple.py
git show HEAD:test_strategy_param.py | cmp - tests/chunking/test_strategy_param.py
git show HEAD:test_file_watching.py | cmp - tests/scanner/test_file_watching.py
git show HEAD:test_semantic.py | cmp - tests/semantic/test_semantic.py
git show HEAD:test_read_file.py | cmp - tests/server/test_read_file.py
git show HEAD:test_search_natural_language.py | cmp - tests/server/test_search_natural_language.py
git diff --exit-code -- test_install.ps1 sample-client/pytest.ini md_mcp/
```

**Attempt budget:** 3 failed attempts, then stop and revise this plan instead of retrying.

## Phase 2: Add pytest path configuration and update CI paths if present
<!-- phase: 2 -->
<!-- targets: pyproject.toml, .github/workflows/*.yml -->
<!-- frozen: tests/**, sample-client/pytest.ini, test_install.ps1, md_mcp/** -->

**Goal:** Plain `pytest` from the repository root collects only the moved tests under `tests/`, excludes `sample-client`, and the full suite passes; any CI workflow that names an old root-level test file points at its new path.

**Changes:**
- `pyproject.toml`: Add this exact block in a valid TOML position (for example after `[project.urls]`):
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```
- `.github/workflows/*.yml`: For each workflow file, if it contains any literal old root-level test module path, replace that literal with the new path from the mapping. Mapping:
  - `test_chunking.py` → `tests/chunking/test_chunking.py`
  - `test_chunking_simple.py` → `tests/chunking/test_chunking_simple.py`
  - `test_strategy_param.py` → `tests/chunking/test_strategy_param.py`
  - `test_file_watching.py` → `tests/scanner/test_file_watching.py`
  - `test_semantic.py` → `tests/semantic/test_semantic.py`
  - `test_read_file.py` → `tests/server/test_read_file.py`
  - `test_search_natural_language.py` → `tests/server/test_search_natural_language.py`
  Do not change any other workflow logic. If no old literal exists, leave the file unchanged.
- Do not add `pytest.ini`, `conftest.py`, or any new test file. Do not edit anything under `tests/`.

**Definition of done:**
- [ ] `pyproject.toml` contains exactly `[tool.pytest.ini_options]` with `testpaths = ["tests"]` and `pythonpath = ["."]`.
- [ ] `python -m pytest --collect-only -q` from the repository root exits 0 and every collected node ID starts with `tests/`. No node ID starts with `test_` and no node ID contains `sample-client`. This proves spec behaviours 1, 4, 5, 8, 12.
- [ ] `python -m pytest -q` exits 0 and all collected tests pass. This proves spec behaviours 6, 7.
- [ ] `python -m pytest -q --ignore=sample-client` exits 0 and collects at least one test.
- [ ] `sample-client/pytest.ini` still contains `testpaths = tests/step_defs` and `bdd_features_base_dir = tests/features`, unchanged (`git diff --exit-code -- sample-client/pytest.ini`).
- [ ] `test_install.ps1` and every file under `md_mcp/` are unchanged (`git diff --exit-code -- test_install.ps1 md_mcp/`). This proves spec behaviours 9, 10, 11.
- [ ] No CI workflow references an old root-level test module path. The grep in Verify proves spec behaviour 14.

**Verify:**
```bash
python -m pytest --collect-only -q
python -m pytest -q
python -m pytest -q --ignore=sample-client
! python -m pytest --collect-only -q | grep -q 'sample-client'
! python -m pytest --collect-only -q | grep -E '^test_.*\.py::'
! python -m pytest --collect-only -q | grep -E '^[^:]+::' | grep -v '^tests/'
! grep -R -n -E '(^|[^/])test_(chunking|chunking_simple|strategy_param|file_watching|semantic|read_file|search_natural_language)\.py' .github/workflows
git diff --exit-code -- sample-client/pytest.ini test_install.ps1 md_mcp/
```

**Attempt budget:** 3 failed attempts, then stop and revise this plan instead of retrying.

## Risks
- `tests/scanner/test_file_watching.py` creates `tests/scanner/test_data/` at runtime. Phase 1’s `git diff --exit-code` does not see untracked directories, so this will not fail the phase, but the builder should not commit that directory.
- `tests/semantic/test_semantic.py` skips at module level when `sentence-transformers` is absent. Phase 2’s collection check still passes because the module contributes zero collected tests in that environment. If a later environment installs the `semantic` extra, the same module adds its 14 tests; the set is unchanged relative to that environment.
- A CI workflow may contain an old root-level test path. Phase 2’s grep check fails immediately if one remains, so the builder must apply the mapping before the phase passes.
- `python -m pytest --collect-only -q` can exit 0 even if the collected set is wrong. The Phase 2 shell checks enforce no root-level or `sample-client` node IDs and that all collected nodes are under `tests/`.

## Open questions
- The approved spec forbids adding new test functions or test modules (behaviours 12 and 13). This plan therefore does not add a new meta-test file; the phase tests are the moved test modules themselves plus the `pytest --collect-only` and shell checks in Verify. If the pipeline requires an additional pytest test file, that would contradict the approved spec and needs a spec change.
- The contents of `.github/workflows/*.yml` are not available in the provided repository excerpt. Assumption: no workflow invokes pytest with explicit root-level `test_*.py` paths. Phase 2’s grep check fails if one does, and the builder updates it using the mapping above.
- In the verification environment the `semantic` extra is not installed, so `tests/semantic/test_semantic.py` contributes zero collected tests. The expected collected node IDs are the 13 tests in `tests/chunking/`, `tests/scanner/`, and `tests/server/`:
  - `tests/chunking/test_chunking.py::test_basic_chunking`
  - `tests/chunking/test_chunking.py::test_search`
  - `tests/chunking/test_chunking.py::test_real_files`
  - `tests/chunking/test_chunking.py::test_large_content`
  - `tests/chunking/test_chunking_simple.py::test_basic`
  - `tests/chunking/test_chunking_simple.py::test_search`
  - `tests/chunking/test_chunking_simple.py::test_large_section`
  - `tests/chunking/test_strategy_param.py::test_strategy_validation`
  - `tests/chunking/test_strategy_param.py::test_keyword_search`
  - `tests/chunking/test_strategy_param.py::test_comparison_ready`
  - `tests/scanner/test_file_watching.py::test_file_watching`
  - `tests/server/test_read_file.py::test_read_file`
  - `tests/server/test_read_file.py::test_file_not_found`

## Hand back
When every phase is built and its Verify block passes:
1. Create `sdlc/features/005-put-all-pytest-tests-into-an/build-log.md` with one section per phase, in order. Head each one `## Phase <n>: <title>`, then list the files changed, the Verify command you ran and its result, and any deviation from this plan (or "none").
2. Commit it and push it to `feature/005-put-all-pytest-tests-into-an`.
