# Classification rubric

Assign exactly **one** category per message. Order matters — earlier categories win over later ones when evidence overlaps.

## Categories (winning order)

1. **security** — password resets, login/2FA codes, sign-in attempts, new-device alerts, unusual-activity warnings, account-lock notices, antivirus/breach notifications. *Anything about account access or verification.*
2. **urgent** — time-sensitive: deadlines, expiring offers/codes, action-required-now, same-day asks. Only if the message itself states the time pressure.
3. **finance** — invoices, receipts, billing, statements, payment/order confirmations, tax, refunds, subscription fees. When a receipt could be either finance or ads, prefer **finance**.
4. **travel** — flights, boarding passes, check-in, hotels, bookings, itineraries, reservations, trip confirmations.
5. **important** — needs genuine attention but isn't urgent, security, finance, or travel: direct requests, decisions, something the user is expected to act on or is waiting on.
6. **personal** — from people the user knows, personal correspondence, invites.
7. **updates** — newsletters, product updates, notifications, transactional mail the user opted into (non-financial).
8. **ads** — marketing, promotions, offers, deals, unsolicited announcements.
9. **other** — everything that fits nothing above.

## Tie-breaks

- A security email also containing a deadline is still **security**.
- A personal note with an explicit deadline is **urgent** if time pressure is real, else **personal**.
- A travel booking with a deadline to act (check-in window) is **travel**, not urgent, unless action is due within hours.
- Ads never beat security, urgent, finance, or travel.
- When genuinely unsure, choose the category the sender would call it, not the one that's safest.

## Evidence to weigh

- **Sender + domain** — known human sender vs. service/marketing domain.
- **Subject/snippet** — keywords, urgency markers.
- **Gmail label** — `CATEGORY_PROMOTIONS` strongly suggests ads, `CATEGORY_UPDATES` suggests updates, unless overridden by security/urgent/finance/travel.
- **Bulk headers** (`List-Unsubscribe`, `Precedence: bulk`) — strongly suggests updates/ads.
- **Attachments** — `has_attachment` and names can tip finance (PDF invoice) or security (risky `.zip`/`.exe`).

Trust the CLI's rule results unless evidence clearly contradicts them; your job is to resolve the `rule_indeterminate: true` messages and fix obvious mislabels.
