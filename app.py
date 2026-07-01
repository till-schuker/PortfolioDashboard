"""
Portfolio Dashboard (robust production version)
"""

import pandas as pd
import streamlit as st

# Plotly optional (verhindert Cloud-Crashes)
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
# Robust CSV loader
# -----------------------------
def read_csv_robust(file, path):
    encodings = ["utf-8", "utf-8-sig", "utf-16", "latin1"]

    for enc in encodings:
        try:
            if file is not None:
                return pd.read_csv(file, encoding=enc)
            else:
                return pd.read_csv(path, encoding=enc)
        except Exception:
            continue

    raise ValueError("CSV konnte mit keinem Encoding gelesen werden.")


@st.cache_data(show_spinner=False)
def load_data(file, path):
    warnings = []

    try:
        df = read_csv_robust(file, path)
    except Exception as e:
        st.error(f"CSV konnte nicht geladen werden: {e}")
        return pd.DataFrame(), [str(e)]

    if df.empty:
        return pd.DataFrame(), ["CSV ist leer"]

    # normalize columns
    df.columns = [c.strip().lower() for c in df.columns]

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        return pd.DataFrame(), [f"Fehlende Spalten: {missing}"]

    # clean text fields
    df["name"] = df["name"].fillna("Unknown")
    df["asset_type"] = df["asset_type"].fillna("Other")

    # numeric conversion
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")
    df["price"] = pd.to_numeric(df["price"], errors="coerce")

    df = df.dropna(subset=["quantity", "price"])

    # remove negative nonsense
    df = df[(df["quantity"] >= 0) & (df["price"] >= 0)]

    # compute value
    df["value"] = df["quantity"] * df["price"]

    return df, warnings


# -----------------------------
# Sidebar
# -----------------------------
st.sidebar.title("📂 Daten")

uploaded = st.sidebar.file_uploader("CSV hochladen", type=["csv"])

df, warnings = load_data(uploaded, CSV_PATH)

for w in warnings:
    st.warning(w)

if df.empty:
    st.info("Keine gültigen Daten vorhanden.")
    st.stop()


# -----------------------------
# KPIs
# -----------------------------
total_value = df["value"].sum()

col1, col2, col3 = st.columns(3)
col1.metric("Portfolio Wert", f"{total_value:,.2f} €")
col2.metric("Positionen", len(df))
col3.metric("Ø Position", f"{total_value/len(df):,.2f} €")

st.divider()


# -----------------------------
# Allocation
# -----------------------------
st.subheader("Asset Allocation")

alloc = df.groupby("asset_type")["value"].sum().reset_index()

if PLOTLY_AVAILABLE:
    fig = px.pie(alloc, names="asset_type", values="value", hole=0.4)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("Plotly nicht verfügbar → Tabelle")
    st.dataframe(alloc)


# -----------------------------
# Top holdings
# -----------------------------
st.subheader("Top Positionen")

top = df.sort_values("value", ascending=False)

st.dataframe(top, use_container_width=True)


# -----------------------------
# Concentration risk
# -----------------------------
st.subheader("Konzentration")

sorted_vals = df.sort_values("value", ascending=False)["value"]

top3 = sorted_vals.head(3).sum()
top5 = sorted_vals.head(5).sum()

top3_share = top3 / total_value * 100 if total_value else 0
top5_share = top5 / total_value * 100 if total_value else 0

c1, c2 = st.columns(2)
c1.metric("Top 3 Anteil", f"{top3_share:.1f}%")
c2.metric("Top 5 Anteil", f"{top5_share:.1f}%")


if top3_share > 50:
    st.warning("Hohe Konzentration im Portfolio")
elif top3_share > 30:
    st.info("Moderate Konzentration")
else:
    st.success("Gut diversifiziert")


# -----------------------------
# Raw data
# -----------------------------
with st.expander("Rohdaten"):
    st.dataframe(df, use_container_width=True)
