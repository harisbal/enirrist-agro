import pandas as pd
import geopandas as gpd
from app import cache

import pickle


@cache.memoize(timeout=60)
def fetch_data():

    try:
        with open("filename.pickle", "rb") as handle:
            data = pickle.load(handle)
    except FileNotFoundError:
        data = {}

        data["epsgs"] = {"world": 4326, "proj": 32633}

        fp = r"./assets/data/boundaries/NUTS_RG_03M_2021_4326.json"
        nuts = read_nuts(fp, data["epsgs"])
        data["nuts"] = nuts

        fp = r"./assets/data/boundaries/nuts-lookup.csv"
        nuts_lookup = read_nuts_lookup(fp)
        data["nuts_lookup"] = nuts_lookup

        fp = r"./assets/data/od-survey.xlsx"
        odsurv = read_odsurvey(fp, nuts_lookup)

        # f = 'Προϊόντα γεωργίας, θήρας και δασοκομίας, ψάρια και άλλα προϊόντα αλιείας' == 1
        odsurv = odsurv[odsurv["cargo_group_type"] == 1]
        odsurv = odsurv[
            (odsurv["origin_country"] == "EL") & (odsurv["destination_country"] == "EL")
        ]
        data["od-survey"] = odsurv

        distr = odsurv.groupby(["origin_nuts", "destination_nuts"], observed=True)[
            "loaded_weight_kg"
        ].sum()
        distr = distr[distr > 0]
        distr /= distr.sum()
        data["distr"] = distr

        productions = read_prodscons(r"./assets/data/productions.csv")
        consumptions = read_prodscons(r"./assets/data/consumptions.csv")
        data["prods"] = productions
        data["cons"] = consumptions

        with open("filename.pickle", "wb") as handle:
            pickle.dump(data, handle, protocol=pickle.HIGHEST_PROTOCOL)

    return data


def clean_od_survey(df, nuts_lookup):

    df["origin_nuts"] = df["origin_nuts"].replace(nuts_lookup)
    df["destination_nuts"] = df["destination_nuts"].replace(nuts_lookup)

    df["combined"] = ~df["origin_port"].isna()

    # df = df.replace("^GR", "EL", regex=True)
    df["origin_country"] = df["origin_nuts"].str[0:2]
    df["destination_country"] = df["destination_nuts"].str[0:2]

    cols = [
        "carriage_type",
        "package_type",
        "cargo_type",
        "cargo_group_type",
        "vehicle_type",
    ]
    for col in cols:
        df[col] = df[col].replace(nuts_lookup)
        df[col] = df[col].astype("category")
    return df


def clean_prodcons(df, cat_cols):
    for c in cat_cols:
        df[c] = df[c].astype("category")

    df["week"] = df["week"].str[1:].astype(int)

    for c in ["product_group", "product_name"]:
        df[c] = df[c].str.strip()

    df = df.groupby(["year", "week", "nuts", "product_group", "product_name"])[
        "quantity_tn"
    ].sum()
    return df


def read_nuts(fp, epsgs):
    nuts = gpd.read_file(fp).set_index("id")
    # nuts = nuts[nuts.LEVL_CODE==3]
    nuts = nuts.set_crs(epsg=epsgs["world"])  # .to_crs(epsg=epsgs["proj"])
    # nuts_centroids = nuts.copy()
    # nuts_centroids.geometry = nuts_centroids.geometry.centroid
    return nuts


def read_nuts_lookup(fp):
    df = pd.read_csv(fp, delimiter="\t")
    nuts_lookup = df.sort_values(["year", "old", "new"]).groupby("old")["new"].last()
    return nuts_lookup


def read_odsurvey(fp, nuts_lookup):
    # r'../data/od-survey.pkl'
    try:
        df = pd.read_pickle(fp.replace(".xlsx", ".pkl"))
    except:
        df = pd.read_excel(fp, sheet_name="DB")
        df = clean_od_survey(df, nuts_lookup)
        df.to_pickle(fp.replace(".xlsx", ".pkl"))

    return df


def read_prodscons(fp, year=None):
    # r'../data/productions.csv'
    df = pd.read_csv(fp, delimiter="\t", low_memory=False)
    df = clean_prodcons(df, cat_cols=["product_group", "product_name"])
    df = df[df > 0]
    if year:
        df = df.loc[year]
    return df
