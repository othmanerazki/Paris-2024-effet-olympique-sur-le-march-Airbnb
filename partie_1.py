import matplotlib

matplotlib.use("Agg")  # Force matplotlib à travailler en mode "sans affichage"
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import s3fs
from urllib.parse import quote

# Fonction optimisée pour charger un seul mois à la demande
def charger_un_mois(mois_recherche="octobre"):
  fs = s3fs.S3FileSystem(
      anon=True, client_kwargs={"endpoint_url": "https://minio.lab.sspcloud.fr"}
  )
  files = fs.find("etiennealpy/données paris")

  for f in files:
    nom_fichier = f.split("/")[-1].lower()
    if "listing_" in nom_fichier and mois_recherche in nom_fichier:
      url = f"https://minio.lab.sspcloud.fr/{quote(f, safe='/')}"
      print(f"Téléchargement de {nom_fichier} en cours...")
      return pd.read_csv(url)

  return None


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


def analyser_prix_par_distance(df, lat_jo, lon_jo):
  df = df.copy()
  df["price_clean"] = (
      df["price"].astype(str).str.replace(r"[^\d.]", "", regex=True)
  )
  df["price_clean"] = pd.to_numeric(df["price_clean"], errors="coerce")
  df["distance_km"] = calculer_distance(
      df["latitude"], df["longitude"], lat_jo, lon_jo
  )
  df = df.dropna(subset=["price_clean", "distance_km"])
  df["tranche_km"] = np.floor(df["distance_km"]).astype(int)
  resultats = df.groupby("tranche_km")["price_clean"].mean().reset_index()
  return resultats


# test sur la tour eiffel
df_octobre = charger_un_mois("octobre")

if df_octobre is not None:
  lat_jo = 48.8584
  lon_jo = 2.2945

  print("Calcul des distances et moyennes...")
  res = analyser_prix_par_distance(df_octobre, lat_jo, lon_jo)

  # Affichage des données dans le terminal pour vérification
  print("Données prêtes à être tracées :")
  print(res.head(10))

  print("Enregistrement du graphique...")
  fig, ax = plt.subplots(figsize=(10, 6))

  ax.plot(res["tranche_km"], res["price_clean"], marker="o", linestyle="-")
  ax.set_xlabel("Distance au site des JO (km)")
  ax.set_ylabel("Prix moyen (€)")
  ax.set_title("Prix moyen par tranche de distance - Octobre (Tour Eiffel)")
  ax.grid(True)


  plt.savefig("graphique_eiffel_octobre_v2.png", bbox_inches="tight")
  plt.close()

  print("Graphique sauvegardé avec succès sous graphique_eiffel_octobre_v2.png !")
else:
  print("Erreur : Fichier d'octobre introuvable.")