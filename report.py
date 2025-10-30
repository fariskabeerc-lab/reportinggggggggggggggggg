import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Google Sheet Form Input", layout="wide")
st.title("📄 Google Sheet Form Input")

# Google Sheet ID
SHEET_ID = "1fitI_tGZEsZIVq0vdlwOXebK_6twq25D7-tOks7x5AM"

# Load credentials from Streamlit secrets
service_account_info = st.secrets["google_service_account"]
creds = Credentials.from_service_account_info(service_account_info, scopes=["https://www.googleapis.com/auth/spreadsheets"])

# Connect to Google Sheet
client = gspread.authorize(creds)
sheet = client.open_by_key(SHEET_ID).sheet1

# Display current data
data = pd.DataFrame(sheet.get_all_records())
st.subheader("Current Data")
st.dataframe(data)

# Form to add new data
st.subheader("Add New Row")
with st.form("add_row_form"):
    col1 = st.text_input("Column 1")
    col2 = st.text_input("Column 2")
    col3 = st.number_input("Column 3", step=1)
    submitted = st.form_submit_button("Add Row")
    
    if submitted:
        sheet.append_row([col1, col2, col3])
        st.success("Row added successfully!")
        st.experimental_rerun()
