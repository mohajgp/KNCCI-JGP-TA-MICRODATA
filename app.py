import pandas as pd
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="KNCCI TA Microdata Dashboard", layout="wide")
st.title("📊 Jiinue Growth Program - Microdata Summary Dashboard")

# === Step 1: Google Sheet link ===
sheet_url = "https://docs.google.com/spreadsheets/d/1LDPRGnR5jlzIMP6RJ9gAcB5m91OO_Wf_1_4liYtVPYM/edit?usp=sharing"
csv_url = sheet_url.replace("/edit?usp=sharing", "/export?format=csv")

# === Step 2: Read the Sheet ===
df = pd.read_csv(csv_url)
df.columns = df.columns.str.strip()
st.subheader("Raw Data Preview")
st.dataframe(df.head())

# === Step 3: Clean and summarize ===
df_clean = df.drop_duplicates(subset=['WHAT IS YOUR NATIONAL ID?', 'Business phone number'], keep='first')
st.success(f"✅ Cleaned records: {len(df_clean)} (from {len(df)} original)")

county_counts = df_clean['Business Location'].value_counts().reset_index()
county_counts.columns = ['County', 'Count']

st.subheader("📍 County Summary")
st.dataframe(county_counts)
st.bar_chart(data=county_counts.set_index('County'))

# === Step 4: Push results back to Google Sheet ===
st.write("### 📤 Export cleaned data back to Google Sheets")

upload = st.checkbox("Export cleaned data to Google Sheet (requires credentials.json)")

if upload:
    try:
        # Your service account file must be in the same folder
        creds = Credentials.from_service_account_file(
            "credentials.json",
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )

        client = gspread.authorize(creds)

        # Create or open target sheet
        sheet = client.open_by_url(sheet_url)

        # Replace existing sheets or add new ones
        if "Cleaned_Data" in [ws.title for ws in sheet.worksheets()]:
            ws_cleaned = sheet.worksheet("Cleaned_Data")
            sheet.del_worksheet(ws_cleaned)
        sheet.add_worksheet(title="Cleaned_Data", rows="1000", cols="30")
        ws_cleaned = sheet.worksheet("Cleaned_Data")

        # Write cleaned data
        ws_cleaned.update([df_clean.columns.values.tolist()] + df_clean.values.tolist())

        # Add summary sheet
        if "County_Summary" in [ws.title for ws in sheet.worksheets()]:
            ws_summary = sheet.worksheet("County_Summary")
            sheet.del_worksheet(ws_summary)
        sheet.add_worksheet(title="County_Summary", rows="100", cols="10")
        ws_summary = sheet.worksheet("County_Summary")
        ws_summary.update([county_counts.columns.values.tolist()] + county_counts.values.tolist())

        st.success("✅ Successfully exported cleaned data and summary to your Google Sheet!")
    except Exception as e:
        st.error(f"❌ Failed to export: {e}")
