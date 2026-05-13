import os
from groq import Groq

# 🔹 Create Groq client
client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)

# 🔹 Main Function
def extract_data(email_text):

    print("\n🧠 Sending data to Groq...\n")

    prompt = f"""
Convert this financial email into structured JSON.

Email:
{email_text}

Return ONLY JSON with fields:
customer_name,
transaction_id,
amount,
payment_method
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

        output = response.choices[0].message.content

        print("🤖 GROQ RESPONSE:\n")
        print(output)

        return output

    except Exception as e:
        print("❌ GROQ ERROR:", e)
        return "LLM FAILED"