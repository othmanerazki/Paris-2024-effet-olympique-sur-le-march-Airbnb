"""Carte des annonces observées à Paris et des sites des Jeux de 2024.

Exécution : python carte_interactive.py
Dépendances : pandas, s3fs, folium, shapely, requests.
Les dates correspondent aux noms des fichiers ; elles ne sont pas des dates de séjour.
"""

import html
from pathlib import Path
from urllib.parse import quote

import branca.colormap as cm
import folium
import pandas as pd
import requests
from shapely.geometry import Point, shape
from shapely.strtree import STRtree

from sites_competition import site_olympique_paris, site_paralympiques_paris


URL_ARRONDISSEMENTS = "https://opendata.paris.fr/api/explore/v2.1/catalog/datasets/arrondissements/exports/geojson"
URL_STOCKAGE = "https://minio.lab.sspcloud.fr/"
FICHIERS = {
    "14 juillet 2024": "etiennealpy/données paris/listing_14_juillet_2024.csv",
    "9 août 2024": "etiennealpy/données paris/listing_09_aout_2024.csv",
}
SORTIE = Path(__file__).resolve().parent / "carte_airbnb_paris.html"


def charger_arrondissements():
    """Récupère les contours officiels de la Ville de Paris."""
    reponse = requests.get(URL_ARRONDISSEMENTS, timeout=60)
    reponse.raise_for_status()
    contours = reponse.json()
    if len(contours["features"]) != 20:
        raise ValueError("Les contours doivent contenir les 20 arrondissements.")
    return contours


def compter_annonces(chemin, contours):
    """Compte les identifiants uniques par arrondissement, selon leurs coordonnées."""
    url = URL_STOCKAGE + quote(chemin, safe="/")
    annonces = pd.read_csv(url, usecols=["id", "latitude", "longitude"])
    annonces = annonces.dropna(subset=["id", "latitude", "longitude"]).drop_duplicates("id")
    geometries = [shape(f["geometry"]) for f in contours["features"]]
    arbre = STRtree(geometries)
    comptes = [0] * len(geometries)
    hors_paris = 0
    for ligne in annonces.itertuples(index=False):
        point = Point(ligne.longitude, ligne.latitude)
        candidats = arbre.query(point, predicate="intersects")
        if len(candidats):
            # Un point sur une limite est affecté une seule fois.
            comptes[int(candidats[0])] += 1
        else:
            hors_paris += 1
    print(f"{chemin} : {sum(comptes)} annonces situées à Paris ; {hors_paris} hors contours")
    return comptes


def ajouter_sites(carte, sites, titre, couleur):
    couche = folium.FeatureGroup(name=titre)
    for site in sites.itertuples(index=False):
        texte = f"<b>{html.escape(str(site.nom_site))}</b><br>{html.escape(str(site.sports))}"
        folium.CircleMarker(
            location=[site.latitude, site.longitude], radius=6, color=couleur,
            fill=True, fill_opacity=0.85, tooltip=html.escape(str(site.nom_site)),
            popup=folium.Popup(texte, max_width=350),
        ).add_to(couche)
    couche.add_to(carte)


def creer_carte():
    contours = charger_arrondissements()
    (date_avant, chemin_avant), (date_apres, chemin_apres) = FICHIERS.items()
    avant = compter_annonces(chemin_avant, contours)
    apres = compter_annonces(chemin_apres, contours)
    for i, feature in enumerate(contours["features"]):
        p = feature["properties"]
        p["arrondissement_carte"] = str(p.get("l_ar", p.get("c_ar", "?")))
        p["avant"] = avant[i]
        p["apres"] = apres[i]
        p["variation"] = round((apres[i] - avant[i]) / avant[i] * 100, 1) if avant[i] else None
        p["variation_texte"] = f"{p['variation']:+.1f} %" if p["variation"] is not None else "Non calculable"

    carte = folium.Map(location=[48.8566, 2.3522], zoom_start=12, tiles="OpenStreetMap")
    valeurs = [f["properties"]["variation"] for f in contours["features"] if f["properties"]["variation"] is not None]
    if not valeurs:
        raise ValueError("Aucune évolution calculable : vérifier les données et les coordonnées.")
    borne = max(max(abs(x) for x in valeurs), 1)
    palette = cm.LinearColormap(["#2166ac", "#f7f7f7", "#b2182b"], vmin=-borne, vmax=borne)
    palette.caption = f"Évolution des annonces (%) : {date_avant} → {date_apres}"
    palette.add_to(carte)
    folium.GeoJson(
        contours, name="Évolution par arrondissement",
        style_function=lambda f: {
            "fillColor": palette(f["properties"]["variation"]) if f["properties"]["variation"] is not None else "#aaaaaa",
            "color": "#555555", "weight": 1, "fillOpacity": 0.7,
        },
        highlight_function=lambda _: {"weight": 3, "color": "#111111"},
        tooltip=folium.GeoJsonTooltip(
            fields=["arrondissement_carte", "avant", "apres", "variation_texte"],
            aliases=["Arrondissement", date_avant, date_apres, "Évolution"],
            sticky=False,
        ),
    ).add_to(carte)
    ajouter_sites(carte, site_olympique_paris, "Sites olympiques", "#1855c9")
    ajouter_sites(carte, site_paralympiques_paris, "Sites paralympiques", "#e27100")
    folium.LayerControl(collapsed=False).add_to(carte)
    carte.get_root().html.add_child(folium.Element(
        '<div style="position:fixed;top:10px;left:55px;z-index:1000;background:white;padding:8px;'
        'border-radius:4px;font-size:14px"><b>Airbnb à Paris et sites des Jeux 2024</b><br>'
        'Annonces observées : 14 juillet → 9 août 2024<br>'
        'Bleu : olympique · orange : paralympique<br>'
        'Sources : Inside Airbnb, Ville de Paris, ministère des Sports</div>'
    ))
    carte.save(str(SORTIE))
    print(f"Carte créée : {SORTIE}")
    return carte


if __name__ == "__main__":
    creer_carte()
