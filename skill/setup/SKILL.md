---
name: gmail-triage-setup
description: Install and configure the gmail-triage tool — Python CLI plus Google Cloud OAuth client, first-time authentication, adding Gmail accounts, and troubleshooting auth/access errors. Use when the user asks to install or set up gmail-triage, add another Gmail account, or when authentication fails (403 access_denied, missing token, "No such option", etc.). Triages mail only after setup; this skill is about setup, not triage.
---

Installs the `gmail-triage` CLI and wires up Google Cloud OAuth so it can read the user's Gmail **read-only**. The agent runs every shell step itself; it guides the user click-by-click through the parts that require their Google account and browser, and waits for their handoff at those points.

## Guardrail

**Read-only, always.** This skill sets up a read-only tool. Never use it to send, modify, archive, delete, or label mail. `credentials.json` and the `.gmail-triage/` directory are secrets — never print, echo, or commit their contents.

## Scope

Setup only. Once auth works, stop: classification/triage is the `gmail-triage` skill's job. End by pointing the user there.

## Process

### 1. Locate the project

State dir is `<cwd>/.gmail-triage`, so **every command must run from the project dir**. Default is `C:\Users\a956064\gmail-triage` (confirm with the user if unsure). If the project isn't there, ask where they cloned it.

### 2. Check the state

- `credentials.json` exists in the project dir?
- `.gmail-triage/<account>/token.json` exists for the account they want?
- Command available? (`gmail-triage --help`)

Report what's present before starting; only do the steps that are missing.

### 3. Google Cloud console — guided, one click at a time

The user must do these in their browser (the agent has no Google access). Walk them **one step at a time**, pausing for a clear "done" before continuing. Use the Google Cloud project used before, or a new one if none exists.

1. **Create/select a project** at https://console.cloud.google.com/.
2. **Enable the Gmail API**: APIs & Services → Library → "Gmail API" → Enable.
3. **OAuth consent screen** (APIs & Services → **Google Auth Platform** — this is what "OAuth consent screen" is now called):
   - Audience tab → User type: **External**.
   - Audience tab → **Test users → Add users**: add every Google account that will authorize (required while the app is in Testing status — an account not listed here gets `403 access_denied`).
   - Scopes: `https://www.googleapis.com/auth/gmail.readonly` (read-only).
4. **Create OAuth client**: APIs & Services → Credentials → Create Credentials → OAuth client ID → Application type: **Desktop app** → download the JSON and save it as `credentials.json` in the project dir.

**Handoff point:** verify `credentials.json` now exists in the project dir before proceeding. If missing, re-prompt rather than skipping.

### 4. Install

```bash
pip install -e .
```

Verify with `gmail-triage --help`.

### 5. Authenticate

Ask the user whether a browser can open on their machine:

- **Browser OK:** `gmail-triage --account <name> auth-run` (opens a browser, they sign in once). The token lands at `.gmail-triage/<name>/token.json`.
- **Headless / agent-mediated (works with no local browser):**
  1. `gmail-triage --account <name> auth-run --no-browser` — prints a consent URL.
  2. **Handoff point:** give the user the URL. They open it, sign in with the account to add, and copy the verification code back.
  3. `gmail-triage --account <name> auth-complete <that-code>` — saves the token.

Default account name is `default` (`gmail-triage auth-run`); use `--account <name>` before the command for any other name.

### 6. Add more accounts

Repeat step 5 with a new `--account <name>`. Remind the user: **each additional address must already be in Test users** (step 3), or it gets `403 access_denied`.

### 7. Verify

```bash
gmail-triage --account <name> classify --hours 24
```

Must return a categorized message list with no auth errors. Then hand off to the `gmail-triage` skill for actual triage.

## Troubleshooting

| Symptom | Cause → Fix |
|---|---|
| `403 access_denied` when authorizing | Account not in **Test users**. Add it (Google Auth Platform → Audience → Test users), retry. |
| `No such option '--account'` | `--account` is a group option — it goes **before** the command: `gmail-triage --account work auth-run`, not `gmail-triage auth-run --account work`. |
| `No pending auth found` | Ran `auth-complete` before `auth-run --no-browser`, or the account name differs. Run `auth-run --no-browser` first with the same `--account`. |
| `No OAuth client found` | `credentials.json` missing/wrong dir. Back to step 3. |
| `gmail-triage: command not found` | Not installed. Run step 4. |
| `invalid_grant` / refresh failures | Delete `.gmail-triage/<account>/token.json` and re-run auth for that account. |
| Wrong mailbox / looks like another account | `.gmail-triage/<account>/` holds one token per account; each account needs its own `auth-run` (step 6). |

## Completion criterion

The chosen account(s) return live mail via `classify --hours 24` with no auth errors, the user knows how to add another account, and the user is pointed to the `gmail-triage` skill for triage.
