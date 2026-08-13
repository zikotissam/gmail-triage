---
name: gmail-triage
description: Triage and classify the user's Gmail inbox (important, ads, security, urgent, personal, updates). Use when the user asks to triage/classify/summarize/check their inbox, email, or mail, asks what's important or urgent in their mail, or wants a digest of unread mail in a date range.
---

Triages the user's Gmail inbox read-only and reports a categorized summary, with recommended replies for the messages that need a response. The CLI does a deterministic first pass; you finish the classification with your judgment.

## What the tool reads

By default: sender, subject, snippet (~150-char preview), Gmail labels, and bulk headers (`List-Unsubscribe` etc.). **Not** the full body.

Full bodies are available on demand: add `--full` to fetch them (also works with `--json`). Fetch bodies only when the snippet is genuinely ambiguous for classification or the user explicitly wants the full message read — full bodies are large and eat context. After a full read, prefer the body over the snippet. State which mode you used if the user asks whether you've read the whole email.

## Guardrail

**Read-only, always.** This tool can only read mail. Never attempt to modify, send, archive, delete, or label messages through it. If the user asks for such an action, say it isn't supported. Recommended replies are drafts you propose in the digest — never sent by the tool.

## Process

### 1. Locate the tool

Run from the `gmail-triage` project dir (`C:\Users\a956064\gmail-triage`). The command is `gmail-triage`. If it's not installed, tell the user to run `pip install -e .` there.

### 2. Confirm access

If `.gmail-triage/token.json` doesn't exist in the project dir, the user must run `gmail-triage auth-run` once (opens a browser). Check before proceeding.

### 3. Ask for the search range

**Always ask before fetching.** If the user didn't specify, ask a one-line question offering sensible options, e.g.: *"How far back should I scan — last 24 hours, this week, this month, or a specific date range?"*

Resolve their answer into one of:
- `--hours N` for recency (e.g. `--hours 24`, `--hours 168`),
- `--since YYYY-MM-DD` / `--until YYYY-MM-DD` for a date range (Gmail's `before:` is exclusive, so to include a day use the next day as `--until`).

If they say "all unread", use `gmail-triage classify --json` without time flags (or a wide `--since`).

### 4. Fetch and classify

Run:

```
gmail-triage classify --json [--since DATE] [--until DATE | --hours N] [--full]
```

`--since`/`--until` are ISO dates (`YYYY-MM-DD`); `--hours` is mutually exclusive with them. Add `--full` to read full bodies.

### 5. Finish the classification

Each message in the JSON has `rule_category` (`null` when indeterminate), `rule_reasons`, and raw features. Messages with `rule_indeterminate: true` need your judgment — assign exactly one category using the rubric in [`RUBRIC.md`](RUBRIC.md). For messages the rules already classified, only override on clear evidence.

### 6. Recommend replies

For every message in **security**, **urgent**, or **important** (and any personal message clearly expecting an answer), draft a **recommended reply**:

- Keep it short (2-4 sentences), in the user's own voice — informal but professional.
- For **security**: note whether action is needed (e.g. "if this was you, nothing to do").
- For **urgent**: confirm acknowledgment + a proposed action/deadline.
- For **important**: a crisp response the user can send almost as-is.
- For personal messages expecting an answer, offer a light reply.
- Do **not** draft replies for ads/updates/other unless the user asks.

### 7. Report

Output a concise digest:

- **Security** and **urgent** items first, flagged clearly, each with its recommended reply.
- Then **important**/**personal**, each with its recommended reply.
- Then **updates**/**ads**/**other** collapsed to counts.
- One line per flagged item: sender, subject, snippet.
- State the window you covered (e.g. "last 24h" or "2026-01-01 → 2026-02-01").
- End by asking: *"Want me to refine any reply, or draft a different one?"*

**Completion criterion:** every message in the window has exactly one category, the digest covers the full window, and every security/urgent/important message carries a recommended reply. If any message is unclassified or any flagged message lacks a reply, keep going until none remain.
