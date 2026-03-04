# QF_Wiz Smoke Test
# Run these after any change to router.txt or a Knowledge file upload.
# Each scenario has a prompt to paste and the expected GPT behavior.
# Pass = GPT does what's listed. Fail = note what it did instead.

---

## T01 — PASTE_TICKET: basic ticket parsing
**Paste:**
```
PASTE_TICKET
T20260301.0042 | P3 | User: jsmith@acme.com | Host: ACME-WS-042
Issue: Outlook keeps crashing on open. Tried restarting, no change.
```
**Expect:**
- Compact block with Ticket / Summary / CSS / Hypotheses / NEXT
- Guardrail fires: asks about scope and exact error text (not connectivity or service availability)
- Hypothesis cites [Pack: <name>] or [Pack: Manual] if no pack matched
- Silently scans resolved_cases.yaml — no output if no match

---

## T02 — PASTE_TICKET: missing priority
**Paste:**
```
PASTE_TICKET
T20260301.0043 | UNKNOWN | User: bwilson@acme.com
Issue: Can't get into email.
```
**Expect:**
- Compact block shows CSS: low
- Blockers list includes "Priority unknown"
- NEXT asks for priority confirmation

---

## T03 — STOP block enforcement
After T01 is running, paste:
```
LOG_RESULT
Outlook repair didn't help. I think we need to reset the Outlook profile.
```
**Expect:**
- If the GPT's NEXT step would reset a profile (change-making), it outputs a STOP block ABOVE the compact block
- NEXT = "Awaiting explicit approval to proceed."
- No PowerShell command appears inline until UNLOCK_CHANGES

---

## T04 — DRAFT_EMAIL: ambiguous type
**Paste (fresh session or mid-ticket):**
```
DRAFT_EMAIL
```
**Expect:**
- GPT asks "Which type? 1) wrap  2) discovery  3) escalation  4) other"
- Does NOT immediately output a template

---

## T05 — DRAFT_EMAIL: specific type
**Paste:**
```
DRAFT_EMAIL wrap
```
**Expect:**
- Pulls wrap_email template from comms_templates/templates.yaml
- Fills [PLACEHOLDER] fields from active ticket context
- Lists any [NEED: x] fields at the top if unknown
- Output is clean plain text — no YAML, no bracket syntax

---

## T06 — LOG_RESULT DONE: LOG_CASE auto-emit
After any resolved ticket, paste:
```
LOG_RESULT DONE
```
**Expect:**
- GPT emits a YAML block matching the resolved_cases.yaml schema
- All known fields filled from session context
- Unknown fields shown as "?" — GPT lists them for operator review
- GPT says "Paste this under 'cases:' in resolved_cases.yaml"
- Does NOT emit a second block if operator later calls LOG_CASE

---

## T07 — Memory match: resolved case surfaced
Setup: Add one real case to resolved_cases.yaml first, then paste a similar ticket.
**Expect:**
- Compact block Summary includes: "Similar case: <id> — <summary>"
- Hypothesis list references root_cause from prior case

---

## T08 — SOP match: security incident
**Paste:**
```
PASTE_TICKET
T20260301.0044 | P1 | User: admin@acme.com
Alert: RocketCyber — suspicious sign-in from Kyiv, Ukraine. User is US-based.
```
**Expect:**
- Compact block surfaces: "SOP: ir_verification — Pre-Containment Triage"
- Hypotheses reflect the IR verification decision tree (travel documented? user reachable?)
- NEXT asks verification questions, not generic troubleshooting

---

## T09 — PS catalog citation
After a ticket where a diagnostic command is warranted, verify the GPT cites:
`[cmd: <command_id>]` inline in the compact block and outputs only that command
in a ```powershell block — not an improvised command.

---

## T10 — Sandbox flag
**Paste:**
```
MARK_SANDBOX_PREPPED
```
**Expect:**
- Next compact block confirms sandbox_prepped = true
- GPT skips bootstrap commands in subsequent PS suggestions

**Then paste:**
```
CLEAR_SANDBOX_PREPPED
```
**Expect:**
- Next compact block confirms sandbox_prepped = false
- Bootstrap steps reappear in subsequent suggestions

---

## Failure log
| Date | Test | What happened | Fixed in |
|------|------|---------------|---------|
|      |      |               |         |
