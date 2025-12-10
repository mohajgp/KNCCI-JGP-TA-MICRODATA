import pandas as pd
import streamlit as st
from io import BytesIO
from datetime import datetime
import numpy as np

# === Streamlit Config ===
st.set_page_config(page_title="KNCCI TA Microdata Analysis", layout="wide")
st.title("📊 Jiinue Growth Program - Comprehensive Data Analysis Report")

# === 1. Google Sheet link ===
sheet_url = "https://docs.google.com/spreadsheets/d/1LDPRGnR5jlzIMP6RJ9gAcB5m91OO_Wf_1_4liYtVPYM/edit?usp=sharing"
csv_url = sheet_url.replace("/edit?usp=sharing", "/export?format=csv")

# === 2. Load Data ===
@st.cache_data(ttl=300)
def load_data():
    df = pd.read_csv(csv_url)
    df.columns = df.columns.str.strip()
    return df

col_refresh, col_spacer = st.columns([1, 5])
with col_refresh:
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

df_raw = load_data().copy()

# Key columns
id_col = 'WHAT IS YOUR NATIONAL ID?'
phone_col = 'Business phone number'

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

# Helper function
def df_to_excel_bytes(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

# ============================================================================
# SECTION 1: RAW DATA OVERVIEW
# ============================================================================
st.markdown("---")
st.markdown("# 📋 SECTION 1: Raw Data Overview")

total_raw = len(df)
st.metric("Total Raw Records", total_raw)

# Column inventory
st.markdown("### 📑 Data Columns Available")
col_info = pd.DataFrame({
    'Column Name': df.columns,
    'Non-Null Count': [df[col].notna().sum() for col in df.columns],
    'Null Count': [df[col].isna().sum() for col in df.columns],
    'Unique Values': [df[col].nunique() for col in df.columns],
    'Sample Value': [str(df[col].dropna().iloc[0])[:50] if df[col].notna().any() else 'N/A' for col in df.columns]
})
st.dataframe(col_info, use_container_width=True, height=300)

# ============================================================================
# SECTION 2: DUPLICATE ANALYSIS - COMPLETE RECONCILIATION
# ============================================================================
st.markdown("---")
st.markdown("# 🔍 SECTION 2: Duplicate Analysis & Reconciliation")

st.markdown("""
### Methodology
We categorize every record into ONE of the following mutually exclusive categories:
1. **Unique Records** - No duplicate ID or Phone
2. **Exact Duplicates** - Same ID AND Same Phone (keeping first occurrence)
3. **Same ID, Different Phone** - Potential re-registration with new phone
4. **Same Phone, Different ID** - Shared phone or data entry error
5. **Complex Duplicates** - Records that fall into multiple duplicate categories
""")

# Create duplicate flags for each record
df['_row_id'] = range(len(df))  # Track original row

# Flag: Is this ID duplicated anywhere?
df['_id_duplicated'] = df.duplicated(subset=[id_col], keep=False)

# Flag: Is this Phone duplicated anywhere?
df['_phone_duplicated'] = df.duplicated(subset=[phone_col], keep=False)

# Flag: Is this exact ID+Phone combo duplicated?
df['_exact_duplicated'] = df.duplicated(subset=[id_col, phone_col], keep=False)

# Now categorize each record
def categorize_record(row):
    id_dup = row['_id_duplicated']
    phone_dup = row['_phone_duplicated']
    exact_dup = row['_exact_duplicated']
    
    if not id_dup and not phone_dup:
        return 'Unique'
    elif exact_dup and not (id_dup and not exact_dup) and not (phone_dup and not exact_dup):
        # Only exact duplicate, no cross-duplicates
        return 'Exact Duplicate (Same ID + Phone)'
    elif id_dup and not phone_dup:
        return 'Same ID, Different Phone'
    elif phone_dup and not id_dup:
        return 'Same Phone, Different ID'
    elif id_dup and phone_dup:
        if exact_dup:
            return 'Exact Duplicate (Same ID + Phone)'
        else:
            return 'Complex (ID & Phone both duplicated separately)'
    else:
        return 'Other'

df['_duplicate_category'] = df.apply(categorize_record, axis=1)

# === RECONCILIATION TABLE ===
st.markdown("### 📊 Complete Reconciliation Table")

reconciliation = df['_duplicate_category'].value_counts().reset_index()
reconciliation.columns = ['Category', 'Record Count']
reconciliation['Percentage'] = (reconciliation['Record Count'] / total_raw * 100).round(2)

# Add running total
reconciliation['Cumulative'] = reconciliation['Record Count'].cumsum()

st.dataframe(reconciliation, use_container_width=True)

# Verification
total_categorized = reconciliation['Record Count'].sum()
st.markdown(f"""
### ✅ Verification
- **Total Raw Records:** {total_raw:,}
- **Total Categorized:** {total_categorized:,}
- **Difference:** {total_raw - total_categorized} {'✅ BALANCED' if total_raw == total_categorized else '❌ MISMATCH'}
""")

# Visual breakdown
st.markdown("### 📈 Visual Breakdown")
st.bar_chart(reconciliation.set_index('Category')['Record Count'])

# ============================================================================
# SECTION 3: DETAILED DUPLICATE BREAKDOWN
# ============================================================================
st.markdown("---")
st.markdown("# 📑 SECTION 3: Detailed Duplicate Breakdown")

# Tabs for each category
tabs = st.tabs([
    "Unique Records",
    "Exact Duplicates", 
    "Same ID, Diff Phone",
    "Same Phone, Diff ID",
    "Complex Duplicates"
])

# Key display columns
display_cols = [id_col, phone_col, 'Gender of owner', 'Age of owner (full years)', 
                'Business Location', 'Timestamp', '_duplicate_category']
display_cols = [c for c in display_cols if c in df.columns]

with tabs[0]:
    unique_df = df[df['_duplicate_category'] == 'Unique']
    st.markdown(f"### Unique Records: {len(unique_df):,}")
    st.info("These records have no duplicate IDs or phone numbers - clean data.")
    st.dataframe(unique_df[display_cols].head(100), use_container_width=True)
    st.download_button("⬇️ Download Unique Records", df_to_excel_bytes(unique_df), "Unique_Records.xlsx", key="unique_dl")

with tabs[1]:
    exact_dup_df = df[df['_duplicate_category'] == 'Exact Duplicate (Same ID + Phone)']
    st.markdown(f"### Exact Duplicates: {len(exact_dup_df):,}")
    st.warning("Same person submitted multiple times with same ID and phone.")
    
    # Group to show duplicate sets
    if len(exact_dup_df) > 0:
        exact_sorted = exact_dup_df.sort_values([id_col, phone_col, 'Timestamp'])
        st.dataframe(exact_sorted[display_cols], use_container_width=True, height=400)
        
        # Summary: How many duplicate sets?
        dup_sets = exact_dup_df.groupby([id_col, phone_col]).size().reset_index(name='Count')
        st.markdown(f"**Unique ID+Phone combos with duplicates:** {len(dup_sets)}")
        st.markdown(f"**Average duplicates per combo:** {dup_sets['Count'].mean():.1f}")
    
    st.download_button("⬇️ Download Exact Duplicates", df_to_excel_bytes(exact_dup_df), "Exact_Duplicates.xlsx", key="exact_dl")

with tabs[2]:
    same_id_df = df[df['_duplicate_category'] == 'Same ID, Different Phone']
    st.markdown(f"### Same ID, Different Phone: {len(same_id_df):,}")
    st.warning("⚠️ Same National ID registered with different phone numbers.")
    
    if len(same_id_df) > 0:
        same_id_sorted = same_id_df.sort_values([id_col, 'Timestamp'])
        st.dataframe(same_id_sorted[display_cols], use_container_width=True, height=400)
        
        # Summary
        affected_ids = same_id_df[id_col].nunique()
        st.markdown(f"**Unique IDs affected:** {affected_ids}")
    
    st.download_button("⬇️ Download Same ID Diff Phone", df_to_excel_bytes(same_id_df), "SameID_DiffPhone.xlsx", key="sameid_dl")

with tabs[3]:
    same_phone_df = df[df['_duplicate_category'] == 'Same Phone, Different ID']
    st.markdown(f"### Same Phone, Different ID: {len(same_phone_df):,}")
    st.error("🚨 Different National IDs sharing the same phone - potential fraud or shared device.")
    
    if len(same_phone_df) > 0:
        same_phone_sorted = same_phone_df.sort_values([phone_col, 'Timestamp'])
        st.dataframe(same_phone_sorted[display_cols], use_container_width=True, height=400)
        
        # Summary
        affected_phones = same_phone_df[phone_col].nunique()
        st.markdown(f"**Unique Phones affected:** {affected_phones}")
    
    st.download_button("⬇️ Download Same Phone Diff ID", df_to_excel_bytes(same_phone_df), "SamePhone_DiffID.xlsx", key="samephone_dl")

with tabs[4]:
    complex_df = df[df['_duplicate_category'] == 'Complex (ID & Phone both duplicated separately)']
    st.markdown(f"### Complex Duplicates: {len(complex_df):,}")
    st.error("🔴 These records have BOTH their ID and Phone duplicated in different combinations.")
    
    if len(complex_df) > 0:
        st.dataframe(complex_df[display_cols], use_container_width=True, height=400)
    
    st.download_button("⬇️ Download Complex Duplicates", df_to_excel_bytes(complex_df), "Complex_Duplicates.xlsx", key="complex_dl")

# ============================================================================
# SECTION 4: CLEANING IMPACT ANALYSIS
# ============================================================================
st.markdown("---")
st.markdown("# 🧹 SECTION 4: Cleaning Impact Analysis")

st.markdown("""
### Cleaning Strategy
**Method:** Keep FIRST occurrence of each ID+Phone combination  
**Result:** Removes exact duplicates while preserving unique individuals
""")

# Apply cleaning
df_clean = df.drop_duplicates(subset=[id_col, phone_col], keep='first').copy()

col1, col2, col3 = st.columns(3)
col1.metric("Before Cleaning", f"{total_raw:,}")
col2.metric("After Cleaning", f"{len(df_clean):,}")
col3.metric("Records Removed", f"{total_raw - len(df_clean):,}")

# What remains after cleaning?
st.markdown("### 📊 Post-Cleaning Composition")
post_clean_reconciliation = df_clean['_duplicate_category'].value_counts().reset_index()
post_clean_reconciliation.columns = ['Category', 'Count After Cleaning']
st.dataframe(post_clean_reconciliation, use_container_width=True)

# ============================================================================
# SECTION 5: DEMOGRAPHIC ANALYSIS (Cleaned Data)
# ============================================================================
st.markdown("---")
st.markdown("# 👥 SECTION 5: Demographic Analysis (Cleaned Data)")

# Process demographics
df_clean['Age of owner (full years)'] = pd.to_numeric(df_clean['Age of owner (full years)'], errors='coerce')

# Age classification
def classify_age(x):
    if pd.isna(x):
        return 'Unknown/Missing'
    elif x < 18:
        return 'Under 18'
    elif 18 <= x <= 35:
        return 'Youth (18-35)'
    elif x > 35:
        return 'Adult (36+)'
    else:
        return 'Unknown/Missing'

df_clean['Age Group'] = df_clean['Age of owner (full years)'].apply(classify_age)

# Gender normalization
df_clean['gender_norm'] = df_clean['Gender of owner'].astype(str).str.lower().str.strip()

# PWD Status
pwd_col = 'DO YOU IDENTIFY AS A PERSON WITH A DISABILITY? (THIS QUESTION IS OPTIONAL AND YOUR RESPONSE WILL NOT AFFECT YOUR ELIGIBILITY FOR THE PROGRAM.)'
if pwd_col in df_clean.columns:
    df_clean['PWD Status'] = df_clean[pwd_col].astype(str).str.strip().str.lower().apply(
        lambda x: 'Yes' if 'yes' in str(x) else ('No' if 'no' in str(x) else 'Unspecified')
    )
else:
    df_clean['PWD Status'] = 'Unspecified'

# === AGE ANALYSIS ===
st.markdown("### 🎂 Age Distribution")

age_stats = df_clean['Age of owner (full years)'].describe()
col_a1, col_a2, col_a3, col_a4 = st.columns(4)
col_a1.metric("Min Age", f"{age_stats['min']:.0f}" if pd.notna(age_stats['min']) else "N/A")
col_a2.metric("Max Age", f"{age_stats['max']:.0f}" if pd.notna(age_stats['max']) else "N/A")
col_a3.metric("Mean Age", f"{age_stats['mean']:.1f}" if pd.notna(age_stats['mean']) else "N/A")
col_a4.metric("Missing Ages", f"{df_clean['Age of owner (full years)'].isna().sum():,}")

age_breakdown = df_clean['Age Group'].value_counts().reset_index()
age_breakdown.columns = ['Age Group', 'Count']
age_breakdown['Percentage'] = (age_breakdown['Count'] / len(df_clean) * 100).round(2)
st.dataframe(age_breakdown, use_container_width=True)
st.bar_chart(age_breakdown.set_index('Age Group')['Count'])

# === GENDER ANALYSIS ===
st.markdown("### 👫 Gender Distribution")

gender_breakdown = df_clean['Gender of owner'].value_counts().reset_index()
gender_breakdown.columns = ['Gender', 'Count']
gender_breakdown['Percentage'] = (gender_breakdown['Count'] / len(df_clean) * 100).round(2)
st.dataframe(gender_breakdown, use_container_width=True)
st.bar_chart(gender_breakdown.set_index('Gender')['Count'])

# === PWD ANALYSIS ===
st.markdown("### ♿ PWD Status Distribution")

pwd_breakdown = df_clean['PWD Status'].value_counts().reset_index()
pwd_breakdown.columns = ['PWD Status', 'Count']
pwd_breakdown['Percentage'] = (pwd_breakdown['Count'] / len(df_clean) * 100).round(2)
st.dataframe(pwd_breakdown, use_container_width=True)

# === CROSS-TABULATION ===
st.markdown("### 📊 Cross-Tabulation: Age × Gender")

cross_tab = pd.crosstab(df_clean['Age Group'], df_clean['Gender of owner'], margins=True)
st.dataframe(cross_tab, use_container_width=True)

# === TA INDICATOR SUMMARY ===
st.markdown("### 🎯 TA Indicator Summary (USAID Format)")

# Calculate indicators
is_female = df_clean['gender_norm'].str.contains('female', na=False)
is_male = ~is_female & df_clean['gender_norm'].str.contains('male', na=False)
is_youth = df_clean['Age Group'] == 'Youth (18-35)'
is_adult = df_clean['Age Group'] == 'Adult (36+)'
is_pwd = df_clean['PWD Status'] == 'Yes'

ta_summary = pd.DataFrame({
    'Indicator': [
        'Total Participants (Cleaned)',
        'Female',
        'Male',
        'Youth (18-35)',
        'Adult (36+)',
        'Youth Female',
        'Youth Male', 
        'Adult Female',
        'Adult Male',
        'PWD - Total',
        'PWD - Female',
        'PWD - Male',
        'PWD - Youth',
        'PWD - Adult'
    ],
    'Count': [
        len(df_clean),
        is_female.sum(),
        is_male.sum(),
        is_youth.sum(),
        is_adult.sum(),
        (is_youth & is_female).sum(),
        (is_youth & is_male).sum(),
        (is_adult & is_female).sum(),
        (is_adult & is_male).sum(),
        is_pwd.sum(),
        (is_pwd & is_female).sum(),
        (is_pwd & is_male).sum(),
        (is_pwd & is_youth).sum(),
        (is_pwd & is_adult).sum()
    ]
})
ta_summary['Percentage'] = (ta_summary['Count'] / len(df_clean) * 100).round(2)

st.dataframe(ta_summary, use_container_width=True, height=500)
st.download_button("⬇️ Download TA Summary", df_to_excel_bytes(ta_summary), "TA_Indicator_Summary.xlsx", key="ta_dl")

# ============================================================================
# SECTION 6: COUNTY ANALYSIS
# ============================================================================
st.markdown("---")
st.markdown("# 📍 SECTION 6: County-Level Analysis")

county_col = 'Business Location'

# County summary
county_summary = df_clean[county_col].value_counts().reset_index()
county_summary.columns = ['County', 'Participants']
county_summary['Percentage'] = (county_summary['Participants'] / len(df_clean) * 100).round(2)

st.dataframe(county_summary, use_container_width=True)
st.bar_chart(county_summary.set_index('County')['Participants'])

# County × Gender
st.markdown("### County × Gender")
county_gender = pd.crosstab(df_clean[county_col], df_clean['Gender of owner'])
st.dataframe(county_gender, use_container_width=True)

# County × Age Group
st.markdown("### County × Age Group")
county_age = pd.crosstab(df_clean[county_col], df_clean['Age Group'])
st.dataframe(county_age, use_container_width=True)

# County × PWD
st.markdown("### County × PWD Status")
county_pwd = pd.crosstab(df_clean[county_col], df_clean['PWD Status'])
st.dataframe(county_pwd, use_container_width=True)

# ============================================================================
# SECTION 7: DATA QUALITY REPORT
# ============================================================================
st.markdown("---")
st.markdown("# 🔬 SECTION 7: Data Quality Report")

quality_issues = []

# Check for missing critical fields
critical_fields = [id_col, phone_col, 'Gender of owner', 'Age of owner (full years)', county_col]
for field in critical_fields:
    if field in df_clean.columns:
        missing = df_clean[field].isna().sum()
        if missing > 0:
            quality_issues.append({
                'Issue': f'Missing {field}',
                'Count': missing,
                'Percentage': round(missing/len(df_clean)*100, 2)
            })

# Check for invalid ages
invalid_ages = df_clean[(df_clean['Age of owner (full years)'] < 0) | (df_clean['Age of owner (full years)'] > 120)]
if len(invalid_ages) > 0:
    quality_issues.append({
        'Issue': 'Invalid Age (< 0 or > 120)',
        'Count': len(invalid_ages),
        'Percentage': round(len(invalid_ages)/len(df_clean)*100, 2)
    })

# Check for under 18
under_18 = df_clean[df_clean['Age of owner (full years)'] < 18]
if len(under_18) > 0:
    quality_issues.append({
        'Issue': 'Under 18 Years Old',
        'Count': len(under_18),
        'Percentage': round(len(under_18)/len(df_clean)*100, 2)
    })

quality_df = pd.DataFrame(quality_issues)
if len(quality_df) > 0:
    st.dataframe(quality_df, use_container_width=True)
else:
    st.success("✅ No major data quality issues detected!")

# ============================================================================
# SECTION 8: FULL EXPORT
# ============================================================================
st.markdown("---")
st.markdown("# 💾 SECTION 8: Download Complete Report")

# Prepare all sheets
export_sheets = {
    '1_Raw_Data': df.drop(columns=[c for c in df.columns if c.startswith('_')]),
    '2_Reconciliation': reconciliation,
    '3_Unique_Records': unique_df.drop(columns=[c for c in unique_df.columns if c.startswith('_')]),
    '4_Exact_Duplicates': exact_dup_df.drop(columns=[c for c in exact_dup_df.columns if c.startswith('_')]),
    '5_SameID_DiffPhone': same_id_df.drop(columns=[c for c in same_id_df.columns if c.startswith('_')]),
    '6_SamePhone_DiffID': same_phone_df.drop(columns=[c for c in same_phone_df.columns if c.startswith('_')]),
    '7_Complex_Duplicates': complex_df.drop(columns=[c for c in complex_df.columns if c.startswith('_')]),
    '8_Cleaned_Data': df_clean.drop(columns=[c for c in df_clean.columns if c.startswith('_')]),
    '9_TA_Summary': ta_summary,
    '10_County_Summary': county_summary,
    '11_County_Gender': county_gender.reset_index(),
    '12_County_Age': county_age.reset_index(),
    '13_Age_Breakdown': age_breakdown,
    '14_Gender_Breakdown': gender_breakdown
}

def all_to_excel(dfs: dict):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for sheet, data in dfs.items():
            data.to_excel(writer, sheet_name=sheet[:31], index=False)
    return output.getvalue()

st.download_button(
    "📥 Download Complete Analysis Report (All Sheets)",
    data=all_to_excel(export_sheets),
    file_name=f"KNCCI_TA_Complete_Analysis_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

# Final summary
st.markdown("---")
st.markdown("### 📋 Report Summary")
st.markdown(f"""
| Metric | Value |
|--------|-------|
| Report Generated | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} |
| Date Range | {start_date} to {end_date} |
| Total Raw Records | {total_raw:,} |
| Unique Records | {len(unique_df):,} |
| Exact Duplicates | {len(exact_dup_df):,} |
| Same ID, Diff Phone | {len(same_id_df):,} |
| Same Phone, Diff ID | {len(same_phone_df):,} |
| Complex Duplicates | {len(complex_df):,} |
| **Final Clean Count** | **{len(df_clean):,}** |
| Duplicate Rate | {((total_raw - len(df_clean))/total_raw*100):.1f}% |
""")
