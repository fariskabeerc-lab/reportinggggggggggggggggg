import streamlit as st
import pandas as pd

st.set_page_config(page_title="Google Sheet Viewer", layout="wide")
st.title("📊 Google Sheet Data Viewer")

# ==========================
# GOOGLE SHEET CONFIG
# ==========================
SHEET_ID = "1fitI_tGZEsZIVq0vdlwOXebK_6twq25D7-tOks7x5AM"  # from your URL
SHEET_GID = "0"  # from your URL (gid=0)

# ==========================
# LOAD DATA
# ==========================
@st.cache_data
def load_data(sheet_id, gid):
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    df = pd.read_csv(url)
    return df

data = load_data(SHEET_ID, SHEET_GID)

# ==========================
# DISPLAY DATA
# ==========================
st.write(f"Displaying data from sheet with GID = {SHEET_GID}")
st.dataframe(data)
st.write(f"Total rows: {data.shape[0]}, Total columns: {data.shape[1]}")
