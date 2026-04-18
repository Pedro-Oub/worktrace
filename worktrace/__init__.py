"""
worktrace — public write API.

    run = wt.start_run("my_script", tags=["audio"])
    wt.event("audio.switch_profile", resource="audio/device/WH-1000XM4", data={...}, run=run)
    wt.snapshot("audio/device/WH-1000XM4", kind="pipewire-config", data={...}, run=run)
    wt.end_run(run, status="success")
"""

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from worktrace._db import get_conn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _uid() -> str:
    return str(uuid.uuid4())


@dataclass
class Run:
    id: str
    name: str
    tags: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    started_at: str = field(default_factory=_now)
    status: str = "running"


def start_run(
    name: str,
    tags: list[str] | None = None,
    metadata: dict | None = None,
) -> Run:
    """Start a new run and persist it. Returns a Run you pass to event/snapshot/end_run."""
    run = Run(
        id=_uid(),
        name=name,
        tags=tags or [],
        metadata=metadata or {},
    )
    conn = get_conn()
    with conn:
        conn.execute(
            "INSERT INTO runs (id, name, status, started_at, tags, metadata) VALUES (?,?,?,?,?,?)",
            (run.id, run.name, run.status, run.started_at,
             json.dumps(run.tags), json.dumps(run.metadata)),
        )
    return run


def end_run(run: Run, status: str = "success") -> None:
    """Mark a run as finished with the given status."""
    run.status = status
    conn = get_conn()
    with conn:
        conn.execute(
            "UPDATE runs SET status=?, ended_at=? WHERE id=?",
            (status, _now(), run.id),
        )


def event(
    type: str,
    resource: str | None = None,
    data: dict | None = None,
    run: Run | None = None,
) -> None:
    """Emit a single event."""
    conn = get_conn()
    with conn:
        conn.execute(
            "INSERT INTO events (id, run_id, type, resource_uri, timestamp, data) VALUES (?,?,?,?,?,?)",
            (_uid(), run.id if run else None, type,
             resource, _now(), json.dumps(data or {})),
        )


def snapshot(
    resource: str,
    kind: str,
    data: dict,
    run: Run | None = None,
) -> None:
    """Store a snapshot of a resource's state at this point in time."""
    conn = get_conn()
    with conn:
        conn.execute(
            "INSERT INTO snapshots (id, run_id, resource_uri, kind, data, timestamp) VALUES (?,?,?,?,?,?)",
            (_uid(), run.id if run else None, resource,
             kind, json.dumps(data), _now()),
        )
