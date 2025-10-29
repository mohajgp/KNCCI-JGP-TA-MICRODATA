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

# === 4. Ensure numeric age ===
df_clean['Age of owner (full years)'] = pd.to_numeric(df_clean['Age of owner (full years)'], errors='coerce')

# === 5. Add Age Group column ===
df_clean['Age Group'] = df_clean['Age of owner (full years)'].apply(
    lambda x: 'Youth (18–35)' if 18 <= x <= 35 else ('Adult (36+)' if pd.notnull(x) and x > 35 else 'Unknown')
)

# === 6. Normalize PWD responses ===
pwd_col = 'DO YOU IDENTIFY AS A PERSON WITH A DISABILITY? (THIS QUESTION IS OPTIONAL AND YOUR RESPONSE WILL NOT AFFECT YOUR ELIGIBILITY FOR THE PROGRAM.)'
if pwd_col in df_clean.columns:
    df_clean[pwd_col] = df_clean[pwd_col].astype(str).str.strip().str.lower()
    df_clean['PWD Status'] = df_clean[pwd_col].apply(
        lambda x: 'Yes' if 'yes' in x else ('No' if 'no' in x else 'Unspecified')
    )
else:
    df_clean['PWD Status'] = 'Unspecified'

# === 7. Generate summaries ===
county_summary = df_clean['Business Location'].value_counts().reset_index()
county_summary.columns = ['County', 'Count']

gender_summary = df_clean.groupby(['Business Location', 'Gender of owner']).size().reset_index(name='Count')

age_summary = df_clean.groupby(['Business Location', 'Age Group']).size().reset_index(name='Count')

pwd_summary = df_clean.groupby(['Business Location', 'PWD Status']).size().reset_index(name='Count')

# === 8. Display summaries ===
st.subheader("📍 County Summary")
st.dataframe(county_summary)

st.subheader("👩‍💼 Gender Distribution per County")
st.dataframe(gender_summary)

st.subheader("🧑‍💻 Age Group Distribution (Youth vs Adult)")
st.dataframe(age_summary)

st.subheader("♿ Persons with Disabilities (PWD) Summary")
st.dataframe(pwd_summary)

# === 9. Charts ===
st.bar_chart(data=county_summary.set_index('County'))
st.bar_chart(data=df_clean['Gender of owner'].value_counts())
st.bar_chart(data=df_clean['Age Group'].value_counts())
st.bar_chart(data=df_clean['PWD Status'].value_counts())

# === 10. Download all results as Excel (.xlsx) ===
def to_excel(df_dict):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for name, data in df_dict.items():
            data.to_excel(writer, sheet_name=name, index=False)
    processed_data = output.getvalue()
    return processed_data

excel_data = to_excel({
    "Cleaned_Data": df_clean,
    "County_Summary": county_summary,
    "Gender_Summary": gender_summary,
    "Age_Group_Summary": age_summary,
    "PWD_Summary": pwd_summary
})

st.download_button(
    label="⬇️ Download Excel File (All Summaries)",
    data=excel_data,
    file_name="TA_Cleaned_Data_With_PWD.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
