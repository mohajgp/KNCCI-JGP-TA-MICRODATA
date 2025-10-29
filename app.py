import pandas as pd
import streamlit as st

# === Streamlit App Config ===
st.set_page_config(page_title="KNCCI TA Microdata Dashboard", layout="wide")
st.title("📊 Jiinue Growth Program - Microdata Summary Dashboard")

# === Google Sheet link ===
sheet_url = "https://docs.google.com/spreadsheets/d/1LDPRGnR5jlzIMP6RJ9gAcB5m91OO_Wf_1_4liYtVPYM/edit?usp=sharing"

# === Convert to CSV export link ===
csv_url = sheet_url.replace("/edit?usp=sharing", "/export?format=csv")

# === Load data ===
df = pd.read_csv(csv_url)
df.columns = df.columns.str.strip()

st.subheader("Raw Data Preview")
st.dataframe(df.head())

# === Remove duplicates ===
df_clean = df.drop_duplicates(subset=['WHAT IS YOUR NATIONAL ID?', 'Business phone number'], keep='first')
st.success(f"✅ Duplicate removal complete. Cleaned records: {len(df_clean)} (from {len(df)} original)")

# === County counts ===
county_counts = df_clean['Business Location'].value_counts().reset_index()
county_counts.columns = ['County', 'Count']

st.subheader("📍 County Summary")
st.dataframe(county_counts)

# === Bar chart ===
st.bar_chart(data=county_counts.set_index('County'))

# === Optional downloads ===
with st.expander("⬇️ Download Cleaned Data"):
    cleaned_csv = df_clean.to_csv(index=False).encode('utf-8')
    st.download_button("Download Cleaned Data (CSV)", cleaned_csv, "TA_cleaned.csv", "text/csv")

    summary_csv = county_counts.to_csv(index=False).encode('utf-8')
    st.download_button("Download County Summary (CSV)", summary_csv, "TA_county_summary.csv", "text/csv")
