# LedgerFlow Agentic Pipeline

An agentic ETL pipeline built on **LangGraph** to automate the ingestion, extraction, validation, repair, and storage of financial general ledger (GL) transaction records.

```text
                               ┌──────────────┐
                               │  __start__   │
                               └──────┬───────┘
                                      │
                                      ▼
                             ┌────────────────┐
                    ┌───────>│   SUPERVISOR   │<────────┐
                    │        │  (Orchestrator)│         │
                    │        └──────┬─────────┘         │
                    │               │                   │
                    │               ▼                   │
             ┌──────┴───────┐┌──────┴────────┐┌─────────┴────────┐
             │ fetch_email  ││ preprocessing ││   extract_data   │
             └──────────────┘└───────────────┘└──────────────────┘
                    │               │
                    ▼               ▼
             ┌──────────────┐┌───────────────┐
             │   validate   ││  re_extract   │
             └──────┬───────┘└───────────────┘
                    │
                    ├─── (Balanced / Under Limit) ──> push_to_ui ──> [ __end__ ]
                    │                                    │
                    │                                (With Alert)
                    │                                    │
                    └─── (Imbalance / Max Retries) ───> notification ──> [ __end__ ]
```

## Project Overview

LedgerFlow automates the processing of financial/general ledger transaction data. It fetches new files from emails, parses spreadsheets, standardizes formats, validates balance logic, corrects parsing mistakes using AI, and exports audit logs, spreadsheets, and database rows.

The architecture combines:
* **Deterministic Preprocessing Tools**: Fast, precise, and rule-based parsing.
* **AI-Powered Extraction**: Large Language Models (Groq Llama 3.3 70B) to handle highly variable layouts.
* **Accounting Validation**: Checks double-entry bookkeeping rules (e.g. debits == credits).
* **Self-Healing Loop**: Automatic re-extraction and repair loop for malformed data.
* **PostgreSQL Storage & Excel Outputs**: Multi-destination storage for production systems.

---

## Architecture Diagram (Mermaid)

```mermaid
graph TD;
	__start__([__start__])
	supervisor(supervisor)
	fetch_email(fetch_email)
	preprocessing_tools(preprocessing_tools)
	extract_data(extract_data)
	validate(validate)
	re_extract(re_extract)
	push_to_ui(push_to_ui)
	notification(notification)
	__end__([__end__])

	__start__ --> supervisor;
	extract_data --> supervisor;
	fetch_email --> supervisor;
	preprocessing_tools --> supervisor;
	push_to_ui -.-> __end__;
	push_to_ui -.-> notification;
	re_extract --> supervisor;
	supervisor -.-> extract_data;
	supervisor -.-> fetch_email;
	supervisor -.-> notification;
	supervisor -.-> preprocessing_tools;
	supervisor -.-> push_to_ui;
	supervisor -.-> validate;
	validate -.-> notification;
	validate -.-> push_to_ui;
	validate -.-> re_extract;
	notification --> __end__;
```

---

## Environment Variables

Configure these variables in a local `.env` file. The system uses a canonical naming scheme but supports legacy aliases for backward compatibility.

### Canonical Names
* `DATABASE_URL` (e.g., `postgresql://postgres:postgres@localhost:5432/ledgerflow`)
* `LEDGERFLOW_MAIL_USERNAME`
* `LEDGERFLOW_MAIL_PASSWORD`
* `LEDGERFLOW_IMAP_HOST`
* `LEDGERFLOW_IMAP_PORT`
* `LEDGERFLOW_FRONTEND_BASE_URL`
* `LEDGERFLOW_FRONTEND_EMAIL`
* `LEDGERFLOW_FRONTEND_PASSWORD`
* `LEDGERFLOW_ALLOWED_API_HOSTS`
* `LEDGERFLOW_MANAGER_EMAIL`
* `LEDGERFLOW_SENDER_EMAIL`
* `LEDGERFLOW_SENDER_EMAIL_APP_PASSWORD`
* `LEDGERFLOW_SMTP_HOST`
* `LEDGERFLOW_SMTP_PORT`
* `LEDGERFLOW_MAX_ATTACHMENT_MB`

### Supported Legacy Aliases
* `EMAIL_USER` / `EMAIL_PASS`
* `LEDGERFLOW_AGENT_EMAIL` / `LEDGERFLOW_AGENT_PASSWORD`
* `FRONTEND_API_URL` / `LEDGERFLOW_FRONTEND_URL`
* `LOCAL_FILE`

---

## StateGraph Nodes & Agents

### 1. Supervisor (Orchestrator)
A central supervisor node that controls graph routing. It decides which processing step to execute next and intercepts execution to route control flow factually based on state validation results.

### 2. Email Agent (`fetch_email`)
Fetches the latest email body and processes incoming email attachments.
* **Tools**: `fetch_email`

### 3. Preprocessing Agent (`preprocessing_tools`)
Deterministic preprocessing layer that identifies transaction sheets and maps fields.
* **Tools**:
  * **Excel Reader**: Intelligently scores and selects sheets based on financial indicators (e.g. "debit", "credit", "voucher").
  * **Field Mapper**: Maps variable source columns to canonical target schema fields.
  * **Relational Mapper**: Asserts relational accounting structures (vouchers, accounts, etc.).
  * **Financial Logic**: Dynamically calculates debit and credit amounts based on transaction sign fallbacks and business classifications.

### 4. Extraction Agent (`extract_data`)
Converts raw, unformatted financial tables into structured accounting JSON payloads using the Groq Llama 3.3 70B model.
* **Tools**: `extract_data`

### 5. Validator Agent (`validate`)
Performs rigorous structural and business logic checks.
* **Checks**:
  * Schema consistency
  * Required fields
  * Debit-credit balancing (flagging dtcd differences)
  * Duplicate detections

### 6. Re-Extraction Agent (`re_extract`)
Automatically runs target repairs on validation failures (e.g. mismatched columns or missing elements), looping up to 5 times to self-heal extraction inaccuracies.
* **Tools**: `re_extract_field`

### 7. UI Agent (`push_to_ui`)
Persists outputs to local files, databases, and APIs.
* **Actions**:
  * Generates cleaned production-ready JSON (`verified_data.json`).
  * Creates formatted Excel sheets (`verified_data.xlsx`).
  * **PostgreSQL Integration**: Automatically inserts validated rows into the `ledger_transactions` table. Operates with a safety fallback that logs connection warnings and continues exporting gracefully if database is offline.
  * Authenticates and uploads verified data to the frontend system APIs.
* **Tools**: `save_json`, `generate_excel`, `login`, `upload_file`

### 8. Notification Agent (`notification`)
Dispatches failure notifications to manager email addresses or alerts to the UI dashboard in case of double-entry imbalance or unrecoverable processing failures.
* **Tools**: `push_validation_alert`, `send_failure_notification`
