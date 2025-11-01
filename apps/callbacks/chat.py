import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output, State, ALL, ctx
import requests
import json
import uuid
import time
import re
from ..layout.components import UserChatBubble, AgentChatBubble, WikitextBubble, ToolCallBubble, SystemMessage, ToolResponseBubble

API_BASE_URL = "http://localhost:8000"
APP_NAME = "LineageAI"

def register_callbacks(app):
    @app.callback(
        Output("offcanvas-sidebar", "is_open"),
        Input("open-sidebar-btn", "n_clicks"),
        [State("offcanvas-sidebar", "is_open")],
    )
    def toggle_sidebar(n1, is_open):
        if n1:
            return not is_open
        return is_open

    @app.callback(
        [Output('desktop-api-status-indicator', 'children'),
         Output('mobile-api-status-indicator', 'children')],
        Input('api-status-interval', 'n_intervals')
    )
    def update_api_status(n):
        try:
            response = requests.get(f"{API_BASE_URL}/docs", timeout=2)
            if response.status_code == 200:
                status_badge = dbc.Badge("Online", color="success", className="ms-2")
                return status_badge, status_badge
        except requests.exceptions.RequestException as e:
            print(f"API status check failed: {e}")
        status_badge = dbc.Badge("Offline", color="danger", className="ms-2")
        return status_badge, status_badge

    def _parse_events_to_messages(events):
        messages = []
        if not events:
            return messages

        for i, event in enumerate(events):
            # Check for a user message
            if ("new_message" in event and event["new_message"].get("role") == "user") or event.get("author") == "user":
                if "new_message" in event:
                    parts = event["new_message"].get("parts", [])
                else:
                    parts = event.get("content", {}).get("parts", [])
                if parts:
                    full_text = "".join(p.get("text", "") for p in parts)
                    messages.append({"role": "user", "content": full_text})
                continue

            # Check for assistant/tool messages
            author = event.get("author")
            content = event.get("content")
            if not (author and content and "parts" in content):
                continue

            for part in content["parts"]:
                if "text" in part and part["text"]:
                    if messages and messages[-1].get("role") == "assistant" and messages[-1].get("author") == author:
                        messages[-1]["content"] += part["text"]
                    else:
                        messages.append({"role": "assistant", "author": author, "content": part["text"]})
                
                elif "functionCall" in part:
                    tool_call = part["functionCall"]
                    tool_name = tool_call.get('name', '?')
                    tool_input = json.dumps(tool_call.get('args', {}), indent=2)
                    messages.append({"role": "tool", "name": tool_name, "input": tool_input, "author": author})
                    
                elif "functionResponse" in part:
                    tool_response = part["functionResponse"]
                    tool_name = tool_response.get('name', '?')
                    tool_output = json.dumps(tool_response.get('response', {}), indent=2)
                    messages.append({"role": "tool_response", "name": tool_name, "output": tool_output, "author": author})
                    
                elif event.get("role") == "system":
                    messages.append({"role": "system", "content": part["text"]})
        
        return messages

    @app.callback(Output('user-id-store', 'data'), Input('user-id-store', 'data'))
    def initialize_user_id(current_id):
        if current_id is None: return f"user-{uuid.uuid4()}"
        return dash.no_update

    @app.callback(
        [Output('sessions-store', 'data', allow_duplicate=True),
         Output('active-session-store', 'data', allow_duplicate=True),
         Output('messages-store', 'data', allow_duplicate=True),
         Output('desktop-new-session-btn', 'n_clicks'),
         Output('mobile-new-session-btn', 'n_clicks')],
        Input('user-id-store', 'data'),
        [State('sessions-store', 'data'),
         State('active-session-store', 'data'),
         State('messages-store', 'data')],
        prevent_initial_call='initial_duplicate',
    )
    def initialize_sessions(user_id, existing_sessions, active_session_id, messages_data):
        if not user_id or active_session_id:
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

        # If sessions are already loaded, do nothing to them, but set the active session
        if existing_sessions:
            return dash.no_update, list(existing_sessions.keys())[-1], dash.no_update, dash.no_update, dash.no_update

        try:
            url = f"{API_BASE_URL}/apps/{APP_NAME}/users/{user_id}/sessions"
            response = requests.get(url)
            response.raise_for_status()
            sessions_data = response.json()
            sessions = {}
            if isinstance(sessions_data, list):
                if sessions_data and isinstance(sessions_data[0], dict):
                    sessions = {s['id']: s.get('title', f'Session {i+1}') for i, s in enumerate(sessions_data)}
                elif sessions_data:
                    sessions = {sid: f"Session {i+1}" for i, sid in enumerate(sorted(sessions_data))}
            elif isinstance(sessions_data, dict):
                sessions = sessions_data

            if sessions:
                latest_session_id = sorted(sessions.keys(), reverse=True)[0]

                # Now, fetch the messages for the latest session
                try:
                    url = f"{API_BASE_URL}/apps/{APP_NAME}/users/{user_id}/sessions/{latest_session_id}"
                    response = requests.get(url)
                    response.raise_for_status()
                    session_details = response.json()
                    
                    new_messages = messages_data.copy()
                    session_history_events = session_details.get('events', [])
                    parsed_messages = _parse_events_to_messages(session_history_events)
                    new_messages[latest_session_id] = parsed_messages
                    
                    return sessions, latest_session_id, new_messages, dash.no_update, dash.no_update
                    
                except requests.exceptions.RequestException as e:
                    print(f"API call to fetch session messages failed: {e}")
                    # Fallback to just loading the session without history
                    return sessions, latest_session_id, dash.no_update, dash.no_update, dash.no_update
            else:
                print("Sessions: No sessions found on server")
        except requests.exceptions.RequestException as e:
            print(f"API call to fetch sessions failed: {e}")
            # If the API call fails, we'll proceed to create a new session locally.
            pass

        # If no sessions are found on the server, or if the API call fails,
        # trigger the creation of a new session.
        print("Sessions: Creating new session")
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, 1

    @app.callback(
        [Output('sessions-store', 'data', allow_duplicate=True), 
         Output('active-session-store', 'data', allow_duplicate=True), 
         Output('messages-store', 'data', allow_duplicate=True)],
        [Input('desktop-new-session-btn', 'n_clicks'),
         Input('mobile-new-session-btn', 'n_clicks')],
        [State('user-id-store', 'data'), 
         State('sessions-store', 'data'), 
         State('messages-store', 'data')],
        prevent_initial_call=True
    )
    def create_session(desktop_clicks, mobile_clicks, user_id, sessions_data, messages_data):
        if not ctx.triggered_id or user_id is None: return dash.no_update, dash.no_update, dash.no_update
        session_id = f"session-{int(time.time())}"
        try:
            response = requests.post(f"{API_BASE_URL}/apps/{APP_NAME}/users/{user_id}/sessions/{session_id}", headers={"Content-Type": "application/json"}, data=json.dumps({}))
            response.raise_for_status()
            new_sessions = sessions_data.copy()
            new_sessions[session_id] = f"Session {len(new_sessions) + 1}"
            new_messages = messages_data.copy()
            if session_id not in new_messages: new_messages[session_id] = []
            return new_sessions, session_id, new_messages
        except requests.exceptions.RequestException as e:
            error_message = f"Failed to create session: {e}"
            print(error_message)
            new_messages = messages_data.copy()
            # Use a temporary session ID for the error message
            error_session_id = f"error-{uuid.uuid4()}"
            new_messages[error_session_id] = [{
                "role": "assistant", 
                "author": "System", 
                "content": error_message
            }]
            # Also update the sessions store to include the error session
            new_sessions = sessions_data.copy()
            new_sessions[error_session_id] = "Error"
            return new_sessions, error_session_id, new_messages

    @app.callback(
        [Output('desktop-session-list-container', 'children'),
         Output('mobile-session-list-container', 'children')],
        [Input('sessions-store', 'data'), Input('active-session-store', 'data')]
    )
    def update_session_list(sessions, active_session_id):
        if not sessions: 
            spinner = dbc.Spinner(size="sm")
            return spinner, spinner
        buttons = [dbc.Button(name, id=f'{{"type": "session-btn", "index": "{sid}"}}', color="primary" if sid == active_session_id else "light", className="w-100 mb-1 text-start") for sid, name in reversed(list(sessions.items()))]
        return buttons, buttons

    @app.callback(
        Output('active-session-store', 'data', allow_duplicate=True),
        Input({"type": "session-btn", "index": ALL}, 'n_clicks'),
        State({"type": "session-btn", "index": ALL}, 'id'),
        prevent_initial_call=True
    )
    def select_session(n_clicks, ids):
        if not ctx.triggered or not any(n_clicks): return dash.no_update
        button_id = json.loads(ctx.triggered[0]['prop_id'].split('.')[0])
        return button_id['index']

    @app.callback(
        Output('conversation-title', 'children'),
        [Input('active-session-store', 'data'),
         Input('sessions-store', 'data')]
    )
    def update_conversation_title(active_session_id, sessions):
        if not active_session_id or not sessions: return "Conversation"
        return sessions.get(active_session_id, "Conversation")

    @app.callback(
        Output('chat-history', 'children'),
        [Input('messages-store', 'data'),
         Input('active-session-store', 'data')]
    )
    def update_chat_history(messages_data, active_session_id):
        if not active_session_id:
            return SystemMessage("Loading session...", with_spinner=True)

        messages = messages_data.get(active_session_id, [])
        if not messages:
            return SystemMessage("What can I help you with?")

        bubbles = []
        for i, msg in enumerate(messages):
            role = msg.get('role')
            content = msg.get('content', '')
            author = msg.get('author', 'Assistant')
            tool_name = msg.get('name', 'Unknown Tool')

            if role == 'user':
                bubbles.append(UserChatBubble(content))
            
            elif role == 'assistant':
                if '```wiki' in content:
                    bubbles.append(WikitextBubble(author, content))
                else:
                    bubbles.append(AgentChatBubble(author, content))

            elif role == 'tool':
                bubbles.append(ToolCallBubble(author, tool_name, msg.get('input', '{}')))
            
            elif role == 'tool_response':
                if tool_name != 'transfer_to_agent':
                    bubbles.append(ToolResponseBubble(author, tool_name, msg.get('output', '{}')))

            elif role == 'system':
                bubbles.append(SystemMessage(content))
            
        return html.Div(bubbles, className="p-3")

    @app.callback(
        Output('messages-store', 'data', allow_duplicate=True),
        Output('user-input', 'value'),
        Output('api-trigger-store', 'data'),
        Output('is-thinking-store', 'data'),
        Input('send-btn', 'n_clicks'),
        Input('start-research-btn', 'n_clicks'),
        Input('format-biography-btn', 'n_clicks'),
        State('user-input', 'value'),
        State('active-session-store', 'data'),
        State('messages-store', 'data'),
        prevent_initial_call=True
    )
    def handle_user_actions(send_clicks, research_clicks, format_clicks, user_input, active_session_id, messages_data):
        if not ctx.triggered_id:
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update

        if not active_session_id or active_session_id.startswith('error-'):
            error_message = "Cannot send message: No active session. Please start a new session."
            new_messages = messages_data.copy()
            session_id_to_update = active_session_id if active_session_id else f"error-{uuid.uuid4()}"
            
            if session_id_to_update not in new_messages:
                new_messages[session_id_to_update] = []

            new_messages[session_id_to_update].append({
                "role": "assistant",
                "author": "System",
                "content": error_message
            })
            return new_messages, dash.no_update, dash.no_update, False

        input_text = ""
        clear_input = False

        if ctx.triggered_id == 'send-btn':
            if not user_input:
                return dash.no_update, dash.no_update, dash.no_update, dash.no_update
            input_text = user_input
            clear_input = True
        elif ctx.triggered_id == 'start-research-btn':
            input_text = "Use the researcher agent to perform research. Look for any relevant genealogical records."
        elif ctx.triggered_id == 'format-biography-btn':
            input_text = "Use the formatter agent to format a biography that includes as much relevant details about a profiles we've been talking about, including references and only links to known profiles."

        if not input_text:
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update

        new_messages = messages_data.copy()
        if active_session_id not in new_messages:
            new_messages[active_session_id] = []
        
        new_messages[active_session_id].append({"role": "user", "content": input_text})
        
        trigger_data = {"user_input": input_text, "timestamp": time.time()}
        
        output_user_input = "" if clear_input else dash.no_update

        return new_messages, output_user_input, trigger_data, True

    @app.callback(
        [Output('messages-store', 'data', allow_duplicate=True), 
         Output('sessions-store', 'data', allow_duplicate=True),
         Output('is-thinking-store', 'data', allow_duplicate=True)],
        Input('api-trigger-store', 'data'),
        State('user-id-store', 'data'),
        State('active-session-store', 'data'),
        State('messages-store', 'data'),
        State('sessions-store', 'data'),
        background=True,
        progress=[
            Output('messages-store', 'data'),
            Output('sessions-store', 'data')
        ],
        prevent_initial_call=True
    )
    def stream_agent_response(set_progress, trigger_data, user_id, active_session_id, messages_data, sessions_data):
        if not trigger_data or (active_session_id and active_session_id.startswith('error-')):
            raise dash.exceptions.PreventUpdate

        new_messages = messages_data.copy()
        new_sessions = sessions_data.copy()

        payload = {
            "app_name": APP_NAME,
            "user_id": user_id,
            "session_id": active_session_id,
            "new_message": {"role": "user", "parts": [{"text": trigger_data['user_input']}]}
        }

        try:
            with requests.post(f"{API_BASE_URL}/run_sse", headers={"Content-Type": "application/json"}, data=json.dumps(payload), stream=True) as r:
                r.raise_for_status()
                is_first_model_chunk = True

                for chunk in r.iter_lines():
                    if not chunk: continue
                    chunk_str = chunk.decode('utf-8')
                    if chunk_str.startswith('data: '): chunk_str = chunk_str[6:]
                    try:
                        data = json.loads(chunk_str)
                        events = data if isinstance(data, list) else [data]
                        for event in events:
                            state_delta = event.get('actions', {}).get('stateDelta', {})
                            if state_delta.get('session_title'):
                                new_sessions[active_session_id] = state_delta['session_title']

                            author = event.get("author", "Assistant")
                            content = event.get("content", {})
                            if not content or not content.get("parts"):
                                continue

                            for part in content.get("parts"):
                                if "text" in part and part["text"]:
                                    if is_first_model_chunk:
                                        new_messages[active_session_id].append({"role": "assistant", "author": author, "content": part["text"]})
                                        is_first_model_chunk = False
                                    else:
                                        last_msg = new_messages[active_session_id][-1]
                                        if last_msg["role"] == "assistant" and last_msg["author"] == author:
                                            last_msg['content'] += part["text"]
                                        else:
                                            new_messages[active_session_id].append({"role": "assistant", "author": author, "content": part["text"]})

                                elif "functionCall" in part:
                                    is_first_model_chunk = True
                                    tool_call = part["functionCall"]
                                    tool_name = tool_call.get('name', '?')
                                    tool_input = json.dumps(tool_call.get('args', {}), indent=2)
                                    tool_message = {"role": "tool", "name": tool_name, "input": tool_input, "author": author}
                                    new_messages[active_session_id].append(tool_message)
                                
                                elif "functionResponse" in part:
                                    is_first_model_chunk = True
                                    tool_response = part["functionResponse"]
                                    tool_name = tool_response.get('name', '?')
                                    response_data = tool_response.get('response', {})
                                    
                                    if tool_name == 'set_current_subject':
                                        new_title = response_data.get('session_title')
                                        if new_title:
                                            new_sessions[active_session_id] = new_title
                                            # We have the title, no need to show the full response bubble for this tool
                                            continue

                                    tool_output = json.dumps(response_data, indent=2)
                                    response_message = {"role": "tool_response", "name": tool_name, "output": tool_output, "author": author}
                                    new_messages[active_session_id].append(response_message)

                                else:
                                    unsupported_message = {
                                        "role": "system",
                                        "author": "System",
                                        "content": f"Unsupported message part type. Full part: {json.dumps(part)}",
                                    }
                                    print(f"Unsupported message part type: {part}")
                                    new_messages[active_session_id].append(unsupported_message)
                                
                        set_progress((new_messages, new_sessions))
                    except json.JSONDecodeError as e:
                        print(f"JSON decode error: {e} - Bad chunk: {chunk_str}")
                        pass
            return new_messages, new_sessions, False
        except requests.exceptions.RequestException as e:
            error_content = f"Error communicating with agent: {e}"
            if hasattr(e, 'response') and e.response is not None:
                error_content += f" (Status code: {e.response.status_code})"
            new_messages[active_session_id].append({"role": "assistant", "author": "Error", "content": error_content})
            return new_messages, new_sessions, False

    @app.callback(
        [Output('thinking-indicator', 'style'),
         Output('chat-history', 'style'),
         Output('chat-history', 'className')],
        Input('is-thinking-store', 'data'),
        [State('thinking-indicator', 'style'),
         State('chat-history', 'style'),
         State('chat-history', 'className')]
    )
    def update_thinking_indicator(is_thinking, ti_style, ch_style, ch_className):
        ch_className = ch_className or ""
        if is_thinking:
            ti_style['opacity'] = 1
            ti_style['max-height'] = '100px'
            ch_style['padding-bottom'] = '1em'
            if "fade-out-bottom" not in ch_className:
                ch_className += " fade-out-bottom"
        else:
            ti_style['opacity'] = 0
            ti_style['max-height'] = '0px'
            ch_style['padding-bottom'] = '0px'
            ch_className = ch_className.replace(" fade-out-bottom", "")
        return ti_style, ch_style, ch_className

    # --- Sidebar Collapse Callbacks ---

    @app.callback(
        Output('sidebar-collapsed-store', 'data'),
        Input('collapse-sidebar-btn', 'n_clicks'),
        State('sidebar-collapsed-store', 'data'),
        prevent_initial_call=True
    )
    def toggle_sidebar_collapse(n_clicks, is_collapsed):
        if n_clicks:
            return not is_collapsed
        return dash.no_update

    @app.callback(
        Output('sidebar', 'style'),
        Input('sidebar-collapsed-store', 'data')
    )
    def update_sidebar_style(is_collapsed):
        if is_collapsed:
            return {"width": "0px", "height": "100vh", "transition": "width 0.3s", "overflow": "hidden"}
        else:
            return {"width": "280px", "height": "100vh", "transition": "width 0.3s", "overflow": "hidden"}
