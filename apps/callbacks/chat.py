import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output, State, ALL, ctx
import requests
import json
import uuid
import time
import re

from ..layout.components import SystemMessage, ErrorBubble, UserChatBubble, AgentChatBubble, AgentTransferLine, ToolCallBubble, ToolResponseBubble, WikitextBubble
from .utils import _parse_events_to_messages

API_BASE_URL = "http://localhost:8000"
APP_NAME = "LineageAI"

def register_chat_callbacks(app):

    @app.callback(
        [Output('desktop-api-status-indicator', 'children'),
         Output('mobile-api-status-indicator', 'children')],
        [Input('api-status-interval', 'n_intervals'),
         Input('is-thinking-store', 'data')]
    )
    def update_api_status(n_intervals, is_thinking):
        triggered_id = ctx.triggered_id

        if triggered_id == 'is-thinking-store':
            if is_thinking:
                status_badge = dbc.Badge("Online", color="success", className="ms-2")
                return status_badge, status_badge
            else:
                pass
        
        try:
            response = requests.get(f"{API_BASE_URL}/docs", timeout=2)
            if response.status_code == 200:
                status_badge = dbc.Badge("Online", color="success", className="ms-2")
                return status_badge, status_badge
        except requests.exceptions.RequestException as e:
            print(f"API status check failed: {e}")
        
        status_badge = dbc.Badge("Offline", color="danger", className="ms-2")
        return status_badge, status_badge

    @app.callback(
        Output('chat-history', 'children'),
        [Input('messages-store', 'data'),
         Input('active-session-store', 'data')]
    )
    def update_chat_history(messages_data, active_session_id):
        if not active_session_id:
            return SystemMessage("Loading sessions…", with_spinner=True)
        if active_session_id not in messages_data:
            return SystemMessage("Restoring session…", with_spinner=True)

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
                if tool_name == 'transfer_to_agent':
                    bubbles.append(AgentTransferLine(author, tool_name, msg.get('input', '{}')))
                else:
                    bubbles.append(ToolCallBubble(author, tool_name, msg.get('input', '{}')))
            
            elif role == 'tool_response':
                if tool_name != 'transfer_to_agent':
                    show_author = True
                    if i > 0 and messages[i-1].get('role') == 'tool':
                        show_author = False
                    bubbles.append(ToolResponseBubble(author, tool_name, msg.get('output', '{}'), show_author=show_author))

            elif role == 'error':
                bubbles.append(ErrorBubble(
                    author=msg.get('author', 'System'),
                    main_message=msg.get('main_message', 'An error occurred.'),
                    details=msg.get('details', '{}')
                ))

            elif role == 'system':
                bubbles.append(SystemMessage(content))
            
        return html.Div(bubbles, className="p-3")

    @app.callback(
        [Output('messages-store', 'data', allow_duplicate=True),
         Output('user-input', 'value'),
         Output('api-trigger-store', 'data'),
         Output('is-thinking-store', 'data')],
        [Input('send-btn', 'n_clicks'),
         Input('start-research-btn', 'n_clicks'),
         Input('format-biography-btn', 'n_clicks'),
         Input('fetch-profile-ok-btn', 'n_clicks'),
         Input('wikitree-profile-id-input', 'n_submit')],
        [State('user-input', 'value'),
         State('wikitree-profile-id-input', 'value'),
         State('active-session-store', 'data'),
         State('messages-store', 'data')],
        prevent_initial_call=True
    )
    def handle_user_actions(send_clicks, research_clicks, format_clicks, fetch_clicks, n_submit, user_input, profile_id, active_session_id, messages_data):
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
            input_text = "Use the formatter agent to format a biography that includes as much relevant details about the profile we've been talking about, including references and only links to known profiles."
        elif ctx.triggered_id == 'fetch-profile-ok-btn' or ctx.triggered_id == 'wikitree-profile-id-input':
            if profile_id:
                input_text = f"Read {profile_id} from WikiTree, fetching it as the data may have changed if you have read it previously."
            else:
                return dash.no_update, dash.no_update, dash.no_update, dash.no_update

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

                for chunk in r.iter_lines():
                    if not chunk: continue
                    chunk_str = chunk.decode('utf-8')
                    if chunk_str.startswith('data: '): chunk_str = chunk_str[6:]
                    
                    try:
                        data = json.loads(chunk_str)
                        events = data if isinstance(data, list) else [data]
                        
                        parsed_messages, session_title = _parse_events_to_messages(events)

                        if session_title:
                            new_sessions[active_session_id] = session_title
                        
                        if parsed_messages:
                            if active_session_id not in new_messages:
                                new_messages[active_session_id] = []
                            new_messages[active_session_id].extend(parsed_messages)

                        set_progress((new_messages, new_sessions))

                    except json.JSONDecodeError as e:
                        print(f"JSON decode error: {e} - Bad chunk: {chunk_str}")
                        pass
            
            return new_messages, new_sessions, False
        except requests.exceptions.RequestException as e:
            error_content = f"Error communicating with agent: {e}"
            if hasattr(e, 'response') and e.response is not None:
                error_content += f" (Status code: {e.response.status_code})"
            
            if active_session_id not in new_messages:
                new_messages[active_session_id] = []
            new_messages[active_session_id].append({"role": "assistant", "author": "Error", "content": error_content})
            return new_messages, new_sessions, False

    @app.callback(
        [Output('thinking-indicator', 'style'),
         Output('chat-history', 'style'),
         Output('chat-history', 'className'),
         Output('api-status-interval', 'disabled')],
        Input('is-thinking-store', 'data'),
        [State('thinking-indicator', 'style'),
         State('chat-history', 'style'),
         State('chat-history', 'className')]
    )
    def update_thinking_indicator(is_thinking, ti_style, ch_style, ch_className):
        ch_className = ch_className or ""
        disabled = False
        if is_thinking:
            ti_style['opacity'] = 1
            ti_style['max-height'] = '100px'
            ch_style['padding-bottom'] = '1em'
            if "fade-out-bottom" not in ch_className:
                ch_className += " fade-out-bottom"
            disabled = True
        else:
            ti_style['opacity'] = 0
            ti_style['max-height'] = '0px'
            ch_style['padding-bottom'] = '0px'
            ch_className = ch_className.replace(" fade-out-bottom", "")
        return ti_style, ch_style, ch_className, disabled

    @app.callback(
        Output("profile-modal", "is_open"),
        [Input("fetch-profile-btn", "n_clicks"),
         Input("fetch-profile-cancel-btn", "n_clicks"),
         Input("fetch-profile-ok-btn", "n_clicks"),
         Input("wikitree-profile-id-input", "n_submit")],
        [State("profile-modal", "is_open")],
        prevent_initial_call=True,
    )
    def toggle_profile_modal(n1, n2, n3, n4, is_open):
        if n1 or n2 or n3 or n4:
            return not is_open
        return is_open

    app.clientside_callback(
        """
        function(is_open) {
            if (is_open) {
                setTimeout(function() {
                    var input = document.getElementById('wikitree-profile-id-input');
                    if (input) {
                        input.focus();
                        input.select();
                    }
                }, 100);
            }
            return window.dash_clientside.no_update;
        }
        """,
        Output('wikitree-profile-id-input', 'className', allow_duplicate=True),
        Input('profile-modal', 'is_open'),
        prevent_initial_call=True
    )