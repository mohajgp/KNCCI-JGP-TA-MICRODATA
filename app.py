import pandas as pd
import streamlit as st
from io import BytesIO
from datetime import datetime

# === Streamlit Config ===
st.set_page_config(page_title="KNCCI TA Microdata Dashboard", layout="wide")
st.title("📊 Jiinue Growth Program - Microdata Summary Dashboard")

# === 1. Google Sheet link ===
sheet_url = "https://docs.google.com/spreadsheets/d/1LDPRGnR5jlzIMP6RJ9gAcB5m91OO_Wf_1_4liYtVPYM/edit?usp=sharing"
csv_url = sheet_url.replace("/edit?usp=sharing", "/export?format=csv")

# === 2. Load Data ===
df = pd.read_csv(csv_url)
df.columns = df.columns.str.strip()

# === 3. Calculate Duplicates Before Cleaning ===
initial_count = len(df)
df_clean = df.drop_duplicates(subset=['WHAT IS YOUR NATIONAL ID?', 'Business phone number'], keep='first')
cleaned_count = len(df_clean)
duplicates_removed = initial_count - cleaned_count

# === 4. Clean and enrich columns ===
df_clean['Age of owner (full years)'] = pd.to_numeric(df_clean['Age of owner (full years)'], errors='coerce')

df_clean['Age Group'] = df_clean['Age of owner (full years)'].apply(
    lambda x: 'Youth (18–35)' if 18 <= x <= 35 else ('Adult (36+)' if pd.notnull(x) and x > 35 else 'Unknown')
)

pwd_col = 'DO YOU IDENTIFY AS A PERSON WITH A DISABILITY? (THIS QUESTION IS OPTIONAL AND YOUR RESPONSE WILL NOT AFFECT YOUR ELIGIBILITY FOR THE PROGRAM.)'
if pwd_col in df_clean.columns:
    df_clean[pwd_col] = df_clean[pwd_col].astype(str).str.strip().str.lower()
    df_clean['PWD Status'] = df_clean[pwd_col].apply(
        lambda x: 'Yes' if 'yes' in x else ('No' if 'no' in x else 'Unspecified')
    )
else:
    df_clean['PWD Status'] = 'Unspecified'

# === 5. Compute General Summaries ===
total_participants = cleaned_count
total_youth = len(df_clean[df_clean['Age Group'] == 'Youth (18–35)'])
total_adults = len(df_clean[df_clean['Age Group'] == 'Adult (36+)'])
female_count = len(df_clean[df_clean['Gender of owner'].str.lower().str.contains('female', na=False)])
pwd_count = len(df_clean[df_clean['PWD Status'] == 'Yes'])

# Percentages
youth_pct = (total_youth / total_participants) * 100 if total_participants else 0
female_pct = (female_count / total_participants) * 100 if total_participants else 0
pwd_pct = (pwd_count / total_participants) * 100 if total_participants else 0

# === 6. Display General Summary Cards ===
st.markdown("## 🧾 General Summary")
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total Records (Before Cleaning)", initial_count)
col2.metric("Cleaned Participants", total_participants)
col3.metric("Duplicates Removed", duplicates_removed)
col4.metric("Youth (18–35)", f"{total_youth} ({youth_pct:.1f}%)")
col5.metric("PWD Participants", f"{pwd_count} ({pwd_pct:.1f}%)")

col6, col7 = st.columns(2)
col6.metric("Female Participants", f"{female_count} ({female_pct:.1f}%)")
col7.metric("Adult (36+)", total_adults)

st.caption(f"⏱️ Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# === 7. Generate County Summaries ===
county_summary = df_clean['Business Location'].value_counts().reset_index()
county_summary.columns = ['County', 'Count']

gender_summary = df_clean.groupby(['Business Location', 'Gender of owner']).size().reset_index(name='Count')
age_summary = df_clean.groupby(['Business Location', 'Age Group']).size().reset_index(name='Count')
pwd_summary = df_clean.groupby(['Business Location', 'PWD Status']).size().reset_index(name='Count')

# === 8. Display Detailed Tables ===
st.markdown("## 📍 County-Level Summaries")
st.dataframe(county_summary)

st.markdown("### 👩‍💼 Gender Distribution per County")
st.dataframe(gender_summary)

st.markdown("### 🧑‍💻 Age Group Distribution (Youth vs Adult)")
st.dataframe(age_summary)

st.markdown("### ♿ Persons with Disabilities (PWD) Summary")
st.dataframe(pwd_summary)

# === 9. Charts ===
st.markdown("## 📊 Visual Insights")
st.bar_chart(data=county_summary.set_index('County'))
st.bar_chart(data=df_clean['Gender of owner'].value_counts())
st.bar_chart(data=df_clean['Age Group'].value_counts())
st.bar_chart(data=df_clean['PWD Status'].value_counts())

# === 10. Download All Summaries as Excel ===
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
    file_name="TA_Cleaned_Data_Report.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
