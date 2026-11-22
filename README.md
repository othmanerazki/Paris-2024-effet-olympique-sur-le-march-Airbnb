# Airbnb et les Jeux de Paris 2024

Ce projet de groupe étudie l'évolution des annonces Airbnb et de leurs prix affichés autour des sites des Jeux olympiques et paralympiques. Les résultats sont descriptifs : une variation observée ne démontre pas, à elle seule, un effet causal des Jeux.

## Installer et lancer le projet

Depuis le dossier du projet, avec Python et un environnement virtuel activé :

```bash
python -m pip install -r requirements.txt
python sites_competition.py
jupyter lab
```

La seconde commande télécharge et prépare les données des sites dans `donnees_sites/donnees_nettoyees.csv`, dossier non suivi par Git. Elle demande une connexion Internet. Dans JupyterLab, ouvrir `analyse_descriptive.ipynb` et exécuter ses cellules dans l'ordre. L'exécution utilise Internet pour lire les relevés Airbnb sur SSP Cloud et peut prendre plusieurs minutes. Les fichiers sont accessibles sous réserve du maintien du partage public SSP Cloud.


Pour produire une carte de prix :

```bash
python carte_sites_paris.py --mois aout --sans-fenetre
```

Les images sont enregistrées dans `cartes prix/`. Le notebook descriptif ne régénère pas ces cartes. Les prix sont exprimés en dollars.

## Données

- Relevés d'annonces Airbnb pour 2024 : source Inside Airbnb, copies hébergées sur SSP Cloud sous `etiennealpy/données paris/` ; les chemins utilisés par les cartes figurent dans `carte_sites_paris.py`. La disponibilité future des copies et les conditions de partage doivent être vérifiées.
- Sites des Jeux : [données du ministère chargé des Sports via data.gouv.fr](https://www.data.gouv.fr/api/1/datasets/r/5a0599d1-ad3f-42d1-b64c-204ee19cf520), avec les corrections et leurs références documentées dans `sites_competition.py`.
- Contours : `contours_arrondissements.geojson`, provenant des [données des arrondissements de Paris](https://opendata.paris.fr/explore/dataset/arrondissements/).

Les relevés sont des photographies à une date donnée. Le prix affiché ne correspond pas nécessairement à une réservation ou à un prix payé. Les coordonnées des annonces sont approximatives. Les prix sont en dollars ; la comparabilité des relevés doit être examinée avant leur interprétation.
