import matplotlib

matplotlib.use("Agg")
from pathlib import Path
import re
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from importation_données import charger_donnees_paris
from sites_competition import charger_tables_locales, garder_sites_paris


def calculer_distance(lat1, lon1, lat2, lon2):
  R = 6371.0
  lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
  dlon = lon2 - lon1
  dlat = lat2 - lat1
  a = (
      np.sin(dlat / 2.0) ** 2
      + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2.0) ** 2
  )
  c = 2 * np.arcsin(np.sqrt(a))
  return R * c


def analyser_prix_par_distance(df, lat_site, lon_site):
  df = df.copy()
  df["price_clean"] = (
      df["price"].astype(str).str.replace(r"[^\d.]", "", regex=True)
  )
  df["price_clean"] = pd.to_numeric(df["price_clean"], errors="coerce")
  df["distance_km"] = calculer_distance(
      df["latitude"], df["longitude"], lat_site, lon_site
  )
  df = df.dropna(subset=["price_clean", "distance_km"])
  df["tranche_km"] = np.floor(df["distance_km"]).astype(int)
  resultats = df.groupby("tranche_km")["price_clean"].mean().reset_index()
  return resultats


def nettoyer_nom_fichier(texte):
  texte_clean = re.sub(r"[^\w\s-]", "", texte).strip().lower()
  return re.sub(r"[-\s]+", "_", texte_clean)


def main():
  dfs = charger_donnees_paris()
  olympiques, _ = charger_tables_locales()
  sites_paris = garder_sites_paris(olympiques)

  dossier_sortie = Path("graphiques_sites_paris_tous_les_mois")
  dossier_sortie.mkdir(exist_ok=True)

  sites_uniques = sites_paris.drop_duplicates(subset=["code_site"])

  for _, row in sites_uniques.iterrows():
    code = row["code_site"]
    nom = row["nom_site"]
    lat = row["latitude"]
    lon = row["longitude"]

    if pd.isna(lat) or pd.isna(lon):
      continue

    fig, ax = plt.subplots(figsize=(12, 8))
    courbes_tracees = 0

    for mois, df in dfs.items():
      if df is not None and not df.empty:
        res = analyser_prix_par_distance(df, lat, lon)
        if not res.empty:
          ax.plot(
              res["tranche_km"],
              res["price_clean"],
              marker="o",
              linestyle="-",
              label=mois,
              alpha=0.7,
          )
          courbes_tracees += 1

    if courbes_tracees == 0:
      plt.close()
      continue

    ax.set_xlabel("Distance au site (km)", fontsize=12)
    ax.set_ylabel("Prix moyen (€)", fontsize=12)
    ax.set_title(
        f"Prix moyen par tranche de distance - Tous les mois\nSite : {nom}"
        f" ({code})",
        fontsize=13,
    )
    ax.grid(True, linestyle="--", alpha=0.6)
    ax.legend(title="Mois", bbox_to_anchor=(1.05, 1), loc="upper left")

    nom_propre = nettoyer_nom_fichier(nom)
    nom_fichier = dossier_sortie / f"site_{code}_{nom_propre}.png"

    plt.savefig(nom_fichier, bbox_inches="tight")
    plt.close()


if __name__ == "__main__":
  main()