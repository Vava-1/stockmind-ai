import streamlit as st
import requests
import json
import os
import uuid

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="StockMind AI", page_icon="✨", layout="wide", initial_sidebar_state="expanded")

# --- CUSTOM CSS (Gemini Style) ---
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .block-container { padding-top: 2rem; padding-bottom: 5rem; }
    </style>
""", unsafe_allow_html=True)

# --- CHAT HISTORY SYSTEM ---
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
        "messages": [{"role": "assistant", "content": "Hi! I am StockMind AI. How can I help you manage the inventory today?"}]
    }

# --- SIDEBAR ---
with st.sidebar:
    st.title("✨ StockMind AI")
    if st.button("➕ New Chat", use_container_width=True):
        new_id = str(uuid.uuid4())
        st.session_state.current_chat_id = new_id
        st.session_state.all_chats[new_id] = {
            "title": "New Chat",
            "messages": [{"role": "assistant", "content": "Hi! I am StockMind AI. How can I help you manage the inventory today?"}]
        }
        st.rerun()
    
    st.markdown("### Recent Chats")
    for chat_id, chat_data in reversed(list(st.session_state.all_chats.items())):
        if st.button(chat_data["title"], key=chat_id, use_container_width=True):
            st.session_state.current_chat_id = chat_id
            st.rerun()

# --- MAIN CHAT INTERFACE ---
current_chat = st.session_state.all_chats[st.session_state.current_chat_id]

# Loop through all messages and display them
for index, msg in enumerate(current_chat["messages"]):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        
        # ADDITION: The Learning Loop (Only show for the AI's answers, skipping the first greeting)
        if msg["role"] == "assistant" and index > 0:
            # Create a unique ID for this specific feedback button
            feedback_key = f"feedback_{st.session_state.current_chat_id}_{index}"
            
            # Show the thumbs up/down widget
            feedback = st.feedback("thumbs", key=feedback_key)
            
            # If the user clicks a button, save it to the AI's memory!
            if feedback is not None and msg.get("feedback") != feedback:
                msg["feedback"] = feedback # 1 is Thumbs Up, 0 is Thumbs Down
                
                # Save to our permanent JSON file
                st.session_state.all_chats[st.session_state.current_chat_id] = current_chat
                save_history(st.session_state.all_chats)
                
                if feedback == 1:
                    st.toast("✅ Positive feedback saved! StockMind will prioritize similar answers.")
                else:
                    st.toast("⚠️ Negative feedback logged. StockMind will flag this for review.")

# --- USER INPUT & AI COMMUNICATION ---
if prompt := st.chat_input("Message StockMind AI (e.g., 'Analyze market trends for today')..."):
    
    with st.chat_message("user"):
        st.markdown(prompt)
    current_chat["messages"].append({"role": "user", "content": prompt})
        
    if current_chat["title"] == "New Chat" and len(current_chat["messages"]) > 2:
        current_chat["title"] = prompt[:25] + "..."
        
    with st.chat_message("assistant"):
        with st.spinner("Analyzing..."):
            try:
                # Send the command and the full chat history to your FastAPI backend
                payload = {"query": prompt, "history": current_chat["messages"]}
                # NOTE: This assumes your main.py has an endpoint named /chat
               response = requests.post("https://stockmind-ai-production.up.railway.app/chat", json=payload)
                
                if response.status_code == 200:
                    ai_reply = response.json().get("reply", "No response received.")
                else:
                    ai_reply = f"⚠️ Backend returned an error: {response.status_code}. We will need to update your main.py to accept this request!"
            except Exception as e:
                ai_reply = "⚠️ Could not connect to the backend. Make sure your `python main.py` terminal is still running!"
            
            st.markdown(ai_reply)
            current_chat["messages"].append({"role": "assistant", "content": ai_reply})
    
    # Save to file and refresh
    st.session_state.all_chats[st.session_state.current_chat_id] = current_chat
    save_history(st.session_state.all_chats)
    st.rerun()
