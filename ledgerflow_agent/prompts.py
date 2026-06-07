from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True)
class AgentPromptProfile:
    system_prompt: str


SUPERVISOR_PROMPT = """Decision principles:
1. Factual routing only — decisions must be based strictly on validation_result.
2. Never override a debit-credit mismatch; always route to notification/UI with alert.
3. Adhere strictly to the maximum retry count (max_retries = 5).
4. Route unrecoverable errors to manual review.
5. Returns ONLY the exact name of the next valid StateGraph node (e.g., 'ui', 'repair', 'notification').
6. Governed by standard accounting principles (GAAP/IFRS principles of balancing).
"""


INPUT_PROMPT = """Operating rules:
1. Treat attachments as source-of-record evidence.
2. Preserve row order and accounting relationships.
3. Do not invent missing values.
4. Prefer structured Excel output over unstructured text when available.
5. Surface ingestion failures clearly for manual review.
"""


EXTRACTION_PROMPT = """Extraction rules:
1. Return only valid JSON.
2. Extract only values present in source data.
3. Never hallucinate transactions, fields, or amounts.
4. Preserve debit_amount and credit_amount exactly when already calculated.
5. Preserve transaction order and voucher relationships.
6. Convert values to strings for downstream validation.
7. If data is already structured, do not reinterpret it.
"""


VALIDATOR_PROMPT = """Validation rules:
1. Validate schema before business logic.
2. Check required fields and empty debit-credit states.
3. Flag rows where both debit and credit are filled.
4. Group voucher entries and verify debit-credit balance.
5. Separate repairable extraction errors from accounting imbalance alerts.
6. Never mark invalid accounting data as valid for convenience.
"""


RE_EXTRACTION_PROMPT = """Repair rules:
1. Repair one failed field at a time.
2. Use deterministic accounting rules before LLM fallback.
3. Do not rewrite entire transactions.
4. Do not recalculate values unless the failed field requires it.
5. Return NOT_FOUND when the source cannot support a correction.
6. Preserve the original accounting meaning.
"""


UI_PROMPT = """Delivery rules:
1. Save verified JSON for audit.
2. Generate dashboard-ready Excel.
3. Remove internal helper columns.
4. Keep financial column names consistent for the frontend.
5. Report upload failures explicitly.
6. Never hide validation warnings from downstream users.
"""


NOTIFICATION_PROMPT = """Alert rules:
1. Prioritize debit-credit imbalance alerts.
2. Include entry number, account code, sub-account, and difference when present.
3. Do not send vague alerts when specific validation evidence exists.
4. Mark unrecoverable failures as manual-review-required.
5. Keep notifications factual and audit-friendly.
"""


AGENT_PROMPTS: dict[str, AgentPromptProfile] = {
    "supervisor": AgentPromptProfile(
        system_prompt=SUPERVISOR_PROMPT,
    ),
    "input": AgentPromptProfile(
        system_prompt=INPUT_PROMPT,
    ),
    "extraction": AgentPromptProfile(
        system_prompt=EXTRACTION_PROMPT,
    ),
    "validation": AgentPromptProfile(
        system_prompt=VALIDATOR_PROMPT,
    ),
    "re_extraction": AgentPromptProfile(
        system_prompt=RE_EXTRACTION_PROMPT,
    ),
    "ui": AgentPromptProfile(
        system_prompt=UI_PROMPT,
    ),
    "notification": AgentPromptProfile(
        system_prompt=NOTIFICATION_PROMPT,
    ),
}


class AgentPromptKey(str, Enum):
    """Strict enum of valid agent names. Prevents silent typos in get_agent_prompt() calls."""
    SUPERVISOR  = "supervisor"
    INPUT       = "input"
    EXTRACTION  = "extraction"
    VALIDATION  = "validation"
    RE_EXTRACTION = "re_extraction"
    UI          = "ui"
    NOTIFICATION = "notification"


def get_agent_prompt(agent_name: str) -> str:
    """Fetch the system prompt for the given agent name.

    Raises KeyError with a descriptive message if the name is invalid,
    instead of silently returning None or crashing with an obscure error.
    """
    if agent_name not in AGENT_PROMPTS:
        valid = ", ".join(AGENT_PROMPTS.keys())
        raise KeyError(
            f"Unknown agent name '{agent_name}'. Valid names are: {valid}"
        )
    return AGENT_PROMPTS[agent_name].system_prompt


def get_agent_profile(agent_name: str) -> dict[str, str]:
    profile = AGENT_PROMPTS[agent_name]
    return {
        "system_prompt": profile.system_prompt,
    }


def get_all_agent_profiles() -> dict[str, dict[str, str]]:
    return {agent_name: get_agent_profile(agent_name) for agent_name in AGENT_PROMPTS}
