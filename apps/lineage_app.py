# This is a Plotly Dash application that connects to an Agent Development Kit (ADK) API server.
# The ADK implementation resides in the LineageAI directory.
#
# It is executed from the root project directory with:
# $ python apps/lineage_app.py

import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output, State, ALL, CeleryManager, DiskcacheManager, ctx
import requests
import json
import uuid
import time

# For background callbacks
import diskcache
cache = diskcache.Cache("./cache")
background_callback_manager = DiskcacheManager(cache)

# Constants
API_BASE_URL = "http://localhost:8000"
APP_NAME = "LineageAI"

# Initialize the Dash app
app = dash.Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.DARKLY,
        dbc.icons.BOOTSTRAP,
        "/assets/custom.css"
    ],
    assets_folder='../assets',
    background_callback_manager=background_callback_manager,
    title="LineageAI",
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}]
)

# Add Google Fonts link
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

# --- Reusable Components ---

def create_sidebar_content(prefix: str):
    """Creates the content for the sidebar, used in both desktop and mobile views."""
    return [
        html.Div([
            html.A(
                href="/",
                className="sidebar-header",
                children=[
                    html.Img(src=app.get_asset_url('lineageai-icon.svg'), className="app-icon", alt="LineageAI Logo"),
                    html.Span("LineageAI", className="app-title")
                ]
            ),
            html.Div(id=f'{prefix}-api-status-indicator')
        ], className="d-flex justify-content-between align-items-center"),
        dbc.Nav(
            [dbc.Button("New Session", id=f'{prefix}-new-session-btn', color="primary", className="w-100")],
            vertical=True, pills=True, className="my-3"
        ),
        html.Hr(),
        html.Div(id=f'{prefix}-session-list-container', children=[dbc.Spinner(size="sm")]),
        html.Hr(),
    ]

# --- App Layout ---

store_components = html.Div([
    dcc.Store(id='user-id-store'),
    dcc.Store(id='sessions-store', data={}),
    dcc.Store(id='active-session-store', data=None),
    dcc.Store(id='messages-store', data={}),
    dcc.Store(id='api-trigger-store', data=None),
    dcc.Interval(id='api-status-interval', interval=60*1000, n_intervals=0),
])

# Sidebar for large screens
desktop_sidebar = html.Div(
    id="sidebar",
    className="d-none d-lg-flex flex-column flex-shrink-0 p-3",
    style={"width": "280px", "height": "100vh"},
    children=create_sidebar_content(prefix='desktop')
)

# Collapsible sidebar for small screens
mobile_sidebar = dbc.Offcanvas(
    id="offcanvas-sidebar",
    is_open=False,
    title="LineageAI",
    children=create_sidebar_content(prefix='mobile')
)

header = html.Div(
    id="main-header",
    className="d-flex align-items-center p-3 border-bottom",
    children=[
        dbc.Button(html.I(className="bi bi-list"), id="open-sidebar-btn", className="d-lg-none me-2", n_clicks=0),
        html.H4(id="conversation-title", className="m-0"),
    ]
)

chat_history = html.Div(
    id="chat-history",
    style={"flexGrow": "1", "overflowY": "auto"},
    children=[html.Div(
        [dbc.Spinner(), html.Span(" Initializing session...", className="ms-2")],
        className="d-flex justify-content-center align-items-center h-100"
    )]
)

chat_input_area = html.Div(
    id="chat-input-area",
    className="mt-auto p-3",
    style={"flexShrink": "0"},
    children=[
        dbc.Row([
            dbc.Col(dbc.Button("Start Research", id="start-research-btn", color="secondary"), width="auto"),
            dbc.Col(dbc.Button("Format Biography", id="format-biography-btn", color="secondary"), width="auto"),
        ], className="mb-2"),
        dbc.InputGroup([
            dbc.Input(id="user-input", placeholder="Type your message...", n_submit=0),
            dbc.Button("Send", id="send-btn", color="primary", n_clicks=0),
        ]),
    ]
)

main_content = html.Div(
    id="main-content",
    className="d-flex flex-column",
    style={"flexGrow": 1},
    children=[
        header,
        html.Div(
            id="chat-container",
            className="d-flex flex-column",
            style={"flexGrow": 1, "overflowY": "auto"},
            children=[
                chat_history,
                chat_input_area
            ]
        )
    ]
)

app.layout = html.Div(
    id="app-container", 
    className="d-flex", 
    children=[
        store_components, 
        desktop_sidebar, 
        main_content, 
        mobile_sidebar
    ]
)

# --- Callbacks ---

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
    except requests.exceptions.RequestException:
        pass
    status_badge = dbc.Badge("Offline", color="danger", className="ms-2")
    return status_badge, status_badge

@app.callback(Output('user-id-store', 'data'), Input('user-id-store', 'data'))
def initialize_user_id(current_id):
    if current_id is None: return f"user-{uuid.uuid4()}"
    return dash.no_update

@app.callback(
    [Output('active-session-store', 'data', allow_duplicate=True),
     Output('desktop-new-session-btn', 'n_clicks'),
     Output('mobile-new-session-btn', 'n_clicks')],
    Input('user-id-store', 'data'),
    State('sessions-store', 'data'),
    State('active-session-store', 'data'),
    prevent_initial_call=True
)
def initialize_active_session(user_id, sessions, active_session_id):
    if not user_id or active_session_id: return dash.no_update, dash.no_update, dash.no_update
    if sessions: return list(sessions.keys())[-1], dash.no_update, dash.no_update
    # Trigger the button in the visible sidebar. Since desktop is hidden on small screens,
    # we can assume the mobile one is the one to trigger.
    # A more robust solution might check the screen size.
    return dash.no_update, dash.no_update, 1

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
    except requests.exceptions.RequestException:
        return dash.no_update, 'FAILED', dash.no_update

@app.callback(
    [Output('desktop-session-list-container', 'children'),
     Output('mobile-session-list-container', 'children')],
    [Input('sessions-store', 'data'), Input('active-session-store', 'data')]
)
def update_session_list(sessions, active_session_id):
    if active_session_id == 'FAILED': 
        error_msg = html.P("API Offline", className="text-danger px-3")
        return error_msg, error_msg
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
    Input('active-session-store', 'data'),
    State('sessions-store', 'data')
)
def update_conversation_title(active_session_id, sessions):
    if not active_session_id or not sessions or active_session_id == 'FAILED': return "Conversation"
    return sessions.get(active_session_id, "Conversation")

@app.callback(
    Output('chat-history', 'children'),
    Input('messages-store', 'data'),
    State('active-session-store', 'data')
)
def update_chat_history(messages_data, active_session_id):
    centered_style = "d-flex justify-content-center align-items-center h-100"
    if not active_session_id: return html.Div([dbc.Spinner(), html.Span(" Loading session...", className="ms-2")], className=centered_style)
    if active_session_id == 'FAILED': return html.Div(dbc.Alert("Failed to create or load a session. The API server may be offline.", color="danger"), className=centered_style)
    if active_session_id not in messages_data: return html.Div([dbc.Spinner(), html.Span(" Loading messages...", className="ms-2")], className=centered_style)
    
    messages = messages_data.get(active_session_id, [])
    if not messages: return html.Div(html.P("What can I help you with?"), className=centered_style)

    bubbles = []
    for msg in messages:
        role = msg.get('role')
        if role == 'user':
            bubbles.append(dbc.Alert(dcc.Markdown(msg.get('content', '')), color="primary", style={"width": "fit-content", "maxWidth": "80%", "marginLeft": "auto", "marginRight": "0"}, className="mb-2"))
        elif role == 'assistant':
            author_div = html.Div(msg.get('author', 'Assistant'), className="small text-secondary mb-1")
            bubbles.append(html.Div([author_div, dbc.Alert(dcc.Markdown(msg.get('content', '')), color="secondary", style={"width": "fit-content", "maxWidth": "80%", "marginLeft": "0", "marginRight": "auto"}, className="mb-2")]))
        elif role == 'tool':
            author_div = html.Div(msg.get('author', 'Assistant'), className="small text-secondary mb-1")
            tool_name = msg.get('name', 'Unknown Tool')
            accordion = dbc.Accordion([
                dbc.AccordionItem(
                    html.Pre(html.Code(msg.get('input', '{}'))),
                    title=f"Tool Call: {tool_name}"
                ),
            ], start_collapsed=True, className="mb-2 w-75")
            bubbles.append(html.Div([author_div, accordion]))
    return html.Div(bubbles, className="p-3")

@app.callback(
    Output('messages-store', 'data', allow_duplicate=True),
    Output('user-input', 'value'),
    Output('api-trigger-store', 'data'),
    Input('send-btn', 'n_clicks'),
    Input('user-input', 'n_submit'),
    State('user-input', 'value'),
    State('active-session-store', 'data'),
    State('messages-store', 'data'),
    prevent_initial_call=True
)
def add_user_message_to_chat(n_clicks, n_submit, user_input, active_session_id, messages_data):
    if not active_session_id or not user_input: return dash.no_update, dash.no_update, dash.no_update
    new_messages = messages_data.copy()
    if active_session_id not in new_messages: new_messages[active_session_id] = []
    new_messages[active_session_id].append({"role": "user", "content": user_input})
    new_messages[active_session_id].append({"role": "assistant", "content": "..."})
    trigger_data = {"user_input": user_input, "timestamp": time.time()}
    return new_messages, "", trigger_data

@app.callback(
    [Output('messages-store', 'data', allow_duplicate=True), Output('sessions-store', 'data', allow_duplicate=True)],
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
    if not trigger_data: raise dash.exceptions.PreventUpdate

    new_messages = messages_data.copy()
    new_sessions = sessions_data.copy()
    
    # Pop the placeholder before streaming starts
    if new_messages.get(active_session_id) and new_messages[active_session_id][-1].get('content') == '...':
        new_messages[active_session_id].pop()

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
                        # Check for session title updates
                        state_delta = event.get('actions', {}).get('stateDelta', {})
                        if state_delta.get('session_title'):
                            new_sessions[active_session_id] = state_delta['session_title']

                        author = event.get("author", "Assistant")
                        content = event.get("content", {})
                        if not content or not content.get("parts"): continue

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
                                set_progress((new_messages, new_sessions))

                            elif "functionCall" in part:
                                is_first_model_chunk = True
                                tool_call = part["functionCall"]
                                tool_name = tool_call.get('name', '?')
                                tool_input = json.dumps(tool_call.get('args', {}), indent=2)
                                tool_message = {"role": "tool", "name": tool_name, "input": tool_input, "author": author}
                                new_messages[active_session_id].append(tool_message)
                                set_progress((new_messages, new_sessions))
                except json.JSONDecodeError:
                    pass
        return new_messages, new_sessions
    except requests.exceptions.RequestException as e:
        error_content = f"Error communicating with agent: {e}"
        new_messages[active_session_id].append({"role": "assistant", "author": "Error", "content": error_content})
        return new_messages, new_sessions

if __name__ == "__main__":
    app.run(debug=True, use_reloader=False, port=8050)
