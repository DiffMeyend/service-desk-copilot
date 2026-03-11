# QF_Wiz Rebuild Roadmap

## Purpose
Rebuild QF_Wiz from the ground up with a clear, testable runtime architecture, clean data pipelines, and deterministic routing behavior.

## Guiding Principles
- Ship in thin, usable slices.
- Prefer deterministic routing over heuristic-only matching.
- Keep catalogs and schemas versioned and auditable.
- Treat ticket data as a product: validated, normalized, and observable.

## Glossary
- **CSS (Context Stability Score)**: Deterministic 0-100 measure of context completeness. Computed from 6 weighted domains (Evidence 35%, Reproduction 20%, Symptom Precision 15%, Environment 10%, Change Signals 10%, Identity & Scope 10%). CSS ≥ 90 = sufficient for accelerated resolution. See `runtime/css_source_of_truth.md` for full spec.

## Canonical Inputs
- **PSA Taxonomy**: `Help Desk Issue and Sub-Issue Types.csv` defines 11 Issue Types and ~69 Sub-Issue Types. Every raw ticket dump includes Issue + Sub-Issue as structured fields, enabling deterministic taxonomy-based routing.
- **Issue Types**: Backup and Restore, Workstation, Email, Printer/Scanner, Server, Network, Power, Phone System, File Share, User, Microsoft 365

---

## Phase 0: Discovery & Baseline — COMPLETE

**Objective**: Inventory existing assets, establish baseline metrics, and define acceptance criteria for the rebuilt system.

**Tasks**:
1. Document existing ticket sources (PSA paste/email) ✓
2. Inventory runtime files and schema versions ✓
3. Catalog branch packs and keyword triggers ✓
4. Document routing inputs (ticket fields, notes, issue/sub-issue types) ✓
5. Establish baseline CSS scoring domains and weights ✓
6. Define acceptance criteria for rebuilt system ✓

**Acceptance Criteria**:
- [x] Runtime version map documented (Scratch.md Appendix A)
- [x] All branch packs cataloged with categories and keywords
- [x] CSS scoring domains and weights defined (css_scoring.yaml)
- [x] Tooling context documented (router.txt)

**Key Artifacts**: `Scratch.md`, `runtime/branch_packs_catalog_v1_0.yaml`, `runtime/css_scoring.yaml`, `runtime/router.txt`

---

## Phase 1: Core Runtime Architecture — COMPLETE

**Objective**: Define canonical data model, establish schema versioning, and implement deterministic selection pipeline with clear precedence rules.

**Tasks**:
1. Define context payload schema with all required sections ✓
2. Implement meta section with schema versioning ✓
3. Define ticket, quickfix, environment, problem, constraints sections ✓
4. Define evidence, branches, plan, css, decision, notes sections ✓
5. Establish guardrails block for basic troubleshooting ✓
6. Implement schema validation infrastructure ✓
7. Create template payload for new sessions ✓

**Acceptance Criteria**:
- [x] `context_payload.schema.json` validates all required fields
- [x] Schema version tracked in meta.schema_version (v1.3.1)
- [x] Guardrails block enforces basic troubleshooting before advanced work
- [x] Template JSON matches schema structure
- [x] JSON payloads pass schema validation via `parser_smoke.py --validate-schema`

**Key Artifacts**: `runtime/context_payload.schema.json`, `runtime/context_payload.template.json`, `audit/schema/audit_telemetry.schema.json`

---

## Phase 2: Data Pipelines — 100% COMPLETE

**Objective**: Build ingestion adapters, normalize and enrich tickets, and add validation and error handling for malformed inputs.

**Tasks**:
1. Build ticket ingestion watcher with inbox/ready/processed/error flow ✓
2. Implement all-inclusive parser (no PII scrubbing) ✓
3. Implement PII-friendly parser variant ✓
4. Add JSON envelope unwrapping support ✓
5. Add ticket note extraction into notes.rolling ✓
6. Fix parser field extraction (tighten regex for inline fields) ✓
7. Extract Issue Type and Sub-Issue Type from raw dump ✓
8. Add fuzzy/alias section matching for header variants ✓
9. Add email thread/reply cutoff detection ✓
10. Add generic key:value harvesting for unmapped fields ✓
11. Expand device/user pattern extraction (systeminfo/ipconfig parsing) ✓

**Acceptance Criteria**:
- [x] Watcher processes files from inbox to ready with JSON output
- [x] Parser extracts ticket ID, title, contact, company, site
- [x] Parser extracts device details (hostname, OS, IP, serial, asset_tag)
- [x] Ticket notes flow to notes.rolling with timestamps
- [x] Parser correctly handles inline blobs without miscapture
- [x] Parser extracts Issue Type + Sub-Issue Type into ticket.category/service fields
- [x] Email reply chains stripped from description
- [x] Section aliases (Contact Info, Requester, Location Details) match canonical headings
- [x] Device/user context pulled from systeminfo/ipconfig output (hostname/IP/username/domain)
- [x] User-defined inline key:value fields captured under ticket.user_defined_fields

**Key Artifacts**: `scripts/parsing/parse_ticket.py`, `scripts/parsing/parse_ticket_sanitize.py`, `scripts/Queue Scripts/ticket_ingestion_watcher.py`

---

## Phase 3: Knowledge Packs v2 — 100% COMPLETE

**Objective**: Rebuild pack catalog with consistent schema fields, map Help Desk taxonomy to packs, and add coverage metrics.

**Tasks**:
1. Define pack schema (id, name, category, keywords, signals, goal, hypotheses) ✓
2. Categorize packs (network, identity, m365, messaging, security, endpoint, infrastructure, cross_cutting) ✓
3. Add preconditions (basic_verification_completed flag) ✓
4. Add command_refs linking hypotheses to PowerShell catalog ✓
5. Implement keyword/signal matching with scoring ✓
6. Add selection rules for primary + fallback pack logic ✓
7. Create `runtime/taxonomy_pack_mapping.yaml` ✓
   - Map all 11 Issue Types to pack categories
   - Map all ~69 Sub-Issue Types to specific branch pack IDs
8. Create new packs for taxonomy gaps — COMPLETE
   - Backup and Restore: `backup_failure`, `backup_file_restore`, `backup_workstation_recovery`
   - Phone System: `phone_call_quality`, `phone_voicemail`, `phone_howto`, `phone_changes`, `phone_hardware`, `phone_outage`
   - Power: `power_outage`, `power_ups`
   - Application/SaaS coverage: `email_gsuite`, `email_apple`, `email_third_party`, `email_mobile`, `server_hardware`, `server_virtualization`, `server_wvd`, `app_unmanaged`, `app_adobe_reader`, `app_adobe_pro`, `app_quickbooks`, `app_lob`, `app_browser`, `app_password_manager`, `endpoint_macos`, `m365_teams`
9. Expand branch packs for MSP scenarios (target: 50+ packs) ✓
10. Add pack coverage metrics and gaps reporting ✓
11. Validate 100% taxonomy coverage — COMPLETE (CSV + observed PSA variants)
12. Maintain Issue Type alias registry for PSA variants ✓

**Acceptance Criteria**:
- [x] 26+ branch packs with consistent schema
- [x] Each pack has id, name, category, keywords, goal, hypotheses
- [x] Hypotheses include confidence_hint, discriminating_tests, command_refs
- [x] Cross-cutting packs (recent_change, only_this_user, only_this_device) available as fallbacks
- [x] `taxonomy_pack_mapping.yaml` covers all 69 Sub-Issue Types (+ observed PSA variants)
- [x] No Issue/Sub-Issue maps to empty pack list (current tickets route via taxonomy)
- [x] Application and SaaS packs exist for every taxonomy workload (total packs: 37)
- [x] Coverage report shows gaps in MSP scenario handling
- [x] 50+ packs covering common MSP helpdesk issues

**Key Artifacts**: `runtime/branch_packs_catalog_v1_0.yaml`, `runtime/taxonomy_pack_mapping.yaml`, `scripts/parsing/branch_pack_selector.py`

---

## Phase 4: Routing & Decisioning — 100% COMPLETE

**Objective**: Implement routing rules with primary + cross-cutting pack selection, add confidence scoring and explainability, support manual overrides with audit trails.

**Tasks**:
1. Implement keyword/signal matching across ticket summary + body ✓
2. Score matches by hit count, summary presence, and token length ✓
3. Select primary pack (highest score) + optional cross-cutting fallback ✓
4. Format hypotheses with pack metadata (id, pack_id, pack_name, category) ✓
5. Log source_pack array for observability ✓
6. Implement taxonomy-first routing ✓
   - Load taxonomy_pack_mapping.yaml
   - Use Issue/Sub-Issue as PRIMARY routing signal
   - Fall back to keyword matching when taxonomy yields no pack
7. Add confidence scoring computation — COMPLETE
8. Add explainability hooks (why this pack was selected) — COMPLETE
   - Log whether selection was taxonomy-based or keyword-based ✓
   - Show which Issue/Sub-Issue or keywords triggered match ✓
9. Support manual overrides via LOAD_BRANCH_PACK command ✓
10. Implement audit trail for pack selection and hypothesis evolution ✓
11. Persist routing metadata for observability (taxonomy vs keyword, alias/fuzzy path) ✓

**Acceptance Criteria**:
- [x] Primary pack selected based on highest keyword match score
- [x] Cross-cutting pack added when symptoms span areas
- [x] source_pack logged after each ingestion
- [x] CSS hard caps enforce guardrails (78 cap for incomplete basics)
- [x] Taxonomy mapping used as primary routing signal (alias + fuzzy matching)
- [x] Keyword matching used as secondary/fallback
- [x] Routing metadata persisted for QA (branches.routing_metadata captures alias/exact/fuzzy + fallback reason)
- [x] Confidence scoring documented in payload (`confidence_score` on hypotheses)
- [x] Explainability output shows taxonomy OR keyword trigger (`match_type` + `match_explanation`)
- [x] Manual overrides captured and applied when LOAD_BRANCH_PACK commands are present (branches.manual_overrides)

**Key Artifacts**: `scripts/parsing/branch_pack_selector.py`, `runtime/taxonomy_pack_mapping.yaml`, `runtime/css_scoring.yaml`

---

## Phase 5: Observability & QA — 95% COMPLETE

**Objective**: Add tracing for routing decisions, build QA harness for known ticket scenarios, track coverage and collision rates.

**Tasks**:
1. Log source_pack after each ingestion ✓
2. Add regression tests for branch pack selection ✓ (13 test cases)
3. Create test fixtures for known ticket scenarios ✓
4. Implement parser smoke test with schema validation ✓
5. Add reingest fixture script for deterministic testing ✓
6. Track pack selection collision rates — COMPLETE (routing_dashboard CLI)
7. Track false positive rates for pack selection — COMPLETE (manual override analytics)
8. Add audit log output for decision tracing — COMPLETE (`--audit-log-dir`)
9. Build QA dashboard for routing metrics (routing metadata + confidence) — COMPLETE
10. Add coverage reporting for pack gaps — COMPLETE (`scripts/qa/pack_coverage.py`)
11. Expose routing metadata (taxonomy vs keyword) in payloads for QA ✓
12. Surface confidence/explainability data in QA dashboards (routing_dashboard CLI) — PARTIAL
13. Capture confidence/explainability outputs for QA review ✓

**Acceptance Criteria**:
- [x] 13+ regression tests pass for pack selection
- [x] Parser smoke test validates schema compliance
- [x] Reingest workflow documented and scripted
- [x] Watcher logs source_pack for immediate visibility
- [x] Routing metadata captured in `branches.routing_metadata` for QA dashboards
- [x] Collision rate and manual override rate tracked via `scripts/qa/routing_dashboard.py`
- [x] False positive (manual override) rate visible in QA dashboard reports
- [x] Audit logs can be emitted via `--audit-log-dir` for decision tracing

**Key Artifacts**: `scripts/tests/test_branch_pack_selector.py`, `scripts/tests/parser_smoke.py`, `scripts/tests/reingest_fixture.py`

---

## Phase 6: Hardening & Launch — 5% (DEPRIORITIZED)

**Objective**: Security review, performance tuning, load testing, rollout plan, training, and post-launch monitoring.

**Note**: This phase is deprioritized while Phase 7 proceeds in parallel.

**Tasks**:
1. Security review - API key management ✓ (env var exists)
2. Security review - PII handling in parser variants ✓
3. Security review - input validation in API — OPEN
4. Implement rate limiting on API — OPEN
5. Add request logging and monitoring — OPEN
6. Performance profiling of parser — OPEN
7. Load testing for concurrent ticket processing — OPEN
8. Document rollout plan — OPEN
9. Create operator training materials — OPEN
10. Set up post-launch monitoring dashboards — OPEN

**Acceptance Criteria**:
- [x] PII-friendly parser available
- [x] API key required for all requests
- [ ] Rate limiting prevents abuse (100 req/min)
- [ ] Request logs captured for debugging
- [ ] Parser processes ticket < 500ms
- [ ] System handles 10 concurrent ingestions
- [ ] Training documentation complete
- [ ] Monitoring alerts configured for errors

**Key Artifacts**: `api/server.py`, `scripts/parsing/parse_ticket_sanitize.py`

---

## Phase 7: Local Runtime Agent (Windows Sandbox) — DRAFT

**Objective**: Build a local agent that operates fully inside the Windows Sandbox, defaults to the `runtime` files for reasoning, and uses web queries only when runtime gaps arise.

**Design Notes (Draft)**
1. Primary knowledge = `runtime/*.yaml`, `runtime/*.json`, `runtime/*.md` with deterministic routing and guardrails from `runtime/router.txt`.
2. Fallback knowledge = web queries only when runtime lacks the needed answer; results must be cited and cached locally.
3. Execution context = local PowerShell + local tools (Python, Git, VS Code), no external services required to function.
4. Interface = interactive CLI loop in VS Code terminal; optional file-drop inputs for operator results.
5. Safety = automatic web queries allowed; explicit approval required for any change-making action or downloads.

**Build Plan (Full)**
1. **Runtime Loader**
   - Parse `branch_packs_catalog_v1_0.yaml`, `taxonomy_pack_mapping.yaml`, `context_payload.schema.json`, `Workflow.yaml`, `State_Machine.yaml`, `router.txt`.
   - Validate schema versions and surface mismatch warnings.
2. **Routing Engine**
   - Implement taxonomy-first selection with keyword fallback (mirror `branch_pack_selector.py`).
   - Maintain `source_pack` and routing metadata for audit.
3. **CP Update Engine**
   - Apply operator input and `LOG_RESULT` into the CP JSON in place.
   - Recompute CSS using `css_scoring.yaml` and update `branches` per Workflow.
4. **Interactive Agent Loop**
   - CLI loop that outputs the compact block format from `runtime/router.txt`.
   - Persist CP updates back to the same `tickets/ready/*.json` file each turn.
5. **Operator Input Paths**
   - Primary: stdin (interactive CLI).
   - Optional: file-drop watcher for `tickets/results/*.json` or text notes.
6. **Web Fallback Module**
   - Trigger only on runtime gap detection.
   - Run web queries automatically, always cite sources.
   - Cache results in `runtime/web_cache.json` with timestamps and citations.
7. **VS Code Integration**
   - Add a task to run the agent loop from the integrated terminal.
   - Add `launch.json` entry to debug the agent loop with breakpoints.
   - Document how to run the task and debug profile.
8. **Tests & Fixtures**
   - Schema validation test.
   - Pack selection regression tests.
   - End-to-end fixture for a sample ticket + LOG_RESULT chain.

**Acceptance Criteria**
- [ ] Agent runs fully offline using only runtime files and local tools.
- [ ] Agent produces compact blocks matching `runtime/router.txt` formatting rules.
- [ ] Taxonomy-first routing matches `taxonomy_pack_mapping.yaml` and falls back to keyword matching when needed.
- [ ] CP updates are persisted back to `tickets/ready/*.json` in real time.
- [ ] Web fallback is used only when a runtime gap is detected and results are cached in `runtime/web_cache.json` with citations.
- [ ] CLI can process a sample ticket JSON and emit deterministic output.

**Key Artifacts**: `runtime/*`, `scripts/agent/*` (new), `scripts/tests/*`

---

## Work Queue (Priority Order)

| Task | Phase | Priority | Status |
|:--|:--|:--|:--|
| Add coverage reporting for pack gaps | Phase 3/5 | MEDIUM | Complete |
| Branch packs catalog expansion (target 50+) | Phase 3 | HIGH | Complete |
| Build QA dashboard from routing metadata + coverage signals | Phase 5 | MEDIUM | Complete |
| Add audit log output + collision/FP tracking | Phase 5 | MEDIUM | Complete |
| Stabilize API tunnel URL | Phase 6 | HIGH | Open |
| Add operator feedback + health endpoints | Phase 6 | MEDIUM | Open |
| Local HTML logging UI (Option B) | Phase 7 | MEDIUM | Open |

---

## Milestones

- **M0**: Discovery complete, acceptance criteria defined. ✓
- **M1**: Core runtime + schema v1.3.1. ✓
- **M2**: Ingestion + normalization working end-to-end. ✓
- **M3**: Taxonomy mapping live, 100% Sub-Issue coverage. ✓
- **M4**: Routing engine with taxonomy-first + explainability. ✓
- **M5**: Stable API integration and pilot rollout.
- **M6**: Hardening complete, production launch.

---

## Open Questions — RESOLVED

- ~~Which ticket sources are in scope for v1 rebuild?~~ → PSA paste/email via raw dump
- ~~What is the minimum viable pack coverage target?~~ → 100% of PSA taxonomy Sub-Issue Types
- ~~What feedback signals are available post-resolution?~~ → Deferred to Phase 6 (deprioritized)
---

## Repository Cleanup — 2025-02-25

**Objective**: Consolidate scripts, remove cruft, and establish clear entry points.

**Changes Made**:
1. ✓ Deleted `Archive/` directory (deprecated PowerShell catalogs)
2. ✓ Moved `scripts/Queue Scripts/` → `scripts/pipeline/`
3. ✓ Created `requirements.txt` (pyyaml, jsonschema)
4. ✓ Fixed version drift in `powershell_nondisruptive_catalog.yaml` (1.1 → 1.3.1)
5. ✓ Cleaned test artifacts from `tickets/processed/`
6. ✓ Created `QUICKSTART.md` at repo root

**New Directory Structure**:
```
scripts/
├── pipeline/      # Ingestion watcher + utilities (moved from Queue Scripts)
├── parsing/       # Ticket parsing
├── agent/         # Agent loop
├── tests/         # Regression tests
└── qa/            # Coverage analysis
```

**Canonical Entry Points**:
- Ingestion: `python scripts/pipeline/ticket_ingestion_watcher.py --once`
- Agent: `python scripts/agent/agent_loop.py`
- Tests: `python scripts/tests/parser_smoke.py`
