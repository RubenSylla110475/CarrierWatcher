from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import msal
import pandas as pd
import requests
from dateutil import parser as date_parser

DATA_DIR = Path("data")
EXCEL_PATH = DATA_DIR / "applications.xlsx"
TOKEN_CACHE = DATA_DIR / "token_cache.json"
SEEN_PATH = DATA_DIR / "seen_emails.json"
STATE_PATH = DATA_DIR / "sync_state.json"

AUTHORITY = "https://login.microsoftonline.com/common"
CLIENT_ID = os.environ.get("AZURE_CLIENT_ID")
SCOPES = ["Mail.Read", "offline_access"]
GRAPH_ENDPOINT = "https://graph.microsoft.com/v1.0"

STATUS_OPTIONS = ["En attente", "Entretien", "Acceptée", "Refusée"]
BASE_COLUMNS = [
    "Code candidature",
    "Entreprise",
    "Thématique",
    "Domaine",
    "Statut",
    "Date d'application",
    "Début de stage",
]
OPTIONAL_COLUMNS = ["Dernier mail", "Source"]
STATUS_PATTERNS = [
    (re.compile(r"(shortlist|interview|convocation|entretien)", re.IGNORECASE), "Entretien"),
    (re.compile(r"(offer|offre|congrats|félicitations)", re.IGNORECASE), "Acceptée"),
    (re.compile(r"(reject|refus|unfortunately|regret)", re.IGNORECASE), "Refusée"),
    (
        re.compile(r"(received|merci.*candidature|thank.*apply)", re.IGNORECASE),
        "En attente",
    ),
]


def ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_json(path: Path) -> dict[str, Any]:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def save_json(path: Path, data: dict[str, Any]) -> None:
    ensure_data_dir()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def acquire_token() -> str:
    if not CLIENT_ID:
        raise RuntimeError("AZURE_CLIENT_ID non défini dans l'environnement.")

    cache = msal.SerializableTokenCache()
    if TOKEN_CACHE.exists():
        cache.deserialize(TOKEN_CACHE.read_text(encoding="utf-8"))

    app = msal.PublicClientApplication(CLIENT_ID, authority=AUTHORITY, token_cache=cache)
    accounts = app.get_accounts()

    result: dict[str, Any] | None = None
    if accounts:
        result = app.acquire_token_silent(SCOPES, account=accounts[0])

    if not result:
        flow = app.initiate_device_flow(scopes=SCOPES)
        if "user_code" not in flow:
            raise RuntimeError("Impossible d'initialiser le Device Code Flow.")
        print(
            "Visite l'URL ci-dessous et saisis le code affiché pour autoriser l'application:\n"
            f"{flow['verification_uri']}\nCode: {flow['user_code']}"
        )
        result = app.acquire_token_by_device_flow(flow)

    TOKEN_CACHE.write_text(cache.serialize(), encoding="utf-8")

    if not result or "access_token" not in result:
        raise RuntimeError(f"Échec de récupération du token: {result}")

    return str(result["access_token"])


def infer_status(subject: str, preview: str) -> str | None:
    text = f"{subject}\n{preview or ''}"
    for pattern, label in STATUS_PATTERNS:
        if pattern.search(text):
            return label
    return None


def infer_company(sender: str, subject: str) -> str | None:
    match = re.search(r"@([A-Za-z0-9\-]+)\.(?:com|fr|io|net|org|co)", sender or "")
    if match:
        return match.group(1).capitalize()

    match = re.search(r"\b([A-Z][A-Za-z\-]{2,})\b", subject or "")
    if match:
        return match.group(1)
    return None


def load_dataframe() -> pd.DataFrame:
    ensure_data_dir()
    if EXCEL_PATH.exists():
        df = pd.read_excel(EXCEL_PATH)
    else:
        df = pd.DataFrame(columns=BASE_COLUMNS + OPTIONAL_COLUMNS)

    for column in BASE_COLUMNS:
        if column not in df.columns:
            df[column] = ""
    for column in OPTIONAL_COLUMNS:
        if column not in df.columns:
            df[column] = ""

    return df


def save_dataframe(df: pd.DataFrame) -> None:
    ensure_data_dir()
    df.to_excel(EXCEL_PATH, index=False)


def fetch_messages(access_token: str, since_iso: str | None, top: int = 30) -> list[dict[str, Any]]:
    headers = {"Authorization": f"Bearer {access_token}"}
    url = f"{GRAPH_ENDPOINT}/me/mailFolders/Inbox/messages"
    params = {
        "$top": str(top),
        "$select": "id,receivedDateTime,subject,from,bodyPreview",
        "$orderby": "receivedDateTime desc",
    }
    response = requests.get(url, headers=headers, params=params, timeout=20)
    response.raise_for_status()
    items = response.json().get("value", [])

    if since_iso:
        cutoff = date_parser.isoparse(since_iso)
        items = [
            item
            for item in items
            if date_parser.isoparse(item["receivedDateTime"]) >= cutoff
        ]
    return items


def upsert_row(
    df: pd.DataFrame,
    *,
    company: str | None,
    status: str | None,
    received_iso: str,
) -> tuple[pd.DataFrame, bool, bool]:
    changed = False
    created = False
    target_index: int | None = None

    if company:
        matches = df.index[df["Entreprise"].fillna("") == company].tolist()
        if matches:
            target_index = matches[0]

    if target_index is None:
        new_row = {
            "Code candidature": "",
            "Entreprise": company or "",
            "Thématique": "",
            "Domaine": "",
            "Statut": status or "En attente",
            "Date d'application": "",
            "Début de stage": "",
            "Dernier mail": received_iso,
            "Source": "email",
        }
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        changed = True
        created = True
    else:
        priority = {s: i for i, s in enumerate(["En attente", "Refusée", "Entretien", "Acceptée"])}
        current_status = df.at[target_index, "Statut"] if pd.notna(df.at[target_index, "Statut"]) else "En attente"
        new_status = status or current_status
        if priority.get(new_status, 0) >= priority.get(current_status, 0) and new_status != current_status:
            df.at[target_index, "Statut"] = new_status
            changed = True
        if df.at[target_index, "Dernier mail"] != received_iso:
            df.at[target_index, "Dernier mail"] = received_iso
            changed = True
        if df.at[target_index, "Source"] != "email":
            df.at[target_index, "Source"] = "email"
            changed = True

    return df, changed, created


def run_once() -> dict[str, Any]:
    ensure_data_dir()
    access_token = acquire_token()

    seen = load_json(SEEN_PATH)
    state = load_json(STATE_PATH)
    since_iso = state.get("last_sync")

    messages = fetch_messages(access_token, since_iso)
    df = load_dataframe()

    created_count = 0
    updated_count = 0

    for message in messages:
        message_id = message["id"]
        if message_id in seen:
            continue

        sender = ((message.get("from") or {}).get("emailAddress") or {}).get("address", "")
        subject = message.get("subject", "") or ""
        preview = message.get("bodyPreview", "") or ""
        received_at = message.get("receivedDateTime", "")

        status = infer_status(subject, preview)
        company = infer_company(sender, subject)

        df, changed, created = upsert_row(
            df,
            company=company,
            status=status,
            received_iso=received_at,
        )

        if changed:
            if created:
                created_count += 1
            else:
                updated_count += 1

        seen[message_id] = True

    save_dataframe(df)
    save_json(SEEN_PATH, seen)

    now_iso = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    state["last_sync"] = now_iso
    save_json(STATE_PATH, state)

    return {
        "fetched": len(messages),
        "created": created_count,
        "updated": updated_count,
        "last_sync": now_iso,
    }


if __name__ == "__main__":
    summary = run_once()
    print(json.dumps(summary, ensure_ascii=False, indent=2))
