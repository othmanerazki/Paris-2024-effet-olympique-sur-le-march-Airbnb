"""Récupère les sites de compétition des Jeux olympiques et paralympiques 2024.

Source : ministère chargé des Sports, via data.gouv.fr, Licence Ouverte 2.0.
Chaque ligne de la source est conservée : un site peut apparaître plusieurs fois.
"""

from io import BytesIO
from pathlib import Path
from urllib.request import urlopen

import pandas as pd


URL_SOURCE = "https://www.data.gouv.fr/api/1/datasets/r/5a0599d1-ad3f-42d1-b64c-204ee19cf520"
DOSSIER_SORTIE = Path(__file__).resolve().parent / "donnees_sites"

# Corrections d'après les épreuves effectivement tenues ; les dates d'origine
# restent disponibles dans les colonnes date_debut_source et date_fin_source.
# Golf : les tournois ont eu lieu en août, pas en septembre.
# https://www.ffgolf.org/golf-pro/jeux-olympiques/actualites/jeux-olympiques-le-golf-national-a-brule-pour-la-flamme
# BMX : les courses ont eu lieu les 1er et 2 août.
# https://fr.uci.org/article/jeux-olympiques-de-paris-2024-qui-sont-les-potentiels-champions-olympiques/4neOsDdP6C1S44tke48VSG
# Concorde : cérémonie d'ouverture paralympique le 28 août, pas le 8 septembre.
# https://www.paralympic.org/paris-2024/news/wait-over-paralympic-games-open-28-august
# Para triathlon : les épreuves du 1er septembre ont été reportées au 2.
# https://www.paralympic.org/paris-2024/news/para-triathlon-postponed-2-september
# Surf : les finales ont eu lieu le 5 août à Tahiti après des reports.
# https://isasurf.org/caroline-marks-and-kauli-vaast-win-gold-medal-at-paris-2024-olympic-games/
# Voile : les dernières épreuves ont eu lieu le 9 août, jour de réserve.
# https://www.sailing.org/2024/08/09/valentin-bontus-from-class-clown-to-olympic-champion/
# Concorde 3 : les sessions de skateboard figurent les 28 et 29 juillet
# dans le calendrier des sessions mis à jour le 30 juillet.
# https://data.europa.eu/data/datasets/https-data-education-gouv-fr-explore-dataset-paris24-calendrier-des-sessions-version-simplifiee-
CORRECTIONS_DATES = {
    ("LGN", "olympique"): ("2024-08-01", "2024-08-10"),
    ("VE2", "olympique"): ("2024-08-01", "2024-08-02"),
    ("LCO", "paralympique"): ("2024-08-28", "2024-08-28"),
    ("ALX", "paralympique"): ("2024-09-02", "2024-09-02"),
    ("TAH", "olympique"): ("2024-07-27", "2024-08-05"),
    ("MAM", "olympique"): ("2024-07-28", "2024-08-09"),
    ("LC3", "olympique"): ("2024-07-28", "2024-07-29"),
}


def recuperer_sites():
    """Télécharge le CSV officiel et retourne ses octets et sa table brute."""
    with urlopen(URL_SOURCE, timeout=30) as reponse:
        contenu = reponse.read()
    table = pd.read_csv(BytesIO(contenu), sep=";", dtype=str)
    return contenu, table


def preparer_sites(table):
    """Harmonise les colonnes utiles sans supprimer les lignes de la source."""
    colonnes = {
        "Code_Site": "code_site",
        "Nom_Site": "nom_site",
        "category_id": "categorie_source",
        "Sports": "sports",
        "start_date": "date_debut",
        "end_date": "date_fin",
        "latitude": "latitude",
        "longitude": "longitude",
    }
    manquantes = set(colonnes) - set(table.columns)
    if manquantes:
        raise ValueError(f"Colonnes absentes de la source : {sorted(manquantes)}")
    resultat = table[list(colonnes)].rename(columns=colonnes).copy()
    for colonne in ("code_site", "nom_site", "categorie_source", "sports"):
        resultat[colonne] = resultat[colonne].str.strip()
    resultat["type_jeux"] = resultat["categorie_source"].map({
        "venue-olympic": "olympique",
        "venue-paralympic": "paralympique",
    }).fillna("inconnu")
    for colonne in ("latitude", "longitude"):
        resultat[colonne] = pd.to_numeric(
            resultat[colonne].str.replace(",", ".", regex=False), errors="coerce"
        )
    for colonne in ("date_debut", "date_fin"):
        resultat[colonne] = pd.to_datetime(resultat[colonne], errors="coerce")
    resultat["date_debut_source"] = resultat["date_debut"]
    resultat["date_fin_source"] = resultat["date_fin"]
    resultat["dates_corrigees"] = False
    for (code, type_jeux), (debut, fin) in CORRECTIONS_DATES.items():
        masque = (resultat["code_site"] == code) & (resultat["type_jeux"] == type_jeux)
        resultat.loc[masque, "date_debut"] = pd.Timestamp(debut)
        resultat.loc[masque, "date_fin"] = pd.Timestamp(fin)
        resultat.loc[masque, "dates_corrigees"] = True
    resultat = resultat[["code_site", "nom_site", "type_jeux", "sports", "date_debut", "date_fin", "date_debut_source", "date_fin_source", "dates_corrigees", "latitude", "longitude", "categorie_source"]]
    return resultat


def separer_sites(sites):
    """Renvoie deux DataFrames indépendants, triés par nom de site."""
    olympiques = sites.loc[sites["type_jeux"] == "olympique"].sort_values("nom_site").reset_index(drop=True)
    paralympiques = sites.loc[sites["type_jeux"] == "paralympique"].sort_values("nom_site").reset_index(drop=True)
    return olympiques, paralympiques


def charger_tables_locales():
    """Charge les deux tables depuis le fichier nettoyé local."""
    fichier = DOSSIER_SORTIE / "donnees_nettoyees.csv"
    if not fichier.exists():
        raise FileNotFoundError("Données absentes : lancez d'abord python sites_competition.py")
    table = pd.read_csv(fichier, parse_dates=["date_debut", "date_fin", "date_debut_source", "date_fin_source"])
    return separer_sites(table)


def main():
    _, table = recuperer_sites()
    sites = preparer_sites(table)
    site_olympiques, site_paralympique = separer_sites(sites)
    DOSSIER_SORTIE.mkdir(exist_ok=True)
    sites.to_csv(DOSSIER_SORTIE / "donnees_nettoyees.csv", index=False, encoding="utf-8")
    print(f"{len(sites)} lignes récupérées ; types de Jeux :")
    print(sites["type_jeux"].value_counts().to_string())
    print("Lignes sans coordonnées :", sites[["latitude", "longitude"]].isna().any(axis=1).sum())
    print("\nSites olympiques :")
    print(site_olympiques.to_string(index=False))
    print("\nSites paralympiques :")
    print(site_paralympique.to_string(index=False))
    print(f"Fichiers enregistrés dans {DOSSIER_SORTIE}")


if __name__ == "__main__":
    main()
else:
    site_olympiques, site_paralympique = charger_tables_locales()
