import streamlit as st
import pandas as pd
import geopandas as gpd
import pydeck as pdk
import plotly.express as px

from shapely.geometry import LineString

import src.io as myio
import src.helpers as helpers
import src.arcs


def create_centroids(nuts):
    centroids = nuts.copy()
    centroids.geometry = centroids.geometry.centroid
    return centroids


st.title("ENIRRIST")

epsgs = {"world": 4326, "proj": 32633}

fp = r"./data/boundaries/NUTS_RG_03M_2021_4326.json"
nuts = myio.read_nuts(fp, epsg_from=epsgs["world"], epsg_to=epsgs["proj"])
nuts_centroids = create_centroids(nuts)

fp = r"./data/PORT_2013_SH/Data/PORT_PT_2013.shp"
ports = myio.read_ports(fp, nuts, epsg_to=epsgs["proj"])

main_greek_ports = ["GRGPA", "GRPIR", "GRIGO", "GRSKG", "GRLVR"]

# Keep only the main greek ports
g = ports.loc[main_greek_ports]
mask = ports["country"] == "EL"
ports = pd.concat([ports.drop(ports[mask].index), g])

try:
    data = pd.read_pickle(r"./data/data-clean.pkl")
except:
    # Read data after filtering out the main ports
    fp = r"./data/data.xlsx"
    data = myio.read_data(fp, ports)

catch_area = helpers.create_catchment_area(ports, nuts_centroids)

df = data.copy()
unique_vehtypes = data["vehicle_type"].unique()

year_min = int(df["year"].min())
year_max = int(df["year"].max())
sel_years = st.sidebar.slider("Year range", year_min, year_min, (year_min, year_max))
sel_vehtypes = st.sidebar.multiselect(
    "Vehicle type", data["vehicle_type"].dropna().unique()
)
sel_combined = st.sidebar.checkbox("Combined")
sel_prodcosn = st.sidebar.radio(
    "Productions/Consumptions", ["production", "consumption"]
)
sel_port = st.sidebar.selectbox("port", main_greek_ports)

catch_areaf = catch_area.loc[sel_port:sel_port]

cols = [
    "origin_nuts",
    "destination_nuts",
    "origin_country",
    "destination_country",
    "origin_port",
    "destination_port",
    "loaded_weight_kg",
]

mask = (df["vehicle_type"].isin(sel_vehtypes or unique_vehtypes)) & (
    data["origin_port"] == sel_port
)
df = data[mask][cols]

# Filter the combined transports based on the 75/130/EEC directive
mask = df[["origin_port", "origin_nuts"]].apply(
    lambda x: x["origin_nuts"] in catch_areaf.get(x["origin_port"], []), axis=1
)
df = df[mask]

# arcs = src.arcs.create_arcs(nuts_centroids, epsgs)

dff = df[df["origin_country"] == "EL"]
dff = dff[dff["destination_country"] != "EL"]
dff = dff[dff["origin_port"] == sel_port]

# TODO FIX
dff = dff[dff["destination_port"].str[0:2] != "EL"]

if sel_prodcosn == "production":
    col = "origin_nuts"
else:
    col = "destination_nuts"

dff = dff.groupby(col)["loaded_weight_kg"].size()

n = nuts.copy()
dfp = n.join(dff, how="right")
dfp = dfp.to_crs(epsg=epsgs["world"])

dfp = dfp.dropna()

bbox = dfp.total_bounds
center = {"lat": (bbox[1] + bbox[3]) / 2, "lon": (bbox[0] + bbox[2]) / 2}

r = px.choropleth_mapbox(
    dfp,
    geojson=dfp.geometry,
    locations=dfp.index,
    color="loaded_weight_kg",
    center=center,
    zoom=5,
    width=1200,
    height=800,
    color_continuous_scale=px.colors.sequential.Reds[1:],
    mapbox_style="carto-positron",
)

st.plotly_chart(r, use_container_width=True)
