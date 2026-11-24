"""Courbes exploratoires : prix moyens en dollars par tranche de 1 km.

Les relevés suivent la liste explicite des cartes ; mars, doublon de juin,
est exclu. Les effectifs et médianes sont exportés pour contrôler les moyennes.
"""
import matplotlib

if __name__ == "__main__":
  matplotlib.use("Agg")
from pathlib import Path
import re
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from importation_données import FICHIERS, charger_annonces, charger_contours
from carte_sites_paris import preparer_population
import json
from shapely.geometry import shape
from shapely.ops import unary_union
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
  c = 2 * np.arcsin(np.sqrt(np.clip(a, 0, 1)))
  return R * c


def analyser_prix_par_distance(df, lat_site, lon_site):
  df = df.copy()
  df["price_clean"] = (
      df["price"].astype(str).str.replace(r"[^\d.\-]", "", regex=True)
  )
  df["price_clean"] = pd.to_numeric(df["price_clean"], errors="coerce")
  for colonne in ["latitude", "longitude"]:
    df[colonne] = pd.to_numeric(df[colonne], errors="coerce")
  df = df.loc[df["price_clean"].gt(0) & df["latitude"].between(-90, 90)
              & df["longitude"].between(-180, 180)].copy()
  df["distance_km"] = calculer_distance(
      df["latitude"], df["longitude"], lat_site, lon_site
  )
  df = df.dropna(subset=["price_clean", "distance_km"])
  df["tranche_km"] = np.floor(df["distance_km"]).astype(int)
  resultats = df.groupby("tranche_km")["price_clean"].agg(
      price_clean="mean", mediane="median", effectif="count").reset_index()
  return resultats


def nettoyer_nom_fichier(texte):
  texte_clean = re.sub(r"[^\w\s-]", "", texte).strip().lower()
  return re.sub(r"[-\s]+", "_", texte_clean)


def main():
  contours = charger_contours()
  paris = unary_union([shape(f["geometry"]) for f in contours])
  dfs = {mois: preparer_population(charger_annonces(mois), paris)[0] for mois in FICHIERS}
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
    controles = []

    for mois, df in dfs.items():
      if df is not None and not df.empty:
        res = analyser_prix_par_distance(df, lat, lon)
        if not res.empty:
          controles.append(res.assign(releve=mois, code_site=code))
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
    ax.set_ylabel("Prix moyen (dollars)", fontsize=12)
    ax.set_title(
        f"Prix moyen par tranche de distance — relevés mensuels 2024\nSite : {nom}"
        f" ({code})",
        fontsize=13,
    )
    ax.grid(True, linestyle="--", alpha=0.6)
    ax.legend(title="Mois", bbox_to_anchor=(1.05, 1), loc="upper left")

    nom_propre = nettoyer_nom_fichier(nom)
    nom_fichier = dossier_sortie / f"site_{code}_{nom_propre}.png"

    plt.savefig(nom_fichier, bbox_inches="tight")
    pd.concat(controles, ignore_index=True).to_csv(
        dossier_sortie / f"controle_distances_{code}.csv", index=False)
    plt.close()


if __name__ == "__main__":
  main()
