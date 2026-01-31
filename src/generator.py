import pandas as pd

def load_adj_pool(path="data/words_adj.csv"):
    df = pd.read_csv(path)
    return df[df["pos"].isin(["i_adj", "na_adj"])].reset_index(drop=True)
