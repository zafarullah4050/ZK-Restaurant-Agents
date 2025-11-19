# streamlit_app.py
import os
from collections import deque

import streamlit as st
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_groq import ChatGroq

from agents_tools import tools
from order_state import order_state, reservation_state

# ==========================
# Environment & LLM setup
# ==========================
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = "llama-3.1-8b-instant"

if not GROQ_API_KEY:
    st.error("GROQ_API_KEY is missing. Please set it in your .env file.")
    st.stop()

llm = ChatGroq(api_key=GROQ_API_KEY, model=GROQ_MODEL, temperature=0.2)

system_prompt = """
You are ZK Restaurant AI Agent — a friendly, helpful, and professional virtual assistant
for ZK Restaurant. Your goal is to give clear, attractive, and engaging responses that make
customers feel welcomed.

You can use the following tools when needed:
menu, order, reserve, delivery, upsell, complaint.

Rules for replying:
- If the user speaks in Urdu, always reply in clean and polite Roman Urdu.
- Keep answers short, clear, and customer-friendly.
- Add a warm and welcoming tone (like a real restaurant host).
- NEVER use code, symbols, or technical formatting.
- When suggesting items, recommend best-sellers politely.
- Make replies sound natural, like a real human service agent.

Format for tool calls:
TOOL_CALL:<tool_name>

Your personality:
- Friendly, respectful, polite.
- Professional like a trained restaurant customer-service agent.
- Always helpful and positive.
- Use emojis lightly when appropriate (🍽️✨🔥).
"""

TOOLS_REQUIRING_USER = {"order", "reserve", "complaint"}
# Convert tools (ToolWrapper instances) into lookup mapping
TOOL_LOOKUP = {tool.name: tool for tool in tools}


def sync_session_state_from_globals():
    """
    Copy the latest shared tool state into the user's Streamlit session.
    Call this after any operation that may modify the global order/reservation dicts.
    """
    st.session_state.order_history = dict(order_state)
    st.session_state.reservation_history = dict(reservation_state)

def fallback_intent_handler(user_text: str, user_id: str):
    """Very lightweight keyword fallback when the LLM forgets to call a tool."""
    lowered = user_text.lower()

    if "order" in lowered:
        order_tool = TOOL_LOOKUP.get("order")
        if order_tool:
            return order_tool.func(user_text, user_id)

    if any(keyword in lowered for keyword in ["reserve", "reservation", "book table", "table"]):
        reservation_tool = TOOL_LOOKUP.get("reserve")
        if reservation_tool:
            return reservation_tool.func(user_text, user_id)

    if "complaint" in lowered or "issue" in lowered:
        complaint_tool = TOOL_LOOKUP.get("complaint")
        if complaint_tool:
            return complaint_tool.func(user_text, user_id)

    return None


# ==========================
# Helper functions
# ==========================
def run_agent(user_text: str, user_id: str):
    """Run the same logic as the FastAPI webhook for the Streamlit UI."""
    prompt = f"{system_prompt}\nUser: {user_text}\nAgent:"
    try:
        response = llm.generate([[HumanMessage(content=prompt)]])
        ai_text = ""
        if hasattr(response, "generations"):
            gens = response.generations
            if isinstance(gens, list) and len(gens) and isinstance(gens[0], list):
                ai_text = gens[0][0].text
            elif isinstance(gens, list) and len(gens) and hasattr(gens[0], "text"):
                ai_text = gens[0].text
        if not ai_text:
            ai_text = "Sorry, I cannot respond right now."
    except Exception as e:
        ai_text = f"Sorry, I cannot respond right now. ({e})"

    handled_by_tool = False
    reply = ai_text
    if "TOOL_CALL:" in ai_text:
        tool_name = ai_text.split("TOOL_CALL:")[1].splitlines()[0].strip()
        tool = TOOL_LOOKUP.get(tool_name)

        if tool:
            if tool_name in TOOLS_REQUIRING_USER:
                reply = tool.func(user_text, user_id)
            else:
                try:
                    reply = tool.func(user_text)
                except TypeError:
                    reply = tool.func()
            handled_by_tool = True
        else:
            reply = "❌ Invalid tool found."

    if not handled_by_tool:
        fallback_reply = fallback_intent_handler(user_text, user_id)
        if fallback_reply:
            reply = fallback_reply

    # Sync the in-memory globals back into session state so UI shows updated info
    sync_session_state_from_globals()
    return reply, ai_text


def render_state(title: str, state_dict: dict):
    st.subheader(title)
    if not state_dict:
        st.caption("No records yet.")
        return

    max_history = 5
    items = list(state_dict.items())[::-1]
    for idx, (user_id, details) in enumerate(items):
        if idx >= max_history:
            break
        st.markdown(f"**User:** `{user_id}`")
        st.write(details)
        st.divider()

# ==========================
# Streamlit page layout
# ==========================
st.set_page_config(page_title="ZK Restaurant Agents", page_icon="🍽️", layout="wide")
st.title("🍽️ ZK Restaurant Agents")
st.caption("Interact with the AI agent, preview menu info, and inspect recent orders/reservations.")

# initialize session state keys
if "chat_history" not in st.session_state:
    st.session_state.chat_history = deque(maxlen=50)
    st.session_state.chat_history.append(("assistant", "Assalam o Alaikum! How can I help you today?"))

if "last_ai_raw" not in st.session_state:
    st.session_state.last_ai_raw = ""

if "user_id" not in st.session_state:
    st.session_state.user_id = "demo-user"

if "order_history" not in st.session_state:
    st.session_state.order_history = {}

if "reservation_history" not in st.session_state:
    st.session_state.reservation_history = {}

# make sure session sees latest global state on load
sync_session_state_from_globals()

# Sidebar quick actions
with st.sidebar:
    st.header("Quick Actions")
    st.text_input("Session User ID", value=st.session_state.user_id, key="sidebar_user_id")
    # update user id immediately so actions use it
    st.session_state.user_id = st.session_state.sidebar_user_id or "demo-user"

    if st.button("Show Menu"):
        menu_tool = TOOL_LOOKUP.get("menu")
        if menu_tool:
            st.session_state.menu_preview = menu_tool.func("")
            # sync in case menu tool touches state (it doesn't)
            sync_session_state_from_globals()
        else:
            st.session_state.menu_preview = "Menu tool not available."

    custom_delivery_area = st.text_input("Check delivery area", placeholder="e.g. City Center")
    if st.button("Check Delivery") and custom_delivery_area:
        delivery_tool = TOOL_LOOKUP.get("delivery")
        if delivery_tool:
            st.session_state.delivery_status = delivery_tool.func(custom_delivery_area)
            sync_session_state_from_globals()
        else:
            st.session_state.delivery_status = "Delivery tool not available."

    if st.button("Upsell Suggestion"):
        upsell_tool = TOOL_LOOKUP.get("upsell")
        if upsell_tool:
            st.session_state.upsell_text = upsell_tool.func("")
            sync_session_state_from_globals()
        else:
            st.session_state.upsell_text = "Upsell tool not available."

    st.markdown("---")
    st.caption("Run `streamlit run streamlit_app.py` to launch this UI.")

    if "menu_preview" in st.session_state:
        st.markdown("**Menu Preview**")
        st.text(st.session_state.menu_preview)

    if "delivery_status" in st.session_state:
        st.markdown("**Delivery Status**")
        st.info(st.session_state.delivery_status)

    if "upsell_text" in st.session_state:
        st.markdown("**Upsell Suggestion**")
        st.success(st.session_state.upsell_text)


# Chat interface
with st.form("chat_form", clear_on_submit=True):
    user_message = st.text_area("Your message", placeholder="Type a question or order request...", height=80)
    submitted = st.form_submit_button("Send")

    if submitted and user_message.strip():
        st.session_state.chat_history.append(("user", user_message))
        reply, raw_ai = run_agent(user_message.strip(), st.session_state.user_id)
        st.session_state.chat_history.append(("assistant", reply))
        st.session_state.last_ai_raw = raw_ai

# Render chat
chat_container = st.container()
with chat_container:
    for role, content in st.session_state.chat_history:
        if role == "user":
            st.chat_message("user").write(content)
        else:
            st.chat_message("assistant").write(content)

if st.session_state.last_ai_raw:
    with st.expander("Debug: Raw LLM output", expanded=False):
        st.write(st.session_state.last_ai_raw)

# Display order/reservation state (from session_state)
col1, col2 = st.columns(2)
with col1:
    render_state("Latest Orders", st.session_state.order_history)
with col2:
    render_state("Latest Reservations", st.session_state.reservation_history)
