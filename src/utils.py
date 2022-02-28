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
    g["quantity_tn_prod"] *= g["quantity_tn_cons"].sum() / g["quantity_tn_prod"].sum()
    dfs.append(g)
df = pd.concat(dfs)

prods = df.groupby(["product_name", "nuts"])["quantity_tn_prod"].sum()
prods
prods.name = "quantity_tn"
cons = df.groupby(["product_name", "nuts"])["quantity_tn_cons"].sum()
cons.name = "quantity_tn"

nuts_el = nuts[(nuts["LEVL_CODE"] == 3) & (nuts["CNTR_CODE"] == "EL")]

seeds = {}
pairs = list(itertools.product(nuts_el.index, repeat=2))
products = cons.index.unique("product_name")

for p in products:
    seeds[p] = {}
    for pair in pairs:
        src, tgt = pair
        try:
            seeds[p][pair] = prods.loc[p, src] * cons.loc[p, tgt] * distr.loc[pair]
        except KeyError:
            continue
