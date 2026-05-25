"""Makerspace Purchasing Manager — main Streamlit entry point."""

import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import streamlit as st

st.set_page_config(page_title="Makerspace Purchasing", page_icon="🔧", layout="wide")


def check_dependencies() -> List[str]:
    """Return names of missing required packages."""
    missing = []
    for module, package in [("supabase", "supabase"), ("groq", "groq")]:
        try:
            __import__(module)
        except ImportError:
            missing.append(package)
    return missing


_missing = check_dependencies()
if _missing:
    st.error(
        f"Missing required packages: {', '.join(_missing)}. "
        f"Install them with:\n\n`pip install {' '.join(_missing)}`"
    )
    st.stop()

import pandas as pd
import plotly.express as px
from dotenv import load_dotenv

from agent import get_groq_key, get_agent_response
from database import (
    AREA_OPTIONS,
    INSERT_COLUMNS,
    PURCHASE_COLUMNS,
    TYPE_OPTIONS,
    fetch_all_purchases,
    insert_purchase,
    insert_purchases,
)

ENV_PATH = Path(__file__).parent / ".env"
PAGES = ["Dashboard", "Purchases", "Ask Kevin's Agent"]

WORKDAY_CATEGORIES = ["Other Supplies", "3D Printing Supplies", "Equipment"]
DISPLAY_COLUMNS = INSERT_COLUMNS
CSV_SKIP = "— not in CSV —"


@st.cache_data
def load_purchases() -> pd.DataFrame:
    """Load purchases from Supabase."""
    df = fetch_all_purchases()
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
    return df


def refresh_data() -> pd.DataFrame:
    """Clear cached purchases and reload from the database."""
    load_purchases.clear()
    return load_purchases()


def format_currency(value: float) -> str:
    return f"${value:,.2f}"


def filter_purchases(
    df: pd.DataFrame,
    start_date,
    end_date,
    areas: List[str],
    types: List[str],
    search: str,
) -> pd.DataFrame:
    """Apply date, area, type, and text search filters."""
    filtered = df[
        (df["date"] >= pd.Timestamp(start_date))
        & (df["date"] <= pd.Timestamp(end_date))
    ]
    if areas:
        filtered = filtered[filtered["area"].isin(areas)]
    if types:
        filtered = filtered[filtered["type"].isin(types)]
    if search.strip():
        query = search.strip().lower()
        mask = filtered["vendor"].str.lower().str.contains(
            query, na=False
        ) | filtered["description"].str.lower().str.contains(query, na=False)
        filtered = filtered[mask]
    return filtered


def ensure_display_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Return DataFrame with all display columns present."""
    if df.empty:
        return pd.DataFrame(columns=DISPLAY_COLUMNS)
    out = df.copy()
    for col in DISPLAY_COLUMNS:
        if col not in out.columns:
            out[col] = None
    return out[DISPLAY_COLUMNS]


def apply_csv_mapping(
    raw_df: pd.DataFrame,
    column_map: dict,
    default_area: str,
    default_type: str,
) -> pd.DataFrame:
    """Build a purchases DataFrame from uploaded CSV using column mapping."""
    mapped = {}
    for field in INSERT_COLUMNS:
        source = column_map.get(field, CSV_SKIP)
        if field == "area" and source == CSV_SKIP:
            mapped[field] = default_area
        elif field == "type" and source == CSV_SKIP:
            mapped[field] = default_type
        elif source == CSV_SKIP:
            mapped[field] = None
        else:
            mapped[field] = raw_df[source]
    result = pd.DataFrame(mapped)
    if "area" in result.columns:
        result["area"] = result["area"].fillna(default_area)
    if "type" in result.columns:
        result["type"] = result["type"].fillna(default_type)
    return result


def _csv_map_default_index(field: str, raw_columns: List[str]) -> int:
    """Pick matching CSV column in selectbox, or 'not in CSV'."""
    options = [CSV_SKIP] + list(raw_columns)
    if field in raw_columns:
        return options.index(field)
    return 0


def render_csv_column_mapper(raw_df: pd.DataFrame) -> Optional[pd.DataFrame]:
    """Show column mapper UI; return mapped DataFrame when user confirms."""
    st.write("Map your CSV columns to purchase fields:")
    csv_columns = [CSV_SKIP] + list(raw_df.columns)
    column_map = {}

    map_cols = st.columns(2)
    for idx, field in enumerate(INSERT_COLUMNS):
        target = map_cols[idx % 2]
        default_idx = _csv_map_default_index(field, list(raw_df.columns))
        if field == "area":
            column_map[field] = target.selectbox(
                "Area column",
                csv_columns,
                index=default_idx,
                key="csv_map_area_col",
            )
        elif field == "type":
            column_map[field] = target.selectbox(
                "Type column",
                csv_columns,
                index=default_idx,
                key="csv_map_type_col",
            )
        else:
            column_map[field] = target.selectbox(
                field,
                csv_columns,
                index=default_idx,
                key=f"csv_map_{field}",
            )

    default_area = st.selectbox(
        "Default area (used when area column is not mapped or empty)",
        AREA_OPTIONS,
        key="csv_default_area",
    )
    default_type = st.selectbox(
        "Default type (used when type column is not mapped or empty)",
        TYPE_OPTIONS,
        key="csv_default_type",
    )

    mapped_df = apply_csv_mapping(raw_df, column_map, default_area, default_type)
    st.write("Preview (first 5 rows after mapping):")
    st.dataframe(ensure_display_columns(mapped_df).head(5), hide_index=True)

    if st.button("Confirm and insert into database"):
        return mapped_df
    return None


def render_dashboard(df: pd.DataFrame) -> None:
    st.title("Kevin's Purchasing Dashboard")

    if df.empty:
        st.info("No purchases yet. Go to the Purchases page to upload your data.")
        return

    current_year = datetime.now().year
    total_spend = df["amount"].sum()
    year_spend = df.loc[df["date"].dt.year == current_year, "amount"].sum()
    transaction_count = len(df)
    top_area = (
        df.groupby("area")["amount"]
        .sum()
        .sort_values(ascending=False)
        .index[0]
    )

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Spend (All Time)", format_currency(total_spend))
    col2.metric(f"Total Spend ({current_year})", format_currency(year_spend))
    col3.metric("Number of Transactions", f"{transaction_count:,}")
    col4.metric("Top Spending Area", top_area)

    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    st.subheader("Spend by Area")
    spend_by_area = (
        df.groupby("area", as_index=False)["amount"]
        .sum()
        .sort_values("amount", ascending=True)
    )
    area_chart = px.bar(
        spend_by_area,
        x="amount",
        y="area",
        orientation="h",
        labels={"amount": "Total Spend ($)", "area": "Area"},
    )
    area_chart.update_layout(
        height=350,
        margin=dict(l=20, r=20, t=20, b=20),
        xaxis_tickprefix="$",
        showlegend=False,
    )
    st.plotly_chart(area_chart, use_container_width=True)

    st.subheader("Monthly Spend Over Time")
    area_options = ["All Areas"] + AREA_OPTIONS
    selected_area = st.selectbox(
        "Filter by area", area_options, label_visibility="collapsed"
    )

    monthly_df = df.copy()
    if selected_area != "All Areas":
        monthly_df = monthly_df[monthly_df["area"] == selected_area]

    if monthly_df.empty:
        st.info(f"No purchases in **{selected_area}** to chart.")
    else:
        monthly_spend = (
            monthly_df.assign(month=monthly_df["date"].dt.to_period("M"))
            .groupby("month")["amount"]
            .sum()
            .reset_index()
        )
        monthly_spend["date"] = monthly_spend["month"].dt.to_timestamp()

        line_chart = px.line(
            monthly_spend,
            x="date",
            y="amount",
            markers=True,
            labels={"date": "Month", "amount": "Spend ($)"},
        )
        line_chart.update_layout(
            height=350,
            margin=dict(l=20, r=20, t=20, b=20),
            yaxis_tickprefix="$",
            xaxis_title="Month",
        )
        st.plotly_chart(line_chart, use_container_width=True)

    st.subheader("Recent Purchases")
    recent = df.nlargest(5, "date")[
        ["date", "vendor", "description", "amount", "area"]
    ].copy()
    recent["date"] = recent["date"].dt.strftime("%Y-%m-%d")
    recent["amount"] = recent["amount"].apply(lambda x: f"${x:,.2f}")
    recent.columns = ["Date", "Vendor", "Description", "Amount", "Area"]
    st.dataframe(recent, use_container_width=True, hide_index=True)


def render_purchases(df: pd.DataFrame) -> None:
    st.title("Purchases")

    if st.session_state.get("purchase_success"):
        st.success(st.session_state.purchase_success)
        del st.session_state.purchase_success

    min_date = df["date"].min().date() if not df.empty else datetime.today().date()
    max_date = df["date"].max().date() if not df.empty else datetime.today().date()

    st.subheader("Filters")
    date_col1, date_col2, area_col, type_col = st.columns([1, 1, 1, 1])
    start_date = date_col1.date_input("Start date", value=min_date)
    end_date = date_col2.date_input("End date", value=max_date)
    selected_areas = area_col.multiselect("Area", AREA_OPTIONS, default=AREA_OPTIONS)
    selected_types = type_col.multiselect("Type", TYPE_OPTIONS, default=TYPE_OPTIONS)
    search = st.text_input("Search vendor or description")

    if df.empty:
        filtered = pd.DataFrame(columns=DISPLAY_COLUMNS)
    else:
        filtered = filter_purchases(
            df, start_date, end_date, selected_areas, selected_types, search
        )

    table_df = ensure_display_columns(filtered)
    if not table_df.empty:
        table_df = table_df.sort_values("date", ascending=False)
        table_df["date"] = pd.to_datetime(table_df["date"]).dt.strftime("%Y-%m-%d")

    st.subheader(f"Purchases ({len(table_df)} rows)")

    export_df = table_df.copy()
    csv_data = export_df.to_csv(index=False)
    st.download_button(
        label="Download current view as CSV",
        data=csv_data,
        file_name="purchases_filtered.csv",
        mime="text/csv",
    )

    st.dataframe(table_df, use_container_width=True, hide_index=True)

    st.subheader("Upload CSV")
    uploaded = st.file_uploader("Choose a CSV file", type=["csv"])
    if uploaded is not None:
        try:
            raw_df = pd.read_csv(uploaded)
            if raw_df.empty:
                st.warning("The uploaded CSV file is empty.")
            else:
                mapped_df = render_csv_column_mapper(raw_df)
                if mapped_df is not None:
                    missing = set(PURCHASE_COLUMNS) - set(mapped_df.columns)
                    if missing:
                        st.error(
                            f"Mapped data is missing required columns: "
                            f"{', '.join(sorted(missing))}"
                        )
                    else:
                        count = insert_purchases(mapped_df)
                        refresh_data()
                        st.session_state.purchase_success = (
                            f"Successfully added {count} row(s) to the database."
                        )
                        st.rerun()
        except Exception as exc:
            st.error(f"Could not read CSV: {exc}")

    with st.expander("Add Single Purchase"):
        with st.form("add_purchase_form"):
            form_date = st.date_input("Date", value=datetime.today())
            vendor = st.text_input("Vendor")
            description = st.text_input("Description")
            amount = st.number_input("Amount", min_value=0.0, step=0.01, format="%.2f")
            area = st.selectbox("Area", AREA_OPTIONS)
            purchase_type = st.selectbox("Type", TYPE_OPTIONS)
            workday_category = st.selectbox("Workday category", WORKDAY_CATEGORIES)
            pca_code = st.text_input("PCA code", placeholder="100 · MKR · SUPPLY")
            invoice_number = st.text_input("Invoice number", placeholder="50951200")
            po_number = st.text_input("PO number", placeholder="0825KARNE")
            notes = st.text_area("Notes")
            saved = st.form_submit_button("Save")

            if saved:
                if not vendor.strip() or not description.strip():
                    st.error("Vendor and description are required.")
                elif amount <= 0:
                    st.error("Amount must be greater than zero.")
                else:
                    insert_purchase(
                        {
                            "date": form_date.strftime("%Y-%m-%d"),
                            "vendor": vendor.strip(),
                            "description": description.strip(),
                            "amount": amount,
                            "area": area,
                            "type": purchase_type,
                            "workday_category": workday_category,
                            "pca_code": pca_code.strip(),
                            "invoice_number": invoice_number.strip(),
                            "po_number": po_number.strip(),
                            "notes": notes.strip(),
                        }
                    )
                    refresh_data()
                    st.session_state.purchase_success = (
                        "Successfully added 1 row to the database."
                    )
                    st.rerun()


def render_agent(df: pd.DataFrame) -> None:
    st.title("Ask Kevin's Agent")

    st.warning(
        "This agent only answers based on your uploaded purchasing data. "
        "It will not guess or estimate."
    )

    purchases_df = df
    purchase_count = len(purchases_df)
    st.caption(f"Kevin's data: {purchase_count} purchases loaded")

    groq_key = get_groq_key()
    if not groq_key or groq_key == "your-api-key-here":
        st.error(
            "GROQ_API_KEY is missing. Add it to Streamlit secrets (Cloud) or "
            "`.env` (local) with your key from [console.groq.com](https://console.groq.com)."
        )
        return

    if purchases_df.empty:
        st.warning(
            "No purchasing data found. Upload purchases on the **Purchases** page first."
        )
        return

    if "agent_messages" not in st.session_state:
        st.session_state.agent_messages = []

    for message in st.session_state.agent_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Ask a question about your purchasing data"):
        st.session_state.agent_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    try:
                        purchases_df = refresh_data()
                    except Exception:
                        purchases_df = df
                    response = get_agent_response(prompt, purchases_df)
                except Exception as exc:
                    response = f"Sorry, something went wrong: {exc}"
            st.markdown(response)

        st.session_state.agent_messages.append(
            {"role": "assistant", "content": response}
        )


# --- Sidebar & routing ---
st.sidebar.markdown("## 🔧 Makerspace Purchasing")
page = st.sidebar.radio("Navigation", PAGES)
st.sidebar.subheader(page)
st.sidebar.divider()

if page == "Ask Kevin's Agent":
    if st.sidebar.button("Clear chat history", use_container_width=True):
        st.session_state.agent_messages = []
        st.rerun()

try:
    df = load_purchases()
except Exception as exc:
    st.error(
        "Could not load purchases from Supabase. Check `SUPABASE_URL` and "
        "`SUPABASE_KEY` in your `.env` file (Supabase → Settings → API → anon key)."
    )
    st.caption(f"Details: {exc}")
    df = pd.DataFrame()

if not df.empty:
    st.sidebar.caption(f"{len(df):,} purchases in database")

if page == "Dashboard":
    render_dashboard(df)
elif page == "Purchases":
    render_purchases(df)
else:
    render_agent(df)
