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

cols = ["product_name", "nuts"]
prods = data["prods"].groupby(cols).sum()
cons = data["cons"].groupby(cols).sum()


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
                                                    id="map-prods",
                                                    style={"height": "80vh"},
                                                ),
                                                width=6,
                                            ),
                                            dbc.Col(
                                                dcc.Graph(
                                                    id="map-cons",
                                                    style={"height": "80vh"},
                                                ),
                                                width=6,
                                            ),
                                        ]
                                    ),
                                    title="Maps",
                                ),
                                dbc.AccordionItem(html.Div()),
                            ],
                        )
                    ),
                ]
            ),
        ]
    )

    return layout


@callback(
    Output("map-prods", "figure"),
    Output("map-cons", "figure"),
    Input("input-products", "value"),
)
def update_map(products):

    figs = []
    for df in [prods, cons]:
        dff = df.copy()
        if products:
            dff = df.loc[products]

        dff = dff.groupby("nuts").sum()

        nutsf = pd.merge(
            dff,
            nuts.rename_axis(index={"id": "nuts"}).geometry,
            left_index=True,
            right_index=True,
            how="left",
        )

        nutsf = gpd.GeoDataFrame(nutsf, geometry=nutsf.geometry)
        # nutsf = nuts.loc[prodsf.index.unique("nuts")]
        bbox = nutsf.total_bounds
        center = {"lat": (bbox[1] + bbox[3]) / 2, "lon": (bbox[0] + bbox[2]) / 2}

        fig = px.choropleth_mapbox(
            nutsf,
            geojson=nutsf.geometry,
            locations=nutsf.index,
            color="quantity_tn",
            center=center,
            zoom=5,
            mapbox_style="carto-positron",
        )

        figs.append(fig)

    return figs[0], figs[1]
