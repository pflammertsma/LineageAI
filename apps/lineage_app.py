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
if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "messages" not in st.session_state:
    st.session_state.messages = []

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
        st.session_state.session_id = session_id
        st.session_state.messages = []
        return True
    else:
        st.error(f"Failed to create session: {response.text}")
        return False

def send_message(message):
    """
    Send a message to the LineageAI agent and return the response.
    """
    if not st.session_state.session_id:
        st.error("No active session. Please create a session first.")
        return ""

    # Send message to API
    response = requests.post(
        f"{API_BASE_URL}/run",
        headers={"Content-Type": "application/json"},
        data=json.dumps({
            "app_name": APP_NAME,
            "user_id": st.session_state.user_id,
            "session_id": st.session_state.session_id,
            "new_message": {
                "role": "user",
                "parts": [{"text": message}]
            }
        })
    )

    if response.status_code != 200:
        st.error(f"Error: {response.text}")
        return ""

    # Process the response
    events = response.json()

    # Extract assistant's text response
    assistant_message = ""
    for event in events:
        if event.get("content", {}).get("role") == "model" and "text" in event.get("content", {}).get("parts", [{}])[0]:
            assistant_message += event["content"]["parts"][0]["text"]

    return assistant_message


# UI Components
st.title("LineageAI Chat")

# Sidebar for session management
with st.sidebar:
    st.header("Session Management")
    if st.session_state.session_id:
        st.success(f"Active session: {st.session_state.session_id}")
        if st.button("New Session"):
            create_session()
    else:
        st.warning("No active session")
        if st.button("Create Session"):
            create_session()

    st.divider()
    st.caption("This app interacts with the LineageAI agent via the ADK API Server.")
    st.caption("Make sure the ADK API Server is running on port 8000.")

# Chat interface
st.subheader("Conversation")

# Display messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])
        if msg["role"] == "assistant":
            copy_button(msg["content"], icon="st")

def handle_input(message):
    st.session_state.messages.append({"role": "user", "content": message})
    st.chat_message("user").write(message)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response = send_message(message)
            st.write(response)
    st.session_state.messages.append({"role": "assistant", "content": response})

# Input for new messages
if st.session_state.session_id:
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

    if message_to_send:
        handle_input(message_to_send)
else:
    st.info("Create a session to start chatting")
