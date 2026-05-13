import imaplib
import email
import os
from dotenv import load_dotenv
from pathlib import Path
import PyPDF2
import pandas as pd

env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

# Credentials
EMAIL_USER = "testpurpose917@gmail.com"
EMAIL_PASS = "yurwgblgotrhrbjf"

print("EMAIL_USER:", EMAIL_USER)
print("EMAIL_PASS:", EMAIL_PASS)

ATTACHMENT_FOLDER = "attachments"
os.makedirs(ATTACHMENT_FOLDER, exist_ok=True)


# 🔹 Connect to Email
def connect_email():
    print("🔌 Connecting to Gmail...")
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(EMAIL_USER, EMAIL_PASS)
    print(" Connected successfully!")
    return mail


# 🔹 Fetch Latest Email
def fetch_latest_email(mail):
    mail.select("inbox")

    status, messages = mail.search(None, "ALL")
    print(" Email search status:", status)

    email_ids = messages[0].split()
    print(" Total emails found:", len(email_ids))

    if not email_ids:
        print("❌ No emails found!")
        return ""

    latest_email_id = email_ids[-1]
    print("📩 Latest email ID:", latest_email_id)

    res, msg_data = mail.fetch(latest_email_id, "(RFC822)")

    for response in msg_data:
        if isinstance(response, tuple):
            msg = email.message_from_bytes(response[1])
            return process_email(msg)

    return ""


# 🔹 Process Email (Body + Attachments)
def process_email(msg):
    full_text = ""

    for part in msg.walk():
        content_type = part.get_content_type()
        filename = part.get_filename()

        print(" Found part:", content_type, "| File:", filename)

        # 📄 Email Body (handles plain + html)
        if "text" in content_type and filename is None:
            try:
                body = part.get_payload(decode=True)
                if body:
                    body = body.decode(errors="ignore")
                    full_text += "\n" + clean_text(body)
            except Exception as e:
                print("⚠️ Error reading body:", e)

        # 📎 Attachments
        elif filename:
            filepath = os.path.join(ATTACHMENT_FOLDER, filename)

            try:
                with open(filepath, "wb") as f:
                    f.write(part.get_payload(decode=True))

                extracted_text = extract_attachment_text(filepath)
                full_text += "\n" + extracted_text
            except Exception as e:
                print("⚠️ Error processing attachment:", e)

    return full_text.strip()


# 🔹 Extract Text from Attachments
def extract_attachment_text(filepath):
    if filepath.lower().endswith(".pdf"):
        return extract_pdf(filepath)

    elif filepath.lower().endswith((".xlsx", ".xls")):
        return extract_excel(filepath)

    else:
        return ""


# 🔹 PDF Reader
def extract_pdf(filepath):
    text = ""
    try:
        with open(filepath, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text += page.extract_text() or ""
    except Exception as e:
        print("⚠️ PDF read error:", e)

    return clean_text(text)


# 🔹 Excel Reader
def extract_excel(filepath):
    try:
        df = pd.read_excel(filepath)
        return clean_text(df.to_string())
    except Exception as e:
        print("⚠️ Excel read error:", e)
        return ""


# 🔹 Clean Text
def clean_text(text):
    text = text.strip()
    text = " ".join(text.split())
    return text


# 🔹 Final Function (IMPORTANT)
def get_email_text():
    print(" Starting email extraction pipeline...")

    mail = connect_email()
    data = fetch_latest_email(mail)

    print("\n📄 FINAL EXTRACTED DATA:\n", data[:500])  # show preview

    return data