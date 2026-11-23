"""Télécharge les relevés Inside Airbnb 2026 utilisés par regression_sur_le_prix.ipynb.

Exécution : python telecharger_donnees_externes.py
Tout est enregistré dans donnees_externes/insideairbnb/ (dossier exclu de git, environ 150 Mo).

Source (vérifiée le 21 novembre 2026) : relevés publics Inside Airbnb de juin à septembre 2026,
année de comparaison « sans Jeux ». Seuls les relevés des 12 derniers mois sont publics ;
les plus anciens renvoient une erreur 403.
"""

from pathlib import Path
from urllib.request import urlretrieve


DOSSIER = Path(__file__).resolve().parent / "donnees_externes"

INSIDE_AIRBNB = "https://data.insideairbnb.com/france/ile-de-france/paris/{date}/data/listings.csv.gz"
RELEVES_INSIDE_AIRBNB = ["2026-06-16", "2026-07-15", "2026-08-15", "2026-09-16"]


def telecharger(url, chemin):
    """Télécharge url vers chemin, sauf si le fichier existe déjà."""
    if chemin.exists():
        return
    chemin.parent.mkdir(parents=True, exist_ok=True)
    print(f"Téléchargement : {chemin.relative_to(DOSSIER)}")
    urlretrieve(url, chemin)


def inside_airbnb():
    """Annonces des relevés de l'été 2026."""
    for date in RELEVES_INSIDE_AIRBNB:
        telecharger(INSIDE_AIRBNB.format(date=date), DOSSIER / "insideairbnb" / f"listings_{date}.csv.gz")


if __name__ == "__main__":
    inside_airbnb()
    print(f"Données dans {DOSSIER}")
