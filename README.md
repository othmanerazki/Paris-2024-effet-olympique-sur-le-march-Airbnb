# Airbnb et les Jeux de Paris 2024

Le projet étudie l'offre Airbnb et les prix affichés à Paris, puis cherche si les annonces proches des sites ont connu une hausse particulière pendant les Jeux. Il combine description annuelle, cartes, courbes par site, régression linéaire sur le logarithme du prix et panel comparant 2024 à 2026. Les prix sont en **dollars**, sans conversion.

## Lire le rapport

Ouvrir **[Final report.ipynb](Final%20report.ipynb)** dans Jupyter ou VS Code. Les résultats disponibles sont intégrés aux sorties. **[Final report.html](Final%20report.html)** offre une lecture sans code et sans connexion, avec les figures incorporées. Les galeries complémentaires se déplient au clic.

Le rapport distingue les calculs descriptifs et les résultats économétriques déjà enregistrés : afficher ces derniers ne réestime pas les modèles. Le notebook source est [regression_sur_le_prix.ipynb](regression_sur_le_prix.ipynb).

## Installer et recalculer

Depuis la racine du dépôt, avec Python et un environnement virtuel activé :

```powershell
python -m pip install -r requirements.txt
python importation_données.py --source sites
jupyter lab
```

1. Lancer `python importation_données.py` pour mettre en cache les huit relevés de l'été 2024 et 2026, puis `python verifier_regression.py` pour exécuter intégralement le notebook de régression corrigé.
2. Ouvrir `Final report.ipynb` et exécuter les cellules dans l'ordre. Les relevés descriptifs 2024 sont lus sur SSP Cloud ; une connexion et l'accès aux fichiers distants sont nécessaires.
3. Pour produire le HTML après exécution du notebook, lancer `jupyter nbconvert --to html --no-input "Final report.ipynb"`.

Le dépôt ne contient pas les fichiers bruts volumineux. `donnees_sites/`, `donnees_airbnb/` et `donnees_externes/` sont exclus de Git. La disponibilité des liens distants conditionne le recalcul complet. Les huit relevés d'été ont été téléchargés, les régressions corrigées et réestimées, et les neuf cartes régénérées depuis le cache. Les autres mois de la description annuelle conservent leurs sorties précédentes.

`python analyse_ceremonies.py` calcule les prix à proximité des deux parcours simplifiés et leur sensibilité aux seuils de 0,5, 0,75 et 1 km. Les lignes de travail sont documentées dans `parcours_ceremonies.geojson` : ce ne sont pas des traces GPS officielles.

## Régénérer les figures

```powershell
python carte_sites_paris.py --mois juillet --sans-fenetre --analyse-complete
python carte_sites_paris.py --mois aout --sans-fenetre --analyse-complete
python carte_sites_paris.py --mois septembre --sans-fenetre --analyse-complete
python prix_en_fonction_de_la_distance.py
```

Les cartes utilisent une échelle commune et au moins cinq prix par maille. Le script des courbes utilise les relevés distincts de la liste explicite de `carte_sites_paris.py`, retire les prix non positifs et exporte les effectifs et médianes par tranche dans des CSV de contrôle. Les figures historiques du dépôt conservent une ligne « mars », doublon de juin : le rapport le signale et ne traite pas ce mois comme une observation supplémentaire. Leurs axes ont été corrigés en dollars sans changer les courbes.

## Fichiers et sources

- `carte_sites_paris.py` : relevés 2024, nettoyage et cartes des prix médians.
- `sites_competition.py` : collecte et préparation des sites olympiques et paralympiques, avec références des corrections de dates.
- `prix_en_fonction_de_la_distance.py` : courbes de prix moyens autour des sites olympiques parisiens.
- `regression_sur_le_prix.ipynb` : modèles hédoniques et triple différence ; tous les sites sont inclus dans le calcul de proximité.
- `importation_données.py` : toutes les fonctions de collecte et de chargement (Airbnb 2024/2026, cache, sites, contours, parcours, Eurostat et INSEE).
- `analyse_ceremonies.py` : médianes et couverture des prix près des parcours des cérémonies.

Les annonces proviennent d'[Inside Airbnb](https://insideairbnb.com/get-the-data/) ; les copies 2024 sont hébergées sur SSP Cloud aux chemins documentés dans `importation_données.py`. Les sites viennent du [ministère chargé des Sports](https://www.data.gouv.fr/api/1/datasets/r/5a0599d1-ad3f-42d1-b64c-204ee19cf520). Les contours des arrondissements viennent de [Paris Data](https://opendata.paris.fr/explore/dataset/arrondissements/).

Les prix sont affichés, pas nécessairement payés. Les coordonnées sont approximatives et la couverture des prix varie selon le relevé. L'absence d'effet relatif significatif près des sites ne démontre pas l'absence de tout effet des Jeux sur Paris.
