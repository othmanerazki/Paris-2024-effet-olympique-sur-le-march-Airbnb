from importation_données import charger_donnees_paris

dfs = charger_donnees_paris()

premier_mois = list(dfs.keys())[0]
print(f"--- {premier_mois} ---")
print(dfs[premier_mois].head(2))