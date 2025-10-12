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

def send_message_stream(message):
    """
    Send a message to the LineageAI agent and stream the response events.
    """
    if not st.session_state.active_session_id:
        st.error("No active session. Please create a session first.")
        return

    try:
        with requests.post(
            f"{API_BASE_URL}/run_sse",
            headers={"Content-Type": "application/json"},
            data=json.dumps({
                "app_name": APP_NAME,
                "user_id": st.session_state.user_id,
                "session_id": st.session_state.active_session_id,
                "new_message": {
                    "role": "user",
                    "parts": [{"text": message}]
                }
            }),
            stream=True
        ) as r:
            r.raise_for_status()
            for chunk in r.iter_lines():
                if chunk:
                    chunk_str = chunk.decode('utf-8')
                    if chunk_str.startswith('data: '):
                        chunk_str = chunk_str[6:]
                    try:
                        data = json.loads(chunk_str)
                        events = data if isinstance(data, list) else [data]
                        for event in events:
                            yield event
                    except json.JSONDecodeError:
                        pass
    except requests.exceptions.RequestException as e:
        st.error(f"Error streaming response: {e}")


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
            full_response_parts = []
            for event in send_message_stream(message):
                if isinstance(event, dict):
                    content = event.get("content", {})
                    if content.get("role") == "model":
                        for part in content.get("parts", []):
                            if "text" in part:
                                st.write(part["text"])
                                full_response_parts.append(part["text"])
                            elif "functionCall" in part:
                                fc = part["functionCall"]
                                func_name = fc.get("name")
                                func_args = fc.get("args")
                                
                                if func_name == "transfer_to_agent":
                                    agent_name = func_args.get("agent_name", "Unknown Agent")
                                    with st.expander(f"Transferring to: `{agent_name}`"):
                                        st.json(part)
                                else:
                                    with st.expander(f"Calling function: `{func_name}`"):
                                        st.json(part)
                            else:
                                st.json(part)
                else:
                    st.json(event)
        
        if full_response_parts:
            st.session_state.messages[st.session_state.active_session_id].append({"role": "assistant", "content": "\n\n".join(full_response_parts)})

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