import dash
from dash import html, dcc
import uuid

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
