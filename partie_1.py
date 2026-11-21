import matplotlib

matplotlib.use("Agg")  # Mode sans affichage direct
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from importation_données import charger_donnees_paris


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


# --- EXÉCUTION ---
print("Chargement de tous les mois de l'année...")
dfs = charger_donnees_paris()

lat_jo = 48.8584
lon_jo = 2.2945

print("Génération du graphique comparatif...")
fig, ax = plt.subplots(figsize=(12, 8))

# On parcourt chaque mois chargé dans le dictionnaire
for mois, df in dfs.items():
  if df is not None and not df.empty:
    res = analyser_prix_par_distance(df, lat_jo, lon_jo)
    # matplotlib attribue automatiquement une couleur différente à chaque courbe
    ax.plot(
        res["tranche_km"],
        res["price_clean"],
        marker="o",
        linestyle="-",
        label=mois,
        alpha=0.8,
    )

ax.set_xlabel("Distance au site des JO (km)", fontsize=12)
ax.set_ylabel("Prix moyen (€)", fontsize=12)
ax.set_title(
    "Comparaison du prix moyen par tranche de distance - Tous les mois (Tour"
    " Eiffel)",
    fontsize=14,
)
ax.grid(True, linestyle="--", alpha=0.6)

# Placement de la légende proprement sur le côté pour ne pas cacher les courbes
ax.legend(title="Mois", bbox_to_anchor=(1.05, 1), loc="upper left")

# Sauvegarde de l'image globale
plt.savefig("graphique_tous_les_mois.png", bbox_inches="tight")
plt.close()

print("Graphique de tous les mois sauvegardé sous 'graphique_tous_les_mois.png' !")