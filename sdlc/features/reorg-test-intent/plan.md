<!-- sdlc stage=plan model=deepseek-v4.1-flash:cloud from=intent.md,spec.md@125545f -->
## Approach
Create a top-level `tests/` directory, move the seven root-level pytest modules into it without changing their contents, add `tests/README.md` documenting the layout and the exact command `uv run pytest tests/`, leave `test_install.ps1` and `sample-client/tests/` untouched, and add a separate verification test file under the feature folder so the documented main-suite command still collects exactly the seven moved modules.

## Steps
1. Create the `tests/` directory at the repository root if it does not already exist.
2. Move each listed root-level pytest module into `tests/` using `git mv` or equivalent: `test_chunking.py`, `test_chunking_simple.py`, `test_file_watching.py`, `test_read_file.py`, `test_search_natural_language.py`, `test_semantic.py`, and `test_strategy_param.py`. If any listed file is absent, skip that move without error. Do not move `test_install.ps1`.
3. Create `tests/README.md` containing: a folder-layout section describing `tests/` as the main pytest suite location; the exact command `uv run pytest tests/`; and a note that `sample-client/tests/` is separate and uses its own command documented in the root `README.md`.
4. Audit `.github/workflows/*.yml` and `pyproject.toml` for explicit references to the moved root-level filenames or the old root `test_*.py` pattern. If such references exist, update them to `tests/<basename>` or `tests/**`. If none exist, make no configuration changes. Do not edit `sample-client/tests/`. Do not add `tests/__init__.py`.
5. Add the new verification test file `sdlc/features/reorg-test-intent/test_reorg_acceptance.py` with the test functions listed below. This file is outside `tests/`, so `uv run pytest tests/` continues to collect only the seven moved modules.
6. Run `uv run pytest tests/` and `uv run pytest sdlc/features/reorg-test-intent/test_reorg_acceptance.py`; both must pass.

## Tests
Create one new test file: `sdlc/features/reorg-test-intent/test_reorg_acceptance.py`.

- `test_root_has_no_pytest_modules` — proves spec behaviour 2 and 10: the repository root contains no `test_*.py` files and `tests/README.md` exists.
- `test_moved_modules_exist_only_under_tests` — proves spec behaviour 1: all seven listed modules exist at `tests/<same basename>` and none of those basenames exist directly at the repository root.
- `test_test_install_ps1_remains_at_root` — proves spec behaviour 3: `test_install.ps1` is still directly at the repository root and not under `tests/`.
- `test_sample_client_tests_untouched` — proves spec behaviour 4: expected files under `sample-client/tests/` still exist at their original paths, and `git diff --quiet HEAD -- sample-client/tests` succeeds when git is available.
- `test_tests_readme_exists` — proves spec behaviour 5: `tests/README.md` exists.
- `test_tests_readme_documents_layout_and_command` — proves spec behaviour 6: `tests/README.md` mentions the `tests/` layout, contains the exact command `uv run pytest tests/`, and notes that `sample-client/tests/` is separate.
- `test_documented_command_collects_moved_modules` — proves spec behaviour 7: running `uv run pytest tests/ --collect-only -q` lists all seven moved test modules.
- `test_documented_command_passes` — proves spec behaviour 8: running `uv run pytest tests/` exits successfully.
- `test_ci_and_pytest_config_references_updated` — proves spec behaviour 9: `.github/workflows/*.yml` and `pyproject.toml` do not reference the old root-level test filenames without the `tests/` prefix, and any old root `test_*.py` discovery pattern is updated to `tests/**`.
- `test_listed_files_handled_idempotently` — proves spec behaviour 11: for each listed basename, either `tests/<basename>` exists or neither the root nor `tests/` copy exists, meaning absent files are treated as skipped without error.

## Risks
- Missing a moved file could leave a root-level `test_*.py` behind. `test_root_has_no_pytest_modules` and `test_moved_modules_exist_only_under_tests` will catch this.
- `tests/README.md` may omit or misstate the run command. `test_tests_readme_documents_layout_and_command` will catch this.
- Moving tests may break imports if the package is not installed in the `uv run` environment. `test_documented_command_passes` will catch import failures.
- Moving tests may break tests that rely on repository-root working-directory paths such as `test-samples`. `test_documented_command_passes` runs the documented command from the repository root and will catch this.
- CI or pytest configuration may still point at old root paths. `test_ci_and_pytest_config_references_updated` will catch explicit stale references.
- `sample-client/tests/` could be accidentally moved or edited. `test_sample_client_tests_untouched` will catch path removals and, when git is available, edits.
- Adding a test file under `tests/` would change the documented main-suite collection. Keeping the verification file under `sdlc/features/reorg-test-intent/` avoids that; `test_documented_command_collects_moved_modules` verifies only the seven moved modules are collected by `uv run pytest tests/`.

## Files
- sdlc/features/reorg-test-intent/test_reorg_acceptance.py
- tests/README.md
- tests/test_chunking.py
- tests/test_chunking_simple.py
- tests/test_file_watching.py
- tests/test_read_file.py
- tests/test_search_natural_language.py
- tests/test_semantic.py
- tests/test_strategy_param.py
