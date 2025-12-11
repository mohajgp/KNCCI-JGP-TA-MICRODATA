import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
from datetime import datetime

# ============================================================================
# CONFIG
# ============================================================================
st.set_page_config(page_title="KNCCI TA - National Microdata Integrity Dashboard", layout="wide")
st.title("🇰🇪 Jiinue Growth Programme – National Microdata Integrity Dashboard")

# ============================================================================
# DATA SOURCE
# ============================================================================
sheet_url = "https://docs.google.com/spreadsheets/d/1LDPRGnR5jlzIMP6RJ9gAcB5m91OO_Wf_1_4liYtVPYM/edit?usp=sharing"
csv_url = sheet_url.replace("/edit?usp=sharing", "/export?format=csv")

@st.cache_data(ttl=300)
def load_data():
    df = pd.read_csv(csv_url)
    df.columns = df.columns.str.strip()
    return df

# Refresh button
if st.button("🔄 Refresh Dataset"):
    st.cache_data.clear()
    st.rerun()

df_raw = load_data().copy()

# ============================================================================
# BASIC CLEANUP
# ============================================================================
id_col = "WHAT IS YOUR NATIONAL ID?"
phone_col = "Business phone number"
county_col = "Business Location"

# Parse date column
if "Timestamp" in df_raw.columns:
    df_raw["Timestamp"] = pd.to_datetime(df_raw["Timestamp"], errors="coerce")
elif "Training date" in df_raw.columns:
    df_raw["Timestamp"] = pd.to_datetime(df_raw["Training date"], errors="coerce")
else:
    df_raw["Timestamp"] = pd.NaT

# ============================================================================
# SIDEBAR FILTERS
# ============================================================================
st.sidebar.header("📅 Filter Options")

min_date = df_raw["Timestamp"].min()
max_date = df_raw["Timestamp"].max()

start_date = st.sidebar.date_input("Start Date", min_date.date())
end_date = st.sidebar.date_input("End Date", max_date.date())

# County filter
all_counties = sorted(df_raw[county_col].dropna().unique())
selected_counties = st.sidebar.multiselect("Filter by County", all_counties, default=[])

df = df_raw.copy()
df = df[(df["Timestamp"].dt.date >= start_date) & (df["Timestamp"].dt.date <= end_date)]

if len(selected_counties) > 0:
    df = df[df[county_col].isin(selected_counties)]

# ============================================================================
# HELPER FOR DOWNLOADS
# ============================================================================
def df_to_excel_bytes(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

# ============================================================================
# DUPLICATE CLASSIFICATION
# ============================================================================
df["_row_id"] = range(len(df))
df["_id_dup"] = df[id_col].duplicated(keep=False)
df["_phone_dup"] = df[phone_col].duplicated(keep=False)
df["_exact_dup"] = df.duplicated(subset=[id_col, phone_col], keep=False)

def classify(r):
    if not r["_id_dup"] and not r["_phone_dup"]:
        return "Unique"
    elif r["_exact_dup"]:
        return "Exact Duplicate (Same ID + Phone)"
    elif r["_id_dup"] and not r["_phone_dup"]:
        return "Same ID, Different Phone"
    elif r["_phone_dup"] and not r["_id_dup"]:
        return "Same Phone, Different ID"
    else:
        return "Complex Duplicate"

df["_category"] = df.apply(classify, axis=1)

# ============================================================================
# HIGH-LEVEL SUMMARY
# ============================================================================
st.markdown("## 🧮 Executive Summary Metrics")

total_records = len(df)
unique_records = len(df[df["_category"] == "Unique"])
exact_dups = len(df[df["_category"] == "Exact Duplicate (Same ID + Phone)"])
same_id_dups = len(df[df["_category"] == "Same ID, Different Phone"])
same_phone_dups = len(df[df["_category"] == "Same Phone, Different ID"])
complex_dups = len(df[df["_category"] == "Complex Duplicate"])

duplicate_rate = ((total_records - unique_records) / total_records * 100)

col1, col2, col3 = st.columns(3)
col1.metric("Total Records", f"{total_records:,}")
col2.metric("Unique Records", f"{unique_records:,}")
col3.metric("Duplicate Rate", f"{duplicate_rate:.1f}%")

col4, col5, col6, col7 = st.columns(4)
col4.metric("Exact Duplicates", exact_dups)
col5.metric("Same ID Diff Phone", same_id_dups)
col6.metric("Same Phone Diff ID", same_phone_dups)
col7.metric("Complex Duplicates", complex_dups)

st.markdown("---")

# ============================================================================
# COUNTY DUPLICATE INTELLIGENCE TABLE
# ============================================================================
st.markdown("## 🏛️ County-Level Duplicate Intelligence (National Overview)")

county_stats = df.groupby(county_col).agg(
    Total=("Timestamp", "count"),
    ExactDup=(" _category", lambda x: (x == "Exact Duplicate (Same ID + Phone)").sum()),
    SameID=(" _category", lambda x: (x == "Same ID, Different Phone").sum()),
    SamePhone=(" _category", lambda x: (x == "Same Phone, Different ID").sum()),
    Complex=(" _category", lambda x: (x == "Complex Duplicate").sum())
).reset_index()

county_stats["TotalDuplicates"] = (
    county_stats["ExactDup"] +
    county_stats["SameID"] +
    county_stats["SamePhone"] +
    county_stats["Complex"]
)

county_stats["DuplicateRate"] = (
    county_stats["TotalDuplicates"] / county_stats["Total"] * 100
).round(2)

st.dataframe(county_stats.sort_values("DuplicateRate", ascending=False), use_container_width=True)

st.download_button(
    "⬇️ Download County Duplicate Intelligence",
    df_to_excel_bytes(county_stats),
    "County_Duplicate_Intelligence.xlsx"
)

st.markdown("---")

# ============================================================================
# COUNTY DEEP AUDIT SECTION
# ============================================================================
st.markdown("## 🔍 County Deep Audit (Record-Level Examination)")

audit_county = st.selectbox("Select County to Audit", sorted(df[county_col].dropna().unique()))

audit_df = df[df[county_col] == audit_county]

st.metric("Total Records in County", len(audit_df))

# RAW RECORDS
st.markdown("### 📌 Raw Records")
st.dataframe(audit_df.head(500), use_container_width=True)
st.download_button(
    f"⬇️ Download Raw – {audit_county}",
    df_to_excel_bytes(audit_df),
    f"RAW_{audit_county}.xlsx"
)

# Exact duplicates
exact_df = audit_df[audit_df["_category"] == "Exact Duplicate (Same ID + Phone)"]
st.markdown(f"### 🔁 Exact Duplicates ({len(exact_df)})")
st.dataframe(exact_df, use_container_width=True)
st.download_button(
    f"⬇️ Download Exact Dups – {audit_county}",
    df_to_excel_bytes(exact_df),
    f"Exact_{audit_county}.xlsx"
)

# Same ID – diff phone
sameid_df = audit_df[audit_df["_category"] == "Same ID, Different Phone"]
st.markdown(f"### 🔄 Same ID, Different Phone ({len(sameid_df)})")
st.dataframe(sameid_df, use_container_width=True)
st.download_button(
    f"⬇️ Download SameID – {audit_county}",
    df_to_excel_bytes(sameid_df),
    f"SameID_{audit_county}.xlsx"
)

# Same phone – diff ID
samephone_df = audit_df[audit_df["_category"] == "Same Phone, Different ID"]
st.markdown(f"### 📱 Same Phone, Different ID ({len(samephone_df)})")
st.dataframe(samephone_df, use_container_width=True)
st.download_button(
    f"⬇️ Download SamePhone – {audit_county}",
    df_to_excel_bytes(samephone_df),
    f"SamePhone_{audit_county}.xlsx"
)

# Complex duplicates
complex_df = audit_df[audit_df["_category"] == "Complex Duplicate"]
st.markdown(f"### 🧬 Complex Duplicates ({len(complex_df)})")
st.dataframe(complex_df, use_container_width=True)
st.download_button(
    f"⬇️ Download Complex – {audit_county}",
    df_to_excel_bytes(complex_df),
    f"Complex_{audit_county}.xlsx"
)

# ============================================================================
# END OF DASHBOARD
# ============================================================================
st.markdown("---")
st.markdown(f"Report generated on **{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}**")
