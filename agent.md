# LedgerFlow Agent Handoff

This is the shortest useful briefing for another agent working in this repository. Read it first when you need the combined web app and extraction pipeline context.

## Project Summary

LedgerFlow is a financial workflow system with two tightly related parts:

- A web app for upload, review, audit, alerts, and role-based dashboards
- An agentic ETL pipeline for extracting, validating, repairing, and exporting general ledger data

The web app is the operator surface. The pipeline is the automation layer that cleans messy source data and produces verified outputs for the backend and UI.

## Repo Map

- `frontend/` - React UI, role-based pages, upload center, dashboards, alerts, and audit views
- `backend/` - FastAPI API, auth, uploads, comments, approvals, alerts, audit, analytics, WebSockets
- `ledgerflow_agent/` - LangGraph orchestration, routing, state, prompts, guardrails, memory
- `agents/` - Specialised workers for input, extraction, validation, repair, UI export, and notification
- `tools/` - Deterministic helpers for parsing, field mapping, financial logic, and related rules
- `graph/` - Visual graph assets and diagram source
- `tests/` - Pytest coverage for routing, validation, utilities, and integration paths

## Runtime Flow

1. The source file or email payload is ingested.
2. Preprocessing normalizes sheets, columns, and transaction shape.
3. The extraction step converts raw content into structured transaction data.
4. Validation checks schema and accounting rules, especially debit and credit balance.
5. Repair logic patches bad fields when the issue is recoverable.
6. Verified output is written to JSON and Excel, then pushed to the UI and optionally the database.
7. Unrecoverable failures trigger alerts and manual review notifications.

## Pipeline Nodes

The pipeline is implemented in `ledgerflow_agent/nodes.py` and compiled by the graph in `ledgerflow_agent/graph.py`.

Typical node roles:

- `start_node` - initialize runtime state and memory
- `input_node` - fetch or normalize the incoming source data
- `extraction_node` - run the extraction agent when structured data is not already available
- `validation_node` - run deterministic and LLM-assisted validation
- `repair_node` - triage validation failures and repair specific fields
- `ui_node` - generate `verified_data.json` and `verified_data.xlsx`, then push the result onward
- `notification_node` - emit alerts and human-review notifications
- `finalize_node` - persist memory and close out the run

## Routing Rules

Routing is intended to be factual and state-driven.

- Start routes to input or validation depending on whether the payload is already structured
- Validation routes to UI when the result is clean
- Recoverable failures route to repair and then back to validation
- Balance failures and unrecoverable issues route to notification
- Retry limits are enforced by workflow state, not by ad hoc node behavior

## Important Files

### Pipeline

- `ledgerflow_agent/state.py` - shared state shape
- `ledgerflow_agent/routing.py` - route helpers
- `ledgerflow_agent/prompts.py` - prompt registry
- `ledgerflow_agent/registry.py` - tool execution registry
- `ledgerflow_agent/tool_policy.py` - agent-to-tool permissions
- `ledgerflow_agent/guardrails.py` - sanitization and safety checks
- `ledgerflow_agent/memory.py` - runtime memory persistence
- `ledgerflow_agent/executor.py` - execution entrypoint helpers
- `ledgerflow_agent/orchestrator.py` - orchestration helpers

### Workers

- `agents/data_input.py` - fetch email body, attachments, and source text
- `agents/llm_extractor.py` - transform raw text into structured JSON
- `agents/validator.py` - enforce schema and accounting rules
- `agents/re_extractor.py` - repair broken fields without rerunning the entire pipeline
- `agents/ui_agent.py` - write output files and push verified payloads
- `agents/notification_agent.py` - send manual-review notifications
- `agents/repair_agent.py` - decide what to repair and how
- `agents/react_agent.py` - ReAct wrappers and supervisor LLM helpers

### Backend Integration

- `backend/app/api/uploads.py` - upload flow and pipeline integration
- `backend/app/api/alerts.py` - validation alert APIs
- `backend/app/api/comments.py` - review thread APIs
- `backend/app/api/approvals.py` - approval and re-upload flow
- `backend/app/services/excel_parser.py` - spreadsheet parsing and normalization
- `backend/app/services/websocket_manager.py` - live update broadcast

## Data And Outputs

The main generated artifacts are:

- `verified_data.json`
- `verified_data.xlsx`

The pipeline also keeps runtime memory and may write repair or audit metadata depending on the execution path. Those files should not be treated as source of truth for user-facing records.

## Operational Notes

- Keep backend authorization authoritative. Frontend guards are only a usability layer.
- Preserve the current column normalization and financial logic rules when changing extraction or validation behavior.
- When schema changes, update models, migrations, serializers, and docs together.
- When upload or output shape changes, update the backend API, frontend consumers, and pipeline exporters together.
- If the pipeline is run directly, use `main.py`.

## Verification Commands

Backend syntax check:

```powershell
py -3 -m compileall backend\app
```

Frontend build:

```powershell
cd frontend
npm run build
```

Pipeline run:

```powershell
py -3 main.py
```

Full stack rebuild:

```powershell
docker compose down
docker compose up --build --force-recreate
```
