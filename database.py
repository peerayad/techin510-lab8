"""Supabase database setup and helpers for makerspace purchases."""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from dotenv import load_dotenv
from supabase import Client, create_client

PROJECT_DIR = Path(__file__).parent
ENV_PATH = PROJECT_DIR / ".env"
SAMPLE_CSV = PROJECT_DIR / "data" / "sample_purchases.csv"
TABLE_NAME = "purchases"

AREA_OPTIONS = [
    "Lasers",
    "Textiles",
    "3D Printers",
    "Woodshop",
    "Electronics",
    "Casting/Ceramics",
    "Robotics",
    "General",
]

TYPE_OPTIONS = [
    "Materials",
    "Sensors",
    "Tool Repair Supplies",
    "Consumable/Losable Tools",
    "Organization/Security",
    "New Tools",
    "Experimental",
    "Book",
]

PURCHASE_COLUMNS = [
    "date",
    "vendor",
    "description",
    "amount",
    "area",
    "type",
    "workday_category",
    "notes",
]

EXTRA_COLUMNS = ["pca_code", "invoice_number", "po_number"]
INSERT_COLUMNS = PURCHASE_COLUMNS + EXTRA_COLUMNS

_client: Optional[Client] = None


def _load_env() -> None:
    """Load environment variables from .env only (.env.example is never read)."""
    if not ENV_PATH.exists():
        raise FileNotFoundError(
            f"{ENV_PATH.name} not found. Create it from .env.example and add your "
            "SUPABASE_URL and SUPABASE_KEY (only .env is used at runtime)."
        )
    load_dotenv(ENV_PATH, override=True)


def _get_supabase_credentials() -> Tuple[str, str]:
    """
    Load Supabase credentials from .env (local) or st.secrets (Streamlit Cloud).

    Local runs always read .env — never .env.example.
    """
    url: Optional[str] = None
    key: Optional[str] = None

    if ENV_PATH.exists():
        _load_env()
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
    else:
        try:
            from streamlit.runtime.scriptrunner import get_script_run_ctx

            if get_script_run_ctx() is not None:
                import streamlit as st

                if "SUPABASE_URL" in st.secrets:
                    url = st.secrets["SUPABASE_URL"]
                if "SUPABASE_KEY" in st.secrets:
                    key = st.secrets["SUPABASE_KEY"]
        except Exception:
            pass

        if not url or not key:
            raise FileNotFoundError(
                f"{ENV_PATH.name} not found. Create it from .env.example and add "
                "your credentials (.env.example is never loaded). On Streamlit "
                "Cloud, use App secrets instead."
            )

    if not url or not key:
        raise ValueError(
            f"SUPABASE_URL and SUPABASE_KEY must be set in {ENV_PATH.name}. "
            ".env.example is a template only and is never read."
        )

    return url, key


def get_client() -> Client:
    """Return a cached Supabase client."""
    global _client
    if _client is None:
        url, key = _get_supabase_credentials()
        _client = create_client(url, key)
    return _client


def _normalize_date(value: Any) -> str:
    return pd.to_datetime(value).strftime("%Y-%m-%d")


def _prepare_record(row: Dict[str, Any]) -> Dict[str, Any]:
    """Build a Supabase-ready purchase record from a row dict."""
    record: Dict[str, Any] = {}
    for col in INSERT_COLUMNS:
        value = row.get(col)
        if col == "date" and value is not None and value != "":
            record[col] = _normalize_date(value)
        elif col == "notes":
            record[col] = (
                ""
                if value is None or (isinstance(value, float) and pd.isna(value))
                else str(value)
            )
        elif col in EXTRA_COLUMNS:
            record[col] = (
                None
                if value is None or (isinstance(value, float) and pd.isna(value)) or value == ""
                else str(value)
            )
        else:
            record[col] = value
    return record


def _df_to_records(df: pd.DataFrame) -> List[Dict[str, Any]]:
    records = []
    for row in df.to_dict(orient="records"):
        records.append(_prepare_record(row))
    return records


def insert_purchase(purchase: Dict[str, Any]) -> Dict[str, Any]:
    """Insert a single purchase row. Returns the inserted record from Supabase."""
    record = _prepare_record(purchase)
    response = get_client().table(TABLE_NAME).insert(record).execute()
    if not response.data:
        raise RuntimeError("Insert failed — no data returned from Supabase.")
    return response.data[0]


def insert_purchases(df: pd.DataFrame) -> int:
    """Bulk insert purchase rows from a DataFrame. Returns number of rows inserted."""
    missing = set(PURCHASE_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    upload_df = df.copy()
    for col in EXTRA_COLUMNS:
        if col not in upload_df.columns:
            upload_df[col] = None

    records = _df_to_records(upload_df[INSERT_COLUMNS])
    if not records:
        return 0

    response = get_client().table(TABLE_NAME).insert(records).execute()
    return len(response.data) if response.data else len(records)


def fetch_all_purchases() -> pd.DataFrame:
    """Select all purchases, ordered by date descending."""
    response = (
        get_client()
        .table(TABLE_NAME)
        .select("*")
        .order("date", desc=True)
        .execute()
    )
    if not response.data:
        return pd.DataFrame(columns=["id"] + INSERT_COLUMNS)
    return pd.DataFrame(response.data)


def seed_from_csv(csv_path: Path = SAMPLE_CSV) -> int:
    """Delete all purchases, then bulk insert rows from CSV. Returns rows inserted."""
    client = get_client()
    client.table(TABLE_NAME).delete().neq("id", 0).execute()

    df = pd.read_csv(csv_path)
    missing = set(PURCHASE_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"CSV missing required columns: {missing}")

    for col in EXTRA_COLUMNS:
        if col not in df.columns:
            df[col] = None

    return insert_purchases(df)


if __name__ == "__main__":
    rows = seed_from_csv()
    print(f"Seeded {rows} purchases into Supabase")
