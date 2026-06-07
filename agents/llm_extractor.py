import json
from pathlib import Path

from dotenv import load_dotenv

from ledgerflow_agent.guardrails import validate_json_array_output
from ledgerflow_agent.llm import get_groq_client
from ledgerflow_agent.prompts import get_agent_prompt

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")



def convert_all_to_string(data):
    if isinstance(data, list):
        for row in data:
            for key in row:
                row[key] = "" if row[key] is None else str(row[key])
    return data



def extract_data(email_text):
    print("\nEXTRACTING GL DATA...\n")
    print("\nSENDING DATA TO GROQ...\n")

    prompt = f"""
{get_agent_prompt("extraction")}

Your task is to normalize and structure
already preprocessed General Ledger data.

=====================================================
IMPORTANT
=====================================================

The input data is already preprocessed using:

- field mapping
- relational mapping
- financial logic rules

DO NOT recalculate financial values.

=====================================================
STRICT EXTRACTION RULES
=====================================================

1. Extract ONLY values present in input.
2. NEVER hallucinate fields.
3. NEVER generate fake transactions.
4. NEVER modify financial amounts.
5. NEVER change business meaning.
6. Preserve dates exactly as present.
7. Preserve transaction order exactly.
8. Return ONLY valid JSON.
9. Return ONLY JSON array.
10. No markdown.
11. No explanations.
12. No comments.
13. No extra text before JSON.
14. No extra text after JSON.
15. If field not present in source data,
DO NOT include that field in output JSON.
16. Preserve original accounting meaning.
17. Maximum 14 rows only.
18. Ignore helper columns.
19. Ignore unnamed columns.
20. Ignore blank columns.

=====================================================
VERY IMPORTANT DATA TYPE RULE
=====================================================

RETURN ALL VALUES AS STRINGS.

=====================================================
PRE-CALCULATED FINANCIAL VALUES
=====================================================

The following fields are already calculated.

NEVER recalculate them.

- debit_amount
- credit_amount
- account_class
- account_subclass
- country
- region

IMPORTANT:

1. NEVER modify debit_amount.
2. NEVER modify credit_amount.
3. NEVER apply sign logic again.
4. NEVER swap debit/credit.
5. Preserve financial values exactly.

=====================================================
OUTPUT FIELD RULES
=====================================================

1. Return ALL original business fields present in source data.
2. ALWAYS include these fields if present:
- voucher_number
- voucher_date
- particulars
- account
- subaccount
- account_class
- account_subclass
- debit_amount
- credit_amount
- country
- region
- account_key
3. DO NOT create fake values.
4. DO NOT omit account hierarchy fields.
5. Preserve all financial values exactly.

=====================================================
RETURN FORMAT
=====================================================

Return ONLY valid JSON array.

=====================================================
INPUT DATA
=====================================================

{email_text}
"""

    try:
        response = get_groq_client().chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": get_agent_prompt("extraction")},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
            max_tokens=4000,
        )

        output = response.choices[0].message.content.strip()
        output = output.replace("```json", "").replace("```", "").strip()
        parsed_output = validate_json_array_output(output, "Extraction Agent")
        parsed_output = convert_all_to_string(parsed_output)
        output = json.dumps(parsed_output, indent=4)

        print("\nGROQ RESPONSE:\n")
        print(output)
        return output
    except Exception as e:
        print("\nGROQ ERROR:\n")
        print(e)
        return "LLM FAILED"
