import requests
import os

EMAIL_FROM = os.getenv("EMAIL_FROM")
EMAIL_TO_RAW = os.getenv("EMAIL_TO")
EMAIL_URL = os.getenv("EMAIL_URL")
EMAIL_API_KEY = os.getenv("EMAIL_API_KEY")

def send_email(subject: str, html_content: str):
    headers = {"api-key": EMAIL_API_KEY, "Content-Type": "application/json"}
    recipients = [{"email": e.strip()} for e in EMAIL_TO_RAW.split(",") if e.strip()]
    
    payload = {
        "sender": {"email": EMAIL_FROM, "name": "Alertas SigNoz"},
        "to": recipients,
        "subject": subject,
        "htmlContent": html_content,
    }
    
    response = requests.post(EMAIL_URL, json=payload, headers=headers)
    if response.status_code >= 300:
        raise Exception(f"Provider error: {response.text}")