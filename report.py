import streamlit as st
import pandas as pd

# =====================================
# GOOGLE SHEET URL
# =====================================
# Replace this URL with your Google Sheet's "Published to web" CSV link
sheet_url = "https://docs.google.com/spreadsheets/d/1fitI_tGZEsZIVq0vdlwOXebK_6twq25D7-tOks7x5AM/edit?gid=0#gid=0"

# =====================================
# LOAD DATA
# =====================================
@st.cache_data
def load_data(url):
    df = pd.read_csv(url)
    return df

data = load_data(sheet_url)

# =====================================
# DISPLAY DATA
# =====================================
st.title("Google Sheet Data Viewer")
st.dataframe(data)
