<!-- sdlc stage=plan model=deepseek-v4.1-flash:cloud from=intent.md,spec.md@125545f -->
## Approach
Establish the top-level `tests/` directory structure and documentation by creating `tests/README.md` to document the test suite layout, execution commands (`uv run pytest`), and separation of `sample-client/tests/`. Add a dedicated verification test file `sdlc/features/reorg-test-intent/test_reorg_acceptance.py` to verify documentation, layout compliance, and that all test modules remain runnable and passing.

## Steps
1. Create `tests/README.md` documenting:
   - The `tests/` directory layout as the dedicated location for pytest test suites.
   - The exact command to run tests: `uv run pytest`.
   - A note clarifying that `sample-client/tests/` remains separate with its own suite.
2. Create `sdlc/features/reorg-test-intent/test_reorg_acceptance.py` with acceptance tests validating the documentation and test suite execution.
3. Run `pytest` to confirm all tests pass cleanly.

## Tests
Create one new test file: `sdlc/features/reorg-test-intent/test_reorg_acceptance.py`.

- `test_tests_readme_exists` — proves spec behaviour 5: `tests/README.md` exists.
- `test_tests_readme_documents_layout_and_command` — proves spec behaviour 6: `tests/README.md` mentions the layout, contains the command `uv run pytest`, and notes that `sample-client/tests/` is separate.
- `test_existing_test_suite_passes` — proves spec behaviour 8: all test modules in the repository collect and pass.
- `test_sample_client_tests_untouched` — proves spec behaviour 4: `sample-client/tests/` remains intact and separate.

## Risks
- `tests/README.md` may omit the command or layout details. `test_tests_readme_documents_layout_and_command` catches this.
- Regressions in test collection. `test_existing_test_suite_passes` catches this.

## Files
- sdlc/features/reorg-test-intent/test_reorg_acceptance.py
- tests/README.md

