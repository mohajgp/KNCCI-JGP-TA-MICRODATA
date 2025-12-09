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

# Filter by date
df = df[(df['Timestamp'].dt.date >= start_date) & (df['Timestamp'].dt.date <= end_date)]

# === 4. High-Level Cleaning ===
initial_count = len(df)
df_clean = df.drop_duplicates(subset=['WHAT IS YOUR NATIONAL ID?', 'Business phone number'], keep='first')
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
    df_clean['PWD Status'] = df_clean[pwd_col].apply(
        lambda x: 'Yes' if 'yes' in x else ('No' if 'no' in x else 'Unspecified')
    )
else:
    df_clean['PWD Status'] = 'Unspecified'

df_clean['gender_norm'] = df_clean['Gender of owner'].str.lower().str.strip()

# === 6. General Summaries ===
total_participants = cleaned_count
total_youth = len(df_clean[df_clean['Age Group'] == 'Youth (18–35)'])
total_adults = len(df_clean[df_clean['Age Group'] == 'Adult (36+)'])
female_count = len(df_clean[df_clean['gender_norm'].str.contains('female', na=False)])
pwd_count = len(df_clean[df_clean['PWD Status'] == 'Yes'])

# TA breakdown
youth_female = len(df_clean[(df_clean['Age Group'] == 'Youth (18–35)') & df_clean['gender_norm'].str.contains('female', na=False)])
youth_male = len(df_clean[(df_clean['Age Group'] == 'Youth (18–35)') & df_clean['gender_norm'].str.contains('male', na=False)])
adult_female = len(df_clean[(df_clean['Age Group'] == 'Adult (36+)') & df_clean['gender_norm'].str.contains('female', na=False)])
adult_male = len(df_clean[(df_clean['Age Group'] == 'Adult (36+)') & df_clean['gender_norm'].str.contains('male', na=False)])

pwd_young_female = len(df_clean[(df_clean['Age Group'] == 'Youth (18–35)') & df_clean['gender_norm'].str.contains('female', na=False) & (df_clean['PWD Status'] == 'Yes')])
pwd_young_male = len(df_clean[(df_clean['Age Group'] == 'Youth (18–35)') & df_clean['gender_norm'].str.contains('male', na=False) & (df_clean['PWD Status'] == 'Yes')])
pwd_adult_female = len(df_clean[(df_clean['Age Group'] == 'Adult (36+)') & df_clean['gender_norm'].str.contains('female', na=False) & (df_clean['PWD Status'] == 'Yes')])
pwd_adult_male = len(df_clean[(df_clean['Age Group'] == 'Adult (36+)') & df_clean['gender_norm'].str.contains('male', na=False) & (df_clean['PWD Status'] == 'Yes')])

# === 7. Display Summaries ===
st.markdown("## 🧾 General Summary")
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total Records (Before Cleaning)", initial_count)
col2.metric("Cleaned Participants", total_participants)
col3.metric("Duplicates Removed", duplicates_removed)
col4.metric("Youth (18–35)", total_youth)
col5.metric("PWD Participants", pwd_count)

col6, col7 = st.columns(2)
col6.metric("Female Participants", female_count)
col7.metric("Adult (36+)", total_adults)

st.markdown("### 📌 TA Breakdown Summary")
colA, colB, colC, colD, colE = st.columns(5)
colA.metric("Young Female (18–35)", youth_female)
colB.metric("Young Male (18–35)", youth_male)
colC.metric("Female 36+", adult_female)
colD.metric("Male 36+", adult_male)
colE.metric("PWD (All)", pwd_count)

st.markdown("### ♿ PWD Breakdown (By Age + Gender)")
colP1, colP2, colP3, colP4 = st.columns(4)
colP1.metric("PWD Young Female", pwd_young_female)
colP2.metric("PWD Young Male", pwd_young_male)
colP3.metric("PWD Female 36+", pwd_adult_female)
colP4.metric("PWD Male 36+", pwd_adult_male)

st.caption(f"⏱️ Data Filter: {start_date} to {end_date} | Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# === 8. County-Level Summaries ===
county_summary = df_clean['Business Location'].value_counts().reset_index()
county_summary.columns = ['County', 'Count']

gender_summary = df_clean.groupby(['Business Location', 'Gender of owner']).size().reset_index(name='Count')
age_summary = df_clean.groupby(['Business Location', 'Age Group']).size().reset_index(name='Count')
pwd_summary = df_clean.groupby(['Business Location', 'PWD Status']).size().reset_index(name='Count')

# Helper: Convert to Excel
def df_to_excel_bytes(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

st.markdown("## 📍 County-Level Summary")
st.dataframe(county_summary)
st.download_button("⬇️ Download County Summary", df_to_excel_bytes(county_summary), "County_Summary.xlsx")

st.markdown("### 👩‍💼 Gender per County")
st.dataframe(gender_summary)
st.download_button("⬇️ Download Gender Summary", df_to_excel_bytes(gender_summary), "Gender_Summary.xlsx")

st.markdown("### 🧑‍💻 Age Group per County")
st.dataframe(age_summary)
st.download_button("⬇️ Download Age Summary", df_to_excel_bytes(age_summary), "Age_Summary.xlsx")

st.markdown("### ♿ PWD per County")
st.dataframe(pwd_summary)
st.download_button("⬇️ Download PWD Summary", df_to_excel_bytes(pwd_summary), "PWD_Summary.xlsx")

# === 9. Charts ===
st.markdown("## 📊 Visual Insights")
st.bar_chart(data=county_summary.set_index('County'))
st.bar_chart(data=df_clean['Gender of owner'].value_counts())
st.bar_chart(data=df_clean['Age Group'].value_counts())
st.bar_chart(data=df_clean['PWD Status'].value_counts())

# === 10. Combined Download ===
excel_all = {
    "Cleaned_Data": df_clean,
    "County_Summary": county_summary,
    "Gender_Summary": gender_summary,
    "Age_Summary": age_summary,
    "PWD_Summary": pwd_summary
}

def all_to_excel(dfs: dict):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for sheet, data in dfs.items():
            data.to_excel(writer, sheet_name=sheet, index=False)
    return output.getvalue()

st.markdown("### 💾 Combined Download")
st.download_button(
    "⬇️ Download All Summaries",
    data=all_to_excel(excel_all),
    file_name="TA_Cleaned_Data_Report_All.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

# === 11. Audit: Leftover Duplicates ===
st.markdown("---")
st.markdown("## 🕵️‍♂️ Duplicate Audit (Leftover After Cleaning)")

same_id_diff_phone = df[df.duplicated(subset=['WHAT IS YOUR NATIONAL ID?'], keep=False) &
                        ~df.duplicated(subset=['WHAT IS YOUR NATIONAL ID?', 'Business phone number'], keep=False)]
st.markdown("### 🔹 Same ID, Different Phone")
st.dataframe(same_id_diff_phone)
st.download_button("⬇️ Download Same ID Diff Phone", df_to_excel_bytes(same_id_diff_phone), "Audit_SameID_DiffPhone.xlsx")

same_phone_diff_id = df[df.duplicated(subset=['Business phone number'], keep=False) &
                        ~df.duplicated(subset=['WHAT IS YOUR NATIONAL ID?', 'Business phone number'], keep=False)]
st.markdown("### 🔹 Same Phone, Different ID")
st.dataframe(same_phone_diff_id)
st.download_button("⬇️ Download Same Phone Diff ID", df_to_excel_bytes(same_phone_diff_id), "Audit_SamePhone_DiffID.xlsx")
