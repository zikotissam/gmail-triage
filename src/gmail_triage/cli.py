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

LABEL_CHOICES = ["inbox", "spam", "sent", "draft", "trash", "archive", "all", "unread", "starred"]


def _config() -> dict:
    return load_config(CONFIG_FILE)


def _client(account: str = "default") -> GmailClient:
    creds = auth.get_credentials(STATE_DIR, account=account)
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


def _local_iso(dt: str | None) -> str | None:
    if not dt:
        return None
    try:
        parsed = datetime.fromisoformat(dt)
    except ValueError:
        return dt
    if parsed.tzinfo is None:
        return dt
    return parsed.astimezone().isoformat()


def _window_flags(func):
    func = click.option("--hours", type=int, default=None, help="Fetch last N hours (mutually exclusive with --since/--until).")(func)
    func = click.option("--until", type=str, default=None, help="ISO date, e.g. 2026-01-01. Gmail 'before' filter (exclusive).")(func)
    func = click.option("--since", type=str, default=None, help="ISO date, e.g. 2026-01-01. Gmail 'after' filter.")(func)
    func = click.option("--limit", type=int, default=100, help="Max messages to fetch.")(func)
    func = click.option("--full", is_flag=True, help="Fetch full message bodies (default: snippet only).")(func)
    func = click.option("--unread", is_flag=True, help="Only unread messages.")(func)
    func = click.option("--label", type=str, default=None, help=f"Scope: one of {', '.join(LABEL_CHOICES)} or a custom label.")(func)
    func = click.option("--query", type=str, default=None, help="Extra Gmail query terms, e.g. 'from:paypal has:attachment'.")(func)
    return func


@click.group()
@click.option("--account", type=str, default="default", help="Gmail account to use (multi-account).")
@click.pass_context
def cli(ctx, account):
    """Read Gmail read-only and classify messages for AI agents."""
    ctx.ensure_object(dict)
    ctx.obj["account"] = account


@cli.command()
@click.option("--client-file", type=click.Path(), default=None, help="Path to OAuth client JSON.")
@click.pass_context
def auth_run(ctx, client_file):
    """Run the one-time OAuth flow and save token.json for an account."""
    account = ctx.obj["account"]
    auth.get_credentials(STATE_DIR, client_file, account=account)
    click.echo(f"Authenticated account '{account}'. Token saved to .gmail-triage/{account}/token.json")


@cli.command("inbox")
@_window_flags
@click.option("--json", "as_json", is_flag=True, help="Emit raw message list as JSON.")
@click.pass_context
def inbox_cmd(ctx, since, until, hours, limit, full, unread, label, query, as_json):
    """Fetch messages in the window. Read-only."""
    account = ctx.obj["account"]
    client = _client(account)
    since_dt = _parse_date(since) if since else None
    until_dt = _parse_date(until) if until else None
    _resolve(since_dt, until_dt, hours)
    messages = client.fetch(
        since=since_dt,
        until=until_dt,
        hours=hours,
        max_results=limit,
        include_body=full,
        label=label,
        unread_only=unread,
        extra=query,
    )
    payload = [m.to_features(include_body=full) for m in messages]
    if as_json:
        _echo_json(payload)
        return
    for m in payload:
        click.echo(f"[{_local_iso(m['date'])}] {m['from']} - {m['subject']} :: {m['snippet']}")


@cli.command("classify")
@_window_flags
@click.option("--json", "as_json", is_flag=True, help="Emit classified features as JSON.")
@click.pass_context
def classify_cmd(ctx, since, until, hours, limit, full, unread, label, query, as_json):
    """Run deterministic rules and emit features for the agent's LLM pass."""
    account = ctx.obj["account"]
    config = _config()
    client = _client(account)
    since_dt = _parse_date(since) if since else None
    until_dt = _parse_date(until) if until else None
    _resolve(since_dt, until_dt, hours)
    messages = client.fetch(since=since_dt, until=until_dt, hours=hours, max_results=limit, include_body=full, label=label, unread_only=unread, extra=query)
    features = [classify(m, config, include_body=full) for m in messages]

    from .gmail_api import build_query
    query_str, resolved_since, resolved_until = build_query(since_dt, until_dt, hours, label=label, unread_only=unread, extra=query)

    if as_json:
        _echo_json({
            "query": query_str,
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
        click.echo(f"[{status}] {_local_iso(f['date'])} {f['from']} - {f['subject']}")


@cli.command("report")
@_window_flags
@click.option("--format", "fmt", type=click.Choice(["text", "md"]), default="text", help="Output format (text or markdown).")
@click.option("--no-collapse", is_flag=True, help="Don't collapse threads (default collapses multi-message threads).")
@click.pass_context
def report_cmd(ctx, since, until, hours, limit, full, unread, label, query, fmt, no_collapse):
    """Human summary of classification grouped by category."""
    account = ctx.obj["account"]
    config = _config()
    client = _client(account)
    since_dt = _parse_date(since) if since else None
    until_dt = _parse_date(until) if until else None
    _resolve(since_dt, until_dt, hours)
    messages = client.fetch(since=since_dt, until=until_dt, hours=hours, max_results=limit, include_body=full, label=label, unread_only=unread, extra=query)
    features = [classify(m, config, include_body=full) for m in messages]

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
        if fmt == "md":
            click.echo(f"\n## {cat} ({len(group)})")
        else:
            click.echo(f"\n[{cat}] {len(group)}")
        for item in _collapse(group, no_collapse):
            _render_item(item, fmt)

    if indeterminate:
        if fmt == "md":
            click.echo(f"\n## unresolved-by-rules ({len(indeterminate)})")
        else:
            click.echo(f"\n[unresolved-by-rules] {len(indeterminate)}")
        for item in _collapse(indeterminate, no_collapse):
            _render_item(item, fmt)
        click.echo("\nRun `gmail-triage classify --json` and classify the unresolved ones with the skill rubric.")


def _collapse(items: list[dict], no_collapse: bool) -> list[dict]:
    if no_collapse:
        return items
    by_thread: dict[str, list[dict]] = {}
    for it in items:
        by_thread.setdefault(it["thread_id"], []).append(it)
    collapsed = []
    for tid, msgs in by_thread.items():
        latest = max(msgs, key=lambda m: m["date"] or "")
        collapsed.append({**latest, "_thread_count": len(msgs)})
    return collapsed


def _render_item(item: dict, fmt: str) -> None:
    date = _local_iso(item["date"])
    thread = f" (+{item['_thread_count'] - 1} more in thread)" if item.get("_thread_count", 1) > 1 else ""
    unread = " [unread]" if item.get("is_unread") else ""
    att = f" [attachments: {item['attachments']}]" if item.get("has_attachment") else ""
    if fmt == "md":
        click.echo(f"- **{item['from']}** — {item['subject']} `{date}`{unread}{thread}{att}")
        click.echo(f"  > {item['snippet']}")
    else:
        click.echo(f"  - {date} {item['from']} - {item['subject']}{unread}{thread}{att}")
        click.echo(f"      {item['snippet']}")


@cli.command("config")
def config_cmd():
    """Print the merged config."""
    _echo_json(load_config(CONFIG_FILE))
