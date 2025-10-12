import streamlit as st
import requests
import json
import uuid
import time
from st_copy import copy_button

# Set page config
st.set_page_config(
    page_title="LineageAI Chat",
    page_icon=" genealogist:",
    layout="centered"
)

# Constants
API_BASE_URL = "http://localhost:8000"
APP_NAME = "LineageAI"

# Initialize session state variables
if "user_id" not in st.session_state:
    st.session_state.user_id = f"user-{uuid.uuid4()}"
if "sessions" not in st.session_state:
    st.session_state.sessions = {} # Will store session_id -> display_name
if "active_session_id" not in st.session_state:
    st.session_state.active_session_id = None
# Handle migration from single-session to multi-session
if "messages" not in st.session_state or not isinstance(st.session_state.messages, dict):
    st.session_state.messages = {} # Will be a dict mapping session_id to list of messages

def create_session():
    """
    Create a new session with the LineageAI agent.
    """
    session_id = f"session-{int(time.time())}"
    response = requests.post(
        f"{API_BASE_URL}/apps/{APP_NAME}/users/{st.session_state.user_id}/sessions/{session_id}",
        headers={"Content-Type": "application/json"},
        data=json.dumps({})
    )
    if response.status_code == 200:
        st.session_state.sessions[session_id] = f"Session {len(st.session_state.sessions) + 1}"
        st.session_state.active_session_id = session_id
        st.session_state.messages[session_id] = []
        return True
    else:
        st.error(f"Failed to create session: {response.text}")
        return False

def send_message(message):
    """
    Send a message to the LineageAI agent and return the response parts.
    """
    if not st.session_state.active_session_id:
        st.error("No active session. Please create a session first.")
        return []

    # Send message to API
    response = requests.post(
        f"{API_BASE_URL}/run",
        headers={"Content-Type": "application/json"},
        data=json.dumps({
            "app_name": APP_NAME,
            "user_id": st.session_state.user_id,
            "session_id": st.session_state.active_session_id,
            "new_message": {
                "role": "user",
                "parts": [{"text": message}]
            }
        })
    )

    if response.status_code != 200:
        st.error(f"Error: {response.text}")
        return []

    # Process the response
    events = response.json()

    # Extract assistant's text response
    text_parts = []
    for event in events:
        if event.get("content", {}).get("role") == "model":
            for part in event.get("content", {}).get("parts", []):
                if "text" in part:
                    text_parts.append(part["text"])
    return text_parts


# UI Components
st.title("LineageAI Chat")

# Sidebar for session management
with st.sidebar:
    st.header("Session Management")
    if st.button("New Session"):
        create_session()

    if st.session_state.sessions:
        st.subheader("Sessions")
        # Reverse the order of sessions to show the newest first
        for session_id, display_name in reversed(list(st.session_state.sessions.items())):
            if st.button(display_name, key=session_id, use_container_width=True):
                st.session_state.active_session_id = session_id
                st.rerun()
    
    if st.session_state.active_session_id:
        st.success(f"Active session: {st.session_state.sessions[st.session_state.active_session_id]}")
    else:
        st.warning("No active session")


    st.divider()
    st.caption("This app interacts with the LineageAI agent via the ADK API Server.")
    st.caption("Make sure the ADK API Server is running on port 8000.")

# Chat interface
if st.session_state.active_session_id:
    st.subheader(st.session_state.sessions[st.session_state.active_session_id])
else:
    st.subheader("Conversation")

# Display messages
if st.session_state.active_session_id and st.session_state.active_session_id in st.session_state.messages:
    for msg in st.session_state.messages[st.session_state.active_session_id]:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            if msg["role"] == "assistant":
                copy_button(msg["content"], icon="st")

def handle_input(message):
    st.session_state.messages[st.session_state.active_session_id].append({"role": "user", "content": message})
    with st.chat_message("user"):
        st.write(message)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            text_parts = send_message(message)
            full_response = "\n\n".join(text_parts)
            for part in text_parts:
                st.write(part)
                time.sleep(0.5)
            
            if full_response:
                st.session_state.messages[st.session_state.active_session_id].append({"role": "assistant", "content": full_response.strip()})

# Input for new messages
if st.session_state.active_session_id:
    message_to_send = None
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Start Research", use_container_width=True):
            message_to_send = "Use the researcher agent to perform research. Look for any relevant genealogical records."
    with col2:
        if st.button("Format Biography", use_container_width=True):
            message_to_send = "Use the formatter agent to format a biography that includes as much relevant details about a profiles we've been talking about, including references and only links to known profiles."

    if user_input := st.chat_input("Type your message..."):
        message_to_send = user_input

    if message_to_send and st.session_state.active_session_id in st.session_state.messages:
        handle_input(message_to_send)
else:
    st.info("Create a session to start chatting")