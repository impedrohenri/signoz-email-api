from fastapi import FastAPI, Request, HTTPException
import requests
import os

app = FastAPI(title="SigNoz → Brevo Alert API")

EMAIL_API_KEY = os.getenv("EMAIL_API_KEY")
EMAIL_FROM = os.getenv("EMAIL_FROM")
EMAIL_TO = os.getenv("EMAIL_TO")

# Importa url do .env
EMAIL_URL = os.getenv("EMAIL_URL")


@app.post("/alert")
async def receive_alert(request: Request):
    data = await request.json()

    try:
        status = data.get("status", "unknown")

        alerts = data.get("alerts", [])
        alert = alerts[0] if alerts else {}

        labels = alert.get("labels", {})
        annotations = alert.get("annotations", {})

        alert_name = labels.get("alertname", "Alerta sem nome")
        summary = annotations.get("summary", "Sem resumo")
        description = annotations.get("description", "")

        subject = f"[SigNoz] {alert_name} ({status.upper()})"

        body = f"""
            🚨 ALERTA DO SIGOZ

            Status: {status}
            Nome: {alert_name}

            Resumo:
            {summary}

            Descrição:
            {description}
            """

        send_email(subject, body)

        return {"ok": True, "message": "Email enviado"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def send_email(subject: str, content: str):
    if not EMAIL_API_KEY:
        raise Exception("EMAIL_API_KEY não configurada")

    headers = {
        "api-key": EMAIL_API_KEY,
        "Content-Type": "application/json",
        "accept": "application/json",
    }

    payload = {
        "sender": {"email": EMAIL_FROM, "name": "SigNoz Alerts"},
        "to": [{"email": EMAIL_TO}],
        "subject": subject,
        "textContent": content,
    }

    response = requests.post(EMAIL_URL, json=payload, headers=headers)

    if response.status_code >= 300:
        raise Exception(f"Erro Brevo: {response.text}")
