import pandas as pd
import streamlit as st
from io import BytesIO
from datetime import datetime
import numpy as np

# =============================================================================
# STREAMLIT CONFIG
# =============================================================================
st.set_page_config(page_title="KNCCI TA Microdata Analysis", layout="wide")

st.title("📊 Jiinue Growth Program - TA Microdata Analysis & Audit Portal")

# =============================================================================
# 1. DATA LOADING
# =============================================================================

# Google Sheet link
SHEET_URL = "https://docs.google.com/spreadsheets/d/1LDPRGnR5jlzIMP6RJ9gAcB5m91OO_Wf_1_4liYtVPYM/edit?usp=sharing"
CSV_URL = SHEET_URL.replace("/edit?usp=sharing", "/export?format=csv")

@st.cache_data(ttl=300)
def load_data():
    df = pd.read_csv(CSV_URL)
    df.columns = df.columns.str.strip()
    # Standardize timestamp
    if 'Timestamp' in df.columns:
        df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce')
    elif 'Training date' in df.columns:
        df['Timestamp'] = pd.to_datetime(df['Training date'], errors='coerce')
    else:
        df['Timestamp'] = pd.NaT
    return df

# Refresh button
col_refresh, col_spacer = st.columns([1, 5])
with col_refresh:
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

df_raw = load_data().copy()

# Key columns (adjust here if column names ever change)
id_col = 'WHAT IS YOUR NATIONAL ID?'
phone_col = 'Business phone number'
county_col = 'Business Location'
gender_col = 'Gender of owner'
age_col = 'Age of owner (full years)'
pwd_col = 'DO YOU IDENTIFY AS A PERSON WITH A DISABILITY? (THIS QUESTION IS OPTIONAL AND YOUR RESPONSE WILL NOT AFFECT YOUR ELIGIBILITY FOR THE PROGRAM.)'

# =============================================================================
# 2. GLOBAL SIDEBAR FILTERS (DATE + COUNTY + CLEANING LEVEL)
# =============================================================================

st.sidebar.header("📅 Date Filters")
min_date = df_raw['Timestamp'].min()
max_date = df_raw['Timestamp'].max()

start_date = st.sidebar.date_input(
    "Start Date",
    min_date.date() if pd.notnull(min_date) else datetime.now().date()
)
end_date = st.sidebar.date_input(
    "End Date",
    max_date.date() if pd.notnull(max_date) else datetime.now().date()
)

df = df_raw[(df_raw['Timestamp'].dt.date >= start_date) &
            (df_raw['Timestamp'].dt.date <= end_date)].copy()

st.sidebar.header("📍 County Filter")
if county_col in df.columns:
    all_counties = sorted(df[county_col].dropna().unique())
    selected_counties = st.sidebar.multiselect(
        "Select County (leave empty for ALL)",
        options=all_counties,
        default=[]
    )
    if selected_counties:
        df = df[df[county_col].isin(selected_counties)]
else:
    st.sidebar.warning(f"Column '{county_col}' not found in data.")

total_raw = len(df)

# Helper: Excel export
def df_to_excel_bytes(df_in):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_in.to_excel(writer, index=False)
    return output.getvalue()

# =============================================================================
# 3. DUPLICATE CLASSIFICATION (RUN ONCE, USED BY MULTIPLE SECTIONS)
# =============================================================================

# Row id for tracking (if needed later)
df['_row_id'] = range(len(df))

# Flags
df['_id_duplicated'] = df.duplicated(subset=[id_col], keep=False)
df['_phone_duplicated'] = df.duplicated(subset=[phone_col], keep=False)
df['_exact_duplicated'] = df.duplicated(subset=[id_col, phone_col], keep=False)

def categorize_record(row):
    id_dup = row['_id_duplicated']
    phone_dup = row['_phone_duplicated']
    exact_dup = row['_exact_duplicated']

    if not id_dup and not phone_dup:
        return 'Unique'
    elif exact_dup and not (id_dup and not exact_dup) and not (phone_dup and not exact_dup):
        # Pure exact duplicate pattern
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

# Category subsets
unique_df = df[df['_duplicate_category'] == 'Unique']
exact_dup_df = df[df['_duplicate_category'] == 'Exact Duplicate (Same ID + Phone)']
same_id_df = df[df['_duplicate_category'] == 'Same ID, Different Phone']
same_phone_df = df[df['_duplicate_category'] == 'Same Phone, Different ID']
complex_df = df[df['_duplicate_category'] == 'Complex (ID & Phone both duplicated separately)']

# Reconciliation table
reconciliation = df['_duplicate_category'].value_counts().reset_index()
reconciliation.columns = ['Category', 'Record Count']
reconciliation['Percentage'] = (reconciliation['Record Count'] / total_raw * 100).round(2)
reconciliation['Cumulative'] = reconciliation['Record Count'].cumsum()

# =============================================================================
# 4. CLEANING STEPS (STRICT PIPELINE)
# =============================================================================

# STEP 1: Remove exact duplicates
step1_df = df.drop_duplicates(subset=[id_col, phone_col], keep='first').copy()
step1_removed = total_raw - len(step1_df)

# STEP 2: From step1, remove duplicate IDs
step2_df = step1_df.drop_duplicates(subset=[id_col], keep='first').copy()
step2_removed = len(step1_df) - len(step2_df)

# STEP 3: From step2, remove duplicate phones
step3_df = step2_df.drop_duplicates(subset=[phone_col], keep='first').copy()
step3_removed = len(step2_df) - len(step3_df)

cleaning_steps = pd.DataFrame({
    'Step': [
        '0. Raw Data',
        '1. Remove Exact Duplicates (Same ID + Phone)',
        '2. Remove Duplicate IDs (keep first)',
        '3. Remove Duplicate Phones (keep first)'
    ],
    'Records Remaining': [
        total_raw,
        len(step1_df),
        len(step2_df),
        len(step3_df)
    ],
    'Removed in Step': [
        0,
        step1_removed,
        step2_removed,
        step3_removed
    ],
    'Cumulative Removed': [
        0,
        step1_removed,
        step1_removed + step2_removed,
        step1_removed + step2_removed + step3_removed
    ]
})

# Cleaning level selector (sidebar so it’s global)
st.sidebar.header("🧹 Cleaning Level")
cleaning_choice = st.sidebar.radio(
    "Select cleaned dataset for analysis",
    options=[
        f"Step 1: Exact duplicates only ({len(step1_df):,} records)",
        f"Step 2: + Duplicate IDs removed ({len(step2_df):,} records)",
        f"Step 3: + Duplicate Phones removed ({len(step3_df):,} records) [Recommended]"
    ],
    index=2
)

if "Step 1" in cleaning_choice:
    df_clean = step1_df.copy()
    cleaning_level = "Step 1 (Exact Duplicates Only)"
elif "Step 2" in cleaning_choice:
    df_clean = step2_df.copy()
    cleaning_level = "Step 2 (+ Duplicate IDs)"
else:
    df_clean = step3_df.copy()
    cleaning_level = "Step 3 (Strictest - All Duplicates)"

# =============================================================================
# 5. DEMOGRAPHIC PREPROCESS (ON CLEAN DATA)
# =============================================================================

# Age
if age_col in df_clean.columns:
    df_clean[age_col] = pd.to_numeric(df_clean[age_col], errors='coerce')
else:
    df_clean[age_col] = np.nan

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

df_clean['Age Group'] = df_clean[age_col].apply(classify_age)

# Gender normalization
if gender_col in df_clean.columns:
    df_clean['gender_norm'] = df_clean[gender_col].astype(str).str.lower().str.strip()
else:
    df_clean['gender_norm'] = ""

# PWD normalization
if pwd_col in df_clean.columns:
    df_clean['PWD Status'] = df_clean[pwd_col].astype(str).str.strip().str.lower().apply(
        lambda x: 'Yes' if 'yes' in str(x) else ('No' if 'no' in str(x) else 'Unspecified')
    )
else:
    df_clean['PWD Status'] = 'Unspecified'

# Age breakdown
age_breakdown = df_clean['Age Group'].value_counts().reset_index()
age_breakdown.columns = ['Age Group', 'Count']
age_breakdown['Percentage'] = (age_breakdown['Count'] / len(df_clean) * 100).round(2)

# Gender breakdown
if gender_col in df_clean.columns:
    gender_breakdown = df_clean[gender_col].value_counts().reset_index()
    gender_breakdown.columns = ['Gender', 'Count']
    gender_breakdown['Percentage'] = (gender_breakdown['Count'] / len(df_clean) * 100).round(2)
else:
    gender_breakdown = pd.DataFrame(columns=['Gender', 'Count', 'Percentage'])

# PWD breakdown
pwd_breakdown = df_clean['PWD Status'].value_counts().reset_index()
pwd_breakdown.columns = ['PWD Status', 'Count']
pwd_breakdown['Percentage'] = (pwd_breakdown['Count'] / len(df_clean) * 100).round(2)

# TA indicator summary
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

# County summaries (on cleaned data)
if county_col in df_clean.columns:
    county_summary = df_clean[county_col].value_counts().reset_index()
    county_summary.columns = ['County', 'Participants']
    county_summary['Percentage'] = (county_summary['Participants'] / len(df_clean) * 100).round(2)

    county_gender = pd.crosstab(df_clean[county_col], df_clean.get(gender_col, pd.Series()))
    county_age = pd.crosstab(df_clean[county_col], df_clean['Age Group'])
    county_pwd = pd.crosstab(df_clean[county_col], df_clean['PWD Status'])
else:
    county_summary = pd.DataFrame(columns=['County', 'Participants', 'Percentage'])
    county_gender = pd.DataFrame()
    county_age = pd.DataFrame()
    county_pwd = pd.DataFrame()

# =============================================================================
# 6. DATA QUALITY CHECKS (ON CLEANED DATA)
# =============================================================================

quality_issues = []
critical_fields = [id_col, phone_col, gender_col, age_col, county_col]
for field in critical_fields:
    if field in df_clean.columns:
        missing = df_clean[field].isna().sum()
        if missing > 0:
            quality_issues.append({
                'Issue': f'Missing {field}',
                'Count': missing,
                'Percentage': round(missing / len(df_clean) * 100, 2)
            })

# Invalid ages
invalid_ages = df_clean[(df_clean[age_col] < 0) | (df_clean[age_col] > 120)]
if len(invalid_ages) > 0:
    quality_issues.append({
        'Issue': 'Invalid Age (< 0 or > 120)',
        'Count': len(invalid_ages),
        'Percentage': round(len(invalid_ages) / len(df_clean) * 100, 2)
    })

# Under 18
under_18 = df_clean[df_clean[age_col] < 18]
if len(under_18) > 0:
    quality_issues.append({
        'Issue': 'Under 18 Years Old',
        'Count': len(under_18),
        'Percentage': round(len(under_18) / len(df_clean) * 100, 2)
    })

quality_df = pd.DataFrame(quality_issues)

# =============================================================================
# 7. EXPORT PACKAGE (MULTI-SHEET EXCEL)
# =============================================================================

export_sheets = {
    '1_Raw_Filtered': df.drop(columns=[c for c in df.columns if c.startswith('_')]),
    '2_Reconciliation': reconciliation,
    '3_Unique_Records': unique_df.drop(columns=[c for c in unique_df.columns if c.startswith('_')]),
    '4_Exact_Duplicates': exact_dup_df.drop(columns=[c for c in exact_dup_df.columns if c.startswith('_')]),
    '5_SameID_DiffPhone': same_id_df.drop(columns=[c for c in same_id_df.columns if c.startswith('_')]),
    '6_SamePhone_DiffID': same_phone_df.drop(columns=[c for c in same_phone_df.columns if c.startswith('_')]),
    '7_Complex_Duplicates': complex_df.drop(columns=[c for c in complex_df.columns if c.startswith('_')]),
    '8_Clean_Step1': step1_df.drop(columns=[c for c in step1_df.columns if c.startswith('_')]),
    '9_Clean_Step2': step2_df.drop(columns=[c for c in step2_df.columns if c.startswith('_')]),
    '10_Clean_Step3_Final': step3_df.drop(columns=[c for c in step3_df.columns if c.startswith('_')]),
    '11_TA_Summary': ta_summary,
    '12_County_Summary': county_summary,
    '13_Cleaning_Steps': cleaning_steps,
    '14_Age_Breakdown': age_breakdown,
    '15_Gender_Breakdown': gender_breakdown,
    '16_Data_Quality': quality_df
}

def all_to_excel(dfs: dict):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for sheet, data in dfs.items():
            data.to_excel(writer, sheet_name=sheet[:31], index=False)
    return output.getvalue()

# =============================================================================
# 8. "PAGES" INSIDE SINGLE FILE (SECTION SELECTOR)
# =============================================================================

section = st.sidebar.selectbox(
    "📚 Select Section",
    [
        "1️⃣ Raw Data Overview",
        "2️⃣ Duplicate Summary",
        "3️⃣ Duplicate Detail (Audit by County)",
        "4️⃣ Cleaning Impact",
        "5️⃣ Demographic & TA Indicators",
        "6️⃣ County Analysis",
        "7️⃣ Data Quality Report",
        "8️⃣ Export & Report Snapshot"
    ]
)

# =============================================================================
# SECTION 1: RAW DATA OVERVIEW
# =============================================================================
if section == "1️⃣ Raw Data Overview":
    st.markdown("## 📋 SECTION 1: Raw Data Overview")

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Raw Records (after filters)", f"{total_raw:,}")
    col2.metric("Current Cleaning Level", cleaning_level)
    col3.metric("Records Used for Analysis", f"{len(df_clean):,}")

    st.markdown("### 📑 Column Inventory")
    col_info = pd.DataFrame({
        'Column Name': df.columns,
        'Non-Null Count': [df[col].notna().sum() for col in df.columns],
        'Null Count': [df[col].isna().sum() for col in df.columns],
        'Unique Values': [df[col].nunique() for col in df.columns],
        'Sample Value': [str(df[col].dropna().iloc[0])[:50] if df[col].notna().any() else 'N/A'
                         for col in df.columns]
    })
    st.dataframe(col_info, use_container_width=True, height=350)

# =============================================================================
# SECTION 2: DUPLICATE SUMMARY
# =============================================================================
elif section == "2️⃣ Duplicate Summary":
    st.markdown("## 🔍 SECTION 2: Duplicate Analysis & Reconciliation")

    st.markdown("""
**Methodology:**  
Each record is assigned to exactly one category (Unique, Exact Duplicate, Same ID Diff Phone, Same Phone Diff ID, Complex).  
The sum of all categories = total filtered records.
""")

    st.markdown("### 📊 Reconciliation Table")
    st.dataframe(reconciliation, use_container_width=True)

    total_categorized = reconciliation['Record Count'].sum()
    st.markdown(f"""
**Verification**  
- Total Raw Records (filtered): **{total_raw:,}**  
- Total Categorized: **{total_categorized:,}**  
- Difference: **{total_raw - total_categorized}** → {"✅ BALANCED" if total_raw == total_categorized else "❌ MISMATCH"}
""")

    st.markdown("### 📈 Visual Breakdown")
    st.bar_chart(reconciliation.set_index('Category')['Record Count'])

# =============================================================================
# SECTION 3: DUPLICATE DETAIL (AUDIT)
# =============================================================================
elif section == "3️⃣ Duplicate Detail (Audit by County)":
    st.markdown("## 📑 SECTION 3: Detailed Duplicate Breakdown & County Audit")

    st.info("Use the sidebar County Filter to focus on a single county or a subset, then inspect each duplicate type.")

    display_cols = [id_col, phone_col, gender_col, age_col,
                    county_col, 'Timestamp', '_duplicate_category']
    display_cols = [c for c in display_cols if c in df.columns]

    tabs = st.tabs([
        "Unique Records",
        "Exact Duplicates",
        "Same ID, Diff Phone",
        "Same Phone, Diff ID",
        "Complex Duplicates"
    ])

    with tabs[0]:
        st.markdown(f"### Unique Records: {len(unique_df):,}")
        st.dataframe(unique_df[display_cols].head(300), use_container_width=True)
        st.download_button(
            "⬇️ Download Unique Records",
            df_to_excel_bytes(unique_df),
            "Unique_Records.xlsx"
        )

    with tabs[1]:
        st.markdown(f"### Exact Duplicates (Same ID + Phone): {len(exact_dup_df):,}")
        if len(exact_dup_df) > 0:
            exact_sorted = exact_dup_df.sort_values([id_col, phone_col, 'Timestamp'])
            st.dataframe(exact_sorted[display_cols], use_container_width=True, height=400)

            dup_sets = exact_dup_df.groupby([id_col, phone_col]).size().reset_index(name='Count')
            st.markdown(f"**Distinct ID+Phone combos with duplicates:** {len(dup_sets)}")
            st.markdown(f"**Average records per duplicate combo:** {dup_sets['Count'].mean():.1f}")
        st.download_button(
            "⬇️ Download Exact Duplicates",
            df_to_excel_bytes(exact_dup_df),
            "Exact_Duplicates.xlsx"
        )

    with tabs[2]:
        st.markdown(f"### Same ID, Different Phone: {len(same_id_df):,}")
        if len(same_id_df) > 0:
            same_id_sorted = same_id_df.sort_values([id_col, 'Timestamp'])
            st.dataframe(same_id_sorted[display_cols], use_container_width=True, height=400)
            affected_ids = same_id_df[id_col].nunique()
            st.markdown(f"**Unique IDs affected:** {affected_ids}")
        st.download_button(
            "⬇️ Download Same ID – Different Phone",
            df_to_excel_bytes(same_id_df),
            "SameID_DiffPhone.xlsx"
        )

    with tabs[3]:
        st.markdown(f"### Same Phone, Different ID: {len(same_phone_df):,}")
        if len(same_phone_df) > 0:
            same_phone_sorted = same_phone_df.sort_values([phone_col, 'Timestamp'])
            st.dataframe(same_phone_sorted[display_cols], use_container_width=True, height=400)
            affected_phones = same_phone_df[phone_col].nunique()
            st.markdown(f"**Unique Phones affected:** {affected_phones}")
        st.download_button(
            "⬇️ Download Same Phone – Different ID",
            df_to_excel_bytes(same_phone_df),
            "SamePhone_DiffID.xlsx"
        )

    with tabs[4]:
        st.markdown(f"### Complex Duplicates: {len(complex_df):,}")
        if len(complex_df) > 0:
            st.dataframe(complex_df[display_cols], use_container_width=True, height=400)
        st.download_button(
            "⬇️ Download Complex Duplicates",
            df_to_excel_bytes(complex_df),
            "Complex_Duplicates.xlsx"
        )

# =============================================================================
# SECTION 4: CLEANING IMPACT
# =============================================================================
elif section == "4️⃣ Cleaning Impact":
    st.markdown("## 🧹 SECTION 4: Cleaning Impact Analysis")

    st.markdown("### Step-by-Step Cleaning Overview")
    st.dataframe(cleaning_steps, use_container_width=True)

    st.markdown("### 📊 Records Remaining by Step")
    col_c1, col_c2, col_c3, col_c4 = st.columns(4)
    col_c1.metric("Raw", f"{total_raw:,}")
    col_c2.metric("After Step 1", f"{len(step1_df):,}", f"-{step1_removed:,}")
    col_c3.metric("After Step 2", f"{len(step2_df):,}", f"-{step2_removed:,}")
    col_c4.metric("After Step 3 (Final)", f"{len(step3_df):,}", f"-{step3_removed:,}")

    total_dup_rate = (total_raw - len(step3_df)) / total_raw * 100 if total_raw > 0 else 0
    st.markdown(f"**Total duplicate rate (strictest cleaning):** {total_dup_rate:.1f}%")

# =============================================================================
# SECTION 5: DEMOGRAPHIC & TA INDICATORS
# =============================================================================
elif section == "5️⃣ Demographic & TA Indicators":
    st.markdown("## 👥 SECTION 5: Demographic Analysis & TA Indicators (Cleaned Data)")

    st.markdown(f"**Cleaning Level in Use:** {cleaning_level} → **{len(df_clean):,}** records")

    # Age stats
    age_stats = df_clean[age_col].describe()
    col_a1, col_a2, col_a3, col_a4 = st.columns(4)
    col_a1.metric("Min Age", f"{age_stats['min']:.0f}" if pd.notna(age_stats['min']) else "N/A")
    col_a2.metric("Max Age", f"{age_stats['max']:.0f}" if pd.notna(age_stats['max']) else "N/A")
    col_a3.metric("Mean Age", f"{age_stats['mean']:.1f}" if pd.notna(age_stats['mean']) else "N/A")
    col_a4.metric("Missing Ages", f"{df_clean[age_col].isna().sum():,}")

    st.markdown("### 🎂 Age Group Distribution")
    st.dataframe(age_breakdown, use_container_width=True)
    st.bar_chart(age_breakdown.set_index('Age Group')['Count'])

    st.markdown("### 👫 Gender Distribution")
    if not gender_breakdown.empty:
        st.dataframe(gender_breakdown, use_container_width=True)
        st.bar_chart(gender_breakdown.set_index('Gender')['Count'])
    else:
        st.info("Gender column not found in dataset.")

    st.markdown("### ♿ PWD Status Distribution")
    st.dataframe(pwd_breakdown, use_container_width=True)

    st.markdown("### 🎯 TA Indicator Summary (USAID-style)")
    st.dataframe(ta_summary, use_container_width=True, height=500)
    st.download_button(
        "⬇️ Download TA Summary",
        df_to_excel_bytes(ta_summary),
        "TA_Indicator_Summary.xlsx"
    )

# =============================================================================
# SECTION 6: COUNTY ANALYSIS
# =============================================================================
elif section == "6️⃣ County Analysis":
    st.markdown("## 📍 SECTION 6: County-Level Analysis (Cleaned Data)")

    st.markdown(f"**Current Cleaning Level:** {cleaning_level}")
    st.markdown("Use the sidebar County Filter to focus on specific counties.")

    st.markdown("### County Summary")
    st.dataframe(county_summary, use_container_width=True)
    if not county_summary.empty:
        st.bar_chart(county_summary.set_index('County')['Participants'])

    st.markdown("### County × Gender")
    if not county_gender.empty:
        st.dataframe(county_gender, use_container_width=True)
    else:
        st.info("County × Gender table not available (missing columns).")

    st.markdown("### County × Age Group")
    if not county_age.empty:
        st.dataframe(county_age, use_container_width=True)
    else:
        st.info("County × Age Group table not available.")

    st.markdown("### County × PWD Status")
    if not county_pwd.empty:
        st.dataframe(county_pwd, use_container_width=True)
    else:
        st.info("County × PWD Status table not available.")

# =============================================================================
# SECTION 7: DATA QUALITY REPORT
# =============================================================================
elif section == "7️⃣ Data Quality Report":
    st.markdown("## 🔬 SECTION 7: Data Quality Report (Cleaned Data)")

    if not quality_df.empty:
        st.dataframe(quality_df, use_container_width=True)
    else:
        st.success("✅ No major data quality issues detected based on current checks.")

    st.markdown("### Under-18 Records (Flagged)")
    if len(under_18) > 0:
        show_cols = [id_col, phone_col, gender_col, age_col, county_col, 'Timestamp']
        show_cols = [c for c in show_cols if c in under_18.columns]
        st.dataframe(under_18[show_cols], use_container_width=True, height=300)
    else:
        st.info("No under-18 records detected in cleaned dataset.")

# =============================================================================
# SECTION 8: EXPORT & REPORT SNAPSHOT
# =============================================================================
elif section == "8️⃣ Export & Report Snapshot":
    st.markdown("## 💾 SECTION 8: Export Complete Analysis & Summary Snapshot")

    st.markdown("### 📥 Download Full Multi-Sheet Excel Report")
    st.download_button(
        "📥 Download Complete Analysis Report (All Sheets)",
        data=all_to_excel(export_sheets),
        file_name=f"KNCCI_TA_Complete_Analysis_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    st.markdown("---")
    st.markdown("### 📋 Report Summary Snapshot")
    total_dup_rate = (total_raw - len(step3_df)) / total_raw * 100 if total_raw > 0 else 0

    st.markdown(f"""
| Metric | Value |
|--------|-------|
| Report Generated | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} |
| Date Range | {start_date} to {end_date} |
| **Raw Records (after filters)** | **{total_raw:,}** |
| **Cleaning Level in Use** | **{cleaning_level}** |
| Records Used for Analysis | **{len(df_clean):,}** |
| Total Duplicate Rate (Strictest) | {total_dup_rate:.1f}% |
| Unique Records | {len(unique_df):,} |
| Exact Duplicates | {len(exact_dup_df):,} |
| Same ID, Diff Phone | {len(same_id_df):,} |
| Same Phone, Diff ID | {len(same_phone_df):,} |
| Complex Duplicates | {len(complex_df):,} |
""")
