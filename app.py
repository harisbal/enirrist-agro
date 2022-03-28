import dash
from dash import html, Output, Input, State, ALL
import dash_labs as dl
import dash_bootstrap_components as dbc

# from dash.long_callback import DiskcacheLongCallbackManager

# from flask_caching import Cache

from dash_bootstrap_templates import load_figure_template

# import diskcache
# cache = diskcache.Cache("./cache-directory")
# long_callback_manager = DiskcacheLongCallbackManager(cache)

dbc_css = (
    "https://cdn.jsdelivr.net/gh/AnnMarieW/dash-bootstrap-templates@V1.0.4/dbc.min.css"
)

load_figure_template("minty")

app = dash.Dash(
    __name__,
    plugins=[dl.plugins.pages],
    external_stylesheets=[dbc.themes.MINTY, dbc_css],
)

# cache = Cache(app.server, config={"CACHE_TYPE": "filesystem", "CACHE_DIR": "cache"})

dash.register_page("home", layout="We're home!", path="/")

navbar = dbc.NavbarSimple(
    [],
    brand="ENIRRIST / Εφαρμογή Αγροτικών προιόντων",
    color="primary",
    dark=True,
    className="mb-2",
)

navbuttons = dbc.ButtonGroup(
    [
        dbc.Button(
            page["name"],
            href=page["path"],
            outline=True,
            color="primary",
            id={"type": "nav", "index": page["name"]},
        )
        for page in dash.page_registry.values()
        if page["module"] != "pages.not_found_404"
    ],
)

app.layout = dbc.Container(
    [
        navbar,
        dbc.Row(navbuttons, justify="center"),
        dl.plugins.page_container,
    ],
    className="dbc",
    fluid=True,
)


@app.callback(
    Output({"type": "nav", "index": ALL}, "active"),
    Input({"type": "nav", "index": ALL}, "n_clicks_timestamp"),
)
def display_output(ts):
    ts = [t or 0 for t in ts]
    idxmax = ts.index(max(ts))
    active = [False] * len(ts)
    active[idxmax] = True
    return active


if __name__ == "__main__":
    app.run_server(debug=True)
