import pandas as pd
import streamlit as st

# Optional: Plotly (safe import)
try:
    import plotly.express as px
    PLOTLY = True
except Exception:
    PLOTLY = False


# -----------------------------
# CONFIG
# -----------------------------
st.set_page_config(
    page_title="Portfolio Dashboard",
    page_icon="📊",
    layout="wide"
)

CSV_PATH = "positions.csv"

REQUIRED = ["name", "quantity", "price", "asset_type"]


# -----------------------------
# ULTRA ROBUST CSV LOADER
# -----------------------------
def read_csv_robust(file, path):
    encodings = ["utf-8", "utf-8-sig", "utf-16", "utf-16-le", "latin1"]
    separators = [",", ";", "\t"]

    for enc in encodings:
        for sep in separators:
            try:
                if file is not None:
                    file.seek(0)
                    df = pd.read_csv(file, encoding=enc, sep=sep)
                else:
                    df = pd.read_csv(path, encoding=enc, sep=sep)

                # Heuristik: sinnvolle Datei erkannt?
                if df.shape[1] >= 3:
                    return df

            except Exception:
                continue

    # letzter Versuch (Excel / weird files)
    try:
        if file is not None:
            file.seek(0)
            return pd.read_csv(file, engine="python")
        else:
            return pd.read_csv(path, engine="python")
    except Exception as e:
        raise ValueError(f"CSV konnte nicht gelesen werden: {e}")


# -----------------------------
# LOAD + CLEAN
# -----------------------------
@st.cache_data(show_spinner=False)
def load_data(uploaded_file, path):
    df = read_csv_robust(uploaded_file, path)

    warnings = []

    # normalize columns
    df.columns = [c.strip().lower() for c in df.columns]

    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        return pd.DataFrame(), [f"Fehlende Spalten: {missing}"]

    # clean text
    df["name"] = df["name"].fillna("unknown")
    df["asset_type"] = df["asset_type"].fillna("other")

    # numeric
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")
    df["price"] = pd.to_numeric(df["price"], errors="coerce")

    before = len(df)
    df = df.dropna(subset=["quantity", "price"])
    df = df[(df["quantity"] >= 0) & (df["price"] >= 0)]

    df["value"] = df["quantity"] * df["price"]

    after = len(df)

    if before != after:
        warnings.append(f"{before - after} ungültige Zeilen entfernt")

    return df, warnings


# -----------------------------
# SIDEBAR
# -----------------------------
st.sidebar.title("Datenquelle")

uploaded = st.sidebar.file_uploader("CSV hochladen", type=["csv"])

df, warnings = load_data(uploaded, CSV_PATH)

for w in warnings:
    st.warning(w)

if df.empty:
    st.info("Keine gültigen Daten.")
    st.stop()


# -----------------------------
# KPIs
# -----------------------------
total = df["value"].sum()

col1, col2, col3 = st.columns(3)
col1.metric("Portfolio Wert", f"{total:,.2f} €")
col2.metric("Positionen", len(df))
col3.metric("Ø Position", f"{total/len(df):,.2f} €")

st.divider()


# -----------------------------
# ALLOCATION
# -----------------------------
st.subheader("Asset Allocation")

alloc = df.groupby("asset_type")["value"].sum().reset_index()

if PLOTLY:
    fig = px.pie(alloc, names="asset_type", values="value", hole=0.4)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.dataframe(alloc)


# -----------------------------
# TOP POSITIONS
# -----------------------------
st.subheader("Top Positionen")

top = df.sort_values("value", ascending=False)

st.dataframe(top, use_container_width=True)


# -----------------------------
# CONCENTRATION
# -----------------------------
st.subheader("Konzentration")

sorted_vals = df.sort_values("value", ascending=False)["value"]

top3 = sorted_vals.head(3).sum()
top5 = sorted_vals.head(5).sum()

top3_share = top3 / total * 100 if total else 0
top5_share = top5 / total * 100 if total else 0

c1, c2 = st.columns(2)
c1.metric("Top 3 Anteil", f"{top3_share:.1f}%")
c2.metric("Top 5 Anteil", f"{top5_share:.1f}%")

if top3_share > 50:
    st.warning("Starke Konzentration im Portfolio")
elif top3_share > 30:
    st.info("Moderate Konzentration")
else:
    st.success("Gut diversifiziert")


# -----------------------------
# RAW DATA
# -----------------------------
with st.expander("Rohdaten"):
    st.dataframe(df, use_container_width=True)
