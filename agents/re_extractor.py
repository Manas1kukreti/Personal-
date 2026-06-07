import json
from pathlib import Path

from dotenv import load_dotenv

from ledgerflow_agent.llm import get_groq_client
from ledgerflow_agent.prompts import get_agent_prompt

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

from agents.validator import GLTransaction
from tools.financial_logic_tool import determine_debit_credit





def validate_repair(transaction_data, failed_field, new_value):
    from agents.validator import GLTransaction
    
    # We construct a mock transformed transaction just like validator.py does
    transformed = {
        "voucher_date": transaction_data.get("voucher_date", ""),
        "entry_no": transaction_data.get("voucher_number", ""),
        "sub_account": transaction_data.get("subaccount", ""),
        "details": transaction_data.get("particulars", ""),
        "debit_amount": transaction_data.get("debit_amount", ""),
        "credit_amount": transaction_data.get("credit_amount", ""),
        "account_code": transaction_data.get("account_key", ""),
        "country": transaction_data.get("country", ""),
        "region": transaction_data.get("region", ""),
        "class_name": transaction_data.get("account_class", ""),
        "account_subclass": transaction_data.get("account_subclass", "")
    }
    
    field_map = {
        "voucher_date": "voucher_date",
        "voucher_number": "entry_no",
        "subaccount": "sub_account",
        "particulars": "details",
        "debit_amount": "debit_amount",
        "credit_amount": "credit_amount",
        "account_key": "account_code",
        "country": "country",
        "region": "region",
        "account_class": "class_name",
        "account_subclass": "account_subclass"
    }
    
    mapped_field = field_map.get(failed_field, failed_field)
    if mapped_field in transformed:
        transformed[mapped_field] = new_value
        
    try:
        GLTransaction(**transformed)
        return True
    except Exception as e:
        print(f"Local validation rejected repair for {failed_field}: {e}")
        return False

def _safe_return(transaction_data, failed_field, value):
    if value is None or str(value).upper() == "NOT_FOUND" or value == "":
        return None
    if validate_repair(transaction_data, failed_field, value):
        return value
    return None

def re_extract_field(transaction_data, failed_field, current_value):

    print(f"\nRE-EXTRACTING FIELD: {failed_field}\n")

    try:
        if failed_field in ["debit_amount", "credit_amount"]:
            amount = transaction_data.get("amount", 0)
            account_class = transaction_data.get("class", "")
            debit, credit = determine_debit_credit(amount, account_class)
            return _safe_return(transaction_data, failed_field, debit if failed_field == "debit_amount" else credit)

        if failed_field == "ledger_name":
            return transaction_data.get("subaccount", "") or transaction_data.get("account", "") or None

        if failed_field == "voucher_type":
            return transaction_data.get("class", "") or transaction_data.get("subclass", "") or None

        if failed_field in ["particulars", "narration"]:
            return _safe_return(transaction_data, failed_field, transaction_data.get("details", "") or None)

        if failed_field == "account_code":
            account_key = transaction_data.get("account_key", "")
            return _safe_return(transaction_data, failed_field, str(account_key) if account_key != "" else None)

        if failed_field == "country":
            return _safe_return(transaction_data, failed_field, transaction_data.get("country", "") or None)

        if failed_field == "region":
            return _safe_return(transaction_data, failed_field, transaction_data.get("region", "") or None)
    except Exception as e:
        print("\nRULE-BASED RECOVERY FAILED\n")
        print(e)

    print("\nUSING LLM FALLBACK...\n")

    prompt = f"""
{get_agent_prompt("re_extraction")}

Recover ONLY the failed field.

STRICT RULES:
1. Return ONLY corrected value.
2. No explanation.
3. No JSON.
4. No hallucination.
5. If unavailable return:
NOT_FOUND

FAILED FIELD:
{failed_field}

CURRENT VALUE:
{current_value}

TRANSACTION:
{json.dumps(transaction_data, indent=2)}
"""

    try:
        response = get_groq_client().chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": get_agent_prompt("re_extraction")},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
        )
        corrected_value = response.choices[0].message.content.strip().replace("```", "").strip()
        print("\nLLM CORRECTED VALUE:\n")
        print(corrected_value)

        if corrected_value.upper() == "NOT_FOUND" or corrected_value == "":
            return None
        return _safe_return(transaction_data, failed_field, corrected_value)
    except Exception as e:
        print("\nLLM RE-EXTRACTION FAILED\n")
        print(e)
        return None
