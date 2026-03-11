> QF_Wiz Runtime v2.0 — command_palette

Runtime files are provided via Knowledge retrieval. If retrieval fails, ask
the operator to re-share the file.

Core
- PASTE_TICKET          — parse ticket, load memory + branch pack, output compact block
- LOG_RESULT <text>     — feed back output or new info; update ticket state
- DECIDE                — output RESOLVE / ESCALATE_TIME / ESCALATE_SKILL with rationale
- PRINT_CONTEXT         — plain-text summary of current ticket state (no JSON)
- PRINT_NEXT            — re-output the NEXT step only
- PRINT_POWERSHELL      — re-output the last PowerShell command only
- LOG_RESULT DONE       — ticket resolved; prompt to save case to resolved_cases.yaml

Memory + Comms
- DRAFT_NOTE            — draft an internal ticket note
- DRAFT_EMAIL           — draft a customer-facing email using comms_templates/
- DRAFT_HANDOFF         — draft an escalation handoff note
- LOG_CASE              — emit a resolved_cases.yaml entry for the operator to save

PowerShell Safety
- UNLOCK_CHANGES        — approve the immediately pending STOP block (next step only)
- MARK_SANDBOX_PREPPED  — note that sandbox bootstrap is complete; skip it going forward
- CLEAR_SANDBOX_PREPPED — reset sandbox state (e.g. after restart)
