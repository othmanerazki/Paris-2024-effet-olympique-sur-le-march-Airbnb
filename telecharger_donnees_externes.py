"""Télécharge les données qui prolongent la base Airbnb 2024 dans le temps.

Exécution : python telecharger_donnees_externes.py
Tout est enregistré dans donnees_externes/ (dossier exclu de git, environ 1,3 Go).

Sources (vérifiées le 21 novembre 2026) :
- Inside Airbnb : seuls les relevés des 12 derniers mois sont publics
  (novembre 2025 → septembre 2026) ; les plus anciens renvoient une erreur 403.
- Hugging Face : jeu kraina/airbnb_multicity (relevés résumés juin 2022 → mars 2023).
- Eurostat et INSEE : séries mensuelles agrégées, par API.
"""

import itertools
import json
from pathlib import Path
from urllib.request import urlopen, urlretrieve

import pandas as pd


DOSSIER = Path(__file__).resolve().parent / "donnees_externes"

INSIDE_AIRBNB = "https://data.insideairbnb.com/france/ile-de-france/paris/{date}/data/{fichier}"
RELEVES_INSIDE_AIRBNB = [
    "2025-11-12", "2025-12-13", "2026-01-17", "2026-02-18", "2026-03-21", "2026-04-19",
    "2026-05-23", "2026-06-16", "2026-07-15", "2026-08-15", "2026-09-16",
]

HUGGING_FACE = "https://huggingface.co/datasets/kraina/airbnb_multicity/resolve/main/data/all_airbnb.parquet"

# Nuitées réservées via Airbnb, Booking et Expedia, Île-de-France, par mois
EUROSTAT = (
    "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"
    "tour_ce_omn12?geo=FR10&c_resid=TOTAL&indic_to=NGT_SP"
)
# Hôtellerie à Paris : nuitées (milliers) et taux d'occupation (%)
INSEE = "https://bdm.insee.fr/series/sdmx/data/SERIES_BDM/010598705+010599005?startPeriod=2018-01"


def telecharger(url, chemin):
    """Télécharge url vers chemin, sauf si le fichier existe déjà."""
    if chemin.exists():
        return
    chemin.parent.mkdir(parents=True, exist_ok=True)
    print(f"Téléchargement : {chemin.relative_to(DOSSIER)}")
    urlretrieve(url, chemin)


def inside_airbnb():
    """Annonces de chaque relevé public, et avis du dernier relevé seulement :
    ce fichier contient déjà tous les avis depuis 2010."""
    for date in RELEVES_INSIDE_AIRBNB:
        telecharger(INSIDE_AIRBNB.format(date=date, fichier="listings.csv.gz"),
                    DOSSIER / "insideairbnb" / f"listings_{date}.csv.gz")
    dernier = RELEVES_INSIDE_AIRBNB[-1]
    telecharger(INSIDE_AIRBNB.format(date=dernier, fichier="reviews.csv.gz"),
                DOSSIER / "insideairbnb" / f"reviews_{dernier}.csv.gz")


def eurostat_mensuel():
    """Convertit la réponse JSON-stat d'Eurostat en tableau année × mois -> nuitées."""
    with urlopen(EUROSTAT) as reponse:
        d = json.load(reponse)
    dims, tailles = d["id"], d["size"]
    index = {k: d["dimension"][k]["category"]["index"] for k in dims}
    lignes = []
    for combinaison in itertools.product(*(index[k] for k in dims)):
        position = 0
        for k, valeur, taille in zip(dims, combinaison, tailles):
            position = position * taille + index[k][valeur]
        c = dict(zip(dims, combinaison))
        if c["month"] != "TOTAL" and str(position) in d["value"]:
            lignes.append({"annee": int(c["time"]), "mois": int(c["month"][1:]),
                           "nuitees": d["value"][str(position)]})
    return pd.DataFrame(lignes).sort_values(["annee", "mois"])


def series_agregees():
    telecharger(HUGGING_FACE, DOSSIER / "kraina_all_airbnb.parquet")
    eurostat_mensuel().to_csv(DOSSIER / "eurostat_nuitees_plateformes_idf.csv", index=False)
    telecharger(INSEE, DOSSIER / "insee_hotellerie_paris.xml")


if __name__ == "__main__":
    inside_airbnb()
    series_agregees()
    print(f"Données dans {DOSSIER}")
