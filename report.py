import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Google Sheet Form Input", layout="wide")
st.title("📄 Google Sheet Form Input")

# ==========================
# GOOGLE SHEET SETUP
# ==========================
SHEET_ID = "1fitI_tGZEsZIVq0vdlwOXebK_6twq25D7-tOks7x5AM"
SERVICE_ACCOUNT_FILE = "service_account.json"  # path to your JSON key

# Authenticate with Google Sheets
scope = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=scope)
client = gspread.authorize(creds)

# Open sheet
sheet = client.open_by_key(SHEET_ID).sheet1  # first sheet
data = pd.DataFrame(sheet.get_all_records())

# ==========================
# DISPLAY CURRENT DATA
# ==========================
st.subheader("Current Data")
st.dataframe(data)

# ==========================
# FORM TO ADD DATA
# ==========================
st.subheader("Add New Row")
with st.form(key="add_row_form"):
    # Example columns: adapt to your sheet columns
    col1 = st.text_input("Column 1")
    col2 = st.text_input("Column 2")
    col3 = st.number_input("Column 3", step=1)
    submitted = st.form_submit_button("Add Row")

    if submitted:
        new_row = [col1, col2, col3]  # match the number/order of your columns
        sheet.append_row(new_row)
        st.success("Row added successfully!")
        st.experimental_rerun()  # refresh to show new data
