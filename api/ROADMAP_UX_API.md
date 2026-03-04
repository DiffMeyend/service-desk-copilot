## Phase 6: UX & Workflow Integration — 30% COMPLETE

**Objective**: Integrate with ticketing workflow and triage operations, provide clear operator prompts, enable feedback loops.

**Tasks**:
1. Implement API server for payload fetch by ticket ID ✓
2. Add X-API-Key authentication ✓
3. Create VS Code tasks for watcher/API/tunnel ✓
4. Set up Cloudflare tunnel for external access ✓ (quick tunnel)
5. Stabilize API tunnel URL with named Cloudflare tunnel — OPEN
6. Update api/openapi.json with stable hostname — OPEN
7. Add health check endpoint to API server — OPEN
8. Integrate with GPT action calls — PARTIAL (working but URL rotates)
9. Add operator feedback submission endpoint — OPEN
10. Implement feedback loop for routing quality improvement — OPEN

**Acceptance Criteria**:
- [x] API serves payloads at GET /payload/{id}
- [x] API requires valid X-API-Key header
- [x] VS Code tasks launch watcher, API, and tunnel
- [ ] Stable hostname configured (e.g., api.qfwiz.yourdomain.com)
- [ ] OpenAPI spec updated with stable URL
- [ ] Health endpoint returns 200 for connectivity checks
- [ ] GPT actions work without URL refresh

**Key Artifacts**: `api/server.py`, `api/openapi.json`, `.vscode/tasks.json`