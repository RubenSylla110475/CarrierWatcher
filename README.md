# CarrierWatcher

CarrierWatcher est une application Streamlit qui vous aide à suivre manuellement vos candidatures de stage de fin d'étude. Les candidatures sont enregistrées dans un fichier Excel local (`data/applications.xlsx`) et l'interface propose une visualisation claire et professionnelle de votre suivi.

## Fonctionnalités

- Formulaire simple pour ajouter une candidature (code, entreprise, thématique, domaine, dates, statut).
- Tableau de bord synthétique avec le nombre total de candidatures, celles acceptées, refusées et en attente.
- Tableau filtrable par statut, domaine et thématique.
- Graphique de répartition des candidatures par statut.
- Stockage local dans un fichier Excel pour conserver toutes les candidatures.
- Bouton de synchronisation pour importer automatiquement les e-mails de candidature Outlook (Microsoft 365).


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


### Synchroniser votre boîte Outlook

L'application peut importer automatiquement vos candidatures à partir de la boîte mail `ruben.sylla@edu.ece.fr` (ou tout autre compte Microsoft 365) à l'aide de Microsoft Graph. Deux options sont disponibles :

1. **Depuis l'interface Streamlit** : cliquez sur le bouton « Synchroniser la boîte mail maintenant » pour lancer une synchronisation ponctuelle. Un résumé des e-mails scannés, des candidatures créées et mises à jour s'affiche ensuite.
2. **Via le script autonome** : exécutez `python mail_sync.py` pour synchroniser sans démarrer Streamlit (pratique pour un déclenchement manuel ou planifié).

Avant la première synchronisation :

1. Créez une application Microsoft Entra ID (Azure AD) depuis [portal.azure.com](https://portal.azure.com).
   - Type de compte : « Accounts in any organizational directory ».
   - Notez l'**Application (client) ID**.
2. Dans « API permissions », ajoutez les permissions déléguées **Mail.Read** et **offline_access** pour Microsoft Graph, puis accordez le consentement administrateur si nécessaire.
3. Définissez la variable d'environnement `AZURE_CLIENT_ID` avec l'identifiant client récupéré.

Au premier lancement du script (via le bouton Streamlit ou la commande `python mail_sync.py`), Microsoft vous affichera une URL et un code à saisir pour autoriser l'accès à la boîte mail. Les jetons d'accès sont mis en cache dans `data/token_cache.json` afin d'éviter de devoir se reconnecter à chaque synchronisation.

Les e-mails détectés sont rapprochés des candidatures existantes en se basant sur le nom de l'entreprise. Lorsqu'un nouvel e-mail est importé, l'application :

- crée une ligne si aucune candidature correspondante n'existe encore ;
- met à jour le statut selon des mots-clés (En attente, Entretien, Acceptée, Refusée) ;
- enregistre la date du dernier e-mail et indique « email » dans la colonne « Source ».

Vous pouvez également lancer la synchronisation automatiquement via le Planificateur Windows en exécutant régulièrement `python mail_sync.py`.

## Structure du fichier Excel

Chaque ligne du fichier `data/applications.xlsx` contient les informations suivantes :

- Code candidature
- Entreprise
- Thématique
- Domaine
- Statut
- Date d'application
- Début de stage
- Dernier mail (horodatage du dernier e-mail synchronisé)
- Source ("email" lorsqu'une candidature provient de la synchronisation)


Ces colonnes peuvent être enrichies manuellement dans Excel si nécessaire, l'application les conservera lors des lectures suivantes.
