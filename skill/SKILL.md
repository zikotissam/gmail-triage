---
name: gmail-triage
description: Triage and classify the user's Gmail inbox (important, ads, security, urgent, finance, travel, personal, updates). Use when the user asks to triage/classify/summarize/check their inbox, email, or mail, asks what's important or urgent in their mail, or wants a digest of unread mail in a date range.
---

Triages the user's Gmail inbox read-only and reports a categorized summary, with recommended replies for the messages that need a response. The CLI does a deterministic first pass; you finish the classification with your judgment.

## What the tool reads

By default: sender, subject, snippet (~150-char preview), Gmail labels, bulk headers (`List-Unsubscribe` etc.), attachment metadata, and unread status. **Not** the full body.

Full bodies are available on demand: add `--full` to fetch them (also works with `--json`). Fetch bodies only when the snippet is genuinely ambiguous for classification or the user explicitly wants the full message read — full bodies are large and eat context. After a full read, prefer the body over the snippet. State which mode you used if the user asks whether you've read the whole email.

## Guardrail

**Read-only, always.** This tool can only read mail. Never attempt to modify, send, archive, delete, or label messages through it. If the user asks for such an action, say it isn't supported. Recommended replies are drafts you propose in the digest — never sent by the tool.

## Process

### 1. Locate the tool

Run from the `gmail-triage` project dir (`C:\Users\a956064\gmail-triage`). The command is `gmail-triage`. If it's not installed, tell the user to run `pip install -e .` there.

### 2. Confirm access

If the account's token doesn't exist in the project dir (`.gmail-triage/default/token.json` for the default account, `.gmail-triage/<name>/token.json` otherwise), the user must authenticate first. If setup, install, or auth help is needed (e.g. first-time install, adding an account, or an auth error), use the `gmail-triage-setup` skill for the full guided flow, then come back here. Check before proceeding.

### 3. Ask for flags — one question per option

**Always ask before fetching.** If the user gave you some flags already, skip the questions they answered and only ask for what's still open. For each open item, ask one concise question and offer sensible options. Defaults are marked; if the user says "defaults" or "skip", use the defaults.

1. **Range** — *"How far back should I scan?"* → **last 24h** (default) / last 7 days / this month / a date range (get `--since`/`--until` as `YYYY-MM-DD`).
2. **Unread only?** — yes / **no** → `--unread` if yes.
3. **Folder** — **Inbox** (default) / Spam / Sent / Drafts / Trash / Archive / All mail / Unread / Starred / a custom label → `--label <value>`.
4. **Custom query?** — **none** / free-form Gmail query (e.g. `from:paypal has:attachment`) → `--query "<terms>"`.
5. **Full bodies?** — snippet only (**default**) / full messages → `--full`.
6. **Thread collapse in report?** — **collapsed** / flat → `--no-collapse` if flat.
7. **Output format** — text (**default**) / markdown → `--format md`.
8. **Account** — **default** / named account → `--account <name>`.

Assemble the command with exactly the chosen flags, e.g.:
`gmail-triage classify --json --since 2026-08-01 --until 2026-08-14 --label spam --unread`

Attachment metadata, unread status, and unsubscribe links are always included in the JSON output (no flag needed).

**Completion criterion for this step:** you can write the exact `gmail-triage` command from the answers, and every open question above is resolved (either by the user or by default).

### 4. Fetch and classify

Run the assembled command. `--since`/`--until` are ISO dates (`YYYY-MM-DD`); `--hours` is mutually exclusive with them. Gmail's `before:` is exclusive, so to include a day use the next day as `--until`.

### 5. Finish the classification

Each message in the JSON has `rule_category` (`null` when indeterminate), `rule_reasons`, and raw features. Messages with `rule_indeterminate: true` need your judgment — assign exactly one category using the rubric in [`RUBRIC.md`](RUBRIC.md). For messages the rules already classified, only override on clear evidence.

### 6. Recommend replies

For every message in **security**, **urgent**, **finance**, **travel**, or **important** (and any personal message clearly expecting an answer), draft a **recommended reply**:

- Keep it short (2-4 sentences), in the user's own voice — informal but professional.
- For **security**: note whether action is needed (e.g. "if this was you, nothing to do").
- For **urgent**: confirm acknowledgment + a proposed action/deadline.
- For **finance**: flag anything needing action (payment due, unexpected charge, refund).
- For **travel**: confirm the booking/check-in details the user should act on.
- For **important**: a crisp response the user can send almost as-is.
- For personal messages expecting an answer, offer a light reply.
- Do **not** draft replies for ads/updates/other unless the user asks.

### 7. Report

Output a concise digest:

- **Security** and **urgent** items first, flagged clearly, each with its recommended reply.
- Then **important**/**finance**/**travel**/**personal**, each with its recommended reply.
- Then **updates**/**ads**/**other** collapsed to counts.
- One line per flagged item: sender, subject, snippet (add unread/attachment markers when present).
- State the window and flags you used (e.g. "last 24h, unread only, Inbox").
- End by asking: *"Want me to refine any reply, or draft a different one?"*

**Completion criterion:** every message in the window has exactly one category, the digest covers the full window, and every security/urgent/important/finance/travel message carries a recommended reply. If any message is unclassified or any flagged message lacks a reply, keep going until none remain.
