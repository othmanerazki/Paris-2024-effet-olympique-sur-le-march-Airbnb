"""Régressions d'Othmane sur les prix Airbnb près des sites de Paris 2024.

Ce fichier contient la préparation statistique, les modèles hédoniques, le
panel, la triple différence et le graphique. La collecte reste centralisée
dans importation_données.py. Les notebooks appellent ces mêmes fonctions.

Exécution : python regression_lineaire.py
Prérequis : python importation_données.py --source sites
            python importation_données.py
Sorties : tableaux dans le terminal et graphique dans resultats/.
Les notebooks affichent directement les tableaux renvoyés par les fonctions.
"""
from pathlib import Path

import matplotlib
if __name__ == "__main__":
    matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from linearmodels.panel import PanelOLS
from shapely.geometry import shape
from shapely.ops import unary_union

from importation_données import lire_releve, chemin_cache, charger_contours
from carte_sites_paris import preparer_population
from sites_competition import charger_tables_locales

RACINE = Path(__file__).resolve().parent
MOIS_ETE = {"juin": 6, "juillet": 7, "aout": 8, "septembre": 9}
CENTRE_PARIS = (48.85341, 2.34880)
TRANCHE = "C(tranche, Treatment('plus de 3 km'))"
FORMULE = (
    f"log_prix ~ {TRANCHE} + dist_centre_km + C(room_type) + accommodates + bedrooms + bathrooms"
    " + note + sans_note + log_nb_avis + superhote + log_nuits_min"
    " + hote_multi_annonces + C(arrondissement)"
)


def charger_donnees_regression():
    """Charge les huit relevés locaux et applique le même périmètre parisien."""
    absents = [str(chemin_cache(a, m)) for a in [2024, 2026] for m in MOIS_ETE
               if not chemin_cache(a, m).exists()]
    if absents:
        raise FileNotFoundError("Préparer les relevés avec python importation_données.py.\n"
                                + "\n".join(absents))
    paris = unary_union([shape(f["geometry"]) for f in charger_contours()])
    releves = {}
    for annee in [2024, 2026]:
        for mois in MOIS_ETE:
            brut = lire_releve(annee, mois)
            brut["prix"] = pd.to_numeric(
                brut["price"].astype("string").str.replace(r"[$,]", "", regex=True), errors="coerce")
            for colonne in ["latitude", "longitude"]:
                brut[colonne] = pd.to_numeric(brut[colonne], errors="coerce")
            releves[(annee, mois)] = preparer_population(brut, paris)[0]
    sites = (pd.concat(charger_tables_locales()).dropna(subset=["latitude", "longitude"])
             .drop_duplicates("code_site").reset_index(drop=True))
    return releves, sites


def distance_km(lat1, lon1, lat2, lon2):
    """Haversine en kilomètres, avec protection contre les erreurs d'arrondi."""
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    a = (np.sin((lat2-lat1)/2)**2
         + np.cos(lat1)*np.cos(lat2)*np.sin((lon2-lon1)/2)**2)
    return 2*6371.0*np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def distance_site_le_plus_proche(annonces, sites):
    """Renvoie la distance minimale et le code du site pour chaque annonce."""
    distances = distance_km(
        annonces.latitude.to_numpy()[:, None], annonces.longitude.to_numpy()[:, None],
        sites.latitude.to_numpy()[None, :], sites.longitude.to_numpy()[None, :])
    return distances.min(axis=1), sites.code_site.to_numpy()[distances.argmin(axis=1)]


def cellule_500m(lat, lon):
    """Identifiant géographique stable entre relevés pour les erreurs regroupées."""
    ligne = np.floor(np.asarray(lat)/0.0045).astype(np.int64)
    colonne = np.floor(np.asarray(lon)/0.0068).astype(np.int64)
    return (ligne+20000)*100000+(colonne+30000)


def en_pourcent(coefficient):
    """Convertit un coefficient sur le logarithme du prix en écart relatif (%)."""
    return (np.exp(coefficient)-1)*100


def preparer(df, sites):
    """Variables hédoniques ; retrait des prix extrêmes propre à chaque relevé."""
    df = df.assign(prix=pd.to_numeric(
        df.price.astype("string").str.replace(r"[$,]", "", regex=True), errors="coerce"))
    df = df.loc[df.prix.gt(0)].copy()
    df = df.loc[df.prix.between(*df.prix.quantile([0.01, 0.99]))].copy()
    df["log_prix"] = np.log(df.prix)
    df["dist_site_km"], _ = distance_site_le_plus_proche(df, sites)
    # Le libellé historique « plus de 3 km » comprend la borne 3 km.
    df["tranche"] = pd.cut(df.dist_site_km, [0, 1, 3, np.inf], right=False,
                           labels=["moins de 1 km", "1 à 3 km", "plus de 3 km"])
    df["dist_centre_km"] = distance_km(df.latitude, df.longitude, *CENTRE_PARIS)
    df["cellule"] = cellule_500m(df.latitude, df.longitude)
    df["arrondissement"] = df.neighbourhood_cleansed
    df["sans_note"] = df.review_scores_rating.isna().astype(int)
    df["note"] = df.review_scores_rating.fillna(df.review_scores_rating.mean())
    df["log_nb_avis"] = np.log1p(df.number_of_reviews)
    df["log_nuits_min"] = np.log(df.minimum_nights.clip(lower=1))
    df["superhote"] = df.host_is_superhost.eq("t").astype(int)
    df["hote_multi_annonces"] = df.calculated_host_listings_count.gt(1).astype(int)
    return df.dropna(subset=["bedrooms", "bathrooms", "accommodates", "room_type",
                             "arrondissement", "log_nb_avis", "log_nuits_min"])


def estimer(formule, donnees):
    """OLS avec contrôle du rang et erreurs regroupées par cellule géographique."""
    modele = smf.ols(formule, data=donnees)
    if len(modele.endog) != len(donnees) or not np.isfinite(modele.exog).all():
        raise ValueError("Échantillon ou valeurs non finies à vérifier.")
    if np.linalg.matrix_rank(modele.exog) != modele.exog.shape[1]:
        raise ValueError("Matrice de régression non identifiable.")
    return modele.fit(cov_type="cluster", cov_kwds={"groups": donnees.cellule.to_numpy()})


def etoiles(p):
    return "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.1 else ""


def regression_hedonique(releves, sites):
    """Estime les primes de proximité et leur différence entre 2024 et 2026."""
    lignes, modeles = [], {}
    for mois in ["juin", "juillet"]:
        d24, d26 = (preparer(releves[(annee, mois)], sites) for annee in [2024, 2026])
        m24, m26 = estimer(FORMULE, d24), estimer(FORMULE, d26)
        modeles[f"{mois} 2024"], modeles[f"{mois} 2026"] = m24, m26
        test = estimer(FORMULE.replace(TRANCHE, f"{TRANCHE} * annee_2024"),
                       pd.concat([d24.assign(annee_2024=1), d26.assign(annee_2024=0)], ignore_index=True))
        for tranche in ["moins de 1 km", "1 à 3 km"]:
            nom = f"{TRANCHE}[T.{tranche}]"
            lignes.append({"mois": mois, "tranche": tranche,
                "prime 2024 (%)": en_pourcent(m24.params[nom]), "p 2024": m24.pvalues[nom],
                "prime 2026 (%)": en_pourcent(m26.params[nom]), "p 2026": m26.pvalues[nom],
                "écart relatif 2024 / 2026 (%)": en_pourcent(test.params[nom+":annee_2024"]),
                "p écart": test.pvalues[nom+":annee_2024"]})
    coefficients = pd.DataFrame({
        releve: [f"{b:.3f}{etoiles(p)}" if m.model.exog[:, j].std() > 0 or nom == "Intercept"
                 else "non disponible"
                 for j, (nom, b, p) in enumerate(zip(m.params.index, m.params, m.pvalues))]
        for releve, m in modeles.items()}, index=next(iter(modeles.values())).params.index)
    coefficients = coefficients[~coefficients.index.str.startswith(("C(arrondissement)", "Intercept"))]
    coefficients.index = (coefficients.index.str.replace(f"{TRANCHE}[T.", "distance au site : ", regex=False)
                          .str.replace("C(room_type)[T.", "type : ", regex=False).str.rstrip("]"))
    coefficients.loc["R²"] = [f"{m.rsquared:.3f}" for m in modeles.values()]
    coefficients.loc["annonces"] = [f"{int(m.nobs)}" for m in modeles.values()]
    return pd.DataFrame(lignes).set_index(["mois", "tranche"]).round(3), coefficients


def construire_panel(releves, sites):
    """Groupes fixes par identifiant ; bornes des prix communes aux mois d'une année."""
    morceaux = [table.assign(annee=annee, mois=MOIS_ETE[mois])
                for (annee, mois), table in releves.items()]
    ete = pd.concat(morceaux, ignore_index=True).drop_duplicates(["id", "annee", "mois"])
    positions = ete.groupby("id")[["latitude", "longitude"]].median()
    positions["dist_site_km"], _ = distance_site_le_plus_proche(positions, sites)
    positions["cellule"] = cellule_500m(positions.latitude, positions.longitude)
    positions["groupe"] = np.select([positions.dist_site_km < 1, positions.dist_site_km > 2],
                                    ["proche", "témoin"], default="intermédiaire")
    ete = ete.merge(positions[["groupe", "cellule"]], left_on="id", right_index=True)
    ete = ete.loc[ete.groupe.ne("intermédiaire")].copy()
    ete["proche"] = ete.groupe.eq("proche").astype(int)
    ete["prix"] = pd.to_numeric(ete.price.astype("string").str.replace(r"[$,]", "", regex=True), errors="coerce")
    ete.loc[~ete.prix.gt(0), "prix"] = np.nan
    bornes = ete.groupby("annee").prix.quantile([0.01, 0.99]).unstack()
    valide = ete.prix.between(ete.annee.map(bornes[0.01]), ete.annee.map(bornes[0.99]))
    # Convertir les valeurs masquées en NaN avant le logarithme évite de calculer
    # log(0) sur les données internes masquées des tableaux nullable de pandas.
    prix_valides = ete.prix.where(valide).to_numpy(dtype=float, na_value=np.nan)
    ete["log_prix"] = np.log(prix_valides)
    return ete


def effectifs_panel(panel):
    """Identifiants distincts avant exclusion finale des prix non exploitables."""
    return panel.groupby(["annee", "groupe"]).id.nunique().unstack().rename_axis(None, axis=1)


def ecarts(donnees, noms, entite, temps):
    donnees = donnees.set_index([entite, temps])
    return PanelOLS(donnees.log_prix, donnees[noms], entity_effects=True, time_effects=True).fit(
        cov_type="clustered", clusters=donnees[["cellule"]])


def regression_panel(panel):
    """Renvoie la triple différence, la figure et les effectifs réellement estimés."""
    d = panel.dropna(subset=["log_prix"]).copy()
    d["annonce_annee"] = pd.factorize(d.id.astype(str)+"_"+d.annee.astype(str))[0]
    d["periode"] = d.annee*100+d.mois
    for mois in [7, 8, 9]:
        d[f"proche × {mois}"] = d.proche*d.mois.eq(mois)
        d[f"proche × {mois} × 2024"] = d[f"proche × {mois}"]*d.annee.eq(2024)
    noms = [f"proche × {mois}" for mois in [7, 8, 9]]
    noms_jeux = [f"proche × {mois} × 2024" for mois in [7, 8, 9]]
    triple = ecarts(d, noms+noms_jeux, "annonce_annee", "periode")
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for annee, couleur in [(2024, "#e27100"), (2026, "#1855c9")]:
        r = ecarts(d.loc[d.annee.eq(annee)], noms, "id", "mois")
        effet, ic = en_pourcent(r.params.to_numpy()), en_pourcent(r.conf_int().to_numpy())
        ax.errorbar(np.array([7, 8, 9])+(0.08 if annee == 2026 else -0.08), effet,
                    yerr=[effet-ic[:, 0], ic[:, 1]-effet], fmt="o-", capsize=3,
                    color=couleur, label=f"{annee} (proches - témoins, vs juin)")
    ax.axhline(0, color="grey", linewidth=0.8)
    ax.set_xticks([7, 8, 9], ["juillet", "août", "septembre"])
    ax.set_ylabel("Écart relatif de prix affiché (%)")
    ax.set_xlabel("Relevé : juillet à septembre ; référence juin (2024 et 2026)")
    ax.set_title("Prix proches contre éloignés depuis juin\nÉté 2024 (Jeux) et été 2026 (comparaison)")
    ax.legend(fontsize=8)
    fig.tight_layout()
    # Une figure fermée reste affichable dans le notebook et enregistrable en PNG.
    plt.close(fig)
    resultats = pd.DataFrame({
        "supplément relatif 2024 (%)": en_pourcent(triple.params[noms_jeux]).to_numpy(),
        "bas IC 95 %": en_pourcent(triple.conf_int().loc[noms_jeux, "lower"]).to_numpy(),
        "haut IC 95 %": en_pourcent(triple.conf_int().loc[noms_jeux, "upper"]).to_numpy(),
        "p-valeur": triple.pvalues[noms_jeux].to_numpy()}, index=["juillet", "août", "septembre"]).round(3)
    diagnostic = {"observations": len(d), "annonces_années": d.annonce_annee.nunique(),
                  "cellules_spatiales": d.cellule.nunique()}
    return resultats, fig, diagnostic


def main():
    releves, sites = charger_donnees_regression()
    primes, coefficients = regression_hedonique(releves, sites)
    panel = construire_panel(releves, sites)
    effectifs = effectifs_panel(panel)
    triple, figure, diagnostic = regression_panel(panel)
    sortie = RACINE / "resultats"
    sortie.mkdir(exist_ok=True)
    for nom, table in [("primes", primes), ("coefficients", coefficients),
                       ("effectifs", effectifs), ("triple_difference", triple)]:
        print(f"\n{nom}\n{table.to_string()}")
    figure.savefig(sortie/"regression_panel.png", dpi=160, bbox_inches="tight")
    print("\nEffectifs estimés :", diagnostic)


if __name__ == "__main__":
    main()
