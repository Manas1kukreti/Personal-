import json

# 🔹 Validation Agent
def validate_extracted_data(email_text, extracted_json):

    print("\n🔍 VALIDATION AGENT STARTED...\n")

    try:

        # Remove markdown formatting from Groq response
        cleaned_json = extracted_json.replace("```json", "")
        cleaned_json = cleaned_json.replace("```", "")

        # Convert JSON string into Python list
        data = json.loads(cleaned_json)

        verified_data = []

        # Loop through all extracted transactions
        for entry in data:

            verified_entry = {}

            # -----------------------------
            # CUSTOMER NAME VALIDATION
            # -----------------------------
            customer_name = entry.get("customer_name", "")

            if customer_name.lower() in email_text.lower():
                verified_entry["customer_name"] = customer_name
                print(f"✅ Customer verified: {customer_name}")

            else:
                print(f"❌ Customer failed: {customer_name}")

            # -----------------------------
            # TRANSACTION ID VALIDATION
            # -----------------------------
            transaction_id = entry.get("transaction_id", "")

            if transaction_id in email_text:
                verified_entry["transaction_id"] = transaction_id
                print(f"✅ Transaction verified: {transaction_id}")

            else:
                print(f"❌ Transaction failed: {transaction_id}")

            # -----------------------------
            # AMOUNT VALIDATION
            # -----------------------------
            amount = str(entry.get("amount", ""))

            if amount in email_text:
                verified_entry["amount"] = amount
                print(f"✅ Amount verified: {amount}")

            else:
                print(f"❌ Amount failed: {amount}")

            # -----------------------------
            # PAYMENT METHOD VALIDATION
            # -----------------------------
            payment_method = entry.get("payment_method", "")

            if payment_method.lower() in email_text.lower():
                verified_entry["payment_method"] = payment_method
                print(f"✅ Payment method verified: {payment_method}")

            else:
                print(f"❌ Payment method failed: {payment_method}")

            # Add only verified records
            if verified_entry:
                verified_data.append(verified_entry)

        print("\n🎯 FINAL VERIFIED JSON:\n")
        print(json.dumps(verified_data, indent=4))

        return verified_data

    except Exception as e:
        print("❌ VALIDATION ERROR:", e)
        return []