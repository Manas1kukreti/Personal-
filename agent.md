# LedgerFlow Agent Architecture

This document provides a comprehensive, minute-detail overview of the current architecture of the LedgerFlow Agent project. It serves as the definitive reference for the system's design, node states, routing logic, data flow, and file locations.

**Project Root:** `c:\Users\acer\OneDrive\Documents\LedgerFlow agent\agentic_Ai`

---

## 1. High-Level Overview

LedgerFlow is an agentic, AI-driven financial ETL (Extract, Transform, Load) pipeline. Its primary purpose is to:
1. Fetch unstructured financial data (like emails or raw text).
2. Use Large Language Models (LLMs) to extract structured accounting data into JSON.
3. Rigorously validate that data against standard accounting principles (like Debit/Credit balancing).
4. Intelligently triage and repair broken fields using contextual reasoning.
5. Push the verified data to a frontend UI (`verified_data.xlsx`) or alert an administrator via SMTP email if human review is needed.

The system is built on **LangGraph**, orchestrating a state machine of specialized agents.

---

## 2. Directory Structure & File Paths

The architecture strictly separates the "Engine" (orchestration) from the "Workers" (execution).

### The Engine: `ledgerflow_agent/`
Located at: `c:\Users\acer\OneDrive\Documents\LedgerFlow agent\agentic_Ai\ledgerflow_agent\`
This package contains the core orchestration logic. It does not perform data processing; instead, it dictates the rules of execution.

- **`graph.py`**: Initializes the LangGraph `StateGraph`, adds all nodes, sets up conditional edges based on router functions, and compiles the graph.
- **`nodes.py`**: The largest engine file. Contains the actual execution blocks for `start_node`, `input_node`, `extraction_node`, `validation_node`, `repair_node`, `ui_node`, `notification_node`, and `finalize_node`. It also houses the LLM router logic (`_llm_route`).
- **`state.py`**: Defines the `LedgerFlowState` TypedDict, which dictates exactly what data is passed between nodes.
- **`memory.py`**: Manages reading and writing to `runtime_memory.json` to persist state and history between pipeline runs.
- **`prompts.py`**: Centralized repository for all system prompts (`SUPERVISOR_PROMPT`, `INPUT_PROMPT`, `EXTRACTION_PROMPT`, etc.). Fetched via `get_agent_prompt(agent_name)`.
- **`registry.py`**: The global tool registry. Defines the `call_tool()` function which executes tools securely.
- **`tool_policy.py`**: Security module. Defines `filter_langchain_tools()` to restrict which agents (by name) have permission to execute which tools.
- **`guardrails.py`**: Security, data sanitization, API URL validation, and PII masking.
- **`executor.py` / `orchestrator.py`**: Entry points for running the graph dynamically.

### The Workers: `agents/`
Located at: `c:\Users\acer\OneDrive\Documents\LedgerFlow agent\agentic_Ai\agents\`
This directory contains the individual, specialized logic and scripts for each domain.

- **`react_agent.py`**: A core utility that wraps LangChain ReAct agents. It provides `create_react_agent(agent_name)` and `get_supervisor_llm()`, empowering the LLM to reason and execute tools in a loop.
- **`data_input.py`**: Handles fetching emails and reading external data.
- **`llm_extractor.py`**: Transforms raw text into structured JSON.
- **`validator.py`**: Enforces accounting rules (e.g., DTCD balancing) using deterministic logic.
- **`repair_agent.py`**: Contains the `triage()` function to analyze validation errors and build a repair strategy.
- **`re_extractor.py`**: Executes the actual LLM calls to fix specific broken fields based on context.
- **`ui_agent.py`**: Contains `push_to_ui()`, which saves `verified_data.json`, generates `verified_data.xlsx`, logs into the frontend API, and uploads the payload.
- **`notification_agent.py`**: Contains `send_failure_notification()`, which generates and dispatches professional SMTP emails for manual review alerts.

### Supporting Files
- **`tools/`**: Directory containing atomic functions like `field_mapper_tool.py`, `financial_logic_tool.py`, `langchain_tools.py` (which wraps tools for LangChain), etc.
- **`tests/`**: Pytest suite containing 109 tests covering routing, extraction, validation, and logic.
- **`config_loader.py`**: Loads parameters from `project_config.yml`.
- **`main.py`**: The execution entry point for the entire application.

---

## 3. The LangGraph State Machine

The pipeline operates on the `LedgerFlowState` dictionary, passed sequentially between nodes.

### State Schema (`state.py`)
- `processing_status`: Tracks current phase (e.g., "started", "validated", "ui_failed").
- `extracted_data`: The stringified JSON payload of financial transactions.
- `validation_result`: Dictionary containing `status`, `errors` list, and the raw parsed `data`.
- `retry_count`: Integer tracking the number of validation cycles attempted.
- `email_text`: The raw input text.
- `tools_used`: List of executed tools.
- `tool_results`: Dictionary mapping tool names to their outputs (crucial for audit trails).
- `memory_snapshot` & `memory_summary`: Context from previous runs.

### Node Lifecycle (`nodes.py`)

1. **`start_node`**: Initializes state, loads memory from `runtime_memory.json`, attaches metadata (version, timestamp), and fetches the memory summary.
2. **`input_node`**: Uses the `input` ReAct agent or falls back to the `fetch_email` tool. 
   - *Status changes to*: `input_ready`, `structured_input_ready`, or `input_failed`.
3. **`extraction_node`**: Skips if data is already structured. Otherwise, invokes the `extraction` ReAct agent on the raw text. 
   - *Status changes to*: `data_extracted` or `extraction_failed`.
4. **`validation_node`**: The critical gatekeeper. 
   - Feeds the *full* stringified JSON to the `validation` ReAct agent or falls back to `validate_data`.
   - **Crucial Metric**: This is the *only* place where `retry_count` is incremented, standardizing it as a strict "validation cycle" counter.
   - *Status changes to*: `validated` or `validation_failed`.
5. **`repair_node`**: 
   - Uses `agents/repair_agent.py:triage` to build a strategy.
   - Loops through errors and invokes `agents/re_extractor.py:re_extract_field`.
   - Appends all successful repairs to `state["tool_results"]["re_extract_field"]`.
   - *Status changes to*: `repaired` or `repair_failed`.
6. **`ui_node`**: 
   - Intercepts the `tool_results` to extract `repaired_fields`.
   - Injects a `Repairs Applied` key into the `validation_result["data"]` dictionaries.
   - Calls `agents/ui_agent.py:push_to_ui` to generate files and push to API.
   - *Status changes to*: `completed`, `ui_pushed_with_alert`, or `ui_failed`.
7. **`notification_node`**: 
   - Handles unrecoverable scenarios.
   - Generates UI alerts via `push_validation_alert`.
   - Calls `agents/notification_agent.py:send_failure_notification()` to dispatch an SMTP email.
   - *Status changes to*: `manual_review_required`.
8. **`finalize_node`**: Logs metrics, calculates `total_duration_ms`, updates `runtime_memory.json`, and terminates execution.

---

## 4. Routing Logic (The Brains)

LedgerFlow uses **LLM-First Routing with Deterministic Fallbacks**. The LLM routing is handled by `_llm_route()` in `nodes.py`, which invokes the `supervisor` agent via `get_supervisor_llm()`.

If the LLM hallucinates an invalid node, `_llm_route` retries up to 3 times before safely falling back to hardcoded python logic.

* **`route_after_start`** (Deterministic): Routes to `validate` if input is pre-structured, otherwise `input`.
* **`route_after_input`** (LLM-First): Valid nodes: `["extract", "validate", "notification"]`. 
  * *Fallback logic*: If `input_failed` → `notification`. If structured → `validate`. Otherwise → `extract`.
* **`route_after_extraction`**: Implicit edge to `validate`.
* **`route_after_validation`** (LLM-First): Valid nodes: `["ui", "repair", "notification"]`.
  * *Fallback logic*: If valid or contains strict balance errors → `ui`. If max retries hit → `notification`. Otherwise → `repair`.
* **`route_after_repair`** (LLM-First): Valid nodes: `["validate", "extract", "notification"]`.
  * *Fallback logic*: If repaired → `validate`. If max retries hit → `notification`. Otherwise → `extract`.
* **`route_after_ui`** (Deterministic): If `ui_failed` or `ui_pushed_with_alert` → `notification`. Otherwise → `finalize`.

---

## 5. Audit Traceability & Data Flow

Data integrity and traceability are paramount in the LedgerFlow pipeline.

1. **Repair Tracing**: When the LLM modifies a financial field in `repair_node`, that modification is logged into `tool_results`.
2. **Audit Injection**: In `ui_node`, before pushing data out, the code parses those tool results, matches them by `transaction_index`, and dynamically injects a `"Repairs Applied": "field_name (strategy)"` key into the row data.
3. **Excel Output**: `agents/ui_agent.py` defines `preferred_columns`, which explicitly includes `Repairs Applied`. Consequently, `verified_data.xlsx` will clearly highlight any cell that was generated or altered by AI, ensuring accountants never blindly trust hallucinated numbers.
4. **Failure Transparency**: If `notification_node` is reached due to validation loop exhaustion, `send_failure_notification` intercepts the exact list of Pydantic validation errors and translates them into a human-readable summary for the SMTP email body.
6. Recent Refactorings

- **Notification Node Split**: The `notification_node` was divided into UI alert handling and SMTP email dispatch, producing distinct `ui_alert` and `smtp_notification` result objects for clearer error tracking.
- **Agent Prompt Enum**: Added `AgentPromptKey` enum in `prompts.py` to enforce valid agent names and raise informative `KeyError` on typos.
- **Tool Append Improvements**: `utils.append_tool` now deduplicates `tools_used` and stores `tool_results` as a list, preserving all tool call histories.
- **Tool Registry & Policy Fixes**: Registered the `read_excel` tool in `registry.py` and added it to the permissions list in `tool_policy.py` so the agent can successfully process files.
- **LangChain/Groq Schema Stabilization**: Migrated tool definitions in `langchain_tools.py` to use `StructuredTool` with `Any` parameter types. This resolves a known conflict where Groq's tool-calling implementation strictly rejects unstructured JSON objects.
- **Validation Node Hardening**: Re-prioritized the deterministic `validate_data` function in `nodes.py` to bypass brittle LLM schema outputs, preventing catastrophic empty-output crashes during the validation phase.
- **Data Sanitization & NaN Handling**: Added strict dataframe sanitization (`df.fillna("")`) in `data_input.py` just before JSON conversion. This prevents unmapped Pandas `NaN` placeholders from poisoning the JSON schema and breaking downstream validation.
- **Pydantic Type Coercion**: Implemented an explicit string coercion loop in `validator.py` right before passing the `transformed_transaction` to the Pydantic `GLTransaction` model. This fixes a fatal crash in Pydantic's strict `string_type` mode that was violently rejecting raw floats and integers (like voucher numbers `2001.1`) originating from the Excel file.

