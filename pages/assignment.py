import pandas as pd
import geopandas as gpd

import plotly.express as px
import dash
from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc

from src.io import fetch_data
from src.utils import rename_nuts, pairwise

dash.register_page(__name__)

data = fetch_data()
epsgs = data["epsgs"]
nuts = data["nuts"]
nuts = nuts[(nuts["LEVL_CODE"] == 3) & (nuts["CNTR_CODE"] == "EL")]

prods = data["prods"]
ods = data["ods"]
net = data["net"]
links = data["links"]
spaths = data["spaths"]


def layout():

    controls = dbc.Card(
        [
            dbc.CardBody(
                [
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.Label("Year"),
                                    dbc.Select(
                                        id="input-year",
                                        options=[
                                            {"label": "2018", "value": 2018},
                                        ],
                                        value=2018,
                                    ),
                                ],
                                width=2,
                            ),
                            dbc.Col(
                                [
                                    dbc.Label("NUTS"),
                                    dcc.Dropdown(
                                        options=nuts.sort_values("NUTS_NAME")[
                                            "NUTS_NAME"
                                        ].to_dict(),
                                        multi=True,
                                        id="input-nuts",
                                    ),
                                ]
                            ),
                        ],
                    ),
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.Label("Products"),
                                    dcc.Dropdown(
                                        options=prods.index.unique(
                                            level="product_name"
                                        ),
                                        multi=True,
                                        id="input-products",
                                    ),
                                ]
                            ),
                        ]
                    ),
                ],
            ),
            dbc.CardFooter(dbc.Button("Update", id="input-update")),
        ]
    )

    layout = html.Div(
        [
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Accordion(
                            [
                                dbc.AccordionItem(controls, title="Controls"),
                            ]
                        )
                    ),
                ],
                class_name="py-2",
            ),
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Accordion(
                            [
                                dbc.AccordionItem(
                                    [
                                        dbc.Row(
                                            [
                                                dbc.Col(
                                                    dbc.Spinner(
                                                        dcc.Graph(
                                                            id="assign-map",
                                                            style={
                                                                "height": "40vh",
                                                                # "width": "100vh",
                                                            },
                                                        )
                                                    ),
                                                    width=4,
                                                ),
                                            ],
                                            justify="center",
                                        )
                                    ],
                                    title="Visuals",
                                ),
                            ],
                        )
                    ),
                ],
                class_name="py-2",
            ),
        ]
    )

    return layout


@callback(
    Output("assign-map", "figure"),
    Input("input-update", "n_clicks"),
    State("input-nuts", "value"),
    State("input-products", "value"),
)
def update_map(click, sel_nuts, products):

    # osmnuts = nuts.reset_index(drop=False).groupby("osmid").last()

    color = None
    odcols = ["origin_nuts", "destination_nuts"]
    odsf = ods.copy()
    if products:
        odsf = ods.loc[products]
    odsf = odsf.groupby(odcols).sum().sort_index()

    dfs = []
    for k, vol in odsf.iteritems():
        src, tgt = k
        src = nuts.at[src, "osmid"]
        tgt = nuts.at[tgt, "osmid"]

        if src == tgt:
            continue

        try:
            path = spaths.at[(src, tgt)].to_frame(name="osmid")
            path.loc[:, "volume"] = vol
            dfs.append(path)
        except KeyError:
            continue

    vols = pd.concat(dfs).groupby("osmid")["volume"].sum()
    vols = vols[vols > 0]

    dfp = links.set_index("osmid").join(vols, how="right")
    dfp = dfp.dropna(subset=["geometry"])
    dfp = gpd.GeoDataFrame(dfp, geometry=dfp.geometry).set_crs(epsg=epsgs["world"])
    dfp = dfp.to_crs(epsg=epsgs["proj"])
    dfp.geometry = dfp.buffer(2000)
    dfp = dfp.to_crs(epsg=epsgs["world"])

    bbox = nuts.total_bounds
    center = {"lat": (bbox[1] + bbox[3]) / 2, "lon": (bbox[0] + bbox[2]) / 2}

    fig = px.choropleth_mapbox(
        dfp,
        geojson=dfp.geometry,
        locations=dfp.index,
        color="volume",
        center=center,
        mapbox_style="carto-positron",
        zoom=10,
    )

    fig.update_traces(marker=dict(line=dict(width=0)))
    # fig.update_geos(fitbounds="geojson", visible=False)
    # fig.add_trace(fig_nuts.data[0])

    return fig
