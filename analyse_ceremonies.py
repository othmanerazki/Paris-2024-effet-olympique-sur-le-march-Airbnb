"""Prix des annonces autour de tracés simplifiés des cérémonies d'ouverture.

Projection locale équirectangulaire en kilomètres, adaptée à une comparaison
de quartiers à Paris ; les tracés manuels ne sont pas des périmètres officiels.
Les groupes sont fixes par identifiant (position médiane des relevés), les prix
et disponibilités sont conservés séparément, et les deux cérémonies ne sont
jamais assimilées à deux expériences indépendantes.
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from shapely import distance, points
from shapely.geometry import LineString, shape
from shapely.ops import unary_union

from importation_données import lire_releve, charger_parcours, charger_contours

RACINE = Path(__file__).resolve().parent
MOIS = ["juin", "juillet", "aout", "septembre"]


def projeter(lon, lat, z=None):
    return (6371 * np.radians(np.asarray(lon)-2.35) * np.cos(np.radians(48.86)),
            6371 * np.radians(np.asarray(lat)-48.86))





def preparer_releves():
    from carte_sites_paris import preparer_population
    contours = charger_contours()
    paris = unary_union([shape(f["geometry"]) for f in contours])
    tableaux = []
    for mois in MOIS:
        brut = lire_releve(2024,mois)
        brut["prix"] = pd.to_numeric(brut["price"].astype("string").str.replace(r"[$,]", "", regex=True), errors="coerce")
        for c in ["latitude","longitude"]:
            brut[c] = pd.to_numeric(brut[c],errors="coerce")
        pop,_ = preparer_population(brut,paris)
        tableaux.append(pop.assign(releve=mois))
    return pd.concat(tableaux,ignore_index=True)


def analyser(annonces, seuil=.75, temoin=2):
    positions = annonces.groupby("id")[["latitude","longitude"]].median()
    xy = points(*projeter(positions.longitude.to_numpy(), positions.latitude.to_numpy()))
    observations = []
    for f in charger_parcours():
        coordonnees = np.asarray(f["geometry"]["coordinates"])
        ligne = LineString(np.column_stack(projeter(coordonnees[:,0],coordonnees[:,1])))
        distances = pd.Series(distance(xy,ligne), index=positions.index)
        d = annonces.assign(distance_km=annonces.id.map(distances))
        d["groupe"] = np.select([d.distance_km < seuil, d.distance_km >= temoin],
                                 ["proche", "éloigné"], default="intermédiaire")
        for (mois,groupe), t in d[d.groupe != "intermédiaire"].groupby(["releve","groupe"]):
            prix = t.loc[t.prix_valide,"prix"]
            observations.append({"ceremonie": f["properties"]["id"], "releve": mois,
                "groupe": groupe,"seuil_proche_km":seuil,"annonces":len(t),"prix_valides":len(prix),
                "part_prix_valides_pct":100*len(prix)/len(t),"prix_median_dollars":prix.median(),
                "part_logements_entiers_pct":100*t.room_type.eq("Entire home/apt").mean(),
                "collecte_min":pd.to_datetime(t.last_scraped,errors="coerce").min(),
                "collecte_max":pd.to_datetime(t.last_scraped,errors="coerce").max()})
    return pd.DataFrame(observations)


def graphiques(resultats):
    fig, axes = plt.subplots(1,2,figsize=(13,4.8))
    for ax,ceremonie in zip(axes,["olympique","paralympique"]):
        sous = resultats[resultats.ceremonie.eq(ceremonie)]
        prix = sous.pivot(index="releve", columns="groupe",values="prix_median_dollars").reindex(MOIS)
        prix.plot(ax=ax,marker="o",color=["#397f84","#bd7045"])
        ax.set(title=f"Parcours {ceremonie} — relevés de l'été 2024",xlabel="Relevé (juin à septembre 2024)",
               ylabel="Prix médian affiché (dollars par nuit)")
        ax.legend(title="Distance au tracé : proche < 0,75 km ; éloigné ≥ 2 km",fontsize=8,title_fontsize=8)
    fig.suptitle("Prix selon la proximité des cérémonies d'ouverture",fontsize=13)
    fig.tight_layout()
    return fig


def main():
    sortie=RACINE/"resultats"
    sortie.mkdir(exist_ok=True)
    annonces=preparer_releves()
    resultats=analyser(annonces)
    resultats.to_csv(sortie/"prix_ceremonies.csv",index=False)
    sensibilite=pd.concat([analyser(annonces,seuil=s) for s in [.5,.75,1]],ignore_index=True)
    sensibilite.to_csv(sortie/"sensibilite_ceremonies.csv",index=False)
    fig=graphiques(resultats)
    fig.savefig(sortie/"prix_ceremonies.png",dpi=160,bbox_inches="tight")
    plt.close(fig)
    print(resultats.to_string(index=False))


if __name__=="__main__":
    main()
