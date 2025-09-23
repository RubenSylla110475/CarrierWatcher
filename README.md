# CarrierWatcher

CarrierWatcher est une application Streamlit qui vous aide à suivre manuellement vos candidatures de stage de fin d'étude. Les candidatures sont enregistrées dans un fichier Excel local (`data/applications.xlsx`) et l'interface propose une visualisation claire et professionnelle de votre suivi.

## Fonctionnalités

- Formulaire simple pour ajouter une candidature (code, entreprise, thématique, domaine, dates, statut).
- Tableau de bord synthétique avec le nombre total de candidatures, celles acceptées, refusées et en attente.
- Tableau filtrable par statut, domaine et thématique.
- Graphique de répartition des candidatures par statut.
- Stockage local dans un fichier Excel pour conserver toutes les candidatures.

## Prérequis

- Python 3.9 ou supérieur

## Installation

```bash
python -m venv .venv
source .venv/bin/activate  # Sous Windows : .venv\\Scripts\\activate
pip install -r requirements.txt
```

## Lancement de l'application

```bash
streamlit run app.py
```

La première exécution crée automatiquement le dossier `data` ainsi que le fichier Excel de suivi. Vous pouvez ensuite accéder à l'application dans votre navigateur à l'adresse indiquée par Streamlit (généralement http://localhost:8501).

## Structure du fichier Excel

Chaque ligne du fichier `data/applications.xlsx` contient les informations suivantes :

- Code candidature
- Entreprise
- Thématique
- Domaine
- Statut
- Date d'application
- Début de stage

Ces colonnes peuvent être enrichies manuellement dans Excel si nécessaire, l'application les conservera lors des lectures suivantes.
