from fastapi import FastAPI, Request, HTTPException
import requests
import os
from datetime import datetime
import re

app = FastAPI(title="SigNoz Dispatcher Pro")

# Configurações de ambiente
EMAIL_API_KEY = os.getenv("EMAIL_API_KEY")
EMAIL_FROM = os.getenv("EMAIL_FROM", "alertas@monitoramento.com")
EMAIL_TO_RAW = os.getenv("EMAIL_TO")
EMAIL_URL = os.getenv("EMAIL_URL")

# Labels que não trazem valor ao operador no corpo do email
BLACK_LIST_LABELS = {
    "alertname", "ruleId", "uid", 
    "monitor", "groupKey", "fingerprint", "threshold.name"
}

@app.post("/alert")
async def receive_alert(request: Request):
    data = await request.json()
    try:
        status = data.get("status", "firing").upper()
        alerts = data.get("alerts", [])
        if not alerts:
            return {"status": "ignored", "reason": "empty_payload"}

        # Extração inteligente do primeiro alerta (padrão de grupo)
        main_alert = alerts[0]
        common_labels = data.get("commonLabels", {})
        common_annotations = data.get("commonAnnotations", {})
        
        # Dados do alerta
        incident_name = common_labels.get("alertname", "Alerta do Sistema")
        severity = common_labels.get("severity", "info").lower()
        if status == "RESOLVED": severity = "resolved"

        # Detalhes
        description = common_annotations.get("description") or common_annotations.get("summary") or "Sem descrição disponível."
        
        # Processamento de Itens Afetados
        processed_alerts = []
        for a in alerts:
            # Filtra labels dinâmicas: remove o que é sistema e o que é redundante
            labels = a.get("labels", {})
            dynamic_metadata = {
                format_key(k): v for k, v in labels.items() 
                if k not in BLACK_LIST_LABELS and v
            }
            
            processed_alerts.append({
                "time": format_timestamp(a.get("startsAt")),
                "metadata": dynamic_metadata,
                "link": a.get("generatorURL", data.get("externalURL", "#"))
            })

        # Construção do Assunto

        # Pega o nome do host a partir da chave host
        host = data.get("commonLabels", {}).get("Host") or data.get("commonLabels", {}).get("host") or data.get("commonLabels", {}).get("host.name") or None


        subject = f"[SigNoz] - {host or severity}: {incident_name}"

        html_body = build_html(
            status=status,
            severity=severity,
            alert_name=incident_name,
            description=description,
            alerts=processed_alerts,
            host=host
        )

        send_email(subject, html_body)
        return {"ok": True, "items_processed": len(alerts)}

    except Exception as e:
        print(f"[ERROR] {str(e)}")
        raise HTTPException(status_code=500, detail="Internal processing error")

def format_key(key: str) -> str:
    clean = key.split("/")[-1]
    return clean.replace("_", " ").replace(".", " ").strip().title()

def format_timestamp(ts: str) -> str:
    if not ts: return "N/A"
    try:
        ts = re.sub(r'(\.\d{6})\d+', r'\1', ts.replace("Z", "+00:00"))
        dt = datetime.fromisoformat(ts)
        return dt.strftime("%d/%m %H:%M:%S")
    except:
        return ts

def build_html(status, severity, alert_name, description, alerts, host):
    # Paleta de Identidade
    themes = {
        "critical": {"color": "#E53935"},
        "error":    {"color": "#E53935"},
        "warning":  {"color": "#FB8C00"},
        "info":     {"color": "#1E88E5"},
        "resolved": {"color": "#43A047"},
    }
    theme = themes.get(severity, themes["info"])

    # Bloco de Alertas (Loop)
    alerts_html = ""
    for a in alerts:
        # Gera as linhas de metadata dinâmicas
        meta_rows = "".join([
            f'<tr><td class="meta-k">{k}</td><td class="meta-v">{v}</td></tr>' 
            for k, v in a['metadata'].items()
        ])


        alerts_html += f"""
        <div class="alert-card">
            <div class="card-header">
                <span>🕒 {a['time']}</span>
                <div class="mx-auto"></div>
                <a href="{a['link']}" class="source-link">Abrir no SigNoz ↗</a>
            </div>
            <table class="meta-table">{meta_rows}</table>
        </div>
        """

    return f"""
    <!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #F0F2F5; color: #1C1E21; margin: 0; padding: 20px; }}
            .container {{ margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 8px 24px rgba(0,0,0,0.08); }}
            
            /* Status Banner */
            .banner {{ background-color: {theme['color']}; padding: 12px 24px; color: white; display: flex; align-items: center; font-size: 14px; font-weight: bold; text-transform: uppercase; letter-spacing: 1px; border-radius: 12px; }}
            
            /* Main Content */
            .content {{ padding: 32px 24px; }}
            .incident-title {{ font-size: 20px; font-weight: 700; color: #050505; margin: 0 0 16px 0; line-height: 1.2; }}
            
            /* Impact Box */
            .description-box {{ background: #F8F9FA; border-radius: 8px; padding: 20px; border-left: 4px solid {theme['color']}; margin-bottom: 32px; }}
            .description-text {{ font-size: 16px; color: #4B4B4B; line-height: 1.6; margin: 0; }}
            
            /* Section Label */
            .section-label {{ font-size: 12px; font-weight: bold; color: #8D949E; text-transform: uppercase; margin-bottom: 12px; display: block; }}
            
            /* Alert Cards */
            .alert-card {{ border: 1px solid #E4E6EB; border-radius: 8px; margin-bottom: 16px; transition: all 0.2s; }}
            .card-header {{ background: #F7F8FA; padding: 10px 16px; border-bottom: 1px solid #E4E6EB; display: flex; justify-content: space-between; font-size: 12px; color: #65676B; font-weight: 600; }}
            .source-link {{ color: {theme['color']}; text-decoration: none; }}
            
            .meta-table {{ width: 100%; border-collapse: collapse; padding: 8px; }}
            .meta-k {{ padding: 10px 16px; font-size: 13px; color: #65676B; width: 40%; border-bottom: 1px solid #F0F2F5; }}
            .meta-v {{ padding: 10px 16px; font-size: 13px; color: #1C1E21; font-weight: 500; border-bottom: 1px solid #F0F2F5; }}
            
            .footer {{ text-align: center; padding: 24px; font-size: 12px; color: #8D949E; background: #F0F2F5; }}
            .mx-auto {{ margin-left: auto; margin-right: auto; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="banner">
                {host} <div class="mx-auto"></div> {status} • {severity}
            </div>
            
            <div class="content">
                <h1 class="incident-title">{alert_name}</h1>
                
                <span class="section-label">Descrição do alerta</span>
                <div class="description-box">
                    <p class="description-text"><strong>{description}</strong></p>
                </div>

                <span class="section-label">Recursos Afetados e Metadados</span>
                {alerts_html}
            </div>

            <div class="footer">
                Painel de Monitoramento • SigNoz<br>
                Este é um e-mail automático, por favor não responda.
            </div>
        </div>
    </body>
    </html>
    """

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
