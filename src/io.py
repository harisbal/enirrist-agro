import itertools
import pandas as pd
import geopandas as gpd
from fuzzywuzzy import process

# from app import cache

import pickle


# @cache.memoize(timeout=3600)
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

        # TODO move approprietly
        # Initiate furness
        cols = ["product_name", "nuts"]
        prods = productions.groupby(cols).sum()
        cons = consumptions.groupby(cols).sum()

        # Normalise based on consumption
        df = pd.merge(
            prods,
            cons,
            how="inner",
            left_index=True,
            right_index=True,
            suffixes=("_prod", "_cons"),
        )

        dfs = []
        for k, g in df.groupby("product_name"):
            g["quantity_tn_prod"] *= (
                g["quantity_tn_cons"].sum() / g["quantity_tn_prod"].sum()
            )
            dfs.append(g)
        df = pd.concat(dfs)

        prods = df.groupby(["product_name", "nuts"])["quantity_tn_prod"].sum()
        prods.name = "quantity_tn"
        cons = df.groupby(["product_name", "nuts"])["quantity_tn_cons"].sum()
        cons.name = "quantity_tn"

        nuts_el = nuts[(nuts["LEVL_CODE"] == 3) & (nuts["CNTR_CODE"] == "EL")]

        friction = pd.read_csv(
            r"./assets/data/friction/exponential_function_74.csv", delimiter="\t"
        )
        friction.index = friction.columns.tolist()
        friction.index.name = "origin_nuts"
        friction.columns.name = "destination_nuts"
        d = (
            nuts[(nuts["LEVL_CODE"] == 3) & (nuts["CNTR_CODE"] == "EL")]
            .set_index("NUTS_NAME")["NUTS_ID"]
            .to_dict()
        )

        l = friction.columns.tolist()
        dd = {}
        for e in l:
            n, v = process.extractOne(e, list(d.keys()))
            dd[e] = n

        friction = (
            friction.rename(columns=dd, index=dd).rename(columns=d, index=d).stack()
        )
        friction = friction.groupby(["origin_nuts", "destination_nuts"]).mean()
        friction

        seeds = {}
        pairs = list(itertools.product(nuts_el.index, repeat=2))
        products = cons.index.unique("product_name")

        for p in products:
            seeds[p] = {}
            for pair in pairs:
                src, tgt = pair
                try:
                    seeds[p][pair] = (
                        prods.loc[p, src] * cons.loc[p, tgt] * distr.loc[pair]
                    )
                except KeyError:
                    continue

        seed = pd.DataFrame(seeds).stack()
        cols = ["origin_nuts", "destination_nuts", "product_name"]
        seed.index.names = cols
        seed.name = "quantity_tn"

        # TODO think about
        seed = (
            seed.unstack("destination_nuts")
            .fillna(0.001)
            .stack("destination_nuts")
            .groupby(cols)
            .sum()
        )

        ms = []

        tol = 0.05

        prods = prods.rename_axis(index={"nuts": "origin_nuts"})
        cons = cons.rename_axis(index={"nuts": "destination_nuts"})

        # conv = {}

        for k, m in seed.groupby("product_name"):
            m = seed.xs(k, level="product_name")

            constrs = itertools.cycle(
                [prods.xs(k, level="product_name"), cons.xs(k, level="product_name")]
            )
            n = 0
            while n <= 500:
                constr = next(constrs)

                grps = constr.index.names
                f = constr / m.groupby(grps).sum()

                if (1 - f).abs().max() <= tol:
                    break

                # todo unstacking is not safe
                cols_unstack = list(set(m.index.names) - set(f.index.names))

                if len(constr.index.names) > 1:
                    m = (
                        m.unstack(cols_unstack)
                        .reorder_levels(constr.index.names)
                        .mul(f, axis=0)
                        .stack(cols_unstack)
                    )
                else:
                    m = m.unstack(cols_unstack).mul(f, axis=0).stack(cols_unstack)

                n += 1
                if n == 501:
                    print(f"{k} not converged")
                # conv[(k, '-'.join(list(grps)))] = f

            m.name = "quantity_tn"
            m = m.to_frame()
            m["product_name"] = k
            m = m.groupby(seed.index.names).sum().squeeze()
            ms.append(m)

        ods = (
            pd.concat(ms)
            .groupby(["product_name", "origin_nuts", "destination_nuts"])
            .sum()
        )

        data["ods"] = ods

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
    df["day"] = df["week"] * 7
    df["date"] = pd.to_datetime(df["year"], format="%Y") + pd.to_timedelta(
        df["day"], unit="D"
    )

    for c in ["product_group", "product_name"]:
        df[c] = df[c].str.strip()

    df = df.groupby(["date", "nuts", "product_group", "product_name"])[
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
