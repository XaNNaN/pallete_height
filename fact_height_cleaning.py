import pandas as pd
from icecream import ic
# Enable to see outputs
# ic.disable()


pd.set_option('display.max_columns', 500)
pd.set_option('display.width', 1000)

raw_fact_height_df = pd.read_excel("fact_pallet_height_raw.xls", index_col=0)
ic(raw_fact_height_df.head(10))
unique_fact_height_df = raw_fact_height_df.drop_duplicates(subset=["INVOICE_ID", "PALLET_NO"])
ic(unique_fact_height_df.head(10))
clean_fact_height = unique_fact_height_df[["INVOICE_ID", "PALLET_NO", "PALLETE_HEIGHT_FACT"]]
ic(clean_fact_height.head(10))

clean_fact_height.to_excel("clean_fact_height.xlsx")