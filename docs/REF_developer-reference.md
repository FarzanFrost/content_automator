# REF_developer-reference — Developer reference tables

> Reference only. Rules live in `GUIDE_developer.md`.

---

## Reference

### Naming Conventions

| Type | Rule | Do | Don't |
|------|------|----|-------|
| Functions | `snake_case`, verb + noun | `get_item_by_id`, `fetch_schema` | `do_stuff`, `thing` |
| Variables | `snake_case`, intent first, avoid generic names | `item_list`, `config_data` | `data`, `tmp` |
| Booleans | prefix `is_` / `has_` / `can_` / `should_` | `is_valid`, `has_items` | `flag`, `state` |
| Event handlers | prefix `handle_` + target + event | `handle_submit_click`, `handle_filter_change` | `on_click`, `click_handler` |
| Async functions | `snake_case`, action-oriented, name what is fetched or saved | `fetch_item_list`, `save_user_settings` | `get_data`, `load_stuff` |
| Data objects (Classes) | `PascalCase`, context + subject + type | `UserAuthInfo`, `SystemStateMap` | `Payload`, `ThingObject` |
| Files (Modules) | short, all-lowercase, use underscores for readability | `storage_manager.py`, `board_renderer.py` | `utils.py`, `misc.py` |

### Commands

| Command | Purpose |
|---------|---------|
| `python -m src.main` | Local development |
| `.venv\Scripts\python.exe -m pytest` | Run tests (.venv execution) |
| `python -m build` | Production build |
| `python scripts/bump_version.py` | Sync version across all files |

### Version

| Item | Detail |
|------|--------|
| Source of truth | `pyproject.toml` |
| Bump command | `python scripts/bump_version.py` |
| Files auto-updated | `pyproject.toml`, `AGENTS.md`, `docs/*.md` |

### Python Environment & Standards Reference

| Item | Value | Notes |
|------|-------|-------|
| Python Runtime | `>=3.11` | Primary runtime |
| Virtualenv Path | `.venv` | Local project environment |
| Test Framework | `pytest` | Run via `.venv\Scripts\python.exe -m pytest` |
| Formatter & Sorter | `black`, `isort` | Python code formatting and import sorting |
| Type Checker | `mypy` | Strict static type checking |

---

*v0.1.0 — 2026-10-10*
