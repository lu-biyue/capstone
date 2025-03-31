import streamlit as st
import fitz  # PyMuPDF
import pandas as pd
import re
import io

st.set_page_config(page_title="SOR PDF Extractor", layout="wide")
st.title("📄 Structured SOR PDF Extractor")

def extract_structured_items_from_pdf(pdf_file):
    doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
    data = []
    pattern_item = re.compile(r'\b(A\d{6})\b')
    pattern_rate = re.compile(r'(Unit|No|Set|Each|Lot)?\s*[\$S]?([\d,]+\.\d{2})')
    
    current_section = ""
    current_category = ""

    for page_num in range(len(doc)):
        blocks = doc.load_page(page_num).get_text("blocks")
        blocks = sorted(blocks, key=lambda b: b[1])

        for block in blocks:
            lines = block[4].split('\n')
            for line in lines:
                line = line.strip()
                if not line:
                    continue

                if line.isupper() and not pattern_item.search(line):
                    if " - " in line:
                        current_section = line
                    else:
                        current_category = line
                    continue

                match = pattern_item.search(line)
                if match:
                    item_no = match.group(1)
                    desc = line.replace(item_no, '').strip()
                    data.append({
                        "Section": current_section,
                        "Category": current_category,
                        "Item No.": item_no,
                        "Description": desc
                    })
                elif data:
                    data[-1]["Description"] += ' ' + line.strip()

    if not data:
        return pd.DataFrame(columns=["Section", "Category", "Item No.", "Description", "Unit", "Rate ($)"])

    df = pd.DataFrame(data)

    units, rates = [], []
    for desc in df["Description"]:
        match = pattern_rate.search(desc)
        if match:
            units.append(match.group(1) or '')
            rates.append(match.group(2))
        else:
            units.append('')
            rates.append('')
    df["Unit"] = units
    df["Rate ($)"] = rates

    df = df[df["Description"].str.strip().astype(bool) | df["Rate ($)"].str.strip().astype(bool)].reset_index(drop=True)
    return df

# File uploader
uploaded_file = st.file_uploader("Upload a SOR PDF file", type=["pdf"])

if uploaded_file:
    st.info("Extracting structured data from PDF... please wait.")
    extracted_df = extract_structured_items_from_pdf(uploaded_file)
    st.success(f"✅ Extraction complete. Found {len(extracted_df)} items.")

    st.dataframe(extracted_df)

    # Download button
    output_buffer = io.BytesIO()
    extracted_df.to_excel(output_buffer, index=False)
    output_buffer.seek(0)
    st.download_button(
        label="📥 Download as Excel",
        data=output_buffer,
        file_name="structured_sor_output.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )