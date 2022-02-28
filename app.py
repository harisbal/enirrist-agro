import dash
import dash_labs as dl
import dash_bootstrap_components as dbc

# from dash.long_callback import DiskcacheLongCallbackManager

from flask_caching import Cache

# import diskcache
# cache = diskcache.Cache("./cache-directory")
# long_callback_manager = DiskcacheLongCallbackManager(cache)

dbc_css = (
    "https://cdn.jsdelivr.net/gh/AnnMarieW/dash-bootstrap-templates@V1.0.4/dbc.min.css"
)

app = dash.Dash(
    __name__,
    plugins=[dl.plugins.pages],
    external_stylesheets=[dbc.themes.BOOTSTRAP, dbc_css],
)

cache = Cache(app.server, config={"CACHE_TYPE": "filesystem", "CACHE_DIR": "cache"})

dash.register_page("home", layout="We're home!", path="/")

navbar = dbc.NavbarSimple(
    dbc.DropdownMenu(
        [
            dbc.DropdownMenuItem(page["name"], href=page["path"])
            for page in dash.page_registry.values()
            if page["module"] != "pages.not_found_404"
        ],
        nav=True,
        label="More Pages",
    ),
    brand="Multi Page App Plugin Demo",
    color="primary",
    dark=True,
    className="mb-2",
)

app.layout = dbc.Container(
    [
        navbar,
        dl.plugins.page_container,
    ],
    className="dbc",
    fluid=True,
)


if __name__ == "__main__":
    app.run_server(debug=True)
