"""Carte des prix Airbnb observés à Paris et des sites des Jeux de 2024.

python carte_sites_paris.py --mois aout
python carte_sites_paris.py --mois juillet --sans-fenetre
Les prix affichés sont issus des annonces, pas des réservations.
"""
import argparse
import csv
import json
import math
import os
import re
import sys
import tempfile
from pathlib import Path
from urllib.parse import quote

import matplotlib
if "--sans-fenetre" in sys.argv:
    matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.collections import PatchCollection
from matplotlib.colors import Normalize
from matplotlib.lines import Line2D
from matplotlib.offsetbox import AnnotationBbox, DrawingArea
from matplotlib.patches import Circle, PathPatch, Polygon, Rectangle
from matplotlib.path import Path as CheminGraphique
from shapely import contains_xy
from shapely.geometry import shape
from shapely.ops import unary_union

DOSSIER = Path(__file__).resolve().parent
CONTOURS = DOSSIER / "contours_arrondissements.geojson"
SITES = DOSSIER / "donnees_sites" / "donnees_nettoyees.csv"
FICHIERS = {
    "juillet": "etiennealpy/données paris/listing_14_juillet_2024.csv",
    "aout": "etiennealpy/données paris/listing_09_aout_2024.csv",
    "septembre": "etiennealpy/données paris/listing_6_septembre_2024",
}
SITES_PARIS = {"BCY", "CDM", "SP1", "SP4", "SP6", "CPL", "GRP", "HDV", "INV",
               "LCO", "LC1", "LC2", "LC3", "LC4", "PDP", "ALX", "RGA", "EIF", "TRO"}
MONUMENTS = [("Arc de Triomphe", 48.8738, 2.2950), ("Tour Eiffel", 48.8584, 2.2945),
             ("Louvre", 48.8606, 2.3376), ("Notre-Dame", 48.8530, 2.3499),
             ("Sacré-Cœur", 48.8867, 2.3431)]


def charger_sites():
    if not SITES.exists():
        raise FileNotFoundError("Exécutez d'abord sites_competition.py pour récupérer les sites.")
    sites = {}
    with SITES.open(encoding="utf-8", newline="") as fichier:
        for ligne in csv.DictReader(fichier):
            if ligne["code_site"] not in SITES_PARIS:
                continue
            site = sites.setdefault(ligne["code_site"], {
                "code": ligne["code_site"], "lat": float(ligne["latitude"]), "lon": float(ligne["longitude"]), "jeux": set(),
            })
            site["jeux"].add(ligne["type_jeux"])
    if not sites:
        raise ValueError("Aucun site parisien trouvé.")
    return list(sites.values())


def charger_annonces(mois):
    chemin = FICHIERS[mois]
    print(f"Chargement des annonces : {chemin} ...", flush=True)
    url = "https://minio.lab.sspcloud.fr/" + quote(chemin, safe="/")
    df = pd.read_csv(url, usecols=["id", "latitude", "longitude", "price", "last_scraped"], dtype={"price": "string"})
    df = df.drop_duplicates("id").copy()
    df["prix"] = pd.to_numeric(df["price"].str.replace(r"[^\d.]", "", regex=True), errors="coerce")
    for colonne in ("latitude", "longitude"):
        df[colonne] = pd.to_numeric(df[colonne], errors="coerce")
    return df.dropna(subset=["id", "latitude", "longitude"])


def ajouter_icone_monument(ax, nom, lon, lat):
    zone = DrawingArea(26, 30, 0, 0)
    zone.add_artist(Circle((13, 15), 12, facecolor="#e4eee9", edgecolor="#087b72", linewidth=1.3))
    if nom == "Tour Eiffel":
        points = [(12, 25), (14, 25), (15, 20), (17, 15), (19, 9), (21, 6), (16, 6),
                  (14, 9), (12, 9), (10, 6), (5, 6), (7, 9), (9, 15), (11, 20)]
        zone.add_artist(Polygon(points, closed=True, facecolor="#087b72", edgecolor="none"))
        zone.add_artist(Rectangle((7, 12), 12, 1.2, facecolor="#087b72", edgecolor="none"))
    elif nom == "Arc de Triomphe":
        zone.add_artist(Rectangle((5, 6), 16, 17, facecolor="#087b72", edgecolor="none"))
        zone.add_artist(Rectangle((4, 22), 18, 2, facecolor="#087b72", edgecolor="none"))
        zone.add_artist(Rectangle((10.5, 6), 5, 8, facecolor="#e4eee9", edgecolor="none"))
        zone.add_artist(Circle((13, 14), 2.5, facecolor="#e4eee9", edgecolor="none"))
    else:
        zone.add_artist(Polygon([(13, 24), (16, 17), (23, 17), (18, 12), (20, 6), (13, 10),
                                 (6, 6), (8, 12), (3, 17), (10, 17)], facecolor="#087b72", edgecolor="none"))
    ax.add_artist(AnnotationBbox(zone, (lon, lat), frameon=False, pad=0, zorder=10))


def creer_carte(mois="aout", afficher=True):
    dossier_cartes = DOSSIER / "cartes prix"
    dossier_cartes.mkdir(exist_ok=True)
    sortie = dossier_cartes / f"carte_prix_paris_{mois}.png"
    contours = json.loads(CONTOURS.read_text(encoding="utf-8"))["features"]
    geometries = [shape(f["geometry"]) for f in contours]
    if len(geometries) != 20:
        raise ValueError("Le fichier des contours doit contenir les 20 arrondissements.")
    paris = unary_union(geometries)
    sites = charger_sites()
    annonces = charger_annonces(mois)
    annonces = annonces.loc[contains_xy(paris, annonces.longitude.to_numpy(), annonces.latitude.to_numpy()) & annonces.prix.notna() & (annonces.prix > 0)].copy()
    if annonces.empty:
        raise ValueError("Aucune annonce avec prix exploitable à Paris.")
    pas_lon, pas_lat = 0.0034, 0.00225  # Mailles d'environ 250 mètres.
    annonces["x"] = np.floor(annonces.longitude / pas_lon).astype(int)
    annonces["y"] = np.floor(annonces.latitude / pas_lat).astype(int)
    mailles = annonces.groupby(["x", "y"])["prix"].agg(["median", "count"]).reset_index()
    mailles = mailles.loc[mailles["count"] >= 5]
    if mailles.empty:
        raise ValueError("Aucune maille n'a au moins cinq prix.")
    dates = pd.to_datetime(annonces["last_scraped"], errors="coerce").dropna()
    dates_texte = f"{dates.min():%d/%m/%Y}–{dates.max():%d/%m/%Y}" if not dates.empty else "dates non renseignées"
    vmin, vmax = np.percentile(mailles["median"], [5, 95])
    if vmin == vmax:
        vmax = vmin + 1

    fig = plt.figure(figsize=(15, 10), facecolor="#f6f8fb")
    ax = fig.add_axes([0.06, 0.22, 0.88, 0.64])
    xmin, ymin, xmax, ymax = paris.bounds
    for geo in geometries:
        for poly in (geo.geoms if geo.geom_type == "MultiPolygon" else [geo]):
            x, y = poly.exterior.xy
            ax.fill(x, y, facecolor="#edf1f5", edgecolor="none", zorder=0)
    cases = [Rectangle((r.x * pas_lon, r.y * pas_lat), pas_lon, pas_lat) for r in mailles.itertuples()]
    couleurs = PatchCollection(cases, cmap="YlOrRd", norm=Normalize(vmin=vmin, vmax=vmax, clip=True), edgecolor="none", zorder=1)
    couleurs.set_array(mailles["median"].to_numpy())
    ax.add_collection(couleurs)
    chemins = []
    for geo in geometries:
        for poly in (geo.geoms if geo.geom_type == "MultiPolygon" else [geo]):
            for anneau in [poly.exterior, *poly.interiors]:
                points = list(anneau.coords)
                codes = [CheminGraphique.MOVETO] + [CheminGraphique.LINETO] * (len(points) - 2) + [CheminGraphique.CLOSEPOLY]
                chemins.append(CheminGraphique(points, codes))
    couleurs.set_clip_path(PathPatch(CheminGraphique.make_compound_path(*chemins), transform=ax.transData))
    for feature, geo in zip(contours, geometries):
        for poly in (geo.geoms if geo.geom_type == "MultiPolygon" else [geo]):
            x, y = poly.exterior.xy
            ax.plot(x, y, color="#7b8a99", linewidth=.65, zorder=2)
        centre = geo.representative_point()
        numero = re.match(r"\d+", str(feature["properties"]["arrondissement"]))
        ax.text(centre.x, centre.y, numero.group() if numero else "?", fontsize=12, weight="bold",
                color="#26374c", ha="center", zorder=3,
                bbox={"facecolor": "#e4eee9", "edgecolor": "none", "alpha": .7, "pad": 1})
        bois = {"12": "Bois de Vincennes", "16": "Bois de Boulogne"}.get(numero.group() if numero else "")
        if bois:
            ax.annotate(bois, (centre.x, centre.y), xytext=(0, -16), textcoords="offset points",
                        ha="center", fontsize=8, color="#547269", style="italic", zorder=3)
    for site in sites:
        commun = {"olympique", "paralympique"}.issubset(site["jeux"])
        if commun:
            symbole, couleur = "D", "#1a3682"
        elif "olympique" in site["jeux"]:
            symbole, couleur = "o", "#145ed0"
        else:
            symbole, couleur = "^", "#6a2499"
        ax.scatter(site["lon"], site["lat"], s=120, marker=symbole, c=couleur,
                   edgecolors="none", zorder=15)
    for nom, lat, lon in MONUMENTS:
        ajouter_icone_monument(ax, nom, lon, lat)
        ax.annotate(nom, (lon, lat), xytext=(15, -3), textcoords="offset points", fontsize=8,
                    color="#075e58", weight="bold", zorder=11,
                    bbox={"boxstyle": "round,pad=0.2", "facecolor": "#e4eee9", "edgecolor": "none", "alpha": .85})
    ax.set_xlim(xmin - .005, xmax + .005)
    ax.set_ylim(ymin - .004, ymax + .004)
    ax.set_aspect(1 / math.cos(math.radians(48.86)))
    ax.axis("off")
    fig.text(.07, .95, "Paris 2024", fontsize=27, weight="bold", color="#15334e")
    fig.text(.07, .908, "Prix Airbnb et sites des Jeux", fontsize=17, color="#34586c")
    fig.text(.07, .878, f"Prix affiché médian par zone · fichier {mois} 2024 · collectes : {dates_texte}", fontsize=11, color="#60788a")
    bar = fig.colorbar(couleurs, cax=fig.add_axes([.14, .175, .49, .016]), orientation="horizontal", extend="both")
    bar.set_label("Prix médian affiché (dollars)", fontsize=10)
    fig.legend(handles=[
        Line2D([], [], marker="o", linestyle="none", markerfacecolor="#145ed0", markeredgecolor="none", markersize=9, label="Site olympique"),
        Line2D([], [], marker="^", linestyle="none", markerfacecolor="#6a2499", markeredgecolor="none", markersize=9, label="Site paralympique"),
        Line2D([], [], marker="D", linestyle="none", markerfacecolor="#1a3682", markeredgecolor="none", markersize=8, label="Les deux Jeux"),
        Line2D([], [], marker="*", linestyle="none", markerfacecolor="#087b72", markeredgecolor="none", markersize=10, label="Monument (repère)"),
        Line2D([], [], marker="s", linestyle="none", markerfacecolor="#edf1f5", markeredgecolor="#a6b4c1", markersize=9, label="Zone sans couleur : moins de 5 prix"),
    ], loc="lower left", bbox_to_anchor=(.07, .065), ncol=3, frameon=False, fontsize=9)
    fig.text(.07, .035, "Prix affichés, pas prix payés · Mailles d’au moins 5 prix · Sites placés selon leurs coordonnées géographiques.", fontsize=8, color="#475569")
    fig.text(.07, .016, "Couleurs saturées aux 5e et 95e percentiles · Sources : Inside Airbnb, Ville de Paris, ministère des Sports, Région Île-de-France.", fontsize=8, color="#475569")
    # Remplacement atomique : évite de modifier directement une image ouverte.
    with tempfile.NamedTemporaryFile(suffix=".png", dir=dossier_cartes, delete=False) as fichier_temporaire:
        chemin_temporaire = Path(fichier_temporaire.name)
    try:
        fig.savefig(chemin_temporaire, dpi=160, facecolor=fig.get_facecolor())
        os.replace(chemin_temporaire, sortie)
    finally:
        chemin_temporaire.unlink(missing_ok=True)
    print(f"Carte enregistrée : {sortie} ; {len(annonces)} annonces à Paris avec prix renseigné.")
    if afficher:
        plt.show()
    else:
        plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Carte des prix affichés autour des sites des Jeux de Paris 2024")
    parser.add_argument("--mois", choices=FICHIERS, default="aout")
    parser.add_argument("--sans-fenetre", action="store_true")
    args = parser.parse_args()
    creer_carte(args.mois, afficher=not args.sans_fenetre)
