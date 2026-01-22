import streamlit as st
import pdfplumber
import pandas as pd
import re

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="Bill of Lading to CSV Converter (Beta)",
    page_icon="📄",
    layout="centered"
)

# ---------------- SIDEBAR ----------------
st.sidebar.header("How to use")
st.sidebar.markdown(
    """
    **1. Upload PDF**  
    Upload a native Bill of Lading (text-based PDF).

    **2. Check preview**  
    Review extracted key fields.

    **3. Download CSV**  
    Export clean data for Excel or ERP.
    """
)

st.sidebar.header("Privacy & Security")
st.sidebar.info(
    "Your files are processed in RAM and never stored. "
    "They are deleted immediately after processing."
)

# ---------------- MAIN TITLE ----------------
st.title("Bill of Lading to CSV Converter (Beta)")
st.subheader(
    "Extract Shipper, Consignee & Weight in seconds. No signup required."
)

st.markdown("---")

uploaded_file = st.file_uploader(
    "Upload your Bill of Lading (PDF only)",
    type=["pdf"]
)

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


# ---------------- MAIN LOGIC (SECURED + NO SILENT FAIL) ----------------

if uploaded_file is not None:
    try:
        with pdfplumber.open(uploaded_file) as pdf:
            raw_text = pdf.pages[0].extract_text()

        if not raw_text:
            raise ValueError("No readable text")

        shipper_block = extract_block(raw_text, "Shipper", "Consignee")
        consignee_block = extract_block(raw_text, "Consignee", "Notify Party")

        shipper_name = extract_company_name(shipper_block)
        consignee_name = extract_company_name(consignee_block)

        # ---- CRITICAL VALIDATION ----
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

        st.success("Extraction completed")
        st.dataframe(df, use_container_width=True)

        csv = df.to_csv(index=False).encode("utf-8")

        st.download_button(
            label="Download CSV",
            data=csv,
            file_name="bill_of_lading_extracted_v05_1.csv",
            mime="text/csv"
        )

    except Exception:
        st.warning(
            "We couldn't detect the data automatically. "
            "This Bill of Lading format might be new to our system."
        )

        mailto_link = (
            f"mailto:{SUPPORT_EMAIL}"
            f"?subject=New%20Format%20Request"
        )

        st.markdown(
            f"[Request support for this format]({mailto_link})"
        )

# ---------------- LEGAL DISCLAIMER ----------------
st.markdown("---")
st.caption(
    "Legal Disclaimer: This tool is provided 'as is' without warranty of any kind. "
    "The user assumes all responsibility for the accuracy of the extracted data. "
    "ParsrLogic is not liable for any errors or omissions."
)
