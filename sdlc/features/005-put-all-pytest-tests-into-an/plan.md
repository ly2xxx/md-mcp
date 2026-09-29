<!-- sdlc stage=plan model=deepseek-v4.1-flash:cloud from=intent.md,spec.md@6abfed1 -->
## Approach
Add pytest path configuration to `pyproject.toml`, move the seven root-level pytest modules into the exact `tests/` subfolders from the spec without changing their bytes, and update any CI or repository script that still invokes an explicit root-level `test_*.py` path. No test functions, fixtures, assertions, or `md_mcp` production modules change.

## Coverage
| Done when (intent.md) | Spec behaviours | Phase |
| :-- | :-- | :-- |
| All pytest test modules that previously sat at the repository root live under a `tests/` directory, organised so the subject of each test is evident from its path. | 2, 12, 15 | Phase 1 |
| No `test_*.py` pytest module remains at the repository root. | 1 | Phase 1 |
| Test path configuration (`pyproject.toml` / `pytest.ini` / any equivalent) reflects the new layout, so a plain `pytest` from the repository root collects the suite without manual path arguments. | 4, 5, 8 | Phase 1 |
| The set of collected tests is unchanged from before the move — nothing lost, nothing silently skipped, nothing added. | 3, 5, 7, 8, 12, 13, 15 | Phase 1 |
| `pytest` completes with 100% of collected tests passing. | 6, 7 | Phase 1 |
| The existing tests still pass. | 6, 9, 10, 11, 13, 14, 15 | Phase 1 |

## Phase 1: Relocate root pytest modules into tests/
<!-- phase: 1 -->
<!-- targets: pyproject.toml, test_chunking.py, tests/chunking/test_chunking.py, test_chunking_simple.py, tests/chunking/test_chunking_simple.py, test_strategy_param.py, tests/chunking/test_strategy_param.py, test_file_watching.py, tests/scanner/test_file_watching.py, test_semantic.py, tests/semantic/test_semantic.py, test_read_file.py, tests/server/test_read_file.py, test_search_natural_language.py, tests/server/test_search_natural_language.py, .github/workflows/*.yml, pypi-build/*.sh -->
<!-- frozen: sample-client/**, test_install.ps1, md_mcp/**, test-samples/** -->

**Goal:** A plain `python -m pytest` from the repository root collects the same tests as before, now only under `tests/`, with no root-level pytest modules left behind.

**Changes:**
- `pyproject.toml`: append exactly this new table at the end of the file, changing nothing else:
  ```toml
  [tool.pytest.ini_options]
  testpaths = ["tests"]
  pythonpath = ["."]
  ```
- Move these files without editing their bytes, using the editor move/rename operation or `git mv`:
  - `test_chunking.py` → `tests/chunking/test_chunking.py`
  - `test_chunking_simple.py` → `tests/chunking/test_chunking_simple.py`
  - `test_strategy_param.py` → `tests/chunking/test_strategy_param.py`
  - `test_file_watching.py` → `tests/scanner/test_file_watching.py`
  - `test_semantic.py` → `tests/semantic/test_semantic.py`
  - `test_read_file.py` → `tests/server/test_read_file.py`
  - `test_search_natural_language.py` → `tests/server/test_search_natural_language.py`
- In every file matching `.github/workflows/*.yml` and `pypi-build/*.sh`, if a line containing `pytest` still references any root-level path from the mapping above, replace only that path with the corresponding `tests/...` path. Preserve every other command, flag, comment, and workflow step. If a file has no such root-level `pytest` reference, leave it byte-identical.
- Do not edit `sample-client/**`, `test_install.ps1`, or any file under `md_mcp/**`.

**Definition of done:**
- [ ] `tests/chunking/test_chunking.py::test_basic_chunking`, `::test_search`, `::test_real_files`, `::test_large_content`: moved byte-identically and execute from the new path; proves spec behaviours 2, 3, and 15.
- [ ] `tests/chunking/test_chunking_simple.py::test_basic`, `::test_search`, `::test_large_section`: moved byte-identically and execute from the new path; proves spec behaviours 2, 3, and 15.
- [ ] `tests/chunking/test_strategy_param.py::test_strategy_validation`, `::test_keyword_search`, `::test_comparison_ready`: moved byte-identically and execute from the new path; proves spec behaviours 2, 3, and 15.
- [ ] `tests/scanner/test_file_watching.py::test_file_watching`: moved byte-identically; its own cleanup stops and joins `server._observer`, and the test creates `tests/scanner/test_data` at runtime via `Path(__file__).parent / "test_data"`; the Verify block removes that generated directory afterward.
- [ ] `tests/semantic/test_semantic.py`: moved byte-identically; when `sentence_transformers` is unavailable the existing module-level `pytest.skip(..., allow_module_level=True)` still skips the whole module, matching pre-move collection.
- [ ] `tests/server/test_read_file.py::test_read_file`, `::test_file_not_found`: moved byte-identically; `test_read_file` writes and unlinks `test-samples/test-decision.md` itself, and the Verify block removes any leftover file.
- [ ] `tests/server/test_search_natural_language.py`: moved byte-identically; it defines only `main()` and therefore contributes zero pytest node IDs, exactly as before the move.
- [ ] CLI: `python -m pytest --collect-only -q` exits 0 and contains no `sample-client` node; proves spec behaviours 4, 5, and 8.
- [ ] CLI: `python -m pytest -q --ignore=sample-client` exits 0 with all collected tests passing or skipping according to the existing module-level skip; proves spec behaviours 6 and 7.
- [ ] CLI: no root-level `test_*.py` file remains; proves spec behaviour 1.
- [ ] CLI: `find tests -name 'test_*.py'` returns exactly the seven expected paths and no placeholder test module; proves spec behaviours 2 and 12.
- [ ] CLI: every moved module is byte-identical to its approved-tag source; proves spec behaviour 3.
- [ ] CLI: `md_mcp`, `sample-client/pytest.ini`, and `test_install.ps1` are unchanged versus the approved tag; proves spec behaviours 9, 10, and 11.
- [ ] CLI: no `.github` or `pypi-build` line that invokes `pytest` still uses an explicit root-level test path from the mapping; proves spec behaviour 14.

**Verify:**
```bash
set -euo pipefail

# No root-level pytest modules remain.
test -z "$(find . -maxdepth 1 -name 'test_*.py' -print)"

# Exactly the seven expected moved modules exist under tests/.
test "$(find tests -name 'test_*.py' -print | sort)" = "$(printf '%s\n' \
  tests/chunking/test_chunking.py \
  tests/chunking/test_chunking_simple.py \
  tests/chunking/test_strategy_param.py \
  tests/scanner/test_file_watching.py \
  tests/semantic/test_semantic.py \
  tests/server/test_read_file.py \
  tests/server/test_search_natural_language.py \
  | sort)"

# Moved modules are byte-identical to the approved pre-move versions.
git show sdlc/005-put-all-pytest-tests-into-an/approved:test_chunking.py | cmp - tests/chunking/test_chunking.py
git show sdlc/005-put-all-pytest-tests-into-an/approved:test_chunking_simple.py | cmp - tests/chunking/test_chunking_simple.py
git show sdlc/005-put-all-pytest-tests-into-an/approved:test_strategy_param.py | cmp - tests/chunking/test_strategy_param.py
git show sdlc/005-put-all-pytest-tests-into-an/approved:test_file_watching.py | cmp - tests/scanner/test_file_watching.py
git show sdlc/005-put-all-pytest-tests-into-an/approved:test_semantic.py | cmp - tests/semantic/test_semantic.py
git show sdlc/005-put-all-pytest-tests-into-an/approved:test_read_file.py | cmp - tests/server/test_read_file.py
git show sdlc/005-put-all-pytest-tests-into-an/approved:test_search_natural_language.py | cmp - tests/server/test_search_natural_language.py

# pyproject.toml has the exact pytest path configuration.
grep -q '^\[tool.pytest.ini_options\]$' pyproject.toml
grep -A2 '^\[tool.pytest.ini_options\]$' pyproject.toml | grep -q '^testpaths = \["tests"\]$'
grep -A2 '^\[tool.pytest.ini_options\]$' pyproject.toml | grep -q '^pythonpath = \["\."\]$'

# Collection uses tests/ only, excludes sample-client, and still has no tests
# collected from the main-only regression module.
python -m pytest --collect-only -q
test -z "$(python -m pytest --collect-only -q | grep 'sample-client' || true)"
test -z "$(python -m pytest --collect-only -q | grep 'test_search_natural_language' || true)"

# Full root-level suite passes.
python -m pytest -q --ignore=sample-client

# Unchanged files.
test -z "$(git diff --name-only sdlc/005-put-all-pytest-tests-into-an/approved -- md_mcp sample-client/pytest.ini test_install.ps1 || true)"

# CI/scripts must not still invoke pytest with explicit root-level test paths.
python - <<'PY'
from pathlib import Path

mapping = {
    "test_chunking.py": "tests/chunking/test_chunking.py",
    "test_chunking_simple.py": "tests/chunking/test_chunking_simple.py",
    "test_strategy_param.py": "tests/chunking/test_strategy_param.py",
    "test_file_watching.py": "tests/scanner/test_file_watching.py",
    "test_semantic.py": "tests/semantic/test_semantic.py",
    "test_read_file.py": "tests/server/test_read_file.py",
    "test_search_natural_language.py": "tests/server/test_search_natural_language.py",
}

paths = []
for root in (Path(".github"), Path("pypi-build")):
    if not root.exists():
        continue
    paths.extend(root.rglob("*.yml"))
    paths.extend(root.rglob("*.yaml"))
    paths.extend(root.rglob("*.sh"))

bad = []
for path in paths:
    if not path.is_file():
        continue
    for lineno, line in enumerate(path.read_text(errors="replace").splitlines(), 1):
        if "pytest" not in line:
            continue
        for old, new in mapping.items():
            if old in line and new not in line:
                bad.append(f"{path}:{lineno}: {line.strip()}")

if bad:
    print("\n".join(bad))
    raise SystemExit(1)
PY

# Clean up artifacts produced by the existing test modules.
rm -f test-samples/test-decision.md
rm -rf tests/scanner/test_data
```

**Attempt budget:** 3 failed attempts, then stop and revise this plan instead of retrying.

## Risks
- Missing `pythonpath = ["."]` would break imports of `md_mcp` from the moved tests; Phase 1 Verify runs the full suite and collection.
- Omitting a moved module or adding a placeholder `test_*.py` would change the collected set; Phase 1 Verify checks the exact seven-file `find` result.
- Accidentally editing a test while moving it would violate byte-identical requirements; Phase 1 Verify uses `cmp` against the approved tag.
- `sample-client` tests could be collected by accident; `testpaths = ["tests"]` plus the `sample-client` collection check prevents that.
- `test_semantic.py` may skip when `sentence-transformers` is unavailable; this matches pre-move behaviour and still exits 0.
- `test_file_watching.py` creates `tests/scanner/test_data` at runtime; the phase's test itself stops the observer, and Verify removes the generated directory afterward.
- CI or scripts could still invoke root-level test paths; the Phase 1 CI/script check fails if an explicit root-level `pytest` path remains.

## Open questions
None.

## Hand back
When every phase is built and its Verify block passes:
1. Create `sdlc/features/005-put-all-pytest-tests-into-an/build-log.md` with one section per phase, in order. Head each one `## Phase <n>: <title>`, then list the files changed, the Verify command you ran and its result, and any deviation from this plan (or "none").
2. Commit it and push it to `feature/005-put-all-pytest-tests-into-an`.
