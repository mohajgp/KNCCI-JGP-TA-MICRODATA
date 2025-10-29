import pandas as pd
import streamlit as st
from io import BytesIO

st.set_page_config(page_title="KNCCI TA Microdata Dashboard", layout="wide")
st.title("📊 Jiinue Growth Program - Microdata Summary Dashboard")

# === 1. Google Sheet link ===
sheet_url = "https://docs.google.com/spreadsheets/d/1LDPRGnR5jlzIMP6RJ9gAcB5m91OO_Wf_1_4liYtVPYM/edit?usp=sharing"
csv_url = sheet_url.replace("/edit?usp=sharing", "/export?format=csv")

# === 2. Load data ===
df = pd.read_csv(csv_url)
df.columns = df.columns.str.strip()

st.subheader("Raw Data Preview")
st.dataframe(df.head())

# === 3. Remove duplicates ===
df_clean = df.drop_duplicates(subset=['WHAT IS YOUR NATIONAL ID?', 'Business phone number'], keep='first')
st.success(f"✅ Duplicate removal complete. Cleaned records: {len(df_clean)} (from {len(df)} original)")

# === 4. County summary ===
county_counts = df_clean['Business Location'].value_counts().reset_index()
county_counts.columns = ['County', 'Count']

st.subheader("📍 County Summary")
st.dataframe(county_counts)
st.bar_chart(data=county_counts.set_index('County'))

# === 5. Download as Excel (.xlsx) ===
def to_excel(df_dict):
    """Creates a single Excel file with multiple sheets."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for name, data in df_dict.items():
            data.to_excel(writer, sheet_name=name, index=False)
    processed_data = output.getvalue()
    return processed_data

excel_file = to_excel({
    "Cleaned_Data": df_clean,
    "County_Summary": county_counts
})

st.download_button(
    label="⬇️ Download Excel File",
    data=excel_file,
    file_name="TA_Cleaned_Data.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
