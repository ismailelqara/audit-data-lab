# Interactive web app for the Audit Data Lab
# GitHub @ismailelqara / Linkedin @Ismail EL QARA
# Run with: streamlit run app.py
# app.py

from io import BytesIO

import streamlit as st
from generator import build_dataset


# Helper: build an Excel file in memory 
def to_excel_bytes(data, key, include_key=True):
    """Return an .xlsx file as bytes: 'Invoices' sheet (+ hidden 'Answer_Key')."""
    buffer = BytesIO()
    with st_excel_writer(buffer) as writer:
        data.to_excel(writer, sheet_name="Invoices", index=False)
        ws = writer.sheets["Invoices"]
        ws.freeze_panes = "A2"              # keep the header row visible
        ws.auto_filter.ref = ws.dimensions  # filter buttons on every column
        for col in ws.columns:              # auto-fit column widths
            width = max(len(str(c.value)) if c.value is not None else 0 for c in col)
            ws.column_dimensions[col[0].column_letter].width = min(width + 2, 40)

        if include_key:
            key.to_excel(writer, sheet_name="Answer_Key", index=False)
            writer.sheets["Answer_Key"].sheet_state = "hidden"
    return buffer.getvalue()


def st_excel_writer(buffer):
    import pandas as pd
    return pd.ExcelWriter(buffer, engine="openpyxl", datetime_format="YYYY-MM-DD")


# Page setup 
st.set_page_config(page_title="Audit Data Lab: Anomaly Detection", layout="wide")
st.title("Audit Data Lab: Anomaly Detection")
st.caption(
    "Generate synthetic invoice data with injected anomalies, then practice "
    "detecting them with Excel, SQL or Python.     -      GitHub: @ismailelqara    /    Linkedin: @Ismail EL QARA"
)

# Sidebar: parameters
with st.sidebar:
    st.header("Parameters")

    n = st.slider("Number of invoices", 200, 20000, 1000, 100)
    n_sup = st.slider("Number of suppliers", 5, 200, 50)
    threshold = st.number_input(
        "Approval threshold (MAD)", min_value=1000, value=10000, step=1000
    )
    rate = st.slider("Rate per anomaly type (%)", 0.5, 8.0, 2.0, 0.5) / 100

    st.subheader("Currency mix")
    eur = st.slider("EUR share (%)", 0, 40, 10)
    usd = st.slider("USD share (%)", 0, 40, 5)
    st.caption(f"MAD share: {100 - eur - usd}%")

    seed = st.number_input(
        "Seed (same seed = same data)", value=42, step=1
    )

# Generate button 
if st.button("Generate data", type="primary"):
    try:
        weights = [(100 - eur - usd) / 100, eur / 100, usd / 100]
        data, key = build_dataset(
            n, n_sup, threshold, rate, int(seed), weights
        )
        # Keep results in session_state so they survive reruns
        # (for example when a download button is clicked)
        st.session_state["data"] = data
        st.session_state["key"] = key
    except (ValueError, AssertionError) as e:
        st.error(f"Generation failed: {e}")

# Results 
if "data" in st.session_state:
    data = st.session_state["data"]
    key = st.session_state["key"]

    st.success(f"{len(data)} invoices generated successfully.")

    include_key = st.checkbox(
        "Include the answer key as a hidden sheet in the Excel file", value=True
    )

    col1, col2, col3 = st.columns(3)
    col1.download_button(
        "Download data (CSV)",
        data.to_csv(index=False),
        file_name="invoices.csv",
        mime="text/csv",
    )
    col2.download_button(
        "Download answer key (CSV)",
        key.to_csv(index=False),
        file_name="answer_key.csv",
        mime="text/csv",
    )
    col3.download_button(
        "Download Excel (.xlsx)",
        to_excel_bytes(data, key, include_key),
        file_name="audit_dataset.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    st.subheader("Preview (first 50 rows)")
    st.dataframe(data.head(50), use_container_width=True)

    st.subheader("Injected anomalies")
    st.bar_chart(key["Anomaly_Type"].value_counts())