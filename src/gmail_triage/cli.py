from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import click

from . import auth
from .classify.categories import CANONICAL
from .classify.features import classify
from .config import load_config
from .gmail_api import GmailClient

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except AttributeError:
    pass

STATE_DIR = Path.cwd() / ".gmail-triage"
CONFIG_FILE = Path.cwd() / "config.yml"


def _config() -> dict:
    return load_config(CONFIG_FILE)


def _client() -> GmailClient:
    creds = auth.get_credentials(STATE_DIR)
    return GmailClient(creds)


def _parse_date(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d")


def _resolve(since, until, hours):
    try:
        from .gmail_api import _resolve_window
        return _resolve_window(since, until, hours)
    except ValueError as e:
        raise click.UsageError(str(e))


def _echo_json(payload) -> None:
    click.echo(json.dumps(payload, ensure_ascii=False, indent=2, default=str))


def _window_flags(func):
    func = click.option("--hours", type=int, default=None, help="Fetch last N hours (mutually exclusive with --since/--until).")(func)
    func = click.option("--until", type=str, default=None, help="ISO date, e.g. 2026-01-01. Gmail 'before' filter.")(func)
    func = click.option("--since", type=str, default=None, help="ISO date, e.g. 2026-01-01. Gmail 'after' filter.")(func)
    func = click.option("--limit", type=int, default=100, help="Max messages to fetch.")(func)
    func = click.option("--full", is_flag=True, help="Fetch full message bodies (default: snippet only).")(func)
    return func


@click.group()
def cli():
    """Read Gmail read-only and classify messages for AI agents."""


@cli.command()
@click.option("--client-file", type=click.Path(), default=None, help="Path to OAuth client JSON.")
def auth_run(client_file):
    """Run the one-time OAuth flow and save token.json."""
    auth.get_credentials(STATE_DIR, client_file)
    click.echo("Authenticated. Token saved to .gmail-triage/token.json")


@cli.command("inbox")
@_window_flags
@click.option("--json", "as_json", is_flag=True, help="Emit raw message list as JSON.")
def inbox_cmd(since, until, hours, limit, full, as_json):
    """Fetch messages in the window. Read-only."""
    client = _client()
    since_dt = _parse_date(since) if since else None
    until_dt = _parse_date(until) if until else None
    _resolve(since_dt, until_dt, hours)
    messages = client.fetch(
        since=since_dt,
        until=until_dt,
        hours=hours,
        max_results=limit,
        include_body=full,
    )
    payload = [m.to_features(include_body=full) for m in messages]
    if as_json:
        _echo_json(payload)
        return
    for m in payload:
        click.echo(f"[{m['date']}] {m['from']} - {m['subject']} :: {m['snippet']}")


@cli.command("classify")
@_window_flags
@click.option("--json", "as_json", is_flag=True, help="Emit classified features as JSON.")
def classify_cmd(since, until, hours, limit, full, as_json):
    """Run deterministic rules and emit features for the agent's LLM pass."""
    config = _config()
    client = _client()
    since_dt = _parse_date(since) if since else None
    until_dt = _parse_date(until) if until else None
    _resolve(since_dt, until_dt, hours)
    messages = client.fetch(since=since_dt, until=until_dt, hours=hours, max_results=limit, include_body=full)
    features = [classify(m, config, include_body=full) for m in messages]

    from .gmail_api import build_query
    query, resolved_since, resolved_until = build_query(since_dt, until_dt, hours)

    if as_json:
        _echo_json({
            "query": query,
            "window": {
                "since": resolved_since.isoformat() if resolved_since else None,
                "until": resolved_until.isoformat() if resolved_until else None,
            },
            "count": len(features),
            "indeterminate": sum(1 for f in features if f["rule_indeterminate"]),
            "messages": features,
        })
        return

    for f in features:
        status = "?" if f["rule_indeterminate"] else f["rule_category"]
        click.echo(f"[{status}] {f['date']} {f['from']} - {f['subject']}")


@cli.command("report")
@_window_flags
def report_cmd(since, until, hours, limit):
    """Human summary of classification grouped by category."""
    config = _config()
    client = _client()
    since_dt = _parse_date(since) if since else None
    until_dt = _parse_date(until) if until else None
    _resolve(since_dt, until_dt, hours)
    messages = client.fetch(
        since=since_dt,
        until=until_dt,
        hours=hours,
        max_results=limit,
    )
    features = [classify(m, config) for m in messages]

    counts: dict[str, list[dict]] = {c: [] for c in CANONICAL}
    indeterminate: list[dict] = []
    for f in features:
        cat = f["rule_category"]
        (counts.setdefault(cat, []) if cat else indeterminate).append(f)

    click.echo(f"Messages: {len(features)}")
    for cat in CANONICAL:
        group = counts.get(cat, [])
        if not group:
            continue
        click.echo(f"\n[{cat}] {len(group)}")
        for f in group:
            click.echo(f"  - {f['date']} {f['from']} - {f['subject']}")

    if indeterminate:
        click.echo(f"\n[unresolved-by-rules] {len(indeterminate)}")
        for f in indeterminate:
            click.echo(f"  - {f['date']} {f['from']} - {f['subject']}")
        click.echo("\nRun `gmail-triage classify --json` and classify the unresolved ones with the skill rubric.")


@cli.command("config")
def config_cmd():
    """Print the merged config."""
    _echo_json(load_config(CONFIG_FILE))
