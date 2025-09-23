"""Streamlit app for managing internship applications."""
from __future__ import annotations

import importlib
import json
from datetime import date
from pathlib import Path

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


def ensure_data_directory() -> None:
    """Create the data directory when the app starts."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_applications() -> pd.DataFrame:
    """Load existing applications from the Excel file."""
    if EXCEL_PATH.exists():
        df = pd.read_excel(EXCEL_PATH)
    else:
        df = pd.DataFrame(columns=COLUMNS)

    missing_columns = [column for column in COLUMNS if column not in df.columns]
    for column in missing_columns:
        df[column] = ""

    return df


def save_applications(df: pd.DataFrame) -> None:
    """Persist the applications dataframe to the Excel file."""
    ensure_data_directory()
    df.to_excel(EXCEL_PATH, index=False)


def filter_applications(
    df: pd.DataFrame, *, statuses: list[str] | None, domain: list[str] | None, theme: list[str] | None
) -> pd.DataFrame:
    """Return the dataframe filtered according to the provided criteria."""
    filtered = df.copy()
    if statuses:
        filtered = filtered[filtered["Statut"].isin(statuses)]
    if domain:
        filtered = filtered[filtered["Domaine"].isin(domain)]
    if theme:
        filtered = filtered[filtered["Thématique"].isin(theme)]
    return filtered


def format_date_for_storage(value: date | None) -> str:
    """Convert a date to a string suitable for Excel storage."""
    if value is None:
        return ""
    return value.strftime("%Y-%m-%d")


def render_metrics(df: pd.DataFrame) -> None:
    """Display aggregated metrics on top of the page."""
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
    """Render sidebar filters and return the filtered dataframe."""
    st.sidebar.header("Filtres")
    status_selection = st.sidebar.multiselect("Statut", STATUS_OPTIONS)

    domain_options = sorted(value for value in df["Domaine"].dropna().unique() if value)
    domain_selection = st.sidebar.multiselect("Domaine", domain_options)

    theme_options = sorted(value for value in df["Thématique"].dropna().unique() if value)
    theme_selection = st.sidebar.multiselect("Thématique", theme_options)

    return filter_applications(
        df,
        statuses=status_selection or None,
        domain=domain_selection or None,
        theme=theme_selection or None,
    )


def render_application_table(df: pd.DataFrame) -> None:
    """Display the applications table with some styling."""
    st.markdown("### Candidatures")
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
    )


def render_sync_controls() -> None:
    """Display controls to trigger email synchronisation."""
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
        st.experimental_rerun()


def render_status_chart(df: pd.DataFrame) -> None:
    """Display a simple bar chart by application status."""
    if df.empty:
        return

    status_counts = df["Statut"].value_counts().reindex(STATUS_OPTIONS, fill_value=0)
    st.markdown("### Répartition par statut")
    st.bar_chart(status_counts)


def reset_form_fields() -> None:
    """Clear the Streamlit session state for the form fields."""
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
    """Render the form that allows the user to add a new application."""
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
                    "Date d'application": [format_date_for_storage(application_date)],
                    "Début de stage": [format_date_for_storage(start_date)],
                }
            )

            updated_df = pd.concat([df, new_row], ignore_index=True)
            save_applications(updated_df)
            st.success("Candidature enregistrée avec succès !")
            reset_form_fields()
            st.experimental_rerun()


def main() -> None:
    st.set_page_config(
        page_title="CarrierWatcher",
        page_icon="🗂️",
        layout="wide",
    )

    st.title("CarrierWatcher")
    st.write(
        """Application pour suivre vos candidatures de stage de fin d'étude. \
        Enregistrez vos candidatures, suivez leur statut et visualisez facilement \
        votre progression."""
    )

    ensure_data_directory()
    applications_df = load_applications()

    render_sync_controls()
    render_metrics(applications_df)
    filtered_df = render_filters(applications_df)
    render_status_chart(filtered_df)
    render_application_table(filtered_df)
    render_creation_form(applications_df)


if __name__ == "__main__":
    main()
