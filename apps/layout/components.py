import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
import uuid
import json

def SystemMessage(content: str, with_spinner: bool = False) -> html.Div:
    """A component to render a system message."""
    
    children = [html.Span(content, className="ms-2")]
    if with_spinner:
        children.insert(0, dbc.Spinner())
        
    return html.Div(
        children,
        className="d-flex justify-content-center align-items-center h-100"
    )
    

def Wikitext(wikitext: str) -> html.Div:
    """A custom component to render wikitext with syntax highlighting."""
    container_id = f"wikitext-container-{uuid.uuid4()}"

    return html.Div(
        children=[
            html.Pre(html.Code(wikitext, id=container_id))
        ],
        className="highlight-container",
        style={"position": "relative"}
    )

def UserChatBubble(content: str) -> dbc.Alert:
    """A component to render a user chat bubble."""
    return dbc.Alert(
        dcc.Markdown(content),
        color="primary",
        style={
            "width": "fit-content",
            "maxWidth": "80%",
            "marginLeft": "auto",
            "marginRight": "0",
        },
        className="mb-2",
    )

def AgentChatBubble(author: str, content: str) -> html.Div:
    """A component to render an agent chat bubble."""
    author_div = html.Div(author, className="small text-secondary mb-1")
    return html.Div([
        author_div,
        dbc.Alert(
            dcc.Markdown(content),
            color="secondary",
            style={
                "maxWidth": "80%",
                "marginLeft": "0",
                "marginRight": "auto",
            },
            className="mb-2",
        )
    ])

def WikitextBubble(author: str, content: str) -> html.Div:
    """A component to render a wikitext bubble."""
    author_div = html.Div(author, className="small text-secondary mb-1")
    parts = content.split("```wiki")
    children = []
    for part in parts:
        if part.startswith("\n") and part.endswith("\n```"):
            wikitext = part.strip("\n```")
            children.append(Wikitext(wikitext))
        else:
            if part:
                children.append(dcc.Markdown(part))
    return html.Div([
        author_div,
        dbc.Alert(
            children,
            color="secondary",
            style={
                "maxWidth": "80%",
                "marginLeft": "0",
                "marginRight": "auto",
            },
            className="mb-2",
        )
    ])

def ToolCallBubble(author: str, tool_name: str, tool_input: str) -> html.Div:
    """A component to render a tool call bubble."""
    author_div = html.Div(author, className="small text-secondary mb-1")
    title = html.Div([
        html.I(className="bi bi-lightning-fill me-2"),
        tool_name
    ])
    if tool_name == 'transfer_to_agent':
        try:
            tool_input_json = json.loads(tool_input)
            agent_name = tool_input_json.get('agent_name', 'Agent')
            title = html.Div([
                html.I(className="bi bi-arrow-right-circle me-2"),
                html.Span(agent_name, className="fw-bold")
            ])
        except json.JSONDecodeError:
            title = html.Div([
                html.I(className="bi bi-arrow-right-circle me-2"),
                "Transfer to Agent"
            ])
    else:
        try:
            loaded_input = json.loads(tool_input)
            if isinstance(loaded_input, dict):
                inner_json_string = loaded_input.get('json_str')
                if isinstance(inner_json_string, str):
                    parsed_inner_json = json.loads(inner_json_string)
                    tool_input = json.dumps(parsed_inner_json, indent=2)
        except (json.JSONDecodeError, TypeError):
            pass

    accordion = dbc.Accordion([
        dbc.AccordionItem(
            html.Pre(html.Code(tool_input)),
            title=title
        ),
    ], start_collapsed=True, className="mb-2 w-75 tool-call-accordion")
    return html.Div([author_div, accordion])
