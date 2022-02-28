import pandas as pd
import geopandas as gpd

import streamlit as st


@st.cache()
def read_nuts(fp, epsg_from=4326, epsg_to=32633):
    nuts = gpd.read_file(fp,).set_index("id")
    nuts = nuts[nuts.LEVL_CODE == 3]
    nuts = nuts.set_crs(epsg=epsg_from).to_crs(epsg=epsg_to)

    # buffer to ensure inclusion of ports
    nuts.geometry = nuts.buffer(300)

    nuts_centroids = nuts.copy()
    nuts_centroids.geometry = nuts_centroids.geometry.centroid
    return nuts


@st.cache
def read_ports(fp, nuts, epsg_to=32633):

    ports = gpd.read_file(fp)
    ports = ports.to_crs(epsg=epsg_to)

    ports = ports.rename(columns={"PORT_ID": "id"}).set_index("id")

    ports = (
        ports.sjoin(nuts.reset_index()[["id", "geometry"]], predicate="within")
        .rename(columns={"id": "nuts"})
        .drop(columns=["index_right"])
    )

    ports["country"] = ports["nuts"].str[0:2]

    cols = ["nuts", "country", "geometry"]
    return ports[cols]


@st.cache()
def read_data(fp, ports):
    tmp = pd.read_excel(fp, sheet_name=list(range(7)))
    lookups = {}

    for m in tmp:
        df = tmp[m]
        df = df.set_index(df.columns[0]).squeeze()
        lookups[tmp[m].columns[0]] = df.to_dict()

    data = pd.read_excel(fp, sheet_name="DB")
    data["combined"] = ~data["origin_port"].isna()

    df["origin_nuts"] = df["origin_nuts"].replace(lookups["nuts"])
    df["destination_nuts"] = df["destination_nuts"].replace(lookups["nuts"])

    # df = df.replace("^GR", "EL", regex=True)
    df["origin_country"] = df["origin_nuts"].str[0:2]
    df["destination_country"] = df["destination_nuts"].str[0:2]

    nuts_to_ports = ports.reset_index().set_index("nuts")["id"].to_dict()
    df["origin_port"] = (
        df["origin_port"].replace(lookups["nuts"]).replace(nuts_to_ports)
    )
    df["destination_port"] = (
        df["destination_port"].replace(lookups["nuts"]).replace(nuts_to_ports)
    )

    for col in [
        "carriage_type",
        "package_type",
        "cargo_type",
        "cargo_group_type",
        "vehicle_type",
    ]:
        df[col] = df[col].replace(lookups[col])
        df[col] = df[col].astype("category")

    data.to_pickle(fp.replace(".xlsx", "-clean.pkl"))

    return data
