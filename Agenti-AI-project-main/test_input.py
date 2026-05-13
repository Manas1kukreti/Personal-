from data_input import get_email_text
from llm_extractor import extract_data
from validator_agent import validate_extracted_data

# 🔹 STEP 1  Get Email
email_text = get_email_text()

print("\n📩 ORIGINAL EMAIL:\n")
print(email_text)

# 🔹 STEP 2  Extract Data using LLM
extracted_json = extract_data(email_text)

# 🔹 STEP 3  Validate Extracted Data
verified_json = validate_extracted_data(
    email_text,
    extracted_json
)

# 🔹 STEP 4 → Final Output
print("\n✅ FINAL OUTPUT:\n")
print(verified_json)
