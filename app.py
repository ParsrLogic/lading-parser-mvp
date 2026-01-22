import streamlit as st
import pdfplumber
import pandas as pd
import re

st.set_page_config(page_title="Bill of Lading Parser - V0.3.2")
st.title("Bill of Lading Parser - V0.3.2")

uploaded_file = st.file_uploader(
    "Upload a Bill of Lading PDF",
    type=["pdf"]
)

# ---------- UTILITIES ----------

COMPANY_SUFFIXES = [
    "LTD", "LIMITED", "LLC", "PVT", "PVT LTD", "INC",
    "GMBH", "SAS", "SA", "BV", "SRL", "SPA"
]


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

        # Heuristic: must contain a legal company suffix
        if any(suffix in clean for suffix in COMPANY_SUFFIXES):
            # Cut everything after the company name
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


# ---------- MAIN ----------

if uploaded_file is not None:
    with pdfplumber.open(uploaded_file) as pdf:
        raw_text = pdf.pages[0].extract_text()

    if not raw_text:
        st.error("Impossible d'extraire le texte.")
    else:
        shipper_block = extract_block(raw_text, "Shipper", "Consignee")
        consignee_block = extract_block(raw_text, "Consignee", "Notify Party")

        shipper_name = extract_company_name(shipper_block)
        consignee_name = extract_company_name(consignee_block)

        container_no = extract_container_number(raw_text)
        gross_weight = extract_gross_weight(raw_text)

        df = pd.DataFrame({
            "Field": [
                "Shipper (Name)",
                "Consignee (Name)",
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

        st.subheader("Données extraites (V0.3.2)")
        st.dataframe(df, use_container_width=True)

        csv = df.to_csv(index=False).encode("utf-8")

        st.download_button(
            label="Télécharger en CSV",
            data=csv,
            file_name="bill_of_lading_extracted_v03_2.csv",
            mime="text/csv"
        )
