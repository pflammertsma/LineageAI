import dash_bootstrap_components as dbc
from dash import dcc, html

# --- Reusable Components ---

def create_sidebar_content(prefix: str, app):
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

def create_layout(app):
    store_components = html.Div([
        dcc.Store(id='user-id-store', storage_type='local'),
        dcc.Store(id='sidebar-collapsed-store', data=False),
        dcc.Store(id='sessions-store', data={}),
        dcc.Store(id='active-session-store', data=None),
        dcc.Store(id='messages-store', data={}),
        dcc.Store(id='api-trigger-store', data=None),
        dcc.Store(id='is-thinking-store', data=False),
        
        dcc.Interval(id='api-status-interval', interval=60*1000, n_intervals=0),
    ])

    desktop_sidebar = html.Div(
        id="sidebar",
        className="d-none d-lg-flex flex-column flex-shrink-0",
        style={"width": "280px", "height": "100vh", "transition": "width 0.3s", "overflow": "hidden"},
        children=[
            html.Div(
                style={'width': '280px', 'padding': '1rem'},
                children=create_sidebar_content(prefix='desktop', app=app)
            )
        ]
    )

    mobile_sidebar = dbc.Offcanvas(
        id="offcanvas-sidebar",
        is_open=False,
        title="LineageAI",
        children=create_sidebar_content(prefix='mobile', app=app)
    )

    header = html.Div(
        id="main-header",
        className="d-flex align-items-center p-3 border-bottom",
        children=[
            dbc.Button(html.I(className="bi bi-list"), id="open-sidebar-btn", className="d-lg-none me-2", n_clicks=0),
            dbc.Button(html.I(className="bi bi-layout-sidebar"), id="collapse-sidebar-btn", className="d-none d-lg-inline-block me-2", n_clicks=0),
            html.H4(id="conversation-title", className="m-0"),
        ]
    )

    chat_history = html.Div(
        id="chat-history",
        style={"flexGrow": "1", "overflowY": "auto", "position": "relative"},
        children=[html.Div(
            [dbc.Spinner(), html.Span(" Initializing session...", className="ms-2")],
            className="d-flex justify-content-center align-items-center h-100"
        )]
    )

    thinking_indicator = html.Div(
        id="thinking-indicator",
        className="align-items-center",
        style={"transition": "opacity 0.3s, transform 0.3s, max-height 0.3s", "opacity": 0, "transform": "translateY(100%)", "zIndex": 1, "position": "relative", "max-height": "0px"},
        children=[
            dbc.Spinner(size="sm", spinner_class_name="me-2"),
            html.Span("Thinking...")
        ]
    )

    chat_input_area = html.Div(
        id="chat-input-area",
        className="p-3",
        style={"flexShrink": "0", "zIndex": 2, "position": "relative"},
        children=[
            dbc.Row([
                dbc.Col(dbc.Button("Start Research", id="start-research-btn", color="secondary"), width="auto"),
                dbc.Col(dbc.Button("Format Biography", id="format-biography-btn", color="secondary"), width="auto"),
            ], className="mb-2"),
            dbc.InputGroup([
                dcc.Textarea(id="user-input", placeholder="Type your message...", style={'resize': 'none'}, className="user-input-textarea", rows=1),
                dbc.Button(html.I(className="bi bi-send-fill"), id="send-btn", color="primary", n_clicks=0, className="circle-button"),
            ]),
        ]
    )

    main_content = html.Div(
        id="main-content",
        className="d-flex flex-column",
        style={"flexGrow": 1, "position": "relative", "height": "100vh"},
        children=[
            header,
            chat_history,
            thinking_indicator,
            chat_input_area,
            dbc.Button(
                html.I(className="bi bi-arrow-down-circle-fill fs-4"),
                id="scroll-to-bottom-btn",
                style={
                    "position": "absolute",
                    "bottom": "120px",
                    "right": "36px",
                    "display": "none",
                    "zIndex": 10
                },
                className="circle-button"
            )
        ]
    )

    return html.Div(
        id="app-container", 
        className="d-flex", 
        children=[
            store_components, 
            desktop_sidebar, 
            main_content, 
            mobile_sidebar
        ]
    )