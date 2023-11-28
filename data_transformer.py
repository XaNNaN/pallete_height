import pandas as pd
from icecream import ic
# Enable to see outputs
ic.disable()

pd.set_option('display.max_columns', 500)
pd.set_option('display.width', 1000)

raw_df = pd.read_excel("raw_fact_data_28_11.xlsx", index_col=0)
raw_df.drop(columns=["CLIENT_ORDER_NO", "CLIENT_ORDER_DATE"], inplace=True)
groups = raw_df.groupby(by=["INVOICE_ID", "PALLET_NO", "PACK_TYPE"])
s_grouped = groups["CASES"].sum()
ic(raw_df.head(10))
ic(s_grouped.head(10))
ic(type(s_grouped))

raw_df = raw_df.drop_duplicates(subset=["INVOICE_ID", "PALLET_NO", "PACK_TYPE"])
nice_df = raw_df.drop(columns=["CASES"]).merge(s_grouped, on=["PACK_TYPE", "PALLET_NO", "INVOICE_ID"])
ic(nice_df.head(15))

only_small = raw_df[raw_df["PALLETE_HEIGHT_FACT"] == 1]
ic(only_small)
danger = only_small[["ULTIMATE_CUSTOMER_GLN", "INVOICE_DATE"]]
ic(danger)

in_danger = nice_df.merge(danger, on=["ULTIMATE_CUSTOMER_GLN", "INVOICE_DATE"])
ic(in_danger)

nice_df = nice_df[nice_df["INVOICE_ID"].map(lambda x:  x not in in_danger.INVOICE_ID.unique())]
ic(in_danger.INVOICE_ID.unique())
ic(291416 in in_danger.INVOICE_ID.unique())
nice_df.drop(columns=["ULTIMATE_CUSTOMER_GLN", "INVOICE_DATE"], inplace=True)
nice_df.to_excel("ready_fact_data_28_11.xlsx")
