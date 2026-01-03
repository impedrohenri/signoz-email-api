from fastapi import FastAPI, Request, HTTPException
import requests
import os
from datetime import datetime

app = FastAPI(title="SigNoz → Email Alert API")

EMAIL_API_KEY = os.getenv("EMAIL_API_KEY")
EMAIL_FROM = os.getenv("EMAIL_FROM")
EMAIL_TO_RAW = os.getenv("EMAIL_TO")

EMAIL_URL = os.getenv("EMAIL_URL")


@app.post("/alert")
async def receive_alert(request: Request):
    data = await request.json()

    try:
        status = data.get("status", "unknown").upper()
        alerts = data.get("alerts", [])

        if not alerts:
            raise Exception("Payload sem alerts")

        alert = alerts[0]

        labels = alert.get("labels", {})
        annotations = alert.get("annotations", {})
        common_labels = data.get("commonLabels", {})

        alert_name = labels.get("alertname", "Alerta desconhecido")
        severity = labels.get("severity", "N/A").upper()
        instance = labels.get("instance", "N/A")
        device = labels.get("dev", "N/A")

        summary = annotations.get("summary", "")
        info = annotations.get("info", "")
        starts_at = format_datetime(alert.get("startsAt"))

        subject = f"[SigNoz][{severity}] {alert_name} - {status}"

        html_body = build_html_email(
            status=status,
            alert_name=alert_name,
            severity=severity,
            instance=instance,
            device=device,
            summary=summary,
            info=info,
            starts_at=starts_at,
            labels=common_labels,
        )

        send_email(subject, html_body)

        return {"ok": True, "message": "Email HTML enviado"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def build_html_email(
    *,
    status: str,
    alert_name: str,
    severity: str,
    instance: str,
    device: str,
    summary: str,
    info: str,
    starts_at: str,
    labels: dict,
) -> str:
    status_color = "#d93025" if status == "FIRING" else "#188038"
    severity_color = {
        "CRITICAL": "#b71c1c",
        "WARNING": "#f57c00",
        "INFO": "#1976d2",
    }.get(severity, "#333")

    labels_html = "".join(
        f"<tr><td><b>{k}</b></td><td>{v}</td></tr>"
        for k, v in labels.items()
    )

    return f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8" />
  <style>
    body {{
      font-family: Arial, Helvetica, sans-serif;
      background-color: #f4f6f8;
      padding: 20px;
    }}
    .container {{
      max-width: 700px;
      margin: auto;
      background: #ffffff;
      border-radius: 8px;
      padding: 24px;
      box-shadow: 0 2px 6px rgba(0,0,0,0.08);
    }}
    h1 {{
      font-size: 22px;
      margin-bottom: 10px;
    }}
    .status {{
      color: white;
      background: {status_color};
      display: inline-block;
      padding: 6px 12px;
      border-radius: 4px;
      font-weight: bold;
      margin-bottom: 16px;
    }}
    .severity {{
      color: {severity_color};
      font-weight: bold;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin-top: 16px;
    }}
    td {{
      padding: 8px;
      border-bottom: 1px solid #e0e0e0;
    }}
    .footer {{
      margin-top: 24px;
      font-size: 12px;
      color: #666;
      text-align: center;
    }}
  </style>
</head>

<body>
  <div class="container">
    <div class="status">{status}</div>

    <h1>{alert_name}</h1>

    <p>
      <b>Severidade:</b>
      <span class="severity">{severity}</span>
    </p>

    <table>
      <tr>
        <td><b>Instância</b></td>
        <td>{instance}</td>
      </tr>
      <tr>
        <td><b>Dispositivo</b></td>
        <td>{device}</td>
      </tr>
      <tr>
        <td><b>Início</b></td>
        <td>{starts_at}</td>
      </tr>
      <tr>
        <td><b>Resumo</b></td>
        <td>{summary}</td>
      </tr>
      <tr>
        <td><b>Detalhes</b></td>
        <td>{info}</td>
      </tr>
    </table>

    <h3>Labels</h3>
    <table>
      {labels_html}
    </table>

    <div class="footer">
      Alerta gerado automaticamente pelo SigNoz
    </div>
  </div>
</body>
</html>
"""


def parse_recipients(raw: str | None) -> list[dict]:
    if not raw:
        raise Exception("EMAIL_TO não configurado")

    emails = [e.strip() for e in raw.split(",") if e.strip()]

    if not emails:
        raise Exception("Nenhum email válido em EMAIL_TO")

    return [{"email": email} for email in emails]


def send_email(subject: str, html_content: str):
    if not EMAIL_API_KEY:
        raise Exception("EMAIL_API_KEY não configurada")

    recipients = parse_recipients(EMAIL_TO_RAW)

    headers = {
        "api-key": EMAIL_API_KEY,
        "Content-Type": "application/json",
        "accept": "application/json",
    }

    payload = {
        "sender": {"email": EMAIL_FROM, "name": "SigNoz Alerts"},
        "to": recipients,
        "subject": subject,
        "htmlContent": html_content,
    }

    response = requests.post(EMAIL_URL, json=payload, headers=headers)

    if response.status_code >= 300:
        raise Exception(f"Erro Email: {response.text}")


def format_datetime(value: str | None) -> str:
    if not value:
        return "N/A"
    try:
        return datetime.fromisoformat(value.replace("Z", "")).strftime(
            "%d/%m/%Y %H:%M:%S"
        )
    except Exception:
        return value
