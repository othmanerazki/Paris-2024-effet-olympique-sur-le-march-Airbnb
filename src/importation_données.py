"""Collecte et chargement des données du projet.

Ce module regroupe Airbnb 2024/2026, le cache, les sites de compétition,
les fichiers géographiques et les séries contextuelles Eurostat/INSEE.
Les traitements statistiques et les graphiques restent dans leurs scripts.

python src/importation_données.py                        # huit relevés d'été
python src/importation_données.py --tous-mois-2024        # année 2024 et été 2026
python src/importation_données.py --source sites         # préparer les sites
python src/importation_données.py --source contexte      # Eurostat et INSEE
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from functools import lru_cache
import gzip
from io import BytesIO
import itertools
import json
from pathlib import Path
from urllib.parse import quote
from urllib.request import urlopen, urlretrieve
import pandas as pd
import s3fs

RACINE = Path(__file__).resolve().parent.parent
DONNEES = RACINE / "data"
CACHE = DONNEES / "donnees_airbnb"
DOSSIER_EXTERNE = DONNEES / "donnees_externes"
CONTOURS = DONNEES / "contours_arrondissements.geojson"
SITES = DONNEES / "donnees_sites" / "donnees_nettoyees.csv"



FICHIERS = {
    "janvier": "etiennealpy/données paris/listing_13_janvier_2024",
    "fevrier": "etiennealpy/données paris/listing_14_fevrier_2024",
    "avril": "etiennealpy/données paris/listing_17_avril_2024.csv",
    "mai": "etiennealpy/données paris/listing_11_mai_2024.csv",
    "juin": "etiennealpy/données paris/listing_10_juin_2024",
    "juillet": "etiennealpy/données paris/listing_14_juillet_2024.csv",
    "aout": "etiennealpy/données paris/listing_09_aout_2024.csv",
    "septembre": "etiennealpy/données paris/listing_6_septembre_2024",
    "octobre": "etiennealpy/données paris/listing_07_octobre_2024.csv",
    "novembre": "etiennealpy/données paris/listing_09_novembre_2024.csv",
    "decembre": "etiennealpy/données paris/listing_16_decembre_2024",
}


MOIS = {"juin": "2026-06-16", "juillet": "2026-07-15", "aout": "2026-08-15", "septembre": "2026-09-16"}


NOMS_2024 = {mois: chemin.rsplit("/", 1)[-1] for mois, chemin in FICHIERS.items()}


COLONNES = ["id", "latitude", "longitude", "last_scraped", "price", "room_type", "availability_30",
            "neighbourhood_cleansed", "accommodates", "bedrooms", "bathrooms", "minimum_nights",
            "number_of_reviews", "review_scores_rating", "host_is_superhost", "instant_bookable",
            "calculated_host_listings_count"]


INSIDE_AIRBNB = "https://data.insideairbnb.com/france/ile-de-france/paris/{date}/data/listings.csv.gz"


RELEVES_INSIDE_AIRBNB = ["2026-06-16", "2026-07-15", "2026-08-15", "2026-09-16"]


EUROSTAT = (
    "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"
    "tour_ce_omn12?geo=FR10&c_resid=TOTAL&indic_to=NGT_SP"
)


INSEE = "https://bdm.insee.fr/series/sdmx/data/SERIES_BDM/010598705+010599005?startPeriod=2018-01"


URL_SITES = "https://www.data.gouv.fr/api/1/datasets/r/5a0599d1-ad3f-42d1-b64c-204ee19cf520"


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


def charger_donnees_paris():
  fs = s3fs.S3FileSystem(
      anon=True, client_kwargs={"endpoint_url": "https://minio.lab.sspcloud.fr"}
  )
  files = fs.find("etiennealpy/données paris")

  mois_disponibles = [
      "janvier",
      "fevrier",
      "mars",
      "avril",
      "mai",
      "juin",
      "juillet",
      "aout",
      "septembre",
      "octobre",
      "novembre",
      "decembre",
  ]

  dfs = {}
  for f in files:
    nom_fichier = f.split("/")[-1].lower()
    if "listing_" in nom_fichier:
      url = f"https://minio.lab.sspcloud.fr/{quote(f, safe='/')}"
      mois_trouve = "inconnu"
      for m in mois_disponibles:
        if m in nom_fichier:
          mois_trouve = m
          break
      try:
        dfs[mois_trouve] = pd.read_csv(url)
      except Exception as e:
        print(e)

  return dfs


def chemin_cache(annee, mois):
    return CACHE / f"releve_{annee}_{mois}.csv.gz"


def telecharger_releve(annee, mois):
    fichier = chemin_cache(annee, mois)
    if fichier.exists():
        return fichier
    url = ("https://minio.lab.sspcloud.fr/" + quote("etiennealpy/données paris/" + NOMS_2024[mois], safe="/")
           if annee == 2024 else f"https://data.insideairbnb.com/france/ile-de-france/paris/{MOIS[mois]}/data/listings.csv.gz")
    print(f"Lecture en flux : {annee} {mois}", flush=True)
    with urlopen(url, timeout=90) as reponse:
        flux = gzip.GzipFile(fileobj=reponse) if annee == 2026 else reponse
        table = pd.read_csv(flux, usecols=lambda c: c in COLONNES, dtype={"price": "string"}, low_memory=False)
    absentes = sorted(set(COLONNES) - set(table.columns))
    CACHE.mkdir(exist_ok=True)
    temporaire = fichier.with_suffix(".part")
    table.to_csv(temporaire, index=False, compression="gzip")
    temporaire.replace(fichier)
    manifeste = {"url": url, "recupere_utc": datetime.now(timezone.utc).isoformat(),
                 "lignes": len(table), "colonnes": list(table), "colonnes_absentes": absentes}
    fichier.with_suffix(".json").write_text(json.dumps(manifeste, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Cache enregistré : {annee} {mois}, {len(table)} lignes ; absentes : {absentes}", flush=True)
    return fichier


def lire_releve(annee, mois):
    return pd.read_csv(telecharger_releve(annee, mois), dtype={"price": "string"}, low_memory=False)


@lru_cache(maxsize=1)
def charger_annonces(mois):
    chemin = FICHIERS[mois]
    print(f"Chargement des annonces : {chemin} ...", flush=True)
    colonnes = ["id", "latitude", "longitude", "price", "last_scraped", "room_type", "availability_30"]
    df = lire_releve(2024, mois)[colonnes].copy()
    df["prix"] = pd.to_numeric(df["price"].str.replace(r"[^\d.\-]", "", regex=True), errors="coerce")
    for colonne in ("latitude", "longitude"):
        df[colonne] = pd.to_numeric(df[colonne], errors="coerce")
    return df


def telecharger(url, chemin):
    """Télécharge url vers chemin, sauf si le fichier existe déjà."""
    if chemin.exists():
        return
    chemin.parent.mkdir(parents=True, exist_ok=True)
    print(f"Téléchargement : {chemin.relative_to(DOSSIER_EXTERNE)}")
    urlretrieve(url, chemin)


def inside_airbnb():
    """Annonces des relevés de l'été 2026."""
    for date in RELEVES_INSIDE_AIRBNB:
        telecharger(INSIDE_AIRBNB.format(date=date), DOSSIER_EXTERNE / "insideairbnb" / f"listings_{date}.csv.gz")


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
    chemin = DOSSIER_EXTERNE / "eurostat_nuitees_plateformes_idf.csv"
    if not chemin.exists():
        DOSSIER_EXTERNE.mkdir(parents=True, exist_ok=True)
        eurostat_mensuel().to_csv(chemin, index=False)
    telecharger(INSEE, DOSSIER_EXTERNE / "insee_hotellerie_paris.xml")


def recuperer_sites():
    """Télécharge le CSV officiel et retourne ses octets et sa table brute."""
    with urlopen(URL_SITES, timeout=30) as reponse:
        contenu = reponse.read()
    table = pd.read_csv(BytesIO(contenu), sep=";", dtype=str)
    return contenu, table


def charger_donnees_sites():
    """Lit la table locale préparée ; ne déclenche pas de téléchargement."""
    if not SITES.exists():
        raise FileNotFoundError("Préparer les sites avec python src/importation_données.py --source sites")
    return pd.read_csv(SITES, parse_dates=["date_debut", "date_fin", "date_debut_source", "date_fin_source"])


def charger_contours():
    """Lit les contours des arrondissements conservés dans le dépôt."""
    return json.loads(CONTOURS.read_text(encoding="utf-8"))["features"]


def charger_parcours():
    """Lit les tracés simplifiés des cérémonies conservés dans le dépôt."""
    return json.loads((DONNEES / "parcours_ceremonies.geojson").read_text(encoding="utf-8"))["features"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", choices=["airbnb", "sites", "contexte", "tout"], default="airbnb")
    parser.add_argument("--annees", nargs="+", type=int, choices=[2024,2026], default=[2024,2026])
    parser.add_argument("--tous-mois-2024", action="store_true",
                        help="Mettre en cache les 11 relevés distincts de 2024 au lieu des seuls mois d'été.")
    args = parser.parse_args()
    if args.source in ["airbnb", "tout"]:
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = [pool.submit(telecharger_releve, annee, mois)
                       for annee in args.annees
                       for mois in (FICHIERS if annee == 2024 and args.tous_mois_2024 else MOIS)]
            for future in futures:
                future.result()
    if args.source in ["sites", "tout"]:
        from sites_competition import main as preparer_sites_locaux
        preparer_sites_locaux()
    if args.source in ["contexte", "tout"]:
        series_agregees()


if __name__ == "__main__":
    main()
