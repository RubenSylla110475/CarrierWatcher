"""Streamlit app for managing internship applications."""
from __future__ import annotations

import importlib
import json
from datetime import date, datetime
from pathlib import Path
from typing import Iterable

import pandas as pd
import streamlit as st

DATA_DIR = Path("data")
EXCEL_PATH = DATA_DIR / "applications.xlsx"
STATE_PATH = DATA_DIR / "sync_state.json"

STATUS_OPTIONS = [
    "En attente",
    "Entretien",
    "Acceptée",
    "Refusée",
]

COLUMNS = [
    "Code candidature",
    "Entreprise",
    "Thématique",
    "Domaine",
    "Statut",
    "Date d'application",
    "Début de stage",
]

# ------------------------
# Fichiers & I/O
# ------------------------
def ensure_data_directory() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_applications() -> pd.DataFrame:
    """Charge le fichier Excel, garantit les colonnes et normalise les types."""
    if EXCEL_PATH.exists():
        df = pd.read_excel(EXCEL_PATH)
    else:
        df = pd.DataFrame(columns=COLUMNS)

    # Ajoute colonnes manquantes
    for c in COLUMNS:
        if c not in df.columns:
            df[c] = ""

    # Normalise types (évite NaN incohérents)
    for c in ["Code candidature", "Entreprise", "Thématique", "Domaine", "Statut"]:
        df[c] = df[c].fillna("").astype(str)

    # Les dates peuvent venir en str, datetime, Timestamp… on laisse tel quel ici.
    return df[COLUMNS]  # ordre de colonnes garanti


def _to_datestr(value: object) -> str:
    """Transforme ce qu'on a en 'YYYY-MM-DD' ou chaîne vide."""
    if value in (None, "", pd.NaT):
        return ""
    if isinstance(value, str):
        # Déjà formaté ? On tente un parse souple, sinon on renvoie tel quel.
        try:
            dt = pd.to_datetime(value, errors="raise").date()
            return dt.strftime("%Y-%m-%d")
        except Exception:
            return value  # on ne casse pas si l'utilisateur saisit un texte
    if isinstance(value, (datetime, pd.Timestamp)):
        return value.date().strftime("%Y-%m-%d")
    if isinstance(value, date):
        return value.strftime("%Y-%m-%d")
    return str(value)


def save_applications(df: pd.DataFrame) -> None:
    """Sauvegarde en forçant le formatage des dates."""
    ensure_data_directory()
    df = df.copy()
    for c in ["Date d'application", "Début de stage"]:
        df[c] = df[c].map(_to_datestr)
    # Sécurité: ne garder que les colonnes officielles
    df = df.reindex(columns=COLUMNS)
    df.to_excel(EXCEL_PATH, index=False)


# ------------------------
# Filtrage & agrégats
# ------------------------
def filter_applications(
    df: pd.DataFrame, *, statuses: list[str] | None, domain: list[str] | None, theme: list[str] | None
) -> pd.DataFrame:
    filtered = df.copy()
    if statuses:
        filtered = filtered[filtered["Statut"].isin(statuses)]
    if domain:
        filtered = filtered[filtered["Domaine"].isin(domain)]
    if theme:
        filtered = filtered[filtered["Thématique"].isin(theme)]
    return filtered


def render_metrics(df: pd.DataFrame) -> None:
    total = len(df)
    accepted = (df["Statut"] == "Acceptée").sum()
    refused = (df["Statut"] == "Refusée").sum()
    pending = (df["Statut"] == "En attente").sum()

    st.markdown("### Synthèse")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Candidatures", total)
    col2.metric("Acceptées", int(accepted))
    col3.metric("Refusées", int(refused))
    col4.metric("En attente", int(pending))


def render_filters(df: pd.DataFrame) -> pd.DataFrame:
    st.sidebar.header("Filtres")
    status_selection = st.sidebar.multiselect("Statut", STATUS_OPTIONS)

    domain_options = sorted(v for v in df["Domaine"].dropna().unique() if v)
    domain_selection = st.sidebar.multiselect("Domaine", domain_options)

    theme_options = sorted(v for v in df["Thématique"].dropna().unique() if v)
    theme_selection = st.sidebar.multiselect("Thématique", theme_options)

    return filter_applications(
        df,
        statuses=status_selection or None,
        domain=domain_selection or None,
        theme=theme_selection or None,
    )


# ------------------------
# UI de visualisation
# ------------------------
def render_application_table(df: pd.DataFrame) -> None:
    st.markdown("### Candidatures (vue filtrée)")
    st.dataframe(df, use_container_width=True, hide_index=True)


def render_status_chart(df: pd.DataFrame) -> None:
    if df.empty:
        return
    status_counts = df["Statut"].value_counts().reindex(STATUS_OPTIONS, fill_value=0)
    st.markdown("### Répartition par statut")
    st.bar_chart(status_counts)


def render_sync_controls() -> None:
    st.markdown("### Synchronisation e-mail")
    col_status, col_button = st.columns([1, 1])

    last_sync = ""
    if STATE_PATH.exists():
        try:
            state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
            last_sync = state.get("last_sync", "")
        except Exception:
            last_sync = ""

    col_status.write(f"Dernière synchro : **{last_sync or 'Jamais'}**")

    if col_button.button("Synchroniser la boîte mail maintenant", use_container_width=True):
        with st.spinner("Synchronisation en cours..."):
            mail_sync = importlib.import_module("mail_sync")
            try:
                summary = mail_sync.run_once()
                st.success(
                    "OK — {fetched} mails scannés • {created} créés • {updated} mis à jour".format(
                        fetched=summary.get("fetched", 0),
                        created=summary.get("created", 0),
                        updated=summary.get("updated", 0),
                    )
                )
            except Exception as exc:  # noqa: BLE001
                st.error(f"Échec de la synchro : {exc}")
        st.rerun()


# ------------------------
# Formulaire de création
# ------------------------
def reset_form_fields() -> None:
    for key in [
        "code",
        "company",
        "theme",
        "domain",
        "status",
        "application_date",
        "start_date",
    ]:
        if key in st.session_state:
            del st.session_state[key]


def render_creation_form(df: pd.DataFrame) -> None:
    st.markdown("### Ajouter une candidature")
    with st.form("application_form", clear_on_submit=False):
        code = st.text_input("Code de candidature", key="code").strip()
        company = st.text_input("Entreprise", key="company").strip()
        theme = st.text_input("Thématique", key="theme").strip()
        domain = st.text_input("Domaine", key="domain").strip()
        status = st.selectbox("Statut", STATUS_OPTIONS, key="status")
        application_date = st.date_input(
            "Date d'application",
            value=st.session_state.get("application_date"),
            key="application_date",
        )
        start_date = st.date_input(
            "Date de début de stage",
            value=st.session_state.get("start_date"),
            key="start_date",
        )

        submitted = st.form_submit_button("Enregistrer")

        if submitted:
            if not company:
                st.error("Le nom de l'entreprise est obligatoire.")
                return
            if not code:
                st.error("Le code de candidature est obligatoire.")
                return

            new_row = pd.DataFrame(
                {
                    "Code candidature": [code],
                    "Entreprise": [company],
                    "Thématique": [theme],
                    "Domaine": [domain],
                    "Statut": [status],
                    "Date d'application": [_to_datestr(application_date)],
                    "Début de stage": [_to_datestr(start_date)],
                }
            )

            updated_df = pd.concat([df, new_row], ignore_index=True)
            save_applications(updated_df)
            st.success("Candidature enregistrée avec succès !")
            reset_form_fields()
            st.rerun()


# ------------------------
# Mode Édition (modifier / supprimer)
# ------------------------
def _datecol(label: str) -> st.column_config.DateColumn:
    return st.column_config.DateColumn(label=label, format="YYYY-MM-DD")


def _selectcol(label: str, options: Iterable[str]) -> st.column_config.SelectboxColumn:
    return st.column_config.SelectboxColumn(label=label, options=list(options), required=True)


def render_edit_mode(full_df: pd.DataFrame) -> None:
    """
    Éditeur complet:
      - Colonnes éditables (incl. Statut via Selectbox)
      - Colonnes dates éditables via Date picker
      - Colonne _Supprimer avec cases à cocher
      - Boutons 'Enregistrer' et 'Supprimer les lignes cochées'
      - num_rows='dynamic' pour autoriser l'ajout direct de lignes si souhaité
    """
    with st.expander("✏️ Édition & suppression (toutes les candidatures)", expanded=False):
        work_df = full_df.copy()

        # Ajoute une colonne temporaire pour marquer les suppressions
        work_df["_Supprimer"] = False

        edited_df = st.data_editor(
            work_df,
            use_container_width=True,
            hide_index=False,
            num_rows="dynamic",
            key="editor_table",
            column_config={
                "Code candidature": st.column_config.TextColumn("Code candidature", required=True),
                "Entreprise": st.column_config.TextColumn("Entreprise", required=True),
                "Thématique": st.column_config.TextColumn("Thématique"),
                "Domaine": st.column_config.TextColumn("Domaine"),
                "Statut": _selectcol("Statut", STATUS_OPTIONS),
                "Date d'application": _datecol("Date d'application"),
                "Début de stage": _datecol("Début de stage"),
                "_Supprimer": st.column_config.CheckboxColumn("_Supprimer"),
            },
        )

        c1, c2 = st.columns([1, 1])
        if c1.button("💾 Enregistrer les modifications", use_container_width=True):
            to_save = edited_df.drop(columns=["_Supprimer"], errors="ignore").copy()
            save_applications(to_save)
            st.success("Modifications enregistrées.")
            st.rerun()

        if c2.button("🗑️ Supprimer les lignes cochées", use_container_width=True):
            keep_df = edited_df[~edited_df["_Supprimer"]].drop(columns=["_Supprimer"], errors="ignore")
            save_applications(keep_df)
            st.success("Lignes supprimées.")
            st.rerun()


# ------------------------
# Main
# ------------------------
def main() -> None:
    st.set_page_config(page_title="CarrierWatcher", page_icon="🗂️", layout="wide")

    st.title("CarrierWatcher")
    st.write(
        """Application pour suivre vos candidatures de stage de fin d'étude. 
        Enregistrez vos candidatures, modifiez leur statut, supprimez des entrées 
        et visualisez votre progression."""
    )

    ensure_data_directory()
    applications_df = load_applications()

    render_sync_controls()
    render_metrics(applications_df)

    # Filtres (pour la vue et les graphes uniquement)
    filtered_df = render_filters(applications_df)
    render_status_chart(filtered_df)
    render_application_table(filtered_df)

    # Formulaire d'ajout
    render_creation_form(applications_df)

    # Mode édition global (modifier / supprimer)
    render_edit_mode(applications_df)


if __name__ == "__main__":
    main()
