import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

SHEET_ID = "1fitI_tGZEsZIVq0vdlwOXebK_6twq25D7-tOks7x5AM"

service_account_info = st.secrets["gsheets"]
creds = Credentials.from_service_account_info(
    service_account_info,
    scopes=["https://www.googleapis.com/auth/spreadsheets"]
)
client = gspread.authorize(creds)
sheet = client.open_by_key(SHEET_ID).sheet1
