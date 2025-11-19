# app.py
import os
import json
import requests
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse, JSONResponse
from langchain_core.messages import HumanMessage
from langchain_groq import ChatGroq
from dotenv import load_dotenv

from agents_tools import tools
from order_state import order_state, reservation_state


# ==========================
# In-Memory Order Database
# ==========================
orders_db = []   # <<=== NEW
reservations_db = []


# ==========================
# FastAPI app
# ==========================
app = FastAPI(title="ZK Restaurant Chatbot")


# ==========================
# Load environment variables
# ==========================
load_dotenv()
WA_TOKEN = os.getenv("WA_TOKEN")
WA_PHONE_ID = os.getenv("WA_PHONE_ID")
WABA_ID = os.getenv("WABA_ID")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")

GROQ_MODEL = "llama-3.1-8b-instant"

if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY is not set. Please configure it in .env")

if not WA_TOKEN or not WA_PHONE_ID:
    print("⚠️ WhatsApp credentials missing, sending disabled.")


# ==========================
# LLM Client
# ==========================
llm = ChatGroq(
    api_key=GROQ_API_KEY,
    model=GROQ_MODEL,
    temperature=0.2
)


# ==========================
# Main System Prompt
# ==========================
system_prompt = """
You are ZK Restaurant AI Agent...
(unchanged)
"""


# ==========================
# Root
# ==========================
@app.get("/")
async def root():
    return {"message": "ZK Restaurant chatbot is running."}


# ==========================
# WhatsApp Verification
# ==========================
@app.get("/webhook")
async def verify_webhook(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return PlainTextResponse(str(challenge))
    return JSONResponse(status_code=403, content={"error": "Verification failed"})


# ==========================
# WhatsApp Send Message Helper
# ==========================
def send_whatsapp(to: str, text: str) -> bool:
    if not WA_TOKEN or not WA_PHONE_ID:
        print("Skipping WhatsApp send; no credentials.")
        return False

    url = f"https://graph.facebook.com/v18.0/{WA_PHONE_ID}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "text": {"body": text}
    }
    headers = {
        "Authorization": f"Bearer {WA_TOKEN}",
        "Content-Type": "application/json"
    }

    try:
        r = requests.post(url, json=payload, headers=headers, timeout=10)
        r.raise_for_status()
        print("WhatsApp sent:", text[:60], "...")
        return True
    except Exception as e:
        print("WhatsApp send error:", e)
        return False


# ==========================
# Payload Extractor
# ==========================
def extract_message_payload(payload: dict):
    try:
        entry_list = payload.get("entry") or []
        for entry in entry_list:
            for change in entry.get("changes", []):
                value = change.get("value", {})
                msgs = value.get("messages", [])
                if not msgs:
                    continue
                msg = msgs[0]

                user = msg.get("from")
                text = msg.get("text", {}).get("body", "")
                return user, text.strip(), None
        return None, None, "no_message"
    except Exception:
        return None, None, "parse_error"


# ==========================
# NEW: Save Order Function
# ==========================
def save_order(user_id: str, item: str, status="confirmed"):
    order = {
        "user": user_id,
        "item": item,
        "status": status
    }
    orders_db.append(order)
    print("💾 Order Saved:", order)
    return order


# ==========================
# NEW: Latest Orders API
# ==========================
@app.get("/orders/latest")
def latest_orders():
    return {"orders": orders_db}


# ==========================
# Main Webhook Handler
# ==========================
@app.post("/webhook")
async def webhook(request: Request):
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    user, text, status = extract_message_payload(data)
    if status or not text:
        return {"status": status or "empty"}

    # Build LLM Query
    prompt = f"{system_prompt}\nUser: {text}\nAgent:"
    try:
        result = llm.generate([[HumanMessage(content=prompt)]])
        ai_text = result.generations[0][0].text
    except:
        ai_text = "Sorry, mein abhi jawab generate nahi kar paa raha."

    print(f"User({user}):", text)
    print("AI:", ai_text)

    # ==========================
    # ORDER DETECTION LOGIC
    # ==========================
    text_lower = text.lower()

    if "order" in text_lower and "confirm" in text_lower:
        if "burger" in text_lower:
            save_order(user, "ZK Burger")
        elif "pizza" in text_lower:
            save_order(user, "ZK Pizza")
        elif "biryani" in text_lower:
            save_order(user, "Biryani")
        # add more items as needed

    # ==========================
    # Tool Calls
    # ==========================
    if "TOOL_CALL:" in ai_text:
        tool_name = ai_text.split("TOOL_CALL:")[1].splitlines()[0].strip()
        matched = [t for t in tools if getattr(t, "name", None) == tool_name]

        if matched:
            tool = matched[0].func

            if tool_name in ["order", "reserve", "complaint"]:
                reply = tool(text, user)
            else:
                try:
                    reply = tool(text)
                except:
                    reply = tool()
        else:
            reply = "❌ Invalid tool."
    else:
        reply = ai_text

    send_whatsapp(user, reply)

    return {"status": "ok"}
