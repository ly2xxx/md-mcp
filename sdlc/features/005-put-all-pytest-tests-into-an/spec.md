<!-- sdlc stage=spec model=deepseek-v4.1-flash:cloud from=intent.md@b130a07 -->
## Summary
All root-level pytest test modules move into a new `tests/` tree whose subdirectories mirror the `md_mcp` area under test. `pyproject.toml` gains pytest path configuration so `pytest` from the repository root still collects and runs the same suite without manual path arguments. Test contents, assertions, coverage, `test_install.ps1`, and `sample-client` tests do not change.

## Behaviour
1. Given the repository root after the change, when files matching `test_*.py` are listed, then no such file exists at the repository root.
2. Given the pre-change root pytest modules, when their new locations are inspected, then each exists at exactly the path in the Interfaces table and no root-level counterpart remains.
3. Given any moved test module, when its bytes are compared with the pre-change root module of the same name, then the contents are byte-identical.
4. Given `pyproject.toml`, when pytest loads configuration from the repository root, then it contains `[tool.pytest.ini_options]` with `testpaths = ["tests"]` and `pythonpath = ["."]`, regardless of whether any pytest configuration existed before.
5. Given a clean checkout, when `pytest --collect-only -q` runs from the repository root with no path arguments, then pytest exits 0 and collects exactly the pre-change repository-root `test_*.py` test set, excluding `sample-client/tests`, with each node ID now under `tests/`.
6. Given a clean checkout, when `pytest` runs from the repository root with no path arguments, then pytest exits 0 and 100% of collected tests pass.
7. Given a clean checkout, when `pytest` runs from the repository root with no path arguments and no network access, then collection and execution succeed without network access, secrets, or manual steps.
8. Given `sample-client`, when `pytest` runs from the repository root with no path arguments, then no test node under `sample-client/` is collected.
9. Given `sample-client`, when `pytest` runs from `sample-client/` using its own `pytest.ini`, then its `testpaths = tests/step_defs` and `bdd_features_base_dir = tests/features` remain unchanged.
10. Given `test_install.ps1`, when the change is applied, then its path and content remain unchanged.
11. Given `md_mcp/`, when the change is applied, then no production module under `md_mcp/` is added, renamed, moved, or deleted.
12. Given the `tests/` tree, when test discovery runs, then no pre-change test module is missing, no new test module is added beyond the moved modules, and no empty placeholder test module is present.
13. Given any repository file outside the moved test modules and pytest path configuration, when the change is applied, then no test function, fixture, assertion, or test discovery pattern is added, removed, or modified.
14. Given any CI workflow or repository script that invokes pytest with explicit root-level `test_*.py` paths, when the change is applied, then those arguments reference the corresponding `tests/...` paths and the workflow logic is otherwise unchanged.
15. Given a moved test module, when it is collected from its new location, then it imports `md_mcp` modules as before without requiring a new shared `conftest.py` or helper module; if an import-only shim is unavoidable, it adds no fixtures, assertions, or test behaviour.

## Interfaces
No Python function, class, parameter, or return type changes are introduced. The interface changes are file paths and pytest configuration.

`pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

Moved test modules:

| Previous path | New path |
| --- | --- |
| `test_chunking.py` | `tests/chunking/test_chunking.py` |
| `test_chunking_simple.py` | `tests/chunking/test_chunking_simple.py` |
| `test_strategy_param.py` | `tests/chunking/test_strategy_param.py` |
| `test_file_watching.py` | `tests/scanner/test_file_watching.py` |
| `test_semantic.py` | `tests/semantic/test_semantic.py` |
| `test_read_file.py` | `tests/server/test_read_file.py` |
| `test_search_natural_language.py` | `tests/server/test_search_natural_language.py` |

Resulting `tests/` tree:

```text
tests/
  chunking/
    test_chunking.py
    test_chunking_simple.py
    test_strategy_param.py
  scanner/
    test_file_watching.py
  semantic/
    test_semantic.py
  server/
    test_read_file.py
    test_search_natural_language.py
```

`sample-client/pytest.ini` and `test_install.ps1` are unchanged.

## Out of scope
- Rewriting, merging, deleting, or adding test cases, fixtures, or assertions.
- Improving coverage, changing test frameworks, or converting any test style.
- Moving `test_install.ps1`.
- Restructuring `sample-client/tests`.
- Renaming or reorganising `md_mcp` production modules, or any non-test source change.
- Build, release, or CI workflow redesign beyond the minimum path updates needed for pytest to keep working.
- Adding new fixtures or shared test helper modules beyond an import-only shim if required.

## Open questions
- Exact `tests/` subfolder mapping. Assumption: use the mapping and tree in Interfaces.
- Whether root `pytest` should collect `sample-client/tests`. Assumption: no; `testpaths = ["tests"]` keeps it separate, and `sample-client/pytest.ini` remains its entry point.
- Whether a shared `conftest.py` or helper module is introduced. Assumption: only if a moved module cannot import after relocation; any such file is import-only and introduces no new fixture or assertion behaviour.
- Whether `test_install.ps1` is a pytest module. Assumption: no; it remains at the repository root untouched.
- Whether config belongs in `pyproject.toml` or a new `pytest.ini`. Assumption: `pyproject.toml`, using `[tool.pytest.ini_options]`.
