# Airbnb et les Jeux de Paris 2024

Le projet étudie l'évolution de l'offre Airbnb et des prix affichés à Paris en 2024, puis cherche si les annonces proches des sites de compétition ont connu une hausse particulière pendant les Jeux. Tous les prix sont exprimés en **dollars par nuit**, sans conversion en euros.

**Le document de rendu est `Final report.ipynb`.** Il contient les analyses descriptives, les neuf cartes de prix, les dix-neuf courbes par site, l'étude des cérémonies et les régressions linéaires. Les modèles y sont directement exécutables.

## Environnement

La vérification utilise **Python 3.14.6**. Les versions des bibliothèques utilisées sont fixées dans `requirements.txt`. Elles nécessitent Python 3.12 ou supérieur ; Python 3.14 est recommandé pour se rapprocher de l'environnement de vérification. Les versions transitives restent déterminées par l'installateur : ce fichier ne constitue pas un verrouillage intégral de l'environnement.

Depuis la racine du dépôt, dans PowerShell :

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m ipykernel install --sys-prefix --name airbnb-paris --display-name "Python (Airbnb Paris)"
```

Ces commandes utilisent explicitement l'environnement virtuel ; son activation dans PowerShell n'est pas nécessaire. Sous Linux ou macOS, créer l'environnement avec `python3.14 -m venv .venv`, puis remplacer `.\.venv\Scripts\python.exe` par `.venv/bin/python`.

## Préparer les données

Les fonctions de collecte et de chargement sont regroupées dans `src/importation_données.py`.

```powershell
.\.venv\Scripts\python.exe src/importation_données.py --source sites
.\.venv\Scripts\python.exe src/importation_données.py --tous-mois-2024
.\.venv\Scripts\python.exe src/analyse_ceremonies.py
```

La première commande télécharge et prépare les sites olympiques et paralympiques. La deuxième récupère les **onze relevés distincts de 2024**, de janvier à décembre hors mars, ainsi que les **quatre relevés de juin à septembre 2026**. Sans l'option `--tous-mois-2024`, seuls les huit relevés des deux étés sont préparés.

La lecture des CSV distants peut représenter plusieurs gigaoctets transférés lors de la première préparation. Le cache conserve uniquement les colonnes utiles, sous forme compressée, en gardant toutes les lignes et les prix manquants. Les fichiers déjà présents sont réutilisés. Les manifestes associés indiquent les URL, les dates de récupération et les colonnes disponibles. La troisième commande recalcule les tableaux et le graphique des cérémonies dans `resultats/`.

Les dossiers `data/donnees_sites/`, `data/donnees_airbnb/` et `data/donnees_externes/` sont exclus de Git pour ne pas laisser les données en libre service. Il faut donc les préparer sur une nouvelle machine. Les téléchargements dépendent du maintien de l'accès aux sources distantes ; les URL et dates des relevés 2026 sont fixées dans le programme. Une fois les quinze relevés et les sites préparés, les cellules du rapport utilisent les données locales.

`src/telecharger_donnees_externes.py` est un ancien téléchargement des fichiers 2026 complets dans `data/donnees_externes/`. Il ne prépare pas le cache commun attendu par le rapport et ne fait pas partie du parcours de reproduction ci-dessus.

## Exécuter le notebook final

Dans VS Code, ouvrir `Final report.ipynb`, sélectionner **Python (Airbnb Paris)** ou l'interpréteur `.venv`, puis choisir **Redémarrer le noyau et tout exécuter**. Dans JupyterLab, sélectionner le même noyau et lancer **Restart Kernel and Run All Cells**.

Pour une exécution complète en ligne de commande, avec sauvegarde des sorties dans le notebook :

```powershell
.\.venv\Scripts\python.exe -m jupyter nbconvert --to notebook --execute --inplace "Final report.ipynb" --ExecutePreprocessor.kernel_name=airbnb-paris --ExecutePreprocessor.timeout=900
```

Le calcul s'effectue dans un noyau neuf. Il peut prendre plusieurs minutes selon la machine. Le rapport appelle directement les fonctions de préparation et d’estimation de `src/regression_lineaire.py` : il n'est pas nécessaire d'exécuter d'abord `notebooks/regression_sur_le_prix.ipynb`.

Tout le code de préparation statistique, de régression linéaire et de panel est regroupé dans `src/regression_lineaire.py`. Pour lancer ces calculs sans ouvrir de notebook :

```powershell
.\.venv\Scripts\python.exe src/regression_lineaire.py
```

## Figures du dépôt

Les images déjà enregistrées sont affichées par le rapport. Les analyses complémentaires sont accessibles en dépliant les galeries. Pour régénérer les cartes et courbes :

```powershell
.\.venv\Scripts\python.exe src/carte_sites_paris.py --mois juillet --sans-fenetre --analyse-complete
.\.venv\Scripts\python.exe src/carte_sites_paris.py --mois aout --sans-fenetre --analyse-complete
.\.venv\Scripts\python.exe src/carte_sites_paris.py --mois septembre --sans-fenetre --analyse-complete
.\.venv\Scripts\python.exe src/prix_en_fonction_de_la_distance.py
```

Les cartes utilisent une échelle de prix commune et au moins cinq prix par maille. Les courbes historiques portent sur des moyennes par tranche de distance ; leur ligne « mars » duplique juin et ne constitue pas un relevé supplémentaire. Le script de régénération exclut mars et exporte aussi les effectifs et médianes par tranche. Les comparaisons ajoutées au rapport sont calculées sur les données nettoyées, avec leurs propres effectifs.

## Organisation

```
├── Final report.ipynb          Rapport final (document de rendu)
├── README.md
├── requirements.txt
├── notebooks/
│   └── regression_sur_le_prix.ipynb
├── src/                        Code Python (collecte, cartes, distances, cérémonies, régressions)
├── data/                       Fichiers géographiques versionnés + données préparées localement (exclues de Git)
├── figures/
│   ├── cartes_prix/            Cartes des prix médians (+ analyses_complementaires/)
│   └── sites_par_mois/         Courbes prix/distance par site olympique
└── resultats/                  Tableaux et graphiques des cérémonies et de la régression
```

Toutes les commandes se lancent **depuis la racine du dépôt**.

| Fichier | Rôle |
| --- | --- |
| `Final report.ipynb` | Rapport complet : données, analyses descriptives, cartes, distances, cérémonies, régressions et conclusion. |
| `notebooks/regression_sur_le_prix.ipynb` | Explicaiton régression linéaire, obtenus avec les mêmes fonctions Python que le rapport. |
| `src/importation_données.py` | Collecte Airbnb 2024/2026, cache partagé, chargement des sites et fichiers géographiques ; séries contextuelles optionnelles. |
| `src/sites_competition.py` | Préparation des sites, corrections de dates documentées et séparation des deux Jeux. |
| `src/carte_sites_paris.py` | Nettoyage parisien et cartes des prix médians par maille. |
| `src/prix_en_fonction_de_la_distance.py` | Courbes autour des sites olympiques parisiens et tableaux de contrôle des tranches. |
| `src/analyse_ceremonies.py` | Comparaison des prix près des deux tracés simplifiés et sensibilité aux seuils. |
| `src/regression_lineaire.py` | Code complet des modèles de régression linéaire; tableaux affichés dans le notebook ou le terminal, et graphique de régression. |
| `data/parcours_ceremonies.geojson` | Tracés de travail approximatifs, avec sources ; ce ne sont pas des traces GPS officielles. |
| `data/contours_arrondissements.geojson` | Contours des vingt arrondissements utilisés pour sélectionner les annonces parisiennes. |
| `resultats/` | Tableaux et graphique des cérémonies ; graphique de la régression. |
| `figures/cartes_prix/`, `figures/sites_par_mois/` | Figures incluses dans le rapport. |

## Sources et portée des résultats

- Annonces 2024 : relevés [Inside Airbnb](https://insideairbnb.com/get-the-data/) copiés sur SSP Cloud ; chemins explicités dans `src/importation_données.py`. Mars est exclu car il duplique juin.
- Annonces 2026 : quatre relevés Inside Airbnb, utilisés comme année de comparaison sans Jeux ; leurs dates nominales et URL sont explicites dans le fichier d'importation.
- Sites : [ministère chargé des Sports, via data.gouv.fr](https://www.data.gouv.fr/api/1/datasets/r/5a0599d1-ad3f-42d1-b64c-204ee19cf520).
- Contours : [arrondissements de Paris, Paris Data](https://opendata.paris.fr/explore/dataset/arrondissements/).
- Cérémonies : sources du CIO et de la Ville de Paris citées dans le rapport et le GeoJSON. Les tracés simplifiés ne représentent ni les périmètres de sécurité ni une visibilité sur le défilé.

La description montre une offre maximale en juillet et un prix médian maximal en août 2024. Les modèles ne détectent pas de supplément de hausse statistiquement significatif près des sites au seuil de 5 %. En août, l'estimation relative vaut +1,54 %, avec un intervalle à 95 % de −0,34 % à +3,46 %. Cela ne démontre ni l'absence de tout effet des Jeux, ni que la prime de proximité provient uniquement de l'emplacement.

Une annonce observée n'est pas forcément louée, une nuit indisponible n'est pas forcément réservée et un prix affiché n'est pas nécessairement payé. Les prix manquants, les coordonnées approximatives, la collecte discontinue, les changements entre 2024 et 2026 et le manque de recul avant les Jeux limitent l'interprétation causale. Les séries Eurostat et INSEE prévues par le fichier d'importation restent optionnelles et ne sont pas exploitées dans les résultats du rapport.
