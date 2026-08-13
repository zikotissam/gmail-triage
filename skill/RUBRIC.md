# Classification rubric

Assign exactly **one** category per message. Order matters — earlier categories win over later ones when evidence overlaps.

## Categories (winning order)

1. **security** — password resets, login/2FA codes, sign-in attempts, new-device alerts, unusual-activity warnings, account-lock notices, antivirus/breach notifications. *Anything about account access or verification.*
2. **urgent** — time-sensitive: deadlines, expiring offers/codes, action-required-now, same-day asks. Only if the message itself states the time pressure.
3. **important** — needs genuine attention but isn't urgent or security: direct requests, decisions, something the user is expected to act on or is waiting on.
4. **personal** — from people the user knows, personal correspondence, invites.
5. **updates** — newsletters, product updates, receipts, notifications, transactional mail the user opted into.
6. **ads** — marketing, promotions, offers, deals, unsolicited announcements.
7. **other** — everything that fits nothing above.

## Tie-breaks

- A security email also containing a deadline is still **security**.
- A personal note with an explicit deadline is **urgent** if time pressure is real, else **personal**.
- Ads never beat security or urgent.
- When genuinely unsure, choose the category the sender would call it, not the one that's safest.

## Evidence to weigh

- **Sender + domain** — known human sender vs. service/marketing domain.
- **Subject/snippet** — keywords, urgency markers.
- **Gmail label** — `CATEGORY_PROMOTIONS` strongly suggests ads, `CATEGORY_UPDATES` suggests updates, unless overridden by security/urgent.
- **Bulk headers** (`List-Unsubscribe`, `Precedence: bulk`) — strongly suggests updates/ads.

Trust the CLI's rule results unless evidence clearly contradicts them; your job is to resolve the `rule_indeterminate: true` messages and fix obvious mislabels.
