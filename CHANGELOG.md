# Changelog

## 0.1.0 — 2026-04-15

Initial release.

- `start_run()`, `end_run()`, `event()`, `snapshot()` write API
- `query.runs()`, `query.events()`, `query.snapshots()` read API with filtering and relative time (`-2h`, `-1d`)
- CLI: `worktrace tail`, `worktrace runs`, `worktrace show-run`
- SQLite backend with WAL mode for safe concurrent writes
