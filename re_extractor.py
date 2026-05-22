import os
import json

from groq import Groq


# =========================================================
# GROQ CLIENT
# =========================================================

client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)


# =========================================================
# RE-EXTRACTION FUNCTION
# =========================================================

def re_extract_field(
    transaction_data,
    failed_field,
    current_value
):

    print(
        f"\nRE-EXTRACTING FIELD: {failed_field}\n"
    )

    # =====================================================
    # SAFETY CHECK
    # =====================================================

    if current_value in ["", None, "NaN"]:

        print(
            "\nORIGINAL VALUE IS EMPTY "
            "IN SOURCE DATA\n"
        )

    # =====================================================
    # ONLY SEND FAILED TRANSACTION
    # =====================================================

    prompt = f"""
You are a financial data correction engine.

Your task:
Extract ONLY the correct value for the missing field.

STRICT RULES:
1. Return ONLY the value.
2. Do NOT explain.
3. Do NOT generate fake values.
4. If value is missing in source, return EXACTLY:
NOT_FOUND
5. Do NOT guess from other transactions.

FAILED FIELD:
{failed_field}

TRANSACTION DATA:
{json.dumps(transaction_data, indent=2)}
"""

    try:

        response = client.chat.completions.create(

            model="llama-3.3-70b-versatile",

            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],

            temperature=0
        )

        corrected_value = (
            response
            .choices[0]
            .message
            .content
            .strip()
        )

        # =================================================
        # SAFETY CHECK
        # =================================================

        if corrected_value == "NOT_FOUND":

            print(
                "\nVALUE NOT FOUND "
                "IN SOURCE DATA\n"
            )

            return None

        if corrected_value == "":

            print(
                "\nEMPTY RESPONSE "
                "FROM LLM\n"
            )

            return None

        print(
            f"\nCORRECTED VALUE: "
            f"{corrected_value}\n"
        )

        return corrected_value

    except Exception as e:

        print("\nRE-EXTRACTION FAILED\n")

        print(e)

        return None