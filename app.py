from fastapi import FastAPI, Request, HTTPException, Depends, status
from datetime import datetime
import re
from services.AuthService import authenticate
from services.EmailService import send_email
from utils.email import build_html, format_key
from utils.utils import format_timestamp

app = FastAPI(title="E-mail Middleware")

# Labels que não trazem valor ao e-mail
BLACK_LIST_LABELS = {
    "alertname", "ruleId", "uid", 
    "monitor", "groupKey", "fingerprint", "threshold.name"
}

@app.post("/alert", dependencies=[Depends(authenticate)])
async def receive_alert(request: Request):
    data = await request.json()
    try:
        status = data.get("status", "firing").upper()
        alerts = data.get("alerts", [])
        if not alerts:
            return {"status": "ignored", "reason": "empty_payload"}

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

        # Construção do Assunto do e-mail
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
