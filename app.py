"""
Portfolio Dashboard (robust version)
"""

import pandas as pd
import streamlit as st

# -----------------------------
# Safe import for plotly
# -----------------------------
try:
    import plotly.express as px
    PLOTLY_AVAILABLE = True
except Exception:
    PLOTLY_AVAILABLE = False

# -----------------------------
# Config
# -----------------------------
st.set_page_config(
    page_title="Portfolio Dashboard",
    page_icon="📊",
    layout="wide",
)

CSV_PATH = "positions.csv"

REQUIRED_COLUMNS = ["name", "quantity", "price", "asset_type"]


# -----------------------------
# Data loader
# -----------------------------
@st.cache_data(show_spinner=False)
def load_data(file, path):
    try:
        if file is not None:
            df = pd.read_csv(file)
        else:
            df = pd.read_csv(path)
    except Exception as e:
        st.error(f"CSV konnte nicht geladen werden: {e}")
        return pd.DataFrame(), [str(e)]

    warnings = []

    # normalize columns
    df.columns = [c.strip().lower() for c in df.columns]

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        warnings.append(f"Fehlende Spalten: {missing}")
        return pd.DataFrame(), warnings

    # clean
    df["name"] = df["name"].fillna("Unknown")
    df["asset_type"] = df["asset_type"].fillna("Other")

    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")
    df["price"] = pd.to_numeric(df["price"], errors="coerce")

    df = df.dropna(subset=["quantity", "price"])

    df["value"] = df["quantity"] * df["price"]

    return df, warnings


# -----------------------------
# Sidebar
# -----------------------------
st.sidebar.title("Daten")

uploaded = st.sidebar.file_uploader("CSV hochladen", type=["csv"])

df, warnings = load_data(uploaded, CSV_PATH)

for w in warnings:
    st.warning(w)

if df.empty:
    st.stop()

# -----------------------------
# KPIs
# -----------------------------
total = df["value"].sum()

col1, col2 = st.columns(2)
col1.metric("Portfolio Wert", f"{total:,.2f} €")
col2.metric("Positionen", len(df))

st.divider()

# -----------------------------
# Allocation
# -----------------------------
st.subheader("Allocation")

alloc = df.groupby("asset_type")["value"].sum().reset_index()

if PLOTLY_AVAILABLE:
    fig = px.pie(alloc, names="asset_type", values="value")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("Plotly nicht installiert → zeige Tabelle statt Chart")
    st.dataframe(alloc)

# -----------------------------
# Top holdings
# -----------------------------
st.subheader("Top Positionen")

top = df.sort_values("value", ascending=False)

st.dataframe(top)

# -----------------------------
# Debug
# -----------------------------
with st.expander("Raw Data"):
    st.dataframe(df)
