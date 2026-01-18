def format_timestamp(ts: str) -> str:
    if not ts: return "N/A"
    try:
        ts = re.sub(r'(\.\d{6})\d+', r'\1', ts.replace("Z", "+00:00"))
        dt = datetime.fromisoformat(ts)
        return dt.strftime("%d/%m %H:%M:%S")
    except:
        return ts