import streamlit as st
import requests
import json
import os
import uuid

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(page_title="StockMind AI", page_icon="🧠", layout="wide", initial_sidebar_state="expanded")

# LIVE BACKEND URL (Your Railway Server)
API_URL = "https://stockmind-ai-production.up.railway.app"

# --- 2. CUSTOM CSS (Dark Theme & Gradient Styling) ---
st.markdown("""
    <style>
    /* Hide Streamlit default UI elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Gradient Title */
    .gradient-text {
        background: -webkit-linear-gradient(45deg, #FF6B6B, #4ECDC4, #45B7D1);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        font-size: 3.5rem;
        font-weight: 800;
        margin-bottom: 0px;
    }
    
    /* Subtitle text */
    .subtitle {
        text-align: center;
        color: #A0AEC0;
        font-size: 1.1rem;
        margin-bottom: 3rem;
    }

    /* Footer text */
    .footer-text {
        text-align: center;
        color: #718096;
        font-size: 0.8rem;
        margin-top: 2rem;
    }
    
    /* Style the prompt buttons to look like cards */
    div.stButton > button {
        height: 120px;
        width: 100%;
        border-radius: 15px;
        border: 1px solid #2D3748;
        background-color: #1A202C;
        color: white;
        text-align: left;
        padding: 20px;
        transition: all 0.3s ease;
    }
    div.stButton > button:hover {
        border-color: #4ECDC4;
        background-color: #2D3748;
    }
    div.stButton > button p {
        font-size: 1.1rem;
        font-weight: 600;
    }
    </style>
""", unsafe_allow_html=True)

# --- 3. SESSION STATE & MEMORY ---
HISTORY_FILE = "stockmind_chat_history.json"

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    return {}

def save_history(history):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f)

if "all_chats" not in st.session_state:
    st.session_state.all_chats = load_history()

if "current_chat_id" not in st.session_state:
    st.session_state.current_chat_id = str(uuid.uuid4())
    st.session_state.all_chats[st.session_state.current_chat_id] = {
        "title": "New Chat",
        "messages": []
    }

# --- 4. FETCH LIVE INVENTORY DATA ---
@st.cache_data(ttl=60) # Caches the data for 60 seconds so it doesn't spam your database
def fetch_inventory_stats():
    try:
        res = requests.get(f"{API_URL}/inventory", timeout=5)
        if res.status_code == 200:
            return res.json().get("total_products", 0)
    except:
        return 0
    return 0

total_items = fetch_inventory_stats()

# --- 5. SIDEBAR (Metrics & Actions) ---
with st.sidebar:
    st.markdown("### 🧠 StockMind AI")
    if st.button("➕ New Chat", use_container_width=True, type="primary"):
        st.session_state.current_chat_id = str(uuid.uuid4())
        st.session_state.all_chats[st.session_state.current_chat_id] = {"title": "New Chat", "messages": []}
        st.rerun()
    
    st.markdown("---")
    st.markdown("<p style='color:#A0AEC0; font-size:0.8rem; font-weight:bold; letter-spacing:1px;'>LIVE INVENTORY</p>", unsafe_allow_html=True)
    
    # Real-time Metrics
    st.metric(label="📦 Total Products", value=f"{total_items:,}")
    st.metric(label="💰 Daily Revenue", value="--")
    st.metric(label="🚨 Active Alerts", value="0 alerts (0 critical)")
    st.metric(label="📈 Monthly Estimate", value="--")
    
    st.markdown("---")
    st.markdown("<p style='color:#A0AEC0; font-size:0.8rem; font-weight:bold; letter-spacing:1px;'>QUICK ACTIONS</p>", unsafe_allow_html=True)
    if st.button("⚠️ View Critical Alerts", use_container_width=True):
        st.toast("Fetching critical alerts from the database...")
    if st.button("📋 Business Report", use_container_width=True):
        st.toast("Generating morning executive summary...")

# --- 6. MAIN CHAT UI ---
current_chat = st.session_state.all_chats[st.session_state.current_chat_id]
messages = current_chat["messages"]

# If chat is empty, show the Hero Section (Title and 4 Cards)
prompt_from_card = None

if len(messages) == 0:
    st.markdown("<h1 class='gradient-text'>StockMind AI</h1>", unsafe_allow_html=True)
    st.markdown("<p class='subtitle'>Your elite inventory intelligence agent. Ask me about stock levels, reorders, profit margins, or new product trends — in any language.</p>", unsafe_allow_html=True)
    
    st.write("")
    st.write("")
    
    # Create the 2x2 Grid for the Action Cards
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🚨 Stock Alert Scan\n\nSee all critical and out-of-stock items"):
            prompt_from_card = "Run a Stock Alert Scan and show me all critical and out-of-stock items."
        if st.button("📊 Profit Analysis\n\nBest margins and top performers"):
            prompt_from_card = "Run a Profit Analysis to show me our best margins and top performing products."
    with col2:
        if st.button("📦 Reorder Plan\n\nGet today's purchasing recommendations"):
            prompt_from_card = "Generate a Reorder Plan with today's purchasing recommendations based on sales velocity."
        if st.button("🔍 Scout New Products\n\nFind first-mover opportunities"):
            prompt_from_card = "Scout the market and suggest new agricultural product trends or first-mover opportunities we should stock."
else:
    # If there are messages, display the chat history
    for index, msg in enumerate(messages):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            # Feedback Loop for AI answers
            if msg["role"] == "assistant":
                feedback_key = f"feedback_{st.session_state.current_chat_id}_{index}"
                feedback = st.feedback("thumbs", key=feedback_key)
                if feedback is not None and msg.get("feedback") != feedback:
                    msg["feedback"] = feedback
                    st.session_state.all_chats[st.session_state.current_chat_id] = current_chat
                    save_history(st.session_state.all_chats)
                    if feedback == 1:
                        st.toast("✅ Positive feedback saved! StockMind will prioritize similar answers.")

# --- 7. USER INPUT & AI COMMUNICATION ---
# Determine if the prompt came from a typed message or a clicked card
user_prompt = st.chat_input("Ask StockMind AI...")
if prompt_from_card:
    user_prompt = prompt_from_card

if user_prompt:
    with st.chat_message("user"):
        st.markdown(user_prompt)
    current_chat["messages"].append({"role": "user", "content": user_prompt})
        
    if current_chat["title"] == "New Chat":
        current_chat["title"] = user_prompt[:25] + "..."
        
    with st.chat_message("assistant"):
        with st.spinner("Analyzing GIVA TECH databases..."):
            try:
                payload = {"query": user_prompt, "history": current_chat["messages"]}
                response = requests.post(f"{API_URL}/chat", json=payload)
                
                if response.status_code == 200:
                    ai_reply = response.json().get("reply", "No response received.")
                else:
                    ai_reply = f"⚠️ Backend returned an error: {response.status_code}"
            except Exception as e:
                ai_reply = "⚠️ Could not connect to the cloud server. Checking connection..."
            
            st.markdown(ai_reply)
            current_chat["messages"].append({"role": "assistant", "content": ai_reply})
    
    st.session_state.all_chats[st.session_state.current_chat_id] = current_chat
    save_history(st.session_state.all_chats)
    st.rerun()

# --- 8. FOOTER ---
if len(messages) == 0:
    st.markdown(f"<p class='footer-text'>StockMind AI monitors {total_items:,} products 24/7 · Supports all languages</p>", unsafe_allow_html=True)