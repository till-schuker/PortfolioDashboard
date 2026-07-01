"""
Portfolio Dashboard
====================
Robuste Streamlit-App zur Auswertung einer manuell gepflegten
Positions-CSV (positions.csv).

Erwartete Spalten in positions.csv:
- name          (Pflicht)
- isin          (optional)
- quantity      (Pflicht, numerisch)
- price         (Pflicht, numerisch)
- asset_type    (Pflicht: Stock, ETF, Krypto, Cash, Festgeld)

Start:
    streamlit run app.py
"""

import io
import pandas as pd
import plotly.express as px
import streamlit as st

# --------------------------------------------------------------------------
# Konfiguration
# --------------------------------------------------------------------------
st.set_page_config(
    page_title="Portfolio Dashboard",
    page_icon="📊",
    layout="wide",
)

CSV_PATH = "positions.csv"
REQUIRED_COLUMNS = ["name", "quantity", "price", "asset_type"]
OPTIONAL_COLUMNS = ["isin"]
VALID_ASSET_TYPES = ["Stock", "ETF", "Krypto", "Cash", "Festgeld"]


# --------------------------------------------------------------------------
# Daten laden & bereinigen
# --------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def load_data(file_bytes: bytes | None, path: str) -> tuple[pd.DataFrame, list[str]]:
    """
    Lädt die Positions-CSV entweder aus hochgeladenen Bytes oder von
    einem lokalen Pfad. Gibt (DataFrame, Liste von Warnungen) zurück.
    Wirft niemals eine Exception, sondern liefert im Fehlerfall ein
    leeres DataFrame + Fehlermeldung als Warnung.
    """
    warnings: list[str] = []

    try:
        if file_bytes is not None:
            df = pd.read_csv(io.BytesIO(file_bytes))
        else:
            df = pd.read_csv(path)
    except FileNotFoundError:
        warnings.append(f"Datei '{path}' wurde nicht gefunden.")
        return pd.DataFrame(), warnings
    except Exception as e:
        warnings.append(f"CSV konnte nicht gelesen werden: {e}")
        return pd.DataFrame(), warnings

    if df.empty:
        warnings.append("Die CSV-Datei enthält keine Zeilen.")
        return pd.DataFrame(), warnings

    # Spaltennamen vereinheitlichen (Groß/Kleinschreibung, Leerzeichen)
    df.columns = [str(c).strip().lower() for c in df.columns]

    # Fehlende Pflichtspalten prüfen
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        warnings.append(
            f"Fehlende Pflichtspalten: {', '.join(missing)}. "
            "Es können keine Auswertungen berechnet werden."
        )
        return pd.DataFrame(), warnings

    # Optionale Spalten sicherstellen
    for col in OPTIONAL_COLUMNS:
        if col not in df.columns:
            df[col] = ""

    # --- Bereinigung ---
    original_len = len(df)

    # name: leere Namen durch Platzhalter ersetzen statt zu droppen
    df["name"] = df["name"].astype(str).str.strip()
    df.loc[df["name"].isin(["", "nan", "None"]), "name"] = "Unbekannte Position"

    # isin: fehlende Werte robust auf "-" setzen
    df["isin"] = df["isin"].astype(str).str.strip()
    df.loc[df["isin"].isin(["", "nan", "None"]), "isin"] = "-"

    # quantity / price numerisch erzwingen
    for col in ["quantity", "price"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    invalid_numeric = df["quantity"].isna() | df["price"].isna()
    n_invalid = int(invalid_numeric.sum())
    if n_invalid > 0:
        warnings.append(
            f"{n_invalid} Zeile(n) mit ungültiger/fehlender Menge oder Preis "
            "wurden ignoriert."
        )
        df = df[~invalid_numeric].copy()

    # negative Mengen/Preise abfangen (unplausibel, aber nicht crashen)
    negative_mask = (df["quantity"] < 0) | (df["price"] < 0)
    n_negative = int(negative_mask.sum())
    if n_negative > 0:
        warnings.append(
            f"{n_negative} Zeile(n) mit negativer Menge oder negativem Preis "
            "wurden ignoriert."
        )
        df = df[~negative_mask].copy()

    # asset_type normalisieren, unbekannte Typen als "Sonstige" markieren
    df["asset_type"] = df["asset_type"].astype(str).str.strip()
    df.loc[df["asset_type"].isin(["", "nan", "None"]), "asset_type"] = "Sonstige"

    unknown_types = sorted(
        set(df["asset_type"]) - set(VALID_ASSET_TYPES) - {"Sonstige"}
    )
    if unknown_types:
        warnings.append(
            "Unbekannte asset_type-Werte gefunden (werden trotzdem "
            f"angezeigt): {', '.join(unknown_types)}"
        )

    if df.empty:
        warnings.append(
            "Nach der Bereinigung sind keine gültigen Positionen mehr übrig."
        )
        return df, warnings

    # Marktwert berechnen
    df["value"] = df["quantity"] * df["price"]

    if len(df) != original_len:
        warnings.append(
            f"{original_len - len(df)} von {original_len} Zeile(n) wurden "
            "beim Einlesen übersprungen (siehe Hinweise oben)."
        )

    return df.reset_index(drop=True), warnings


# --------------------------------------------------------------------------
# Sidebar: Datenquelle
# --------------------------------------------------------------------------
st.sidebar.title("⚙️ Einstellungen")
st.sidebar.caption("Datenquelle: positions.csv")

uploaded = st.sidebar.file_uploader(
    "Alternative CSV hochladen (optional)",
    type=["csv"],
    help="Falls keine Datei hochgeladen wird, versucht die App "
         "'positions.csv' im Arbeitsverzeichnis zu lesen.",
)

file_bytes = uploaded.getvalue() if uploaded is not None else None
df, warnings = load_data(file_bytes, CSV_PATH)

with st.sidebar.expander("📄 CSV-Format", expanded=False):
    st.code(
        "name,isin,quantity,price,asset_type\n"
        "Apple Inc,US0378331005,10,195.50,Stock\n"
        "MSCI World ETF,,50,95.20,ETF\n"
        "Bitcoin,,0.25,58000,Krypto\n"
        "Tagesgeld,,1,5000,Cash\n"
        "Festgeld 12M,,1,10000,Festgeld"
    )

st.sidebar.download_button(
    "📥 Beispiel-CSV herunterladen",
    data=(
        "name,isin,quantity,price,asset_type\n"
        "Apple Inc,US0378331005,10,195.50,Stock\n"
        "MSCI World ETF,,50,95.20,ETF\n"
        "Bitcoin,,0.25,58000,Krypto\n"
        "Tagesgeld,,1,5000,Cash\n"
        "Festgeld 12M,,1,10000,Festgeld\n"
    ),
    file_name="positions_beispiel.csv",
    mime="text/csv",
)

# --------------------------------------------------------------------------
# Titel
# --------------------------------------------------------------------------
st.title("📊 Portfolio Dashboard")
st.caption("Auswertung auf Basis aktueller Positionen (keine Transaktionshistorie).")

# Warnungen anzeigen
for w in warnings:
    st.warning(w)

if df.empty:
    st.info(
        "Keine gültigen Daten vorhanden. Bitte lade eine CSV mit den "
        "Spalten name, quantity, price, asset_type hoch oder lege eine "
        "'positions.csv' im Arbeitsverzeichnis der App ab."
    )
    st.stop()

# --------------------------------------------------------------------------
# Kennzahlen
# --------------------------------------------------------------------------
total_value = float(df["value"].sum())

cash_types = ["Cash", "Festgeld"]
cash_value = float(df.loc[df["asset_type"].isin(cash_types), "value"].sum())
cash_share = (cash_value / total_value * 100) if total_value > 0 else 0.0

n_positions = len(df)

col1, col2, col3 = st.columns(3)
col1.metric("💰 Gesamtwert", f"{total_value:,.2f} €")
col2.metric("🏦 Cash-Anteil (Cash + Festgeld)", f"{cash_share:.1f} %", f"{cash_value:,.2f} €")
col3.metric("📌 Anzahl Positionen", f"{n_positions}")

st.divider()

# --------------------------------------------------------------------------
# Asset Allocation
# --------------------------------------------------------------------------
left, right = st.columns([1, 1])

with left:
    st.subheader("Asset Allocation")
    alloc = (
        df.groupby("asset_type", as_index=False)["value"]
        .sum()
        .sort_values("value", ascending=False)
    )
    if total_value > 0 and not alloc.empty:
        fig_pie = px.pie(
            alloc,
            names="asset_type",
            values="value",
            hole=0.45,
        )
        fig_pie.update_traces(textinfo="percent+label")
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("Keine Werte für die Allokation vorhanden.")

with right:
    st.subheader("Allokation nach Asset-Klasse (Tabelle)")
    if not alloc.empty:
        alloc_display = alloc.copy()
        alloc_display["Anteil %"] = (
            alloc_display["value"] / total_value * 100 if total_value > 0 else 0
        ).round(1)
        alloc_display = alloc_display.rename(
            columns={"asset_type": "Asset-Klasse", "value": "Wert (€)"}
        )
        alloc_display["Wert (€)"] = alloc_display["Wert (€)"].round(2)
        st.dataframe(alloc_display, use_container_width=True, hide_index=True)

st.divider()

# --------------------------------------------------------------------------
# Top 10 Positionen
# --------------------------------------------------------------------------
st.subheader("🏆 Top 10 Positionen nach Wert")

top10 = df.sort_values("value", ascending=False).head(10).copy()
top10["Anteil %"] = (
    (top10["value"] / total_value * 100) if total_value > 0 else 0
).round(1)

top10_display = top10.rename(
    columns={
        "name": "Name",
        "isin": "ISIN",
        "quantity": "Menge",
        "price": "Preis (€)",
        "asset_type": "Asset-Klasse",
        "value": "Wert (€)",
    }
)[["Name", "ISIN", "Asset-Klasse", "Menge", "Preis (€)", "Wert (€)", "Anteil %"]]

top10_display["Preis (€)"] = top10_display["Preis (€)"].round(2)
top10_display["Wert (€)"] = top10_display["Wert (€)"].round(2)

st.dataframe(top10_display, use_container_width=True, hide_index=True)

fig_bar = px.bar(
    top10.sort_values("value", ascending=True),
    x="value",
    y="name",
    orientation="h",
    labels={"value": "Wert (€)", "name": "Position"},
)
st.plotly_chart(fig_bar, use_container_width=True)

st.divider()

# --------------------------------------------------------------------------
# Konzentrationsanalyse
# --------------------------------------------------------------------------
st.subheader("🎯 Konzentrationsanalyse")

sorted_values = df.sort_values("value", ascending=False)["value"]

top3_value = float(sorted_values.head(3).sum())
top5_value = float(sorted_values.head(5).sum())

top3_share = (top3_value / total_value * 100) if total_value > 0 else 0.0
top5_share = (top5_value / total_value * 100) if total_value > 0 else 0.0

c1, c2 = st.columns(2)
c1.metric("Top 3 Positionen", f"{top3_share:.1f} %", f"{top3_value:,.2f} €")
c2.metric("Top 5 Positionen", f"{top5_share:.1f} %", f"{top5_value:,.2f} €")

if top3_share >= 50:
    st.warning(
        "⚠️ Hohe Konzentration: Die Top-3-Positionen machen mehr als "
        "die Hälfte des Portfolios aus."
    )
elif top3_share >= 30:
    st.info(
        "ℹ️ Moderate Konzentration in den Top-3-Positionen."
    )
else:
    st.success("✅ Das Portfolio ist breit gestreut (Top-3-Anteil unter 30 %).")

st.divider()

# --------------------------------------------------------------------------
# Alle Positionen (Rohdaten)
# --------------------------------------------------------------------------
with st.expander("📋 Alle Positionen anzeigen"):
    all_display = df.rename(
        columns={
            "name": "Name",
            "isin": "ISIN",
            "quantity": "Menge",
            "price": "Preis (€)",
            "asset_type": "Asset-Klasse",
            "value": "Wert (€)",
        }
    )[["Name", "ISIN", "Asset-Klasse", "Menge", "Preis (€)", "Wert (€)"]]
    all_display = all_display.sort_values("Wert (€)", ascending=False)
    st.dataframe(all_display, use_container_width=True, hide_index=True)

st.caption(
    "Hinweis: Diese App zeigt ausschließlich den aktuellen Stand der in "
    "positions.csv gepflegten Positionen. Es findet keine Transaktions- "
    "oder Performance-Historie statt."
)
