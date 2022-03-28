from itertools import tee


def pairwise(iterable):
    a, b = tee(iterable)
    next(b, None)
    return zip(a, b)


def rename_nuts(nuts, df, cols, trim_len):
    for c in cols:
        df[c] = df[c].replace(nuts["NUTS_NAME"].to_dict())

    if trim_len:
        for c in cols:
            df[c] = df[c].str[0:trim_len]
    return df
