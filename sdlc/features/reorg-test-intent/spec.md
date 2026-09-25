<!-- sdlc stage=spec model=deepseek-v4.1-flash:cloud from=intent.md@0a7356e -->
## Summary
Move the seven root-level pytest modules into a new top-level `tests/` directory, add `tests/README.md` documenting the layout and run command, and update any explicit references to the moved paths so the same main test suite remains runnable. Contributors get a discoverable main test suite; `sample-client/tests/` remains separate.

## Behaviour
1. Given the repository root contains `test_chunking.py`, `test_chunking_simple.py`, `test_file_watching.py`, `test_read_file.py`, `test_search_natural_language.py`, `test_semantic.py`, and `test_strategy_param.py`, when the change is applied, then each file exists at `tests/<same basename>` and none of those paths exists directly at the repository root.
2. Given the repository root after the change, when listing only the files directly in the root, then no file matching `test_*.py` is present.
3. Given `test_install.ps1`, when the change is applied, then it remains directly in the repository root and is not moved into `tests/`.
4. Given `sample-client/tests/`, when the change is applied, then no file or directory under it is moved, renamed, or edited.
5. Given `tests/README.md` does not exist before the change, when the change is applied, then `tests/README.md` exists.
6. Given `tests/README.md`, when read, then it documents the `tests/` folder layout and the exact command to run the main test suite from the repository root.
7. Given the command documented in `tests/README.md`, when executed from the repository root, then pytest collects and executes the same seven moved test modules that were previously collected as root-level tests.
8. Given the moved test modules, when the documented command is executed, then all tests that passed before the move still pass.
9. Given any CI workflow or configuration file that explicitly names a moved root-level test file or references the old root-level `test_*.py` pattern, when the change is applied, then that reference is updated to the corresponding `tests/...` path or `tests/**` pattern.
10. Given there are no root-level `test_*.py` files to move, when the change is applied, then no move is attempted and `tests/README.md` still exists.
11. Given a listed root-level pytest test file is absent from the branch, when the change is applied, then the move for that file is skipped and the remaining listed files are handled without error.

## Interfaces
No Python function, class, parameter, or return type signatures are added or changed.

File-level interfaces:

| Action | Current path | New path |
| --- | --- | --- |
| Move | `test_chunking.py` | `tests/test_chunking.py` |
| Move | `test_chunking_simple.py` | `tests/test_chunking_simple.py` |
| Move | `test_file_watching.py` | `tests/test_file_watching.py` |
| Move | `test_read_file.py` | `tests/test_read_file.py` |
| Move | `test_search_natural_language.py` | `tests/test_search_natural_language.py` |
| Move | `test_semantic.py` | `tests/test_semantic.py` |
| Move | `test_strategy_param.py` | `tests/test_strategy_param.py` |
| Add | — | `tests/README.md` |
| Modify only if present | `.github/workflows/*.yml` | Update explicit references to moved root test files or old root `test_*.py` patterns to `tests/...` or `tests/**` |
| Modify only if present | `pyproject.toml` or a root pytest config file | Update explicit references to moved root test files to `tests/<basename>` |
| No change | `sample-client/tests/**` | Remains as-is |
| No change | `test_install.ps1` | Remains at repository root |
| No change | — | No `tests/__init__.py` is added by this spec |

`tests/README.md` must contain:
- A layout or folder-structure section describing `tests/` as the main pytest suite location.
- The exact command to run the main suite from the repository root: `uv run pytest tests/`.
- A note that `sample-client/tests/` is separate and uses its own command documented in the root README.

## Out of scope
- Rewriting, refactoring, or adding test logic.
- Reorganizing `sample-client/tests/`.
- Changing the test framework, dependencies, or CI workflows beyond path updates required for discovery.
- Moving `test_install.ps1`.
- Updating the root `README.md` to link to `tests/README.md`.
- Adding `tests/__init__.py`.
- Changing pytest behavior beyond path updates required for the moved tests.

## Open questions
- Folder hierarchy: Assumption: a flat top-level `tests/` directory is sufficient; no subfolders are introduced.
- `sample-client` merge: Assumption: `sample-client/tests/` remains separate and is not merged into the new `tests/` directory.
- Root README link: Assumption: updating the root `README.md` is not required by this change.
- CI and pytest configuration: Assumption: only explicit references to moved paths are updated; if no such references exist, no configuration change is made.
- Documented command: Assumption: `uv run pytest tests/` is the correct command for the main suite. If the repository convention differs, `tests/README.md` must document the equivalent command that targets `tests/`.
