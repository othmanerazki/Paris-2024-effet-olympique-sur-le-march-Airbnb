"""Carte des prix Airbnb observés à Paris et des sites des Jeux de 2024.

python carte_sites_paris.py --mois aout
python carte_sites_paris.py --mois juillet --sans-fenetre
Les prix affichés sont issus des annonces, pas des réservations.
"""
import argparse
import csv
from functools import lru_cache
import json
import math
import os
import re
import sys
import tempfile
from pathlib import Path
from importation_données import FICHIERS, charger_annonces, charger_contours, charger_donnees_sites

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

# Bornes fixes communes à toutes les cartes : les valeurs situées au-delà des
# bornes utilisent les couleurs extrêmes de la légende.
PRIX_MIN_ECHELLE = 100
PRIX_MAX_ECHELLE = 350
SITES_PARIS = {"BCY", "CDM", "SP1", "SP4", "SP6", "CPL", "GRP", "HDV", "INV",
               "LCO", "LC1", "LC2", "LC3", "LC4", "PDP", "ALX", "RGA", "EIF", "TRO"}
MONUMENTS = [("Arc de Triomphe", 48.8738, 2.2950), ("Tour Eiffel", 48.8584, 2.2945),
             ("Louvre", 48.8606, 2.3376), ("Notre-Dame", 48.8530, 2.3499),
             ("Sacré-Cœur", 48.8867, 2.3431)]


def charger_sites():
    if not SITES.exists():
        raise FileNotFoundError("Exécutez d'abord sites_competition.py pour récupérer les sites.")
    sites = {}
    for ligne in charger_donnees_sites().to_dict("records"):
        if ligne["code_site"] not in SITES_PARIS:
            continue
        site = sites.setdefault(ligne["code_site"], {
            "code": ligne["code_site"], "lat": float(ligne["latitude"]), "lon": float(ligne["longitude"]), "jeux": set(),
        })
        site["jeux"].add(ligne["type_jeux"])
    if not sites:
        raise ValueError("Aucun site parisien trouvé.")
    return list(sites.values())





def preparer_population(df, paris):
    """Une ligne par identifiant : sépare les exclusions de l'analyse parisienne."""
    df = df.copy()
    lignes = len(df)
    sans_id = int(df.id.isna().sum())
    df = df.dropna(subset=["id"])
    doublons = int(df.duplicated("id").sum())
    df = df.drop_duplicates("id").copy()
    sans_coord = int(df[["latitude", "longitude"]].isna().any(axis=1).sum())
    df = df.dropna(subset=["latitude", "longitude"])
    masque = contains_xy(paris, df.longitude.to_numpy(), df.latitude.to_numpy())
    hors_paris = int((~masque).sum())
    df = df.loc[masque].copy()
    df["prix_valide"] = df.prix.notna() & (df.prix > 0)
    return df, {"lignes": lignes, "sans_id": sans_id, "doublons": doublons,
                "sans_coord": sans_coord, "hors_paris": hors_paris}


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


def creer_carte(mois="aout", afficher=True, type_logement="tous"):
    seuil = 5
    dossier_cartes = DOSSIER / "cartes prix"
    dossier_cartes.mkdir(exist_ok=True)
    dossier_controles = dossier_cartes / "analyses complementaires"
    if type_logement != "tous":
        dossier_controles.mkdir(exist_ok=True)
        sortie = dossier_controles / f"carte_prix_paris_{mois}_{type_logement}.png"
    else:
        sortie = dossier_cartes / f"carte_prix_paris_{mois}.png"
    contours = charger_contours()
    geometries = [shape(f["geometry"]) for f in contours]
    if len(geometries) != 20:
        raise ValueError("Le fichier des contours doit contenir les 20 arrondissements.")
    paris = unary_union(geometries)
    sites = charger_sites()
    parisien, controles = preparer_population(charger_annonces(mois), paris)
    annonces = parisien.loc[parisien.prix_valide].copy()
    types = {"entiers": "Entire home/apt", "chambres": "Private room"}
    if type_logement != "tous":
        annonces = annonces.loc[annonces.room_type == types[type_logement]].copy()
    if annonces.empty:
        raise ValueError("Aucune annonce avec prix exploitable à Paris.")
    pas_lon, pas_lat = 0.0034, 0.00225  # Mailles d'environ 250 mètres.
    annonces["x"] = np.floor(annonces.longitude / pas_lon).astype(int)
    annonces["y"] = np.floor(annonces.latitude / pas_lat).astype(int)
    mailles = annonces.groupby(["x", "y"])["prix"].agg(["median", "count"]).reset_index()
    mailles = mailles.loc[mailles["count"] >= seuil]
    if mailles.empty:
        raise ValueError(f"Aucune maille n'a au moins {seuil} prix pour {type_logement}.")
    dates = pd.to_datetime(annonces["last_scraped"], errors="coerce").dropna()
    dates_texte = f"{dates.min():%d/%m/%Y}–{dates.max():%d/%m/%Y}" if not dates.empty else "dates non renseignées"

    fig = plt.figure(figsize=(15, 10), facecolor="#f6f8fb")
    ax = fig.add_axes([0.08, 0.26, 0.86, 0.57])
    xmin, ymin, xmax, ymax = paris.bounds
    for geo in geometries:
        for poly in (geo.geoms if geo.geom_type == "MultiPolygon" else [geo]):
            x, y = poly.exterior.xy
            ax.fill(x, y, facecolor="#edf1f5", edgecolor="none", zorder=0)
    cases = [Rectangle((r.x * pas_lon, r.y * pas_lat), pas_lon, pas_lat) for r in mailles.itertuples()]
    couleurs = PatchCollection(cases, cmap="YlOrRd", norm=Normalize(vmin=PRIX_MIN_ECHELLE, vmax=PRIX_MAX_ECHELLE, clip=True), edgecolor="none", zorder=1)
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
    ax.set_xlabel("Longitude (degrés est)", fontsize=8)
    ax.set_ylabel("Latitude (degrés nord)", fontsize=8)
    ax.tick_params(labelsize=7)
    ax.grid(False)
    fig.text(.07, .95, "Paris 2024", fontsize=27, weight="bold", color="#15334e")
    titres_types = {"tous": "Tous types de logements", "entiers": "Logements entiers", "chambres": "Chambres privées"}
    fig.text(.07, .908, "Prix affiché médian des annonces Airbnb à Paris", fontsize=17, color="#34586c")
    fig.text(.07, .878, f"Collecte : {dates_texte} · {titres_types[type_logement]} · fichier {mois} 2024", fontsize=11, color="#60788a")
    bar = fig.colorbar(couleurs, cax=fig.add_axes([.14, .175, .49, .016]), orientation="horizontal", extend="both")
    bar.set_label("Prix médian affiché (dollars)", fontsize=10)
    fig.legend(handles=[
        Line2D([], [], marker="o", linestyle="none", markerfacecolor="#145ed0", markeredgecolor="none", markersize=9, label="Site olympique"),
        Line2D([], [], marker="^", linestyle="none", markerfacecolor="#6a2499", markeredgecolor="none", markersize=9, label="Site paralympique"),
        Line2D([], [], marker="D", linestyle="none", markerfacecolor="#1a3682", markeredgecolor="none", markersize=8, label="Les deux Jeux"),
        Line2D([], [], marker="*", linestyle="none", markerfacecolor="#087b72", markeredgecolor="none", markersize=10, label="Monument (repère)"),
        Line2D([], [], marker="s", linestyle="none", markerfacecolor="#edf1f5", markeredgecolor="#a6b4c1", markersize=9, label=f"Moins de {seuil} prix renseignés"),
    ], loc="lower left", bbox_to_anchor=(.07, .065), ncol=3, frameon=False, fontsize=9)
    fig.text(.07, .035, f"Prix affichés, pas prix payés · Mailles d’au moins {seuil} prix · Sites placés selon leurs coordonnées géographiques.", fontsize=8, color="#475569")
    fig.text(.07, .016, "Échelle fixe : 100–350 ; en dehors, couleurs extrêmes · Sources : Inside Airbnb, Ville de Paris, ministère des Sports, Région Île-de-France.", fontsize=8, color="#475569")
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
    parser.add_argument("--analyse-complete", action="store_true", help="Créer les cartes complémentaires par type de logement.")
    args = parser.parse_args()
    if args.analyse_complete:
        creer_carte(args.mois, afficher=False)
        for type_logement in ("entiers", "chambres"):
            creer_carte(args.mois, afficher=False, type_logement=type_logement)
    else:
        creer_carte(args.mois, afficher=not args.sans_fenetre)
