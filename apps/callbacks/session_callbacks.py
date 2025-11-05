import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output, State, ALL, ctx
import uuid
import time

from .utils import _parse_events_to_messages
from ..layout.components import SystemMessage
from .. import api_client

def register_session_callbacks(app):

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
        if not user_id or existing_sessions or active_session_id:
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

        sessions_data, error = api_client.get_sessions(user_id)

        if error:
            print(f"API call to fetch sessions failed: {error}")
            # Fall through to create a new session
        else:
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
                return sessions, latest_session_id, dash.no_update, dash.no_update, dash.no_update
            else:
                print("Sessions: No sessions found on server")

        print("Sessions: Creating new session")
        return dash.no_update, dash.no_update, dash.no_update, 1, 1

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
        _, error = api_client.create_session(user_id, session_id)

        if not error:
            new_sessions = sessions_data.copy()
            new_sessions[session_id] = f"Session {len(new_sessions) + 1}"
            new_messages = messages_data.copy()
            if session_id not in new_messages: new_messages[session_id] = []
            return new_sessions, session_id, new_messages
        else:
            error_message = f"Failed to create session: {error}"
            print(error_message)
            new_messages = messages_data.copy()
            error_session_id = f"error-{uuid.uuid4()}"
            new_messages[error_session_id] = [{
                "role": "assistant", 
                "author": "System", 
                "content": error_message
            }]
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
        items = [dbc.ListGroupItem(name, id={"type": "session-btn", "index": sid}, action=True, active=(sid == active_session_id), className="session-list-item") for sid, name in reversed(list(sessions.items()))]
        list_group = dbc.ListGroup(items, flush=True)
        return list_group, list_group

    @app.callback(
        [Output('active-session-store', 'data', allow_duplicate=True),
         Output('chat-history', 'children', allow_duplicate=True)],
        Input({"type": "session-btn", "index": ALL}, 'n_clicks'),
        State('active-session-store', 'data'),
        prevent_initial_call=True
    )
    def show_loading_spinner_on_session_change(n_clicks, active_session_id):
        if not ctx.triggered_id or not any(n_clicks):
            return dash.no_update, dash.no_update

        clicked_session_id = ctx.triggered_id['index']

        if clicked_session_id == active_session_id:
            return dash.no_update, dash.no_update

        loading_spinner = SystemMessage("Loading session…", with_spinner=True)
        return clicked_session_id, loading_spinner

    @app.callback(
        Output('messages-store', 'data', allow_duplicate=True),
        Input('active-session-store', 'data'),
        [State('user-id-store', 'data'),
         State('messages-store', 'data')],
        prevent_initial_call=True
    )
    def fetch_session_history(active_session_id, user_id, messages_data):
        if not active_session_id or not user_id:
            return dash.no_update

        if active_session_id in messages_data and messages_data[active_session_id]:
            return dash.no_update

        session_details, error = api_client.get_session_history(user_id, active_session_id)
        new_messages = messages_data.copy()

        if error:
            print(f"API call to fetch session messages failed: {error}")
            new_messages[active_session_id] = [{
                "role": "system",
                "content": f"Failed to load session history: {error}"
            }]
        else:
            session_history_events = session_details.get('events', [])
            parsed_messages, _ = _parse_events_to_messages(session_history_events)
            new_messages[active_session_id] = parsed_messages
            
        return new_messages

    @app.callback(
        Output('conversation-title', 'children'),
        [Input('active-session-store', 'data'),
         Input('sessions-store', 'data')]
    )
    def update_conversation_title(active_session_id, sessions):
        if not active_session_id or not sessions: return "Conversation"
        return sessions.get(active_session_id, "Conversation")