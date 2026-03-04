# Audit Extraction Roadmap

## Scope
- Goal: Move audit artifacts and audit-related runtime docs out of `runtime` into a dedicated directory while keeping the Custom GPT upload set clean.
- Non-goal: Changing the audit schema itself unless explicitly requested.

## Proposed Structure
- `C:\Users\WDAGUtilityAccount\Desktop\Dev\QF_Wiz\audit\`
- `C:\Users\WDAGUtilityAccount\Desktop\Dev\QF_Wiz\audit\logs\`
- `C:\Users\WDAGUtilityAccount\Desktop\Dev\QF_Wiz\audit\schema\`
- `C:\Users\WDAGUtilityAccount\Desktop\Dev\QF_Wiz\audit\README.md`

## Roadmap
1. Inventory and classify audit assets
   - Move `runtime\AuditLogs\*` -> `audit\logs\*`
   - Move `runtime\audit_telemetry.schema.json` -> `audit\schema\audit_telemetry.schema.json`
2. Update runtime references
   - In `runtime\command_palette.md`, point audit telemetry instructions to the new audit location and avoid any local script paths.
3. Add audit README
   - Short guidance: purpose, what gets uploaded (likely none), how to capture and store telemetry.
4. Update any tooling or scripts
   - If any scripts read/write `runtime\AuditLogs`, update paths.
5. Define upload policy
   - For Custom GPT uploads: include `runtime` files only; exclude `audit\logs`.
   - Do not upload audit schemas or logs to the GPT knowledge set.

## Decision
Audit remains fully separate from the GPT to maximize token usage.
- Do not upload audit logs or the audit schema to the GPT knowledge set.
- The GPT should not reference audit artifacts unless the operator explicitly re-shares them for a specific task.
