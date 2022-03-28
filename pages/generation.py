import pandas as pd
import geopandas as gpd
import plotly.express as px
import dash
from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
from src.io import fetch_data

# dash.register_page(__name__)
dash.register_page(
    __name__,
    path="/generation",
    name="generation",
    description="Παραγωγή/Κατανάλωση",
    order=0,
    icon="fa fa-farm",
)


data = fetch_data()
nuts = data["nuts"]
distr = data["distr"]
prods = data["prods"]
cons = data["cons"]

nuts = nuts[(nuts["LEVL_CODE"] == 3) & (nuts["CNTR_CODE"] == "EL")]


def layout():

    controls = dbc.Card(
        [
            dbc.CardBody(
                [
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.Label("Παραγωγές/Ηαταναλώσεις"),
                                    dcc.Dropdown(
                                        options=[
                                            {
                                                "label": "Παραγωγές",
                                                "value": "production",
                                            },
                                            {
                                                "label": "Καταναλώσεις",
                                                "value": "consumption",
                                            },
                                        ],
                                        value="production",
                                        id="input-direction",
                                    ),
                                ],
                                width=2,
                            ),
                            dbc.Col(
                                [
                                    dbc.Label("Έτος"),
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
                                    dbc.Label("Περίοδος ανάλυσης"),
                                    dcc.RangeSlider(
                                        min=1,
                                        max=12,
                                        value=(1, 12),
                                        step=1,
                                        id="input-months",
                                    ),
                                ]
                            ),
                        ],
                    ),
                    dbc.Row(
                        dbc.Col(
                            [
                                dbc.Label("Γεωγραφικές ενότητρες - NUTS"),
                                dcc.Dropdown(
                                    options=nuts.sort_values("NUTS_NAME")[
                                        "NUTS_NAME"
                                    ].to_dict(),
                                    multi=True,
                                    id="input-nuts",
                                ),
                            ]
                        )
                    ),
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dbc.Label("Ομαδοποίηση προϊόντων"),
                                    dcc.Dropdown(
                                        [
                                            {
                                                "label": "Ομάδες",
                                                "value": "product_group",
                                            },
                                            {
                                                "label": "Ξεχωριστά",
                                                "value": "product_name",
                                            },
                                        ],
                                        value="product_group",
                                        id="input-products-type",
                                    ),
                                ],
                                width=2,
                            ),
                            dbc.Col(
                                [
                                    dbc.Label("Προϊόντα"),
                                    dcc.Dropdown(
                                        multi=True,
                                        id="input-products",
                                    ),
                                ]
                            ),
                        ]
                    ),
                ],
            ),
            dbc.CardFooter(dbc.Button("Ενημέρωση", id="input-update")),
        ]
    )

    layout = (
        html.Div(
            [
                dbc.Row(
                    [
                        dbc.Col(
                            dbc.Accordion(dbc.AccordionItem(controls, title="Controls"))
                        ),
                    ],
                    class_name="py-2",
                ),
                dbc.Card(
                    dbc.CardBody(
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        dbc.Row(
                                            [
                                                dbc.Label("Ανάλυση κατά:"),
                                                dbc.RadioItems(
                                                    options=[
                                                        {
                                                            "label": "Χρόνο",
                                                            "value": "date",
                                                        },
                                                        {
                                                            "label": "Γεωγραφικές ενότητες",
                                                            "value": "nuts",
                                                        },
                                                    ],
                                                    value="nuts",
                                                    inline=True,
                                                    id="input-graph-type",
                                                ),
                                            ]
                                        ),
                                        dbc.Row(dcc.Graph(id="gen-graph")),
                                    ],
                                    width=8,
                                ),
                                dbc.Col(
                                    dcc.Graph(
                                        style={"height": "100%"},
                                        id="gen-map",
                                    ),
                                    width=4,
                                ),
                            ],
                        )
                    ),
                    class_name="my-2",
                ),
            ]
        ),
    )

    return layout


@callback(Output("input-products", "options"), Input("input-products-type", "value"))
def change_products_type(products_type):
    if products_type:
        return prods.index.unique(products_type)
    else:
        return dash.no_update


@callback(
    Output("gen-graph", "figure"),
    Output("gen-map", "figure"),
    Input("input-update", "n_clicks"),
    Input("input-graph-type", "value"),
    State("input-direction", "value"),
    State("input-year", "value"),
    State("input-months", "value"),
    State("input-nuts", "value"),
    State("input-products-type", "value"),
    State("input-products", "value"),
)
def update_view(
    n, graph_type, direction, year, months, sel_nuts, products_type, products
):

    if direction == "production":
        df = prods.copy()
    else:
        df = cons.copy()

    df = (
        df.groupby(["date", "nuts", products_type])
        .sum()
        .loc[
            f"{year}-{months[0]}-1":f"{year}-{months[1]}-28",
            sel_nuts or slice(None),
            products or slice(None),
        ]
    )

    df_map = df.groupby("nuts").sum()
    nutsf = pd.merge(
        df_map,
        nuts.rename_axis(index={"id": "nuts"}).geometry,
        left_index=True,
        right_index=True,
        how="left",
    )

    nutsf = gpd.GeoDataFrame(nutsf, geometry=nutsf.geometry)
    # nutsf = nuts.loc[prodsf.index.unique("nuts")]
    bbox = nutsf.total_bounds
    center = {"lat": (bbox[1] + bbox[3]) / 2, "lon": (bbox[0] + bbox[2]) / 2}

    map = px.choropleth_mapbox(
        nutsf,
        geojson=nutsf.geometry,
        locations=nutsf.index,
        color="quantity_tn",
        center=center,
        zoom=5,
        mapbox_style="carto-positron",
    )

    dfp = df.groupby([graph_type, products_type]).sum().reset_index()

    if graph_type == "nuts":
        dfp["nuts"] = dfp["nuts"].replace(nuts["NUTS_NAME"].to_dict()).str[0:20]

    graph = px.bar(
        dfp,
        x=graph_type,
        y="quantity_tn",
        color=products_type,
    )

    graph.update_layout(
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    return graph, map
