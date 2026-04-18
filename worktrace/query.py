"""
worktrace — read API.

    from worktrace import query

    events = query.events(resource="audio/device/WH-1000XM4", since="-2h")
    runs   = query.runs(tag="xtts", status="failed")
"""

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional


def _parse_since(since: str) -> str:
    """
    Parse a relative or absolute time string into a UTC ISO timestamp.
    Accepts: "-2h", "-30m", "-1d", or any ISO 8601 string.
    """
    since = since.strip()
    if since.startswith("-"):
        value, unit = int(since[1:-1]), since[-1]
        delta = {"h": timedelta(hours=value),
                 "m": timedelta(minutes=value),
                 "d": timedelta(days=value)}[unit]
        return (datetime.now(timezone.utc) - delta).isoformat()
    return since  # assume ISO string


@dataclass
class Event:
    id: str
    run_id: Optional[str]
    type: str
    resource_uri: Optional[str]
    timestamp: str
    data: dict


@dataclass
class Run:
    id: str
    name: str
    status: str
    started_at: str
    ended_at: Optional[str]
    tags: list[str]
    metadata: dict


@dataclass
class Snapshot:
    id: str
    run_id: Optional[str]
    resource_uri: str
    kind: str
    data: dict
    timestamp: str


def events(
    resource: str | None = None,
    since: str | None = None,
    type_prefix: str | None = None,
    run_id: str | None = None,
) -> list[Event]:
    """Query events with optional filters."""
    from worktrace._db import get_conn

    clauses, params = [], []

    if resource:
        clauses.append("resource_uri = ?")
        params.append(resource)
    if since:
        clauses.append("timestamp >= ?")
        params.append(_parse_since(since))
    if type_prefix:
        clauses.append("type LIKE ?")
        params.append(type_prefix.rstrip("*") + "%")
    if run_id:
        clauses.append("run_id = ?")
        params.append(run_id)

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    sql = f"SELECT * FROM events {where} ORDER BY timestamp ASC"

    conn = get_conn()
    rows = conn.execute(sql, params).fetchall()
    return [
        Event(
            id=r["id"],
            run_id=r["run_id"],
            type=r["type"],
            resource_uri=r["resource_uri"],
            timestamp=r["timestamp"],
            data=json.loads(r["data"]),
        )
        for r in rows
    ]


def runs(
    tag: str | None = None,
    status: str | None = None,
    since: str | None = None,
    name: str | None = None,
) -> list[Run]:
    """Query runs with optional filters."""
    from worktrace._db import get_conn

    clauses, params = [], []

    if status:
        clauses.append("status = ?")
        params.append(status)
    if since:
        clauses.append("started_at >= ?")
        params.append(_parse_since(since))
    if name:
        clauses.append("name LIKE ?")
        params.append(f"%{name}%")

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    sql = f"SELECT * FROM runs {where} ORDER BY started_at DESC"

    conn = get_conn()
    rows = conn.execute(sql, params).fetchall()

    result = []
    for r in rows:
        tags_list = json.loads(r["tags"])
        # Filter by tag in Python — simpler than JSON SQL queries
        if tag and tag not in tags_list:
            continue
        result.append(Run(
            id=r["id"],
            name=r["name"],
            status=r["status"],
            started_at=r["started_at"],
            ended_at=r["ended_at"],
            tags=tags_list,
            metadata=json.loads(r["metadata"]),
        ))
    return result


def snapshots(
    resource: str | None = None,
    run_id: str | None = None,
    kind: str | None = None,
) -> list[Snapshot]:
    """Query snapshots with optional filters."""
    from worktrace._db import get_conn

    clauses, params = [], []

    if resource:
        clauses.append("resource_uri = ?")
        params.append(resource)
    if run_id:
        clauses.append("run_id = ?")
        params.append(run_id)
    if kind:
        clauses.append("kind = ?")
        params.append(kind)

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    sql = f"SELECT * FROM snapshots {where} ORDER BY timestamp DESC"

    conn = get_conn()
    rows = conn.execute(sql, params).fetchall()
    return [
        Snapshot(
            id=r["id"],
            run_id=r["run_id"],
            resource_uri=r["resource_uri"],
            kind=r["kind"],
            data=json.loads(r["data"]),
            timestamp=r["timestamp"],
        )
        for r in rows
    ]
