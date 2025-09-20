import os
from fastapi import FastAPI, Request
import httpx

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

app = FastAPI()

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

def map_to_notion(trade: dict):
    # Map incoming JSON to Notion properties. Names must match your database.
    props = {
        "Title": {"title": [{"text": {"content": f"{trade.get('symbol','')} {trade.get('side','')} {trade.get('lots','')}"}}]},
        "Date": {"date": {"start": trade.get("closeTime") or trade.get("openTime")}},
        "Symbol": {"rich_text": [{"text": {"content": trade.get("symbol","")}}]},
        "Side": {"select": {"name": trade.get("side")}},  # Buy or Sell
        "Lots": {"number": float(trade.get("lots") or 0)},
        "Entry price": {"number": float(trade.get("entry")) if trade.get("entry") is not None else None},
        "Exit price": {"number": float(trade.get("exit")) if trade.get("exit") is not None else None},
        "SL": {"number": float(trade.get("sl")) if trade.get("sl") is not None else None},
        "TP": {"number": float(trade.get("tp")) if trade.get("tp") is not None else None},
        "Net PnL": {"number": float(trade.get("pnl") or 0)},
        "Fees": {"number": float(trade.get("fees") or 0)},
    }
    if trade.get("strategy"):
        props["Strategy"] = {"select": {"name": str(trade["strategy"])}}
    if trade.get("tags"):
        props["Setup tags"] = {"multi_select": [{"name": str(t)} for t in trade["tags"]]}
    if trade.get("screenshot"):
        props["Screenshot"] = {"url": str(trade["screenshot"])}
    if trade.get("notes"):
        props["Notes"] = {"rich_text": [{"text": {"content": str(trade["notes"])}}]}
    return props

@app.get("/")
def health():
    return {"ok": True}

@app.post("/mt5-webhook")
async def mt5_webhook(request: Request):
    if not NOTION_TOKEN or not NOTION_DATABASE_ID:
        return {"ok": False, "error": "Server missing NOTION_TOKEN or NOTION_DATABASE_ID"}
    trade = await request.json()
    payload = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": map_to_notion(trade)
    }
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post("https://api.notion.com/v1/pages", headers=HEADERS, json=payload)
        if r.status_code >= 400:
            return {"ok": False, "error": r.text}
        return {"ok": True, "pageId": r.json().get("id")}
