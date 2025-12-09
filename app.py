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

# Ensure date column exists
if 'Timestamp' in df.columns:
    df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce')
elif 'Training date' in df.columns:
    df['Timestamp'] = pd.to_datetime(df['Training date'], errors='coerce')
else:
    df['Timestamp'] = pd.NaT

# === 3. Sidebar Filters ===
st.sidebar.header("📅 Date Filters")
min_date = df['Timestamp'].min()
max_date = df['Timestamp'].max()

start_date = st.sidebar.date_input("Start Date", min_date.date() if pd.notnull(min_date) else datetime.now().date())
end_date = st.sidebar.date_input("End Date", max_date.date() if pd.notnull(max_date) else datetime.now().date())

df = df[(df['Timestamp'].dt.date >= start_date) & (df['Timestamp'].dt.date <= end_date)]

# === 4. High-Level Duplicate Cleaning ===
id_col = 'WHAT IS YOUR NATIONAL ID?'
phone_col = 'Business phone number'

initial_count = len(df)
df_clean = df.drop_duplicates(subset=[id_col, phone_col], keep='first')
cleaned_count = len(df_clean)
duplicates_removed = initial_count - cleaned_count

# === 5. Enrich Columns ===
df_clean['Age of owner (full years)'] = pd.to_numeric(df_clean['Age of owner (full years)'], errors='coerce')
df_clean['Age Group'] = df_clean['Age of owner (full years)'].apply(
    lambda x: 'Youth (18–35)' if 18 <= x <= 35 else ('Adult (36+)' if pd.notnull(x) and x > 35 else 'Unknown')
)

pwd_col = 'DO YOU IDENTIFY AS A PERSON WITH A DISABILITY? (THIS QUESTION IS OPTIONAL AND YOUR RESPONSE WILL NOT AFFECT YOUR ELIGIBILITY FOR THE PROGRAM.)'
if pwd_col in df_clean.columns:
    df_clean[pwd_col] = df_clean[pwd_col].astype(str).str.strip().str.lower()
    df_clean['PWD Status'] = df_clean[pwd_col].apply(lambda x: 'Yes' if 'yes' in x else ('No' if 'no' in x else 'Unspecified'))
else:
    df_clean['PWD Status'] = 'Unspecified'

df_clean['gender_norm'] = df_clean['Gender of owner'].str.lower().str.strip()

# === 6. General Summaries ===
total_participants = cleaned_count
youth_count = len(df_clean[df_clean['Age Group'] == 'Youth (18–35)'])
adult_count = len(df_clean[df_clean['Age Group'] == 'Adult (36+)'])
female_count = len(df_clean[df_clean['gender_norm'].str.contains('female', na=False)])
pwd_count = len(df_clean[df_clean['PWD Status'] == 'Yes'])

st.markdown("## 🧾 General Summary")
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total Records (Before Cleaning)", initial_count)
col2.metric("Cleaned Participants", total_participants)
col3.metric("Duplicates Removed", duplicates_removed)
col4.metric("Youth (18–35)", youth_count)
col5.metric("PWD Participants", pwd_count)

col6, col7 = st.columns(2)
col6.metric("Female Participants", female_count)
col7.metric("Adult (36+)", adult_count)

# === 7. TA Breakdown Summary (Youth, Adults & PWD) ===
youth_female = len(df_clean[(df_clean['Age Group'] == 'Youth (18–35)') & (df_clean['gender_norm'].str.contains('female', na=False))])
youth_male = len(df_clean[(df_clean['Age Group'] == 'Youth (18–35)') & (df_clean['gender_norm'].str.contains('male', na=False))])
adult_female = len(df_clean[(df_clean['Age Group'] == 'Adult (36+)') & (df_clean['gender_norm'].str.contains('female', na=False))])
adult_male = len(df_clean[(df_clean['Age Group'] == 'Adult (36+)') & (df_clean['gender_norm'].str.contains('male', na=False))])

pwd_total = len(df_clean[df_clean['PWD Status'] == 'Yes'])
pwd_young_female = len(df_clean[(df_clean['Age Group'] == 'Youth (18–35)') & (df_clean['gender_norm'].str.contains('female', na=False)) & (df_clean['PWD Status'] == 'Yes')])
pwd_young_male = len(df_clean[(df_clean['Age Group'] == 'Youth (18–35)') & (df_clean['gender_norm'].str.contains('male', na=False)) & (df_clean['PWD Status'] == 'Yes')])
pwd_adult_female = len(df_clean[(df_clean['Age Group'] == 'Adult (36+)') & (df_clean['gender_norm'].str.contains('female', na=False)) & (df_clean['PWD Status'] == 'Yes')])
pwd_adult_male = len(df_clean[(df_clean['Age Group'] == 'Adult (36+)') & (df_clean['gender_norm'].str.contains('male', na=False)) & (df_clean['PWD Status'] == 'Yes')])

st.markdown("### 📌 TA Breakdown Summary (Youth, Adults & PWD)")
colA, colB, colC, colD, colE = st.columns(5)
colA.metric("Young Female (18–35)", youth_female)
colB.metric("Young Male (18–35)", youth_male)
colC.metric("Female 36+", adult_female)
colD.metric("Male 36+", adult_male)
colE.metric("PWD (All)", pwd_total)

st.markdown("### ♿ PWD Breakdown (By Age + Gender)")
colF, colG, colH, colI = st.columns(4)
colF.metric("PWD Young Female", pwd_young_female)
colG.metric("PWD Young Male", pwd_young_male)
colH.metric("PWD Female 36+", pwd_adult_female)
colI.metric("PWD Male 36+", pwd_adult_male)

# === 8. Helper: Convert to Excel ===
def df_to_excel_bytes(df_dict):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for sheet_name, df_sheet in df_dict.items():
            df_sheet.to_excel(writer, sheet_name=sheet_name, index=False)
    return output.getvalue()

# === 9. Download Options ===
excel_all = df_to_excel_bytes({
    "Cleaned_Data": df_clean
})

st.download_button(
    label="⬇️ Download Cleaned Data",
    data=excel_all,
    file_name="TA_Cleaned_Data.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
