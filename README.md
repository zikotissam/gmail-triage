# gmail-triage

![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)

Read your Gmail inbox **read-only** and classify messages (important, ads, security, urgent, personal, updates, other) for AI agents. Ships as a Python CLI plus an opencode skill that teaches agents how to run it and finish the LLM part of classification.

## How classification works (hybrid)

1. **Deterministic rules (CLI):** Gmail's native category labels, bulk headers (`List-Unsubscribe`, `Precedence: bulk`), security/urgency keywords, and your allow/block lists in `config.yml`.
2. **LLM pass (agent):** messages the rules can't resolve (`rule_indeterminate: true`) are classified by the agent using the rubric in `skill/RUBRIC.md`. No API key needed — the agent is the LLM.

## Setup

### 1. Google Cloud OAuth client (one time)

1. Go to https://console.cloud.google.com/ and create a project (or reuse one).
2. **Enable the Gmail API** (APIs & Services → Library → "Gmail API" → Enable).
3. **Configure the OAuth consent screen** (APIs & Services → **Google Auth Platform** — this is what "OAuth consent screen" is now called):
   - **Audience** tab → **User type:** **External** (fine for personal use).
   - **Audience** tab → **Test users → Add users**: add the Google account you'll authorize with. **Required** — while the app is in *Testing* status, any account not listed here gets a `403 access_denied` when authorizing.
   - Scopes: add `https://www.googleapis.com/auth/gmail.readonly` (read-only!). Scopes are now configured per OAuth client under the **Clients** tab.
4. **Create OAuth client ID** (APIs & Services → Credentials → Create Credentials → OAuth client ID):
   - Application type: **Desktop app**.
   - Download the JSON and save it as `credentials.json` in this project dir.

### 2. Install

```bash
pip install -e .
```

### 3. Authenticate (one time, opens a browser)

```bash
gmail-triage auth-run
```

Token is saved to `.gmail-triage/token.json`. Both `credentials.json` and `.gmail-triage/` are your secrets — don't commit them.

## Usage

```bash
# All fetch/classify/report commands support date filters:
gmail-triage inbox   --since 2026-01-01 --until 2026-02-01 --json   # full window
gmail-triage classify --hours 24 --json                              # last 24h (agent-facing)
gmail-triage report  --since 2026-07-01                               # human digest
gmail-triage config                                                   # merged config
```

- `--since`/`--until` are ISO dates (`YYYY-MM-DD`); they map to Gmail's `after:`/`before:` queries (server-side filtering).
- `--hours N` is a shortcut and is mutually exclusive with `--since`/`--until`.
- `--limit` caps results (default 100).

### For an AI agent

Use `gmail-triage classify --json` and consume the JSON. Messages with `rule_indeterminate: true` are the ones the agent must classify itself using `skill/RUBRIC.md`. The `gmail-triage` opencode skill automates this whole loop — ask your agent to "triage my inbox" and it will run it.

### Harness-agnostic

The CLI is a plain command that reads Gmail and emits JSON — it is **not** tied to opencode and works with any harness agent that can run a shell command (Claude Code, Codex, Cursor, custom scripts, cron, …). Only the skill wrapper is opencode-specific; it's just instructions, so port it to another harness by copying the process steps into that harness's agent prompt (e.g. `.claude/CLAUDE.md`).

## Configuration

Edit `config.yml` to tune rules:

- `rules.security_keywords` / `rules.urgent_keywords` — keyword lists.
- `rules.allow_senders` — map `email -> category` (e.g. `boss@work.com: important`).
- `rules.block_senders` — map `email` (or subject pattern) `-> category` (e.g. `deals@shop.com: ads`).
- `rules.allow_domains` / `rules.block_domains` — whole-domain rules.

Precedence: `block_senders` → `allow_senders` → `block_domains` → `allow_domains` → security keywords → ads label → urgent keywords → bulk/updates.

## Safety

- OAuth scope is **read-only** (`gmail.readonly`). The tool cannot send, modify, or delete anything.
- The skill carries a hard read-only guardrail.

## Skill (opencode)

Installed at `~/.config/opencode/skills/gmail-triage/` (this repo's `skill/` is the source). To reinstall after edits:

```bash
cp skill/SKILL.md skill/RUBRIC.md ~/.config/opencode/skills/gmail-triage/
```

## License

[MIT](LICENSE)
