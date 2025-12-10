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

# === 2. Load Data with caching ===
@st.cache_data(ttl=300)  # Cache for 5 minutes, then refresh
def load_data():
    df = pd.read_csv(csv_url)
    df.columns = df.columns.str.strip()
    return df

# Add refresh button
col_refresh, col_spacer = st.columns([1, 5])
with col_refresh:
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

df_raw = load_data()

# Ensure date column exists
if 'Timestamp' in df_raw.columns:
    df_raw['Timestamp'] = pd.to_datetime(df_raw['Timestamp'], errors='coerce')
elif 'Training date' in df_raw.columns:
    df_raw['Timestamp'] = pd.to_datetime(df_raw['Training date'], errors='coerce')
else:
    df_raw['Timestamp'] = pd.NaT

# === 3. Sidebar Filters ===
st.sidebar.header("📅 Date Filters")
min_date = df_raw['Timestamp'].min()
max_date = df_raw['Timestamp'].max()

start_date = st.sidebar.date_input("Start Date", min_date.date() if pd.notnull(min_date) else datetime.now().date())
end_date = st.sidebar.date_input("End Date", max_date.date() if pd.notnull(max_date) else datetime.now().date())

# Filter by date
df = df_raw[(df_raw['Timestamp'].dt.date >= start_date) & (df_raw['Timestamp'].dt.date <= end_date)].copy()

# === 4. DUPLICATE DETECTION (Before Cleaning) ===
st.sidebar.markdown("---")
st.sidebar.header("🔍 Duplicate Detection")

id_col = 'WHAT IS YOUR NATIONAL ID?'
phone_col = 'Business phone number'

# Identify all types of duplicates BEFORE cleaning
# Exact duplicates (same ID AND same phone)
exact_duplicates = df[df.duplicated(subset=[id_col, phone_col], keep=False)]
exact_dup_count = len(exact_duplicates)

# Same ID, Different Phone
same_id_mask = df.duplicated(subset=[id_col], keep=False)
same_id_phone_mask = df.duplicated(subset=[id_col, phone_col], keep=False)
same_id_diff_phone = df[same_id_mask & ~same_id_phone_mask].copy()
same_id_diff_phone_count = len(same_id_diff_phone)

# Same Phone, Different ID  
same_phone_mask = df.duplicated(subset=[phone_col], keep=False)
same_phone_diff_id = df[same_phone_mask & ~same_id_phone_mask].copy()
same_phone_diff_id_count = len(same_phone_diff_id)

# Display counts in sidebar
st.sidebar.metric("Exact Duplicates", exact_dup_count)
st.sidebar.metric("Same ID, Diff Phone", same_id_diff_phone_count)
st.sidebar.metric("Same Phone, Diff ID", same_phone_diff_id_count)

# === 5. High-Level Cleaning ===
initial_count = len(df)
df_clean = df.drop_duplicates(subset=[id_col, phone_col], keep='first')
cleaned_count = len(df_clean)
duplicates_removed = initial_count - cleaned_count

# === 6. Enrich Columns ===
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

# === 7. General Summaries ===
total_participants = cleaned_count
total_youth = len(df_clean[df_clean['Age Group'] == 'Youth (18–35)'])
total_adults = len(df_clean[df_clean['Age Group'] == 'Adult (36+)'])
female_count = len(df_clean[df_clean['gender_norm'].str.contains('female', na=False)])
pwd_count = len(df_clean[df_clean['PWD Status'] == 'Yes'])

# TA breakdown
youth_female = len(df_clean[(df_clean['Age Group'] == 'Youth (18–35)') & df_clean['gender_norm'].str.contains('female', na=False)])
youth_male = len(df_clean[(df_clean['Age Group'] == 'Youth (18–35)') & (df_clean['gender_norm'] == 'male')])
adult_female = len(df_clean[(df_clean['Age Group'] == 'Adult (36+)') & df_clean['gender_norm'].str.contains('female', na=False)])
adult_male = len(df_clean[(df_clean['Age Group'] == 'Adult (36+)') & (df_clean['gender_norm'] == 'male')])

pwd_young_female = len(df_clean[(df_clean['Age Group'] == 'Youth (18–35)') & df_clean['gender_norm'].str.contains('female', na=False) & (df_clean['PWD Status'] == 'Yes')])
pwd_young_male = len(df_clean[(df_clean['Age Group'] == 'Youth (18–35)') & (df_clean['gender_norm'] == 'male') & (df_clean['PWD Status'] == 'Yes')])
pwd_adult_female = len(df_clean[(df_clean['Age Group'] == 'Adult (36+)') & df_clean['gender_norm'].str.contains('female', na=False) & (df_clean['PWD Status'] == 'Yes')])
pwd_adult_male = len(df_clean[(df_clean['Age Group'] == 'Adult (36+)') & (df_clean['gender_norm'] == 'male') & (df_clean['PWD Status'] == 'Yes')])

# === 8. Display Summaries ===
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

# === 9. REAL-TIME DUPLICATE AUDIT (Moved Up & Enhanced) ===
st.markdown("---")
st.markdown("## 🕵️‍♂️ Real-Time Duplicate Audit")

# Create tabs for different duplicate views
tab1, tab2, tab3, tab4 = st.tabs([
    f"📋 All Duplicates ({exact_dup_count})", 
    f"🔹 Same ID, Diff Phone ({same_id_diff_phone_count})",
    f"🔹 Same Phone, Diff ID ({same_phone_diff_id_count})",
    "📊 Duplicate Analysis"
])

# Helper: Convert to Excel
def df_to_excel_bytes(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

with tab1:
    st.markdown("### All Exact Duplicates (Same ID + Same Phone)")
    if exact_dup_count > 0:
        # Sort by ID to group duplicates together
        exact_duplicates_sorted = exact_duplicates.sort_values(by=[id_col, phone_col])
        st.dataframe(exact_duplicates_sorted, use_container_width=True, height=400)
        st.download_button(
            "⬇️ Download Exact Duplicates", 
            df_to_excel_bytes(exact_duplicates_sorted), 
            "Audit_Exact_Duplicates.xlsx",
            key="exact_dup_download"
        )
    else:
        st.success("✅ No exact duplicates found!")

with tab2:
    st.markdown("### Same National ID, Different Phone Numbers")
    st.info("These records have the same ID but registered with different phone numbers - potential data entry issues or multiple submissions.")
    if same_id_diff_phone_count > 0:
        same_id_diff_phone_sorted = same_id_diff_phone.sort_values(by=[id_col])
        
        # Show summary of affected IDs
        affected_ids = same_id_diff_phone[id_col].value_counts()
        st.markdown(f"**Affected Unique IDs:** {len(affected_ids)}")
        
        # Display with highlighting
        st.dataframe(same_id_diff_phone_sorted[[id_col, phone_col, 'Gender of owner', 'Business Location', 'Timestamp']], 
                    use_container_width=True, height=400)
        st.download_button(
            "⬇️ Download Same ID Diff Phone", 
            df_to_excel_bytes(same_id_diff_phone_sorted), 
            "Audit_SameID_DiffPhone.xlsx",
            key="same_id_download"
        )
    else:
        st.success("✅ No Same ID with Different Phone duplicates found!")

with tab3:
    st.markdown("### Same Phone Number, Different National IDs")
    st.warning("⚠️ These records share a phone number but have different IDs - could indicate shared devices or fraudulent entries.")
    if same_phone_diff_id_count > 0:
        same_phone_diff_id_sorted = same_phone_diff_id.sort_values(by=[phone_col])
        
        # Show summary of affected phones
        affected_phones = same_phone_diff_id[phone_col].value_counts()
        st.markdown(f"**Affected Unique Phone Numbers:** {len(affected_phones)}")
        
        st.dataframe(same_phone_diff_id_sorted[[id_col, phone_col, 'Gender of owner', 'Business Location', 'Timestamp']], 
                    use_container_width=True, height=400)
        st.download_button(
            "⬇️ Download Same Phone Diff ID", 
            df_to_excel_bytes(same_phone_diff_id_sorted), 
            "Audit_SamePhone_DiffID.xlsx",
            key="same_phone_download"
        )
    else:
        st.success("✅ No Same Phone with Different ID duplicates found!")

with tab4:
    st.markdown("### Duplicate Analysis Summary")
    
    # Create summary metrics
    col_a1, col_a2, col_a3 = st.columns(3)
    col_a1.metric("Total Records", initial_count)
    col_a2.metric("Unique Records", cleaned_count)
    col_a3.metric("Duplicate Rate", f"{(duplicates_removed/initial_count*100):.1f}%" if initial_count > 0 else "0%")
    
    # Duplicate breakdown chart
    dup_data = pd.DataFrame({
        'Type': ['Exact Duplicates', 'Same ID Diff Phone', 'Same Phone Diff ID'],
        'Count': [exact_dup_count, same_id_diff_phone_count, same_phone_diff_id_count]
    })
    st.bar_chart(dup_data.set_index('Type'))
    
    # County-wise duplicate distribution
    if same_id_diff_phone_count > 0 or same_phone_diff_id_count > 0:
        st.markdown("#### Duplicates by County")
        all_dups = pd.concat([same_id_diff_phone, same_phone_diff_id]).drop_duplicates()
        if 'Business Location' in all_dups.columns:
            county_dups = all_dups['Business Location'].value_counts().reset_index()
            county_dups.columns = ['County', 'Duplicate Count']
            st.dataframe(county_dups, use_container_width=True)

# === 10. County-Level Summaries ===
st.markdown("---")
county_summary = df_clean['Business Location'].value_counts().reset_index()
county_summary.columns = ['County', 'Count']

gender_summary = df_clean.groupby(['Business Location', 'Gender of owner']).size().reset_index(name='Count')
age_summary = df_clean.groupby(['Business Location', 'Age Group']).size().reset_index(name='Count')
pwd_summary = df_clean.groupby(['Business Location', 'PWD Status']).size().reset_index(name='Count')

st.markdown("## 📍 County-Level Summary")
st.dataframe(county_summary, use_container_width=True)
st.download_button("⬇️ Download County Summary", df_to_excel_bytes(county_summary), "County_Summary.xlsx", key="county_dl")

st.markdown("### 👩‍💼 Gender per County")
st.dataframe(gender_summary, use_container_width=True)
st.download_button("⬇️ Download Gender Summary", df_to_excel_bytes(gender_summary), "Gender_Summary.xlsx", key="gender_dl")

st.markdown("### 🧑‍💻 Age Group per County")
st.dataframe(age_summary, use_container_width=True)
st.download_button("⬇️ Download Age Summary", df_to_excel_bytes(age_summary), "Age_Summary.xlsx", key="age_dl")

st.markdown("### ♿ PWD per County")
st.dataframe(pwd_summary, use_container_width=True)
st.download_button("⬇️ Download PWD Summary", df_to_excel_bytes(pwd_summary), "PWD_Summary.xlsx", key="pwd_dl")

# === 11. Charts ===
st.markdown("## 📊 Visual Insights")
st.bar_chart(data=county_summary.set_index('County'))
st.bar_chart(data=df_clean['Gender of owner'].value_counts())
st.bar_chart(data=df_clean['Age Group'].value_counts())
st.bar_chart(data=df_clean['PWD Status'].value_counts())

# === 12. Combined Download ===
excel_all = {
    "Cleaned_Data": df_clean,
    "County_Summary": county_summary,
    "Gender_Summary": gender_summary,
    "Age_Summary": age_summary,
    "PWD_Summary": pwd_summary,
    "Audit_SameID_DiffPhone": same_id_diff_phone,
    "Audit_SamePhone_DiffID": same_phone_diff_id,
    "Audit_ExactDuplicates": exact_duplicates
}

def all_to_excel(dfs: dict):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for sheet, data in dfs.items():
            data.to_excel(writer, sheet_name=sheet[:31], index=False)  # Excel sheet name limit
    return output.getvalue()

st.markdown("### 💾 Combined Download (Including All Audits)")
st.download_button(
    "⬇️ Download All Summaries + Audits",
    data=all_to_excel(excel_all),
    file_name="TA_Cleaned_Data_Report_All.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    key="all_dl"
)

# === 13. Auto-refresh Option ===
st.sidebar.markdown("---")
st.sidebar.header("⚙️ Settings")
auto_refresh = st.sidebar.checkbox("Enable Auto-Refresh (5 min)")
if auto_refresh:
    st.sidebar.info("Dashboard will refresh every 5 minutes")
    # This uses streamlit's rerun with a timer approach
    import time
    time.sleep(300)  # 5 minutes
    st.rerun()
