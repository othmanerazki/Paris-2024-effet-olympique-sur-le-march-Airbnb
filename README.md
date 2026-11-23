# Airbnb et les Jeux de Paris 2024

**Question** : les Jeux olympiques et paralympiques de Paris 2024 ont-ils transformé le marché Airbnb parisien, et en particulier fait monter les prix des annonces proches des sites de compétition ?

Le projet se déroule en deux temps :

1. **Description** : nombre d'annonces, prix affichés, disponibilité et types de logement au fil de 2024, puis cartes et graphiques des prix selon la distance aux sites.
2. **Régression** : mesure de l'effet des Jeux sur les prix. On sépare cet effet de l'emplacement (les sites sont dans des quartiers touristiques) et de la saisonnalité grâce à une année de comparaison sans Jeux, 2026.

## Contenu du dépôt

| Fichier | Rôle |
|---|---|
| `Final report.ipynb` | Rapport descriptif : sources, sites, qualité des relevés, prix et types de logement en 2024 |
| `regression_sur_le_prix.ipynb` | Régressions : prime de prix près des sites (2024 contre 2026) et triple différence |
| `sites_competition.py` | Télécharge et prépare les sites olympiques et paralympiques (corrections documentées dans le script) |
| `importation_données.py` | Lit les relevés Airbnb 2024 sur SSP Cloud |
| `carte_sites_paris.py` | Cartes des prix médians par maille avec les sites des Jeux (sorties dans `cartes prix/`) |
| `prix_en_fonction_de_la_distance.py` | Graphiques du prix selon la distance à chaque site (sorties dans `graphiques_sites_paris_tous_les_mois/`) |
| `telecharger_donnees_externes.py` | Télécharge les relevés Inside Airbnb de juin à septembre 2026 |
| `contours_arrondissements.geojson` | Contours des 20 arrondissements de Paris |

## Installer et lancer

Depuis le dossier du projet, avec Python et un environnement virtuel activé :

```bash
python -m pip install -r requirements.txt
python sites_competition.py              # sites des Jeux -> donnees_sites/
python telecharger_donnees_externes.py   # relevés 2026 -> donnees_externes/ (environ 160 Mo)
jupyter lab
```

Ouvrir ensuite les notebooks et exécuter leurs cellules dans l'ordre : `Final report.ipynb`, puis `regression_sur_le_prix.ipynb`. Le notebook de régression lance lui-même les deux scripts ci-dessus si leurs données manquent. Il télécharge aussi les relevés 2024 utiles (environ 200 Mo chacun) dans `donnees_airbnb/` lors de la première exécution. Tout cela demande une connexion Internet et prend plusieurs minutes. Les dossiers de données ne sont pas suivis par Git.

Cartes et graphiques (optionnels, déjà enregistrés dans le dépôt) :

```bash
python carte_sites_paris.py --mois aout --sans-fenetre
python prix_en_fonction_de_la_distance.py
```

## Données

- **Annonces Airbnb 2024** : relevés mensuels [Inside Airbnb](https://insideairbnb.com/), copies hébergées par le groupe sur SSP Cloud (`etiennealpy/données paris/`), sous réserve du maintien du partage public. Le fichier nommé « mars » est identique à celui de juin et est écarté.
- **Annonces Airbnb 2026** : relevés publics [Inside Airbnb](https://insideairbnb.com/get-the-data/) de juin à septembre 2026, utilisés comme année de comparaison sans Jeux. Inside Airbnb ne publie que les 12 derniers mois : ces fichiers ne resteront pas disponibles indéfiniment.
- **Sites des Jeux** : [données du ministère chargé des Sports via data.gouv.fr](https://www.data.gouv.fr/api/1/datasets/r/5a0599d1-ad3f-42d1-b64c-204ee19cf520).
- **Contours** : [arrondissements de Paris, Paris Data](https://opendata.paris.fr/explore/dataset/arrondissements/).

## Principaux résultats

D'après la régression, les Jeux n'ont **pas fait monter les prix de façon mesurable** près des sites. À caractéristiques égales, une annonce à moins de 1 km d'un site est 4 à 6 % plus chère, mais cette prime est la même en 2026 : elle vient de l'emplacement. En suivant les mêmes annonces de juin à septembre et en retirant la saisonnalité grâce à 2026, l'effet des Jeux est compris entre −0,7 % et +1,5 % selon le mois, et n'est significatif aucun mois.

## Limites

- Les relevés sont des photos à une date donnée : le prix affiché est un devis, pas un prix payé, et les annonces complètes n'ont pas de prix.
- Les coordonnées des annonces sont décalées par Airbnb (jusqu'à environ 150 m).
- Les prix sont en dollars, sans conversion.
- La partie descriptive ne permet pas, seule, de conclure à un effet causal. La régression s'en approche en supposant que, sans les Jeux, la saisonnalité des quartiers proches des sites aurait été la même en 2024 et en 2026, deux ans plus tard.
