# service-desk-copilot

Public portfolio version of the production MSP service desk copilot (QF_Wiz).
Referenced on resume and public GitHub. Demonstrates the architecture without proprietary data.

## Tech Stack

- **GPT Runtime:** OpenAI Custom GPT + Knowledge files (production architecture)
- **Agent:** Python 3.10+, PyYAML, NetworkX, NumPy
- **API (prototype):** FastAPI, Uvicorn, Pydantic v2, WebSockets
- **Web (prototype):** React 19, TypeScript, Vite, Tailwind CSS, Zustand, TanStack Query, Recharts
- **Testing:** pytest (pytest-cov, pytest-xdist)

## Project Structure

```
runtime/                GPT Knowledge files (same architecture as production)
  router.txt            Master system prompt (≤8K chars)
  branch_packs_catalog.yaml
  powershell_*_catalog.yaml
  comms_templates/
  kb_articles/
  resolution_logs/
scripts/                Python agent runtime (engineering prototype)
  agent/, core/, parsing/, analytics/, pipeline/, qa/, tests/
api/                    FastAPI service (engineering prototype)
web/                    React dashboard (engineering prototype)
tickets/                Sample ticket fixtures
docs/                   Documentation
```

## Architecture

Same as QF_Wiz: 4 pillars, 3-tier PS catalog, STOP blocks, taxonomy-first routing.
The Python agent, FastAPI API, and React dashboard are engineering prototypes
demonstrating a full-stack implementation beyond the GPT runtime.

## Key Commands

```bash
PYTHONPATH=. pytest scripts/tests/ -v
```

## Guardrails

- **No proprietary SOPs** — kb_articles/ contains generic examples only
- **No real ticket data** — tickets/ready/ has sample fixtures only
- **No customer-specific playbooks** — branch packs are generic (55 examples)
- **No internal references** — no Autotask API keys, ThreatLocker configs, or client names
- When adding content, verify nothing proprietary leaks from QF_Wiz
