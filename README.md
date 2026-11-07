# Projet d’analyse de vols et d’aéroports

Ce projet regroupe un ensemble de scripts Python et une base de requêtes SQL pour analyser des données de vols, comparer les aéroports, mesurer les retards, détecter les données manquantes et produire des visualisations de synthèse.

## Objectif

L’objectif principal est d’explorer les volumes de trafic, les tendances temporelles, les itinéraires les plus fréquentés, les retards de vol, les anomalies de données et les corrélations entre distance et performance.

Le dépôt contient :
- des fichiers CSV synthétiques et agrégés dans le dossier `data/` ;
- des graphiques générés dans le dossier `charts/` ;
- des scripts Python dans `scripts/` ;
- une requête SQL MySQL 8 dans `sql/airport_analytics_mysql8.sql`.

## Structure du dépôt

- `data/airports/` : fichiers CSV de vols par aéroport.
- `data/date_filter_analysis/` : résultats sur les filtres de date et graphiques associés.
- `data/flight_cancellation_analysis/` : synthèses sur les annulations et les données manquantes.
- `data/airport_route_mapping/` : export des routes et cartes associées.
- `charts/` : images générées par les analyses.
- `scripts/` : scripts de génération, traitement et visualisation.
- `sql/airport_analytics_mysql8.sql` : schéma MySQL, vues métier et requêtes analytiques.
- `requirements.txt` : dépendances Python requises.

## Prérequis

Le projet dépend de Python 3 et des bibliothèques suivantes :

- matplotlib
- csv / pathlib / collections / datetime (bibliothèques standard)

Installez les dépendances avec :

```bash
python -m pip install -r requirements.txt
```

## Génération des données

Le script `scripts/generate_airport_flights.py` crée des fichiers CSV de vols par aéroport dans `data/airports/`.

```bash
python scripts/generate_airport_flights.py
```

Ce script produit des données synthétiques avec des identifiants d’avion, des horaires de départ/arrivée, des durées de vol et des aéroports de départ/arrivée.

## Scripts disponibles

### `scripts/generate_airport_flights.py`
Génère les fichiers de données de vols pour les aéroports cibles et crée un résumé global.

### `scripts/airport_traffic_compare.py`
Compare la fréquentation des aéroports, affiche les vols par aéroport et génère le résumé CSV associé.

### `scripts/airport_timeline_analysis.py`
Crée des chronologies de vols et des densités mensuelles pour la série temporelle de chaque aéroport.

### `scripts/airport_date_filters.py`
Applique des filtres de date (1er janvier, mois de novembre/décembre, jours spéciaux, été, départ très tôt) et exporte les résultats et graphiques associés.

### `scripts/airport_advanced_analysis.py`
Produit des analyses avancées sur les volumes mensuels, les distributions de durée, les routes les plus fréquentes, la fréquentation par avion et la matrice de trafic par aéroport.

### `scripts/airport_route_mapping.py`
Construit des cartes de routes au niveau spatial, notamment pour les itinéraires domestiques aux États-Unis, en utilisant des coordonnées GPS.

### `scripts/flight_delay_analysis.py`
Calcule les métriques de retard, compare les retards au départ et à l’arrivée, et exporte les vols les plus retardés.

### `scripts/flight_distance_delay_analysis.py`
Étudie la relation entre distance du vol, retard à l’arrivée, retard au départ et vitesse calculée.

### `scripts/flight_custom_sort_analysis.py`
Réalise un tri personnalisé sur les heures HHMM, classe les vols selon les retards et compare les temps de vol réels avec le temps de vol en vol.

### `scripts/flight_cancellation_missing_data.py`
Identifie les colonnes incomplètes, les vols annulés et les tendances par destination, compagnie et mois.

## Exécution des analyses

La plupart des scripts utilisent les fichiers CSV présents dans `data/airports/` et écrivent leurs résultats dans `data/` ou `charts/` selon le cas.

Exemples :

```bash
python scripts/airport_date_filters.py
python scripts/airport_traffic_compare.py
python scripts/airport_advanced_analysis.py
python scripts/flight_delay_analysis.py
python scripts/flight_cancellation_missing_data.py
```

## SQL MySQL

Le fichier `sql/airport_analytics_mysql8.sql` contient :
- création et mise à jour du schéma ;
- insertion de données d’aéroports et de filtres de dates ;
- vues calculées pour les métriques de temps et de retard ;
- analyses de trafic, de retard, de données manquantes et de routes.

Pour l’exécuter dans MySQL 8 :

```sql
SOURCE sql/airport_analytics_mysql8.sql;
```

## Sorties attendues

Les scripts produisent des fichiers CSV et des graphiques dans les dossiers suivants :

- `data/date_filter_analysis/`
- `data/flight_cancellation_analysis/`
- `data/airport_route_mapping/`
- `charts/airports/`
- `charts/advanced_analysis/`

## Notes

- Les scripts utilisent largement `matplotlib` avec le mode `Agg` pour permettre l’export sans interface graphique.
- Les sorties sont conçues pour rester compatibles avec un environnement de traitement de données en ligne de commande.
- Les fichiers générés sont destinés à être réutilisés dans des analyses supplémentaires ou des tableaux de bord.
