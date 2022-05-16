import pandas as pd
import plotly.express as px
import dash
from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc

from src.io import fetch_data
from src.utils import rename_nuts

# dash.register_page(__name__)
dash.register_page(
    __name__,
    path="/distribution",
    name="distribution",
    description="Γεωγραφική Κατανομή",
    order=1,
    icon="fa fa-table",
)

data = fetch_data()
nuts = data["nuts"]
nutsf = nuts[(nuts["LEVL_CODE"] == 3) & (nuts["CNTR_CODE"] == "EL")]

distr = data["distr"]
prods = data["prods"]
cons = data["cons"]

ods = data["ods"]


def layout():

    controls = dbc.Card(
        [
            dbc.CardBody(
                [
                    dbc.Row(
                        [
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
                                    dbc.Label("Προελεύσεις/Προορισμοί"),
                                    dcc.Dropdown(
                                        options=[
                                            {
                                                "label": "Προελεύσεις",
                                                "value": "origin",
                                            },
                                            {
                                                "label": "Προορισμοί",
                                                "value": "destination",
                                            },
                                        ],
                                        value="origin",
                                        id="input-direction",
                                    ),
                                ],
                                width=2,
                            ),
                            dbc.Col(
                                [
                                    dbc.Label("Γεωγραφικές ενότητρες - NUTS"),
                                    dcc.Dropdown(
                                        options=nutsf.sort_values("NUTS_NAME")[
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
                                    dbc.Label("Προϊντα"),
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
            dbc.CardFooter(dbc.Button("Ενημέρωση", id="input-update")),
        ]
    )

    layout = html.Div(
        [
            dbc.Row(
                [
                    html.H2("Γεωφραφική κατανομή αγροτικών προϊοντων"),
                    html.H4("(Πίνακας προέλευσης προορισμού)"),
                ]
            ),
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Accordion(
                            [
                                dbc.AccordionItem(controls, title="Φίλτρα"),
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
                                                    dcc.Graph(
                                                        id="distr-map",
                                                        style={"height": "40vh"},
                                                    ),
                                                    width=3,
                                                ),
                                                dbc.Col(
                                                    dcc.Graph(
                                                        id="distr-barchart",
                                                        style={"height": "40vh"},
                                                    ),
                                                    width=5,
                                                ),
                                                dbc.Col(
                                                    dcc.Graph(
                                                        id="distr-heatmap",
                                                        style={"height": "50vh"},
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
    Output("distr-map", "figure"),
    Input("input-update", "n_clicks"),
    State("input-direction", "value"),
    State("input-products", "value"),
    State("input-nuts", "value"),
)
def update_map(click, direction, products, sel_nuts):
    color = None
    odcols = ["origin_nuts", "destination_nuts"]
    odsf = ods.copy()
    if products:
        odsf = ods.loc[products]
    odsf = odsf.groupby(odcols).sum()

    if sel_nuts:
        dfs = []
        for s in sel_nuts:
            try:
                df = odsf.xs(s, level=f"{direction}_nuts")
                df.index.name = "id"
                dfs.append(df)
            except KeyError:
                pass
        if dfs:
            color = pd.concat(dfs).groupby(df.index.name).sum()

    bbox = nutsf.total_bounds
    center = {"lat": (bbox[1] + bbox[3]) / 2, "lon": (bbox[0] + bbox[2]) / 2}
    if not color is None:
        nutsf["quantity_tn"] = nutsf.join(color, how="left")["quantity_tn"].fillna(0)
        color = "quantity_tn"

    nutsff = nutsf.loc[sel_nuts or slice(None)]
    fig_nuts = px.choropleth_mapbox(
        nutsff, geojson=nutsff.geometry, locations=nutsff.index, color=color
    )
    fig_nuts.update_traces(
        dict(marker=dict(line=dict(color="rgb(247, 150, 70)", width=3)))
    )

    fig = px.choropleth_mapbox(
        nutsf,
        geojson=nutsf.geometry,
        locations=nutsf.index,
        color=color,
        center=center,
        # fitbounds="geojson",
        zoom=5,
        mapbox_style="carto-positron",
    )

    fig.add_trace(fig_nuts.data[0])

    return fig


@callback(
    Output("distr-barchart", "figure"),
    Input("input-update", "n_clicks"),
    State("input-direction", "value"),
    State("input-nuts", "value"),
    State("input-products", "value"),
)
def update_barchart(click, direction, sel_nuts, products):
    cols = ["product_name", "origin_nuts", "destination_nuts"]
    odsf = ods.loc[products or slice(None)].groupby(cols).sum()
    dfs = []
    for s in sel_nuts or []:
        try:
            df = odsf.xs(s, level=f"{direction}_nuts")
            dfs.append(df)
        except KeyError:
            pass

    if dfs:
        df = pd.concat(dfs)
        df = df.groupby(list(df.index.names)).sum().squeeze().reset_index()
        nutscol = [c for c in df.columns if "_nuts" in c][0]
        df = rename_nuts(nuts, df, [nutscol], trim_len=15)
        fig = px.bar(
            df.sort_values("quantity_tn", ascending=False),
            x=nutscol,
            y="quantity_tn",
            color="product_name",
        )
        return fig
    else:
        return dash.no_update


@callback(
    Output("distr-heatmap", "figure"),
    Input("input-update", "n_clicks"),
    State("input-products", "value"),
)
def update_heatmap(click, products):
    thresh = 20
    cols = ["origin_nuts", "destination_nuts"]
    df = ods.loc[products or slice(None)].groupby(cols).sum().reset_index()
    df = rename_nuts(nuts, df, cols, trim_len=15)
    df = df.groupby(cols).sum().squeeze()
    df = df[df > thresh].unstack()
    fig = px.imshow(df)
    return fig


# @callback(
#     Output("distr-map", "figure"),
#     Input("distr-map", "clickData"),
#     State("input-direction", "value"),
#     State("input-products", "value"),
# )
# def update_map(click, direction, products):
#     color = None
#     odsf = ods.copy()
#     if products:
#         odsf = ods.loc[products]
#     odsf = odsf.groupby(["origin_nuts", "destination_nuts"]).sum()

#     if click:
#         loc = click["points"][0]["location"]
#         try:
#             color = odsf.xs(loc, level=f"{direction}_nuts")
#             color.index.name = "id"
#         except KeyError:
#             color = None

#     bbox = nutsf.total_bounds
#     center = {"lat": (bbox[1] + bbox[3]) / 2, "lon": (bbox[0] + bbox[2]) / 2}
#     if not color is None:
#         nutsf["color"] = nutsf.join(color, how="left")["quantity_tn"].fillna(0)
#         color = "color"

#     fig = px.choropleth_mapbox(
#         nutsf,
#         geojson=nutsf.geometry,
#         locations=nutsf.index,
#         color=color,
#         center=center,
#         zoom=6,
#         mapbox_style="carto-positron",
#     )

#     return fig
