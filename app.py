import streamlit as st
import pdfplumber
import pandas as pd
import re
import json
import os

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="Bill of Lading Parser (Experimental Tool)",
    page_icon="📄",
    layout="centered"
)

# ---------------- SIDEBAR ----------------
st.sidebar.header("How to use")
st.sidebar.markdown(
    """
    1. Upload PDF  
    2. Check preview  
    3. Download CSV
    """
)

st.sidebar.header("Privacy & Security")
st.sidebar.info(
    "Files are processed temporarily in memory (RAM) and not stored."
)

st.sidebar.warning(
    "No user support provided. This is an experimental tool."
)

# ---------------- MAIN TITLE ----------------
st.title("Bill of Lading Parser (Experimental Tool)")

st.subheader(
    "Automated data extraction from PDF. Output provided as raw indicative data."
)

# ---------------- VEILLE BANNER ----------------
st.warning(
    "Projet en test — non maintenu — sans garantie de disponibilité"
)

st.markdown("---")

uploaded_file = st.file_uploader(
    "Upload PDF (Bill of Lading)",
    type=["pdf"]
)

# ---------------- METRICS ----------------

METRICS_FILE = "metrics.json"

def load_metrics():
    if not os.path.exists(METRICS_FILE):
        return {"uploads": 0, "success": 0, "fail": 0}

    with open(METRICS_FILE, "r") as f:
        return json.load(f)


def save_metrics(metrics):
    with open(METRICS_FILE, "w") as f:
        json.dump(metrics, f)

# ---------------- EXTRACTION UTILITIES ----------------

COMPANY_SUFFIXES = [
    "LTD", "LIMITED", "LLC", "PVT", "PVT LTD", "INC",
    "GMBH", "SAS", "SA", "BV", "SRL", "SPA"
]

SUPPORT_EMAIL = "ParsrLogic@proton.me"


def normalize_line(line: str) -> str:
    line = re.sub(r"[^\x20-\x7E]", "", line)
    line = re.sub(r"\s+", " ", line)
    return line.strip()


def extract_block(raw_text, start_keyword, end_keyword):
    pattern = re.compile(
        rf"{start_keyword}\s*(.*?)\s*{end_keyword}",
        re.DOTALL | re.IGNORECASE
    )
    match = pattern.search(raw_text)
    return match.group(1) if match else ""


def extract_company_name(block: str) -> str:
    lines = block.splitlines()

    for line in lines:
        clean = normalize_line(line).upper()
        if not clean:
            continue

        if any(suffix in clean for suffix in COMPANY_SUFFIXES):
            for suffix in COMPANY_SUFFIXES:
                if suffix in clean:
                    idx = clean.find(suffix) + len(suffix)
                    return clean[:idx].title()

    return ""


def extract_container_number(text):
    match = re.search(r"\b[A-Z]{4}\d{7}\b", text)
    return match.group(0) if match else ""


def extract_gross_weight(text):
    match = re.search(
        r"(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*KG",
        text,
        re.IGNORECASE
    )
    return match.group(1) + " KG" if match else ""


# ---------------- MAIN LOGIC ----------------

if uploaded_file is not None:

    metrics = load_metrics()
    metrics["uploads"] += 1
    save_metrics(metrics)
    
    try:
        with pdfplumber.open(uploaded_file) as pdf:
            raw_text = pdf.pages[0].extract_text()

        if not raw_text:
            raise ValueError("No readable text")

        shipper_block = extract_block(raw_text, "Shipper", "Consignee")
        consignee_block = extract_block(raw_text, "Consignee", "Notify Party")

        shipper_name = extract_company_name(shipper_block)
        consignee_name = extract_company_name(consignee_block)

        if not shipper_name or not consignee_name:
            raise ValueError("Critical fields missing")

        container_no = extract_container_number(raw_text)
        gross_weight = extract_gross_weight(raw_text)

        df = pd.DataFrame({
            "Field": [
                "Shipper",
                "Consignee",
                "Container Number",
                "Gross Weight"
            ],
            "Value": [
                shipper_name,
                consignee_name,
                container_no,
                gross_weight
            ]
        })

        metrics = load_metrics()
        metrics["success"] += 1
        save_metrics(metrics)

        st.dataframe(df, use_container_width=True)

        csv = df.to_csv(index=False).encode("utf-8")

        st.download_button(
            label="Download CSV",
            data=csv,
            file_name="bill_of_lading_extracted.csv",
            mime="text/csv"
        )

    except Exception:

        metrics = load_metrics()
        metrics["fail"] += 1
        save_metrics(metrics)

        st.warning(
            "Extraction failed. Format may not be supported."
        )

        mailto_link = (
            f"mailto:{SUPPORT_EMAIL}"
            f"?subject=New%20Format%20Request"
        )

        st.markdown(
            f"[Request format support]({mailto_link})"
        )

# ---------------- FOOTER ----------------
st.markdown("---")

st.caption(
    "Parsr Logic is an experimental technical data conversion utility. "
    "No carrier-specific logic is implemented. Extracted data is indicative only "
    "and provided without any guarantee of accuracy. The user is solely responsible "
    "for verification, validation and use of the data. The publisher declines all "
    "liability for extraction errors, omissions, unsupported formats or any direct "
    "or indirect damage resulting from use of this service."
)

metrics = load_metrics()

st.caption(
    f"Usage stats — uploads: {metrics['uploads']} | "
    f"success: {metrics['success']} | "
    f"fail: {metrics['fail']}"
)
