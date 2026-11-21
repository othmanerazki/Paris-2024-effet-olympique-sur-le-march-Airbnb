import pandas as pd
from importation_données import charger_donnees_paris

dfs = charger_donnees_paris()

pd.set_option("display.max_columns", None)

premier_mois = list(dfs.keys())[0]
df = dfs[premier_mois]

print(f"--- Colonnes de {premier_mois} ---")
print(list(df.columns))

print(f"\n--- Première ligne de {premier_mois} ---")
print(df.iloc[0])