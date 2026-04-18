"""
worktrace CLI

    worktrace tail              — live-poll new events
    worktrace runs              — list runs
    worktrace show-run <id>     — all events for a run
"""

import json
import time
from typing import Optional

import typer
from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich import box

import worktrace.query as query

app = typer.Typer(help="worktrace — workflow memory CLI", add_completion=False)
console = Console()


def _format_duration(started: str, ended: Optional[str]) -> str:
    from datetime import datetime, timezone
    fmt = "%Y-%m-%dT%H:%M:%S.%f%z"

    def parse(s: str):
        for f in ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z"):
            try:
                return datetime.strptime(s, f)
            except ValueError:
                continue
        return datetime.fromisoformat(s)

    try:
        start = parse(started)
        end = parse(ended) if ended else datetime.now(timezone.utc)
        secs = int((end - start).total_seconds())
        if secs < 60:
            return f"{secs}s"
        return f"{secs // 60}m {secs % 60}s"
    except Exception:
        return "?"


def _status_color(status: str) -> str:
    return {"success": "green", "failed": "red", "running": "yellow"}.get(status, "white")


# ---------------------------------------------------------------------------
# worktrace tail
# ---------------------------------------------------------------------------

@app.command()
def tail(
    resource: Optional[str] = typer.Option(None, "--resource", "-r", help="Filter by resource URI"),
    type_prefix: Optional[str] = typer.Option(None, "--type", "-t", help="Filter by event type prefix"),
    interval: float = typer.Option(1.0, "--interval", "-i", help="Poll interval in seconds"),
):
    """Live-poll new events and print them as they arrive."""
    seen: set[str] = set()

    # Seed with existing events so we only show new ones
    for ev in query.events(resource=resource, type_prefix=type_prefix):
        seen.add(ev.id)

    console.print(f"[dim]Watching events... (Ctrl+C to stop)[/dim]")

    try:
        while True:
            for ev in query.events(resource=resource, type_prefix=type_prefix):
                if ev.id not in seen:
                    seen.add(ev.id)
                    data_str = json.dumps(ev.data) if ev.data else ""
                    res = f"[cyan]{ev.resource_uri}[/cyan]  " if ev.resource_uri else ""
                    run = f"[dim]{ev.run_id[:8]}[/dim]  " if ev.run_id else ""
                    console.print(
                        f"[dim]{ev.timestamp[11:19]}[/dim]  "
                        f"[bold]{ev.type}[/bold]  "
                        f"{res}{run}{data_str}"
                    )
            time.sleep(interval)
    except KeyboardInterrupt:
        pass


# ---------------------------------------------------------------------------
# worktrace runs
# ---------------------------------------------------------------------------

@app.command()
def runs(
    tag: Optional[str] = typer.Option(None, "--tag", help="Filter by tag"),
    status: Optional[str] = typer.Option(None, "--status", help="Filter by status: success|failed|running"),
    since: Optional[str] = typer.Option(None, "--since", help="Since: -1h, -2d, or ISO timestamp"),
    name: Optional[str] = typer.Option(None, "--name", help="Filter by run name (partial match)"),
):
    """List runs."""
    results = query.runs(tag=tag, status=status, since=since, name=name)

    if not results:
        console.print("[dim]No runs found.[/dim]")
        raise typer.Exit()

    table = Table(box=box.SIMPLE_HEAVY, show_header=True, header_style="bold")
    table.add_column("ID", style="dim", width=10)
    table.add_column("Name")
    table.add_column("Status", width=10)
    table.add_column("Duration", width=10)
    table.add_column("Tags")
    table.add_column("Started", width=20)

    for r in results:
        color = _status_color(r.status)
        table.add_row(
            r.id[:8],
            r.name,
            f"[{color}]{r.status}[/{color}]",
            _format_duration(r.started_at, r.ended_at),
            ", ".join(r.tags) or "[dim]-[/dim]",
            r.started_at[:19].replace("T", " "),
        )

    console.print(table)


# ---------------------------------------------------------------------------
# worktrace show-run
# ---------------------------------------------------------------------------

@app.command(name="show-run")
def show_run(
    run_id: str = typer.Argument(..., help="Run ID (or prefix)"),
):
    """Show all events for a run."""
    # Support prefix matching
    all_runs = query.runs()
    matched = [r for r in all_runs if r.id.startswith(run_id)]

    if not matched:
        console.print(f"[red]No run found matching '{run_id}'[/red]")
        raise typer.Exit(1)
    if len(matched) > 1:
        console.print(f"[yellow]Ambiguous prefix '{run_id}' matches {len(matched)} runs. Be more specific.[/yellow]")
        raise typer.Exit(1)

    run = matched[0]
    color = _status_color(run.status)

    console.print(f"\n[bold]{run.name}[/bold]  [dim]{run.id}[/dim]")
    console.print(
        f"  Status:   [{color}]{run.status}[/{color}]\n"
        f"  Duration: {_format_duration(run.started_at, run.ended_at)}\n"
        f"  Started:  {run.started_at[:19].replace('T', ' ')}\n"
        f"  Tags:     {', '.join(run.tags) or '-'}"
    )
    if run.metadata:
        console.print(f"  Metadata: {json.dumps(run.metadata)}")

    evs = query.events(run_id=run.id)
    if not evs:
        console.print("\n[dim]No events recorded for this run.[/dim]\n")
        return

    console.print()
    table = Table(box=box.SIMPLE, show_header=True, header_style="bold")
    table.add_column("Time", style="dim", width=10)
    table.add_column("Type")
    table.add_column("Resource", style="cyan")
    table.add_column("Data")

    for ev in evs:
        data_str = json.dumps(ev.data) if ev.data else ""
        table.add_row(
            ev.timestamp[11:19],
            ev.type,
            ev.resource_uri or "",
            data_str,
        )

    console.print(table)
    console.print()
