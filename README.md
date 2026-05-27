

```text

                ┌────────────────────┐

                │    EMAIL SOURCE    │

                │ Gmail / Outlook    │

                └─────────┬──────────┘

                          │

                          ▼

                ┌────────────────────┐

                │    EMAIL AGENT     │

                │ Fetch latest mail  │

                └─────────┬──────────┘

                          │

                          ▼

                ┌────────────────────┐

                │    INPUT AGENT     │

                │ Tool Orchestrator  │

                └─────────┬──────────┘

                          │

        ┌─────────────────┼─────────────────┐

        ▼                 ▼                 ▼

┌──────────────┐ ┌────────────────┐ ┌──────────────────┐

│ Excel Reader │ │ Field Mapper   │ │ Relational Mapper│

│ Tool         │ │ Tool           │ │ Tool             │

└──────┬───────┘ └────────┬───────┘ └────────┬─────────┘

       │                  │                  │

       └──────────────────┼──────────────────┘

                          ▼

                ┌────────────────────┐

                │ Financial Logic    │

                │ Tool               │

                └─────────┬──────────┘

                          ▼

                ┌────────────────────┐

                │  EXTRACTION AGENT  │

                │ LLM Structured JSON│

                └─────────┬──────────┘

                          ▼

                ┌────────────────────┐

                │ VALIDATOR AGENT    │

                │ Schema Validation  │

                └─────────┬──────────┘

                          │

              ┌───────────┴───────────┐

              │                       │

              ▼                       ▼

    ┌──────────────────┐     ┌──────────────────┐

    │     UI AGENT     │     │ RE-EXTRACTION    │

    │ Excel + Upload   │     │ AGENT            │

    └────────┬─────────┘     └────────┬─────────┘

             │                        │

             ▼                  Retry up to

    ┌────────────────────┐         5 times

    │ FRONTEND / DASHBOARD│             │

    └────────────────────┘              ▼

                              ┌────────────────────┐

                              │ VALIDATOR AGENT    │

                              │ Recheck Output     │

                              └─────────┬──────────┘

                                        │

                         ┌──────────────┴──────────────┐

                         │                             │

                         ▼                             ▼

               ┌──────────────────┐       ┌────────────────────┐

               │     UI AGENT     │       │ NOTIFICATION AGENT │

               │ Excel + Upload   │       │ Failure Alert      │

               └────────┬─────────┘       └────────────────────┘

                        │

                        ▼

               ┌────────────────────┐

               │ FRONTEND / DASHBOARD│

               └────────────────────┘

```


Project Overview

The system automatically processes financial/general ledger data from emails and Excel files and converts it into structured accounting-ready output.

The architecture combines:

* Deterministic preprocessing tools
* AI-powered extraction
* Accounting business logic
* Validation and retry mechanisms
* Frontend integration

This hybrid approach makes the pipeline more reliable and production-oriented compared to using only LLMs.

Agents and Tools

1. Email Agent

Responsible for fetching the latest financial email and extracting attachments.

Tool Used

* email_tool

Output

* Email body
* Excel attachment path
* Raw financial content


2. Input Agent

Acts as the preprocessing and orchestration layer before LLM extraction.

This agent uses multiple deterministic tools.



Excel Reader Tool

Reads all Excel sheets and intelligently selects the most relevant financial transaction sheet using scoring logic.

Features

* Detects transaction sheets
* Rejects master/reference sheets
* Uses financial keywords like:
    * debit
    * credit
    * voucher
    * transaction
    * journal
    
Field Mapper Tool:

Standardizes inconsistent column names into a unified master schema.

⸻

Relational Mapper Tool

Maintains accounting relationships between:

* voucher entries
* accounts
* subaccounts
* hierarchy structures

This helps preserve double-entry accounting behavior.


Financial Logic Tool

Applies intelligent accounting rules to determine:

* Debit Amount
* Credit Amount

Logic Priority

1. Business Rules
2. Account Subclass Rules
3. Keyword Intelligence
4. Amount Sign Fallback

Extra Features

* Handles bracket amounts:
    * (5000) → -5000
* Voucher pairing logic:
    * 1.1 ↔ 1.2
* Real-world accounting behavior


3. Extraction Agent

Uses Groq Llama 3.3 70B to convert processed financial rows into structured JSON.

Tool Used

* llm_tool

Responsibilities

* Extract structured financial data
* Generate accounting-ready JSON
* Preserve transaction relationships


4. Validator Agent

Validates extracted JSON before final processing.

Validation Checks

* Required fields
* Data types
* Empty row removal
* Voucher balancing
* Duplicate detection
* Schema consistency


5. Re-Extraction Agent

Handles extraction failures.

If validation fails:

* Re-runs extraction
* Attempts correction
* Retries up to 5 times

This improves reliability and reduces hallucinations from LLM output.



6. UI Agent

Responsible for generating final Excel output and pushing data to frontend/dashboard APIs.

Features

* Generates final Excel file
* Removes internal fields
* Renames columns for UI readability
* Pushes data to frontend APIs


