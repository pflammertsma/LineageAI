import dash
from dash import html, dcc
import uuid

def Wikitext(wikitext: str) -> html.Div:
    """A custom component to render wikitext with syntax highlighting."""
    container_id = f"wikitext-container-{uuid.uuid4()}"
    button_id = f"wikitext-copy-button-{uuid.uuid4()}"

    dash.clientside_callback(
        """
        function(n_clicks, text) {
            if (n_clicks > 0) {
                navigator.clipboard.writeText(text);
            }
            return window.dash_clientside.no_update;
        }
        """,
        dash.Output(button_id, "n_clicks"),
        [dash.Input(button_id, "n_clicks"), dash.State(container_id, "innerText")]
    )

    return html.Div(
        children=[
            html.Button("Copy", id=button_id, className="copy-code-button"),
            html.Pre(html.Code(wikitext, id=container_id))
        ],
        className="highlight-container",
        style={"position": "relative"}
    )
