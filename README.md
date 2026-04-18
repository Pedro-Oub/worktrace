# worktrace

Lightweight workflow memory for Python scripts.

Most scripts run, do their work, and leave nothing behind. worktrace gives your scripts a structured, queryable history — what ran, when, what happened, and whether it succeeded — stored in a local SQLite database with zero configuration.

```python
import worktrace as wt

run = wt.start_run("train_model", tags=["ml", "audio"])
wt.event("training.start", data={"epochs": 1000}, run=run)

# ... your code ...

wt.event("training.done", data={"loss": 0.042}, run=run)
wt.end_run(run, status="success")
```

```bash
$ worktrace runs
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 ID        Name          Status    Duration   Tags
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 3f2a1b4c  train_model   success   4m 12s     ml, audio
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Install

```bash
pip install worktrace
```

Requires Python 3.10+. No external services, no config files — data lives at `~/.worktrace/worktrace.db`.

---

## Core concepts

**Runs** — a run represents one execution of a script or task. It has a name, status, duration, tags, and optional metadata.

**Events** — timestamped things that happened during a run. Think of them as a structured log: `training.start`, `error`, `export.done`. Each event can carry a dict of data and optionally reference a resource.

**Snapshots** — a full state capture of something at a point in time. Where events say *something happened*, snapshots say *here is what it looked like*. Useful for capturing configs, model parameters, or any state you want to compare later.

---

## Write API

```python
import worktrace as wt

# Start a run
run = wt.start_run(
    name="my_script",
    tags=["etl", "production"],
    metadata={"input_file": "data.csv", "rows": 50000},
)

# Emit events
wt.event("fetch.start", resource="db/users", run=run)
wt.event("fetch.done",  resource="db/users", data={"rows": 50000}, run=run)
wt.event("error",       data={"message": "timeout"}, run=run)

# Store a snapshot of something's state
wt.snapshot(
    resource="model/classifier",
    kind="hyperparameters",
    data={"lr": 0.001, "layers": 4},
    run=run,
)

# End the run
wt.end_run(run, status="success")  # or "failed"
```

---

## Read API

```python
from worktrace import query

# Get all events for a resource in the last 2 hours
events = query.events(resource="db/users", since="-2h")

# Get failed runs
runs = query.runs(status="failed")

# Get runs tagged "production" since yesterday
runs = query.runs(tag="production", since="-1d")

# Get all events of a certain type for a run
events = query.events(run_id=run.id, type_prefix="fetch.*")

# Get snapshots for a resource
snaps = query.snapshots(resource="model/classifier", kind="hyperparameters")
```

`since` accepts `-2h`, `-30m`, `-1d`, or any ISO 8601 timestamp.

---

## CLI

```bash
# Watch events live as your script runs (in a second terminal)
worktrace tail
worktrace tail --resource db/users
worktrace tail --type fetch.*

# List runs
worktrace runs
worktrace runs --status failed
worktrace runs --tag production --since -1d

# Inspect a specific run (ID prefix is enough)
worktrace show-run 3f2a1b4c
```

---

## A real example

Here's worktrace added to a data pipeline:

```python
import worktrace as wt

def run_pipeline(input_path: str):
    run = wt.start_run(
        name="etl_pipeline",
        tags=["etl"],
        metadata={"input": input_path},
    )

    try:
        wt.event("fetch.start", resource=f"file/{input_path}", run=run)
        rows = fetch_data(input_path)
        wt.event("fetch.done", resource=f"file/{input_path}",
                 data={"rows": len(rows)}, run=run)

        wt.event("transform.start", run=run)
        result = transform(rows)
        wt.event("transform.done", data={"rows": len(result)}, run=run)

        wt.event("load.start", resource="db/output", run=run)
        load(result)
        wt.event("load.done", run=run)

        wt.end_run(run, status="success")

    except Exception as e:
        wt.event("error", data={"message": str(e)}, run=run)
        wt.end_run(run, status="failed")
        raise
```

Then from the terminal, while or after it runs:

```bash
$ worktrace tail
10:23:01  fetch.start    file/data.csv
10:23:04  fetch.done     file/data.csv    {"rows": 50000}
10:23:05  transform.start
10:23:09  transform.done                  {"rows": 48231}
10:23:09  load.start     db/output
10:23:11  load.done

$ worktrace runs
 ID        Name          Status    Duration   Tags
 a1b2c3d4  etl_pipeline  success   10s        etl

$ worktrace show-run a1b2
  etl_pipeline  a1b2c3d4-...
  Status:   success
  Duration: 10s
  Started:  2024-04-15 10:23:01

  Time      Type              Resource         Data
  10:23:01  fetch.start       file/data.csv
  10:23:04  fetch.done        file/data.csv    {"rows": 50000}
  10:23:05  transform.start
  10:23:09  transform.done                     {"rows": 48231}
  10:23:09  load.start        db/output
  10:23:11  load.done
```

---

## Why worktrace

Most scripts either log to stdout (unstructured, lost after the terminal closes) or to a logging framework (verbose, hard to query). worktrace sits in between: structured enough to query, lightweight enough to drop into any script in two lines.

- **No server.** SQLite file in your home directory.
- **No schema changes.** Add any data you want to the `data={}` dict.
- **No dependencies** beyond `typer` and `rich` for the CLI.
- **Works everywhere Python runs.** Same code on your laptop, a server, or a Raspberry Pi.

---

## License

MIT
