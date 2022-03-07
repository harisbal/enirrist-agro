import pandas as pd
import geopandas as gpd
import plotly.express as px
import dash
from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc

from src.io import fetch_data

dash.register_page(__name__)

data = fetch_data()
nuts = data["nuts"]
distr = data["distr"]
prods = data["prods"]
cons = data["cons"]

ods = data["ods"]


def layout():

    controls = dbc.Card(
        [
            dbc.CardBody(
                [
                    dbc.Card(
                        [
                            dbc.Card(
                                [dcc.Dropdown([2018], value=2018)],
                                className="mb-3",
                            ),
                            dbc.Card(
                                dcc.Dropdown(
                                    prods.index.unique("product_name").unique(),
                                    multi=True,
                                    id="input-products",
                                )
                            ),
                            dbc.Card(
                                dbc.RadioItems(
                                    options=[
                                        {"label": "Origins", "value": "origin"},
                                        {
                                            "label": "Destinations",
                                            "value": "destination",
                                        },
                                    ],
                                    value="origin",
                                    id="input-direction",
                                ),
                            ),
                        ]
                    ),
                ],
            )
        ]
    )

    layout = html.Div(
        [
            dbc.Row(
                [
                    dbc.Col(controls),
                ]
            ),
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Accordion(
                            [
                                dbc.AccordionItem(
                                    dbc.Row(
                                        [
                                            dbc.Col(
                                                dcc.Graph(
                                                    id="distr-map",
                                                    style={"height": "80vh"},
                                                ),
                                            ),
                                            dbc.Col(dcc.Graph(id="distr-heatmap")),
                                        ]
                                    ),
                                    title="Map",
                                ),
                            ],
                        )
                    ),
                ]
            ),
        ]
    )

    return layout


@callback(Output("distr-heatmap", "figure"), Input("input-products", "value"))
def update_heatmap(products):
    thresh = 10
    df = ods.loc[products or slice(None)].reset_index()

    df = df.groupby(["origin_nuts", "destination_nuts"]).sum().reset_index()
    df["origin_nuts"] = df["origin_nuts"].replace(nuts["NUTS_NAME"].to_dict())
    df["destination_nuts"] = df["destination_nuts"].replace(nuts["NUTS_NAME"].to_dict())
    df = df.groupby(["origin_nuts", "destination_nuts"]).sum()
    df = df[df > thresh].unstack()
    fig = px.imshow(df)
    return fig


@callback(
    Output("distr-map", "figure"),
    Input("distr-map", "clickData"),
    State("input-direction", "value"),
    State("input-products", "value"),
)
def update_map(click, direction, products):
    color = None
    odsf = ods.copy()
    if products:
        odsf = ods.loc[products]
    odsf = odsf.groupby(["origin_nuts", "destination_nuts"]).sum()

    if click:
        loc = click["points"][0]["location"]
        try:
            color = odsf.xs(loc, level=f"{direction}_nuts")
            color.index.name = "id"
        except KeyError:
            color = None

    nutsf = nuts[(nuts["LEVL_CODE"] == 3) & (nuts["CNTR_CODE"] == "EL")]
    bbox = nutsf.total_bounds
    center = {"lat": (bbox[1] + bbox[3]) / 2, "lon": (bbox[0] + bbox[2]) / 2}
    if not color is None:
        nutsf["color"] = nutsf.join(color, how="left")["quantity_tn"].fillna(0)
        color = "color"

    fig = px.choropleth_mapbox(
        nutsf,
        geojson=nutsf.geometry,
        locations=nutsf.index,
        color=color,
        center=center,
        zoom=6,
        mapbox_style="carto-positron",
    )

    return fig
