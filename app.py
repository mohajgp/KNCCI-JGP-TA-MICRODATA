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

# Ensure date column exists and is parsed
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

# === 4. High-Level Cleaning (Non-Aggressive) ===
initial_count = len(df)
df_clean = df.drop_duplicates(subset=['WHAT IS YOUR NATIONAL ID?', 'Business phone number'], keep='first')
cleaned_count = len(df_clean)
duplicates_removed = initial_count - cleaned_count

# === 5. Partial Duplicates Audit ===
id_col = 'WHAT IS YOUR NATIONAL ID?'
phone_col = 'Business phone number'

# Same ID, different phones
id_groups = df_clean.groupby(id_col)[phone_col].nunique()
ids_with_multiple_phones = id_groups[id_groups > 1].index.tolist()
same_id_diff_phone = df_clean[df_clean[id_col].isin(ids_with_multiple_phones)].sort_values(by=id_col)

# Same phone, different IDs
phone_groups = df_clean.groupby(phone_col)[id_col].nunique()
phones_with_multiple_ids = phone_groups[phone_groups > 1].index.tolist()
same_phone_diff_id = df_clean[df_clean[phone_col].isin(phones_with_multiple_ids)].sort_values(by=phone_col)

# === 6. Enrich Columns ===
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

# Normalize gender
df_clean['gender_norm'] = df_clean['Gender of owner'].astype(str).str.lower().str.strip()

# === 7. Summary Metrics ===
total_participants = cleaned_count
total_youth = len(df_clean[df_clean['Age Group'] == 'Youth (18–35)'])
total_adults = len(df_clean[df_clean['Age Group'] == 'Adult (36+)'])
female_count = len(df_clean[df_clean['gender_norm'].str.contains('female', na=False)])
pwd_count = len(df_clean[df_clean['PWD Status'] == 'Yes'])

youth_pct = (total_youth / total_participants) * 100 if total_participants else 0
female_pct = (female_count / total_participants) * 100 if total_participants else 0
pwd_pct = (pwd_count / total_participants) * 100 if total_participants else 0

# Young/Adult breakdown by gender
youth_female = len(df_clean[(df_clean['Age Group'] == 'Youth (18–35)') & (df_clean['gender_norm'].str.contains('female', na=False))])
youth_male = len(df_clean[(df_clean['Age Group'] == 'Youth (18–35)') & (df_clean['gender_norm'].str.contains('male', na=False))])
adult_female = len(df_clean[(df_clean['Age Group'] == 'Adult (36+)') & (df_clean['gender_norm'].str.contains('female', na=False))])
adult_male = len(df_clean[(df_clean['Age Group'] == 'Adult (36+)') & (df_clean['gender_norm'].str.contains('male', na=False))])
pwd_young_female = len(df_clean[(df_clean['Age Group'] == 'Youth (18–35)') & (df_clean['gender_norm'].str.contains('female', na=False)) & (df_clean['PWD Status'] == 'Yes')])
pwd_young_male = len(df_clean[(df_clean['Age Group'] == 'Youth (18–35)') & (df_clean['gender_norm'].str.contains('male', na=False)) & (df_clean['PWD Status'] == 'Yes')])
pwd_adult_female = len(df_clean[(df_clean['Age Group'] == 'Adult (36+)') & (df_clean['gender_norm'].str.contains('female', na=False)) & (df_clean['PWD Status'] == 'Yes')])
pwd_adult_male = len(df_clean[(df_clean['Age Group'] == 'Adult (36+)') & (df_clean['gender_norm'].str.contains('male', na=False)) & (df_clean['PWD Status'] == 'Yes')])

# === 8. Display General Summary ===
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

# TA Breakdown Summary
st.markdown("## 📌 TA Breakdown Summary (Youth, Adults & PWD)")
colA, colB, colC, colD, colE = st.columns(5)
colA.metric("Young Female (18–35)", youth_female)
colB.metric("Young Male (18–35)", youth_male)
colC.metric("Female 36+", adult_female)
colD.metric("Male 36+", adult_male)
colE.metric("PWD (All Genders)", pwd_count)

# PWD Breakdown
st.markdown("### ♿ PWD Breakdown (By Age + Gender)")
colF, colG, colH, colI = st.columns(4)
colF.metric("PWD Young Female", pwd_young_female)
colG.metric("PWD Young Male", pwd_young_male)
colH.metric("PWD Female 36+", pwd_adult_female)
colI.metric("PWD Male 36+", pwd_adult_male)

# === 9. County-Level Summaries ===
county_summary = df_clean['Business Location'].value_counts().reset_index()
county_summary.columns = ['County', 'Count']

gender_summary = df_clean.groupby(['Business Location', 'Gender of owner']).size().reset_index(name='Count')
age_summary = df_clean.groupby(['Business Location', 'Age Group']).size().reset_index(name='Count')
pwd_summary = df_clean.groupby(['Business Location', 'PWD Status']).size().reset_index(name='Count')

st.markdown("## 📍 County-Level Summary")
st.dataframe(county_summary)
st.download_button("⬇️ Download County Summary (.xlsx)", df_clean.to_excel(index=False, engine='openpyxl'), "County_Summary.xlsx")

# === 10. Partial Duplicates Audit Tabs ===
st.markdown("---")
st.markdown("## 🔎 Partial Duplicates Audit (High-Level Cleaning)")
audit_tab1, audit_tab2 = st.tabs([
    f"🆔 Same ID, Different Phone ({len(same_id_diff_phone)})",
    f"📱 Same Phone, Different ID ({len(same_phone_diff_id)})"
])

def df_to_excel_bytes(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

with audit_tab1:
    st.dataframe(same_id_diff_phone)
    st.download_button("⬇️ Download Same ID, Different Phone", df_to_excel_bytes(same_id_diff_phone), "Same_ID_Diff_Phone.xlsx")

with audit_tab2:
    st.dataframe(same_phone_diff_id)
    st.download_button("⬇️ Download Same Phone, Different ID", df_to_excel_bytes(same_phone_diff_id), "Same_Phone_Diff_ID.xlsx")

# === 11. Combined Excel Download ===
excel_all = BytesIO()
with pd.ExcelWriter(excel_all, engine='openpyxl') as writer:
    df_clean.to_excel(writer, sheet_name="Cleaned_Data", index=False)
    county_summary.to_excel(writer, sheet_name="County_Summary", index=False)
    gender_summary.to_excel(writer, sheet_name="Gender_Summary", index=False)
    age_summary.to_excel(writer, sheet_name="Age_Summary", index=False)
    pwd_summary.to_excel(writer, sheet_name="PWD_Summary", index=False)
    same_id_diff_phone.to_excel(writer, sheet_name="Audit_SameID_DiffPhone", index=False)
    same_phone_diff_id.to_excel(writer, sheet_name="Audit_SamePhone_DiffID", index=False)

st.markdown("### 💾 Combined Download")
st.download_button(
    label="⬇️ Download All Summaries + Audit Reports",
    data=excel_all.getvalue(),
    file_name="TA_HighLevel_Cleaned_Audit_Report.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
