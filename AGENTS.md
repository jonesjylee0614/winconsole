# Repository Guidelines

## Project Structure & Module Organization
Code lives under `winconsole/`, split into focused modules: `main.py` boots the PyQt6 app, `main_window.py` renders the splitter layout, `session_manager.py` orchestrates lifecycle events, while `terminal_backend.py` and `terminal_widget.py` wrap pywinpty and the Qt widget. Shared models sit in `models.py`, loaders and helpers in `config_loader.py` and `utils.py`. User-facing configs stay in `config/` (`sessions.yaml` for templates, `app.yaml` for UI defaults). Tests mirror the tree inside `tests/`, and `docs/` hosts functional specs like `docs/设计文档.md`.

## Build, Test, and Development Commands
- `python -m venv .venv && source .venv/Scripts/activate`: create an isolated Windows-friendly environment.
- `pip install -r requirements.txt`: install PyQt6, pywinpty, and PyYAML.
- `python -m winconsole.main`: launch the GUI for manual smoke testing.
- `pytest`: run the whole regression suite; append `-k session_manager` for targeted runs.
- `python -m winconsole.config_loader config/sessions.yaml`: quick validation for YAML parsing when editing templates.

## Coding Style & Naming Conventions
Use Python 3.11 syntax, 4-space indentation, and descriptive snake_case for everything except PascalCase Qt widgets. Add type hints and dataclasses as shown in the spec to keep models self-documented. Keep methods short; split UI logic from backend calls. YAML keys follow kebab-free lowercase (`cmd`, `args`, `cwd`). Prefer f-strings, guard platform-specific paths with helpers in `utils.py`, and keep long-running subprocess code behind the backend layer.

## Testing Guidelines
Pytest drives the suite (`tests/test_session_manager.py`, `tests/test_config_loader.py`). Name tests after the behavior under test: `test_<function>_<scenario>`. When adding modules, mirror them with matching test files. Aim to exercise both success paths (session creation) and failure modes (invalid YAML). Use fixtures to simulate Windows paths, and leverage `pytest.mark.skipif` for OS-specific logic.

## Commit & Pull Request Guidelines
Adopt conventional commits (`feat: add terminal widget splitter`), keep summaries under 70 chars, and describe rationale plus key files in the body. Each PR should link to a tracking issue, list manual verification steps (GUI launch, pytest), include screenshots of UI changes, and note updates to configs or docs. Small, topic-focused PRs are easier to review; rebase before opening to keep history linear.

## Security & Configuration Tips
Never check actual credentials into `sessions.yaml`; use placeholders and rely on environment variables referenced via `%VAR%` or `$VAR`. Review `cmd` targets before sharing configs to avoid leaking local paths, and prefer launching WSL tasks through vetted templates instead of ad-hoc commands.
