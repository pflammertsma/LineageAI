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
        dbc.themes.DARKLY, # Use a dark theme as a base
        "/assets/custom.css" # Custom stylesheet for overrides
    ],
    # Point to the correct assets folder location
    assets_folder='../assets',
    background_callback_manager=background_callback_manager,
    title="LineageAI"
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


# --- App Layout ---

# Store components for state management
store_components = html.Div([
    dcc.Store(id='user-id-store'),
    dcc.Store(id='sessions-store', data={}),  # {session_id: display_name}
    dcc.Store(id='active-session-store', data=None), # active_session_id
    dcc.Store(id='messages-store', data={}), # {session_id: [messages]}
    dcc.Interval(id='api-status-interval', interval=60*1000, n_intervals=0), # 1 minute
])

sidebar = html.Div(
    id="sidebar",
    className="d-flex flex-column flex-shrink-0 p-3",
    style={"width": "280px", "height": "100vh"},
    children=[
        html.Div([
            html.A(
                href="/",
                className="sidebar-header",
                children=[
                    html.Img(src=app.get_asset_url('lineageai-icon.svg'), className="app-icon", alt="LineageAI Logo"),
                    html.Span("LineageAI", className="app-title")
                ]
            ),
            html.Div(id='api-status-indicator')
        ], className="d-flex justify-content-between align-items-center"),
        
        dbc.Nav(
            [
                dbc.Button("New Session", id="new-session-btn", color="primary", className="w-100"),
            ],
            vertical=True,
            pills=True,
            className="my-3"
        ),
        html.Hr(),
        html.Div(id="session-list-container"),
        html.Hr(),
        html.Div(id="debug-info-container"),
    ],
)

chat_history = html.Div(
    id="chat-history",
    style={
        "flexGrow": "1",
        "overflowY": "auto",
        "padding": "15px"
    },
    children=[]
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
        dbc.InputGroup(
            [
                dbc.Input(id="user-input", placeholder="Type your message...", n_submit=0),
                dbc.Button("Send", id="send-btn", color="primary", n_clicks=0),
            ]
        ),
    ]
)

main_content = html.Div(
    id="main-content",
    className="d-flex flex-column",
    style={"height": "100vh", "flexGrow": "1"},
    children=[
        html.H4(id="conversation-title", className="p-3 border-bottom"),
        chat_history,
        chat_input_area,
    ]
)

app.layout = html.Div(
    id="app-container",
    className="d-flex",
    children=[
        store_components,
        sidebar,
        main_content,
    ]
)

# --- Callbacks ---

# API Status Check
@app.callback(
    Output('api-status-indicator', 'children'),
    Input('api-status-interval', 'n_intervals')
)
def update_api_status(n):
    try:
        # Use a GET request to a known endpoint like /docs
        response = requests.get(f"{API_BASE_URL}/docs", timeout=2)
        if response.status_code == 200:
            return dbc.Badge("Online", color="success", className="ms-2")
    except requests.exceptions.RequestException:
        pass
    return dbc.Badge("Offline", color="danger", className="ms-2")

# Initialize user ID
@app.callback(
    Output('user-id-store', 'data'),
    Input('user-id-store', 'data')
)
def initialize_user_id(current_id):
    if current_id is None:
        return f"user-{uuid.uuid4()}"
    return dash.no_update

# Handle New Session button click
@app.callback(
    [Output('sessions-store', 'data'),
     Output('active-session-store', 'data'),
     Output('messages-store', 'data'),
     Output('debug-info-container', 'children')],
    Input('new-session-btn', 'n_clicks'),
    [State('user-id-store', 'data'),
     State('sessions-store', 'data'),
     State('messages-store', 'data')]
)
def create_session(n_clicks, user_id, sessions_data, messages_data):
    if n_clicks is None or user_id is None:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update

    session_id = f"session-{int(time.time())}"
    try:
        response = requests.post(
            f"{API_BASE_URL}/apps/{APP_NAME}/users/{user_id}/sessions/{session_id}",
            headers={"Content-Type": "application/json"},
            data=json.dumps({})
        )
        response.raise_for_status()
        
        new_sessions = sessions_data.copy()
        new_sessions[session_id] = f"Session {len(new_sessions) + 1}"
        
        new_messages = messages_data.copy()
        new_messages[session_id] = []
        
        return new_sessions, session_id, new_messages, dash.no_update

    except requests.exceptions.RequestException as e:
        error_alert = dbc.Alert(
            f"Failed to create session: {e}", 
            color="danger", 
            dismissable=True,
            className="m-3"
        )
        return dash.no_update, dash.no_update, dash.no_update, error_alert

# Update session list in the sidebar
@app.callback(
    Output('session-list-container', 'children'),
    [Input('sessions-store', 'data'),
     Input('active-session-store', 'data')]
)
def update_session_list(sessions, active_session_id):
    if not sessions:
        return html.P("No sessions yet.", className="text-secondary px-3")

    session_buttons = []
    for session_id, display_name in reversed(list(sessions.items())):
        is_active = (session_id == active_session_id)
        button = dbc.Button(
            display_name,
            id=f'{{"type": "session-btn", "index": "{session_id}"}}',
            color="primary" if is_active else "light",
            className="w-100 mb-1 text-start"
        )
        session_buttons.append(button)
    
    return session_buttons

# Handle session selection
@app.callback(
    Output('active-session-store', 'data', allow_duplicate=True),
    Input({"type": "session-btn", "index": ALL}, 'n_clicks'),
    State({"type": "session-btn", "index": ALL}, 'id'),
    prevent_initial_call=True
)
def select_session(n_clicks, ids):
    if not ctx.triggered or not any(n_clicks):
        return dash.no_update

    button_id_str = ctx.triggered[0]['prop_id'].split('.')[0]
    button_id = json.loads(button_id_str)
    session_id = button_id['index']
    return session_id

# Update conversation title
@app.callback(
    Output('conversation-title', 'children'),
    Input('active-session-store', 'data'),
    State('sessions-store', 'data')
)
def update_conversation_title(active_session_id, sessions):
    if not active_session_id or not sessions:
        return "Conversation"
    return sessions.get(active_session_id, "Conversation")

# Update chat history display
@app.callback(
    Output('chat-history', 'children'),
    Input('messages-store', 'data'),
    State('active-session-store', 'data')
)
def update_chat_history(messages_data, active_session_id):
    if not active_session_id or active_session_id not in messages_data:
        return [html.P("Welcome! Select or create a session to begin.", className="p-3")]

    messages = messages_data.get(active_session_id, [])
    if not messages:
        return [html.P("What can I help you with?", className="p-3")]

    chat_bubbles = []
    for msg in messages:
        role = msg.get('role')
        
        if role == 'user':
            bubble = dbc.Alert(
                dcc.Markdown(msg.get('content', '')),
                color="primary",
                style={"width": "fit-content", "maxWidth": "80%", "marginLeft": "auto", "marginRight": "0"},
                className="mb-2"
            )
            chat_bubbles.append(bubble)

        elif role == 'assistant':
            author = msg.get('author', 'Assistant')
            content = msg.get('content', '')
            author_div = html.Div(author, className="small text-secondary mb-1")
            bubble = dbc.Alert(
                dcc.Markdown(content),
                color="secondary",
                style={"width": "fit-content", "maxWidth": "80%", "marginLeft": "0", "marginRight": "auto"},
                className="mb-2"
            )
            chat_bubbles.append(html.Div([author_div, bubble]))

        elif role == 'tool':
            tool_name = msg.get('name', 'Unknown Tool')
            tool_input = msg.get('input', '{}')
            card = dbc.Card([
                dbc.CardHeader(f"Tool Call: {tool_name}"),
                dbc.CardBody(html.Pre(html.Code(tool_input)))
            ], className="mb-2 w-75")
            chat_bubbles.append(card)

    return chat_bubbles

# Callback to add user message and placeholder to the store for immediate display
@app.callback(
    Output('messages-store', 'data', allow_duplicate=True),
    Output('user-input', 'value'),
    Input('send-btn', 'n_clicks'),
    Input('user-input', 'n_submit'),
    State('user-input', 'value'),
    State('active-session-store', 'data'),
    State('messages-store', 'data'),
    prevent_initial_call=True
)
def add_user_message_to_chat(n_clicks, n_submit, user_input, active_session_id, messages_data):
    if not active_session_id or not user_input:
        return dash.no_update, dash.no_update

    new_messages = messages_data.copy()
    if active_session_id not in new_messages:
        new_messages[active_session_id] = []

    # Add user message
    new_messages[active_session_id].append({"role": "user", "content": user_input})
    # Add a placeholder for the assistant's response
    new_messages[active_session_id].append({"role": "assistant", "content": "...", "author": ""})

    return new_messages, ""

# Background callback to handle message sending and streaming response
@app.callback(
    Output('messages-store', 'data', allow_duplicate=True),
    Input('messages-store', 'data'),
    State('user-id-store', 'data'),
    State('active-session-store', 'data'),
    background=True,
    progress=[Output('messages-store', 'data')],
    prevent_initial_call=True
)
def stream_agent_response(set_progress, messages_data, user_id, active_session_id):
    if not active_session_id or not messages_data.get(active_session_id):
        raise dash.exceptions.PreventUpdate

    messages = messages_data[active_session_id]
    last_message = messages[-1]
    second_last_message = messages[-2] if len(messages) > 1 else None

    # Check if the last message is a placeholder and the one before is from the user
    if not (last_message.get('role') == 'assistant' and last_message.get('content') == '...' and 
            second_last_message and second_last_message.get('role') == 'user'):
        raise dash.exceptions.PreventUpdate

    user_input = second_last_message['content']
    new_messages = messages_data.copy()

    # --- Call SSE endpoint and stream response ---
    try:
        with requests.post(
            f"{API_BASE_URL}/run_sse",
            headers={"Content-Type": "application/json"},
            data=json.dumps({
                "app_name": APP_NAME,
                "user_id": user_id,
                "session_id": active_session_id,
                "new_message": {
                    "role": "user",
                    "parts": [{"text": user_input}]
                }
            }),
            stream=True
        ) as r:
            r.raise_for_status()
            
            is_first_chunk = True
            current_author = ""

            for chunk in r.iter_lines():
                if chunk:
                    chunk_str = chunk.decode('utf-8')
                    if chunk_str.startswith('data: '):
                        chunk_str = chunk_str[6:]
                    try:
                        data = json.loads(chunk_str)
                        print(f"--- DEBUG SSE Event ---: {data}") # DEBUG LINE
                        events = data if isinstance(data, list) else [data]
                        for event in events:
                            content = event.get("content", {})
                            role = content.get('role')

                            if role == 'model':
                                author = content.get("author", "Assistant")
                                text_part = next((p.get("text") for p in content.get("parts", []) if "text" in p), None)
                                
                                if text_part:
                                    if is_first_chunk:
                                        # Overwrite the placeholder with the first chunk
                                        new_messages[active_session_id][-1] = {"role": "assistant", "author": author, "content": text_part}
                                        is_first_chunk = False
                                        current_author = author
                                    elif author != current_author:
                                        # If author changes, start a new message
                                        current_author = author
                                        new_message = {"role": "assistant", "author": author, "content": text_part}
                                        new_messages[active_session_id].append(new_message)
                                    else:
                                        # Append text to the last message if author is the same
                                        new_messages[active_session_id][-1]['content'] += text_part
                                    
                                    set_progress(new_messages)

                            elif role == 'tool':
                                # If a tool call comes in, add it as a new message
                                # and prepare a new placeholder for the tool's result
                                tool_name = content.get('name', 'Unknown Tool')
                                tool_input = json.dumps(content.get('args', {}), indent=2)
                                tool_message = {"role": "tool", "name": tool_name, "input": tool_input}
                                new_messages[active_session_id].append(tool_message)
                                # Add a new placeholder for the next assistant response
                                new_messages[active_session_id].append({"role": "assistant", "content": "...", "author": ""})
                                is_first_chunk = True # Reset for the next response
                                set_progress(new_messages)

                    except json.JSONDecodeError:
                        pass
            
            # Final cleanup: if the last message is still a placeholder, remove it
            if new_messages[active_session_id][-1].get('content') == '...':
                new_messages[active_session_id].pop()

        return new_messages

    except requests.exceptions.RequestException as e:
        error_message = f"Error communicating with agent: {e}"
        # Replace the placeholder with an error message
        new_messages[active_session_id][-1] = {"role": "assistant", "author": "Error", "content": error_message}
        return new_messages


# --- Main Entry Point ---
if __name__ == "__main__":
    app.run(debug=True, port=8050)