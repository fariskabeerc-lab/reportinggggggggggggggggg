import streamlit as st
import pandas as pd
from datetime import datetime
import os

# ==========================================
# PAGE CONFIG
# ==========================================
st.set_page_config(page_title="Outlet & Feedback Dashboard", layout="wide")

# ==========================================
# GSHEET CONNECTION & CONFIG (NEW SECTION)
# ==========================================
# Initialize the Google Sheets connection client
@st.cache_resource(ttl="1h") # Cache the connection object
def get_sheets_connection():
    # Uses the 'gsheets' section in .streamlit/secrets.toml
    return st.connection("gsheets", type=st.connections.SQLConnection)

try:
    conn = get_sheets_connection()
except Exception as e:
    # If connection fails (e.g., missing secrets), display error.
    st.error("⚠️ Failed to connect to Google Sheets. Ensure your .streamlit/secrets.toml file is configured correctly and the service account has Editor access to the sheets.")
    st.stop()


# ==========================================
# CUSTOM STYLES
# ==========================================
# CSS to style the st.radio widget as a row of colored boxes
CUSTOM_RATING_CSS = """
<style>
/* Target the div that contains the radio buttons */
div[data-testid="stForm"] > div > div:nth-child(4) > div > div > div > div:nth-child(3) > div {
    display: flex; /* Makes the rating options sit in a row */
    justify-content: space-around;
    align-items: center;
    padding: 10px 0;
}

/* Style for each individual rating box */
div[data-testid="stForm"] > div > div:nth-child(4) div[role="radiogroup"] label {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    width: 40px; 
    height: 40px; 
    border: 1px solid #ccc;
    border-radius: 4px;
    margin: 5px;
    cursor: pointer;
    transition: background-color 0.2s, border-color 0.2s;
    user-select: none; /* Prevents text selection on tap */
}

/* Style for the text inside the box (the number) */
div[data-testid="stForm"] > div > div:nth-child(4) div[role="radiogroup"] label > div {
    font-size: 16px;
    font-weight: bold;
    color: #333;
}

/* Style when the radio button is checked (the green effect) */
div[data-testid="stForm"] > div > div:nth-child(4) div[role="radiogroup"] label input:checked + div {
    background-color: #38C172 !important; /* Green background */
    border-color: #38C1172 !important; /* Green border */
    color: white !important; /* White text */
}

/* Hides the default Streamlit radio circle */
div[data-testid="stForm"] > div > div:nth-child(4) div[role="radiogroup"] label input {
    display: none;
}

/* To ensure the green background applies correctly, we need to target the internal div Streamlit uses */
div[data-testid="stForm"] > div > div:nth-child(4) div[role="radiogroup"] label input:checked + div {
    /* Streamlit structure is complex, this targets the inner container of the radio button. */
    background-color: #38C172 !important;
}

/* This targets the actual box content div */
div[data-testid="stForm"] > div > div:nth-child(4) div[role="radiogroup"] label > div:nth-child(2) > div {
    padding: 0;
    margin: 0;
}
</style>
"""

# ==========================================
# CUSTOM JAVASCRIPT/HTML TO FORCE NUMERIC KEYBOARD
# ==========================================
def inject_numeric_keyboard_script(target_label):
    """
    Injects JavaScript to find the text input widget by its label and set
    its HTML 'inputmode' attribute to 'numeric', triggering the number keyboard on mobile.
    """
    script = f"""
    <script>
        function setInputMode() {{
            const elements = document.querySelectorAll('label');
            elements.forEach(label => {{
                if (label.textContent.includes('{target_label}')) {{
                    const input = label.nextElementSibling.querySelector('input');
                    if (input) {{
                        input.setAttribute('inputmode', 'numeric');
                        input.setAttribute('pattern', '[0-9]*');
                    }}
                }}
            }});
        }}
        // Run on load and whenever Streamlit rerenders the component (e.g., after a form submit)
        window.onload = setInputMode;
        // Also observe for changes in the DOM (needed for dynamic Streamlit content)
        new MutationObserver(setInputMode).observe(document.body, {{ childList: true, subtree: true }});
    </script>
    """
    st.markdown(script, unsafe_allow_html=True)

# ==========================================
# LOAD ITEM DATA (for auto-fill)
# ==========================================
@st.cache_data
def load_item_data():
    # NOTE: The actual file "alllist.xlsx" must be present in the directory 
    file_path = "alllist.xlsx" 
    try:
        df = pd.read_excel(file_path)
        # Ensure column names are clean
        df.columns = df.columns.str.strip()
        
        # Check only critical columns needed for the app to run
        required_cols = ["Item Bar Code", "Item Name", "LP Supplier"] 
        for col in required_cols:
            if col not in df.columns:
                st.error(f"⚠️ Missing critical column: '{col}' in alllist.xlsx. Please check the file.")
                return pd.DataFrame()
        return df
    except FileNotFoundError:
        st.error(f"⚠️ Data file not found: {file_path}. Please ensure the file is in the application directory.")
        return pd.DataFrame()

item_data = load_item_data()

# ==========================================
# LOGIN SYSTEM
# ==========================================
outlets = [
    "Hilal", "Safa Super", "Azhar HP", "Azhar", "Blue Pearl", "Fida", "Hadeqat",
    "Jais", "Sabah", "Sahat", "Shams salem", "Shams Liwan", "Superstore",
    "Tay Tay", "Safa oudmehta", "Port saeed"
]
password = "123123"

# Initialize session state variables
for key in ["logged_in", "selected_outlet", "submitted_items",
             # Main state (persists barcode/lookup details outside of the main form)
             "barcode_value", "item_name_input", "supplier_input", 
             # Manual Entry temporary keys
             "temp_item_name_manual", "temp_supplier_manual",
             # Lookup state
             "lookup_data", "submitted_feedback", "barcode_found",
             # NEW STATE VARIABLE FOR STAFF NAME
             "staff_name"]: 
    
    if key not in st.session_state:
        if key in ["submitted_items", "submitted_feedback"]:
            st.session_state[key] = []
        elif key == "lookup_data":
            st.session_state[key] = pd.DataFrame()
        elif key == "barcode_found":
            st.session_state[key] = False 
        else:
            st.session_state[key] = ""

# ------------------------------------------------------------------
# --- Helper functions to synchronize manual inputs ---
def update_item_name_state():
    """Updates the main item_name_input state variable from the temp manual input."""
    st.session_state.item_name_input = st.session_state.temp_item_name_manual

def update_supplier_state():
    """Updates the main supplier_input state variable from the temp manual input."""
    st.session_state.supplier_input = st.session_state.temp_supplier_manual
# ------------------------------------------------------------------

# ------------------------------------------------------------------
# --- Lookup Logic Function (Callback for Barcode Form) ---
# ------------------------------------------------------------------
def lookup_item_and_update_state():
    """Performs the barcode lookup and updates relevant session state variables."""
    barcode = st.session_state.lookup_barcode_input
    
    # Reset lookup and previous item states
    st.session_state.lookup_data = pd.DataFrame()
    st.session_state.barcode_value = barcode 
    st.session_state.item_name_input = ""
    st.session_state.supplier_input = ""
    st.session_state.barcode_found = False
    
    # Reset temporary keys for manual entry fields
    st.session_state.temp_item_name_manual = ""
    st.session_state.temp_supplier_manual = "" 
    
    if not barcode:
        st.toast("⚠️ Barcode cleared.", icon="❌")
        return

    if not item_data.empty:
        # NOTE: Using .astype(str).str.strip() for robust comparison against excel data
        match = item_data[item_data["Item Bar Code"].astype(str).str.strip() == str(barcode).strip()]
        
        if not match.empty:
            st.session_state.barcode_found = True
            row = match.iloc[0]
            
            # 1. Prepare data for display table
            df_display = row[["Item Name", "LP Supplier"]].to_frame().T
            df_display.columns = ["Item Name", "Supplier"]
            st.session_state.lookup_data = df_display.reset_index(drop=True)
            
            # 2. Automatically transfer details to the main state variables
            st.session_state.item_name_input = str(row["Item Name"])
            st.session_state.supplier_input = str(row["LP Supplier"])
            
            st.toast("✅ Item found. Details loaded.", icon="🔍")
        else:
            # Barcode not found 
            st.session_state.barcode_found = False 
            st.toast("⚠️ Barcode not found. Please enter item name and supplier manually.", icon="⚠️")
    
# ------------------------------------------------------------------

# -------------------------------------------------
# --- Main Form Submission Handler (MODIFIED FOR GSHEETS) ---
# -------------------------------------------------
def process_item_entry(barcode, item_name, qty, cost, selling, expiry, supplier, remarks, form_type, outlet_name, staff_name):
    
    # Validation
    if not barcode.strip():
        st.toast("⚠️ Barcode is required before adding.", icon="❌")
        return False
    if not item_name.strip():
        st.toast("⚠️ Item Name is required before adding.", icon="❌")
        return False
    if not staff_name.strip():
        st.toast("⚠️ Staff Name is required before adding.", icon="❌")
        return False

    try:
        cost = float(cost)
    except ValueError:
        cost = 0.0
    try:
        selling = float(selling)
    except ValueError:
        selling = 0.0

    expiry_display = expiry.strftime("%d-%b-%y") if expiry else ""
    gp = ((selling - cost) / cost * 100) if cost else 0

    # New record dictionary (Keys must match Google Sheet headers!)
    new_record = {
        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Form Type": form_type,
        "Barcode": barcode.strip(),
        "Item Name": item_name.strip(),
        "Qty": int(qty), 
        "Cost": round(cost, 2),
        "Selling": round(selling, 2),
        "Amount": round(cost * qty, 2),
        "GP%": round(gp, 2),
        "Expiry": expiry_display,
        "Supplier": supplier.strip(),
        "Remarks": remarks.strip(),
        "Outlet": outlet_name,
        "Staff Name": staff_name.strip()
    }
    
    # --- 1. Save to Persistent Google Sheet (NEW STEP) ---
    try:
        conn.append(
            spreadsheet=st.secrets.gsheets.inventory_sheet_url, 
            data=[list(new_record.values())],
            headers=list(new_record.keys())
        )
    except Exception as e:
        st.error(f"🚨 Failed to save item data to Google Sheet. Check connection, URL, and permissions. Error: {e}")
        return False
        
    # --- 2. Save to Session State (for current display) ---
    st.session_state.submitted_items.append(new_record)

    # --- CLEAR ONLY THE NON-FORM/NON-ITEM STATE VARIABLES ---
    st.session_state.barcode_value = ""          
    st.session_state.lookup_data = pd.DataFrame()
    st.session_state.barcode_found = False
    
    st.toast("✅ Item added and saved permanently to Google Sheet!", icon="💾")
    return True
# -------------------------------------------------


# ==========================================
# PAGE SELECTION
# ==========================================
if not st.session_state.logged_in:
    st.title("🔐 Outlet Login")
    username = st.text_input("Username", placeholder="Enter username")
    outlet = st.selectbox("Select your outlet", outlets)
    pwd = st.text_input("Password", type="password")

    if st.button("Login"):
        if username == "almadina" and pwd == password:
            st.session_state.logged_in = True
            st.session_state.selected_outlet = outlet
            st.rerun()
        else:
            st.error("❌ Invalid username or password")

else:
    # APPLY CUSTOM CSS FOR RATING BOXES HERE
    st.markdown(CUSTOM_RATING_CSS, unsafe_allow_html=True) 
    
    # ADDED "View Saved Data"
    page = st.sidebar.radio("📌 Select Page", ["Outlet Dashboard", "Customer Feedback", "View Saved Data"])

    # ==========================================
    # OUTLET DASHBOARD
    # ==========================================
    if page == "Outlet Dashboard":
        outlet_name = st.session_state.selected_outlet
        st.markdown(f"<h2 style='text-align:center;'>🏪 {outlet_name} Dashboard</h2>", unsafe_allow_html=True)
        form_type = st.sidebar.radio("📋 Select Form Type", ["Expiry", "Damages", "Near Expiry"])
        st.markdown("---")
        
        # Inject the script to change the barcode field's inputmode
        inject_numeric_keyboard_script("Barcode Lookup")


        # --- 0. Staff Name Input ---
        st.session_state.staff_name = st.text_input(
            "👤 Staff Name (Required)",
            value=st.session_state.staff_name,
            key="staff_name_input_key", # Persistent key for the staff name input
            placeholder="Enter your full name"
        )
        st.markdown("---")

        # --- 1. Dedicated Lookup Form (Enter key only triggers search/filter) ---
        with st.form("barcode_lookup_form", clear_on_submit=False):
            
            col_bar, col_btn = st.columns([5, 1])
            
            with col_bar:
                # Barcode Lookup remains st.text_input, but JS will set inputmode='numeric'
                st.text_input(
                    "Barcode Lookup",
                    key="lookup_barcode_input", 
                    placeholder="Enter or scan barcode and press Enter to search details",
                    value=st.session_state.barcode_value
                )
            
            with col_btn:
                st.markdown("<div style='height: 33px;'></div>", unsafe_allow_html=True) # Spacer
                st.form_submit_button(
                    "🔍 Search", 
                    on_click=lookup_item_and_update_state, 
                    help="Click or press Enter in the barcode field to look up item.",
                    type="secondary",
                    use_container_width=True
                )

        # --- 2. Item Details Display Panel (The 'Filter' result) ---
        if not st.session_state.lookup_data.empty:
            st.markdown("### 🔍 Found Item Details")
            st.dataframe(st.session_state.lookup_data, use_container_width=True, hide_index=True)
        
        # --- 2b. Manual Entry Fallback ---
        # Show manual entry fields ONLY if a search was done and the barcode was NOT found
        if st.session_state.barcode_value.strip() and not st.session_state.barcode_found:
             st.markdown("### ⚠️ Manual Item Entry (Barcode Not Found)")
             col_manual_name, col_manual_supplier = st.columns(2)
             with col_manual_name:
                 st.text_input(
                     "Item Name (Manual)", 
                     value=st.session_state.item_name_input, 
                     key="temp_item_name_manual", 
                     on_change=update_item_name_state
                 )
             with col_manual_supplier:
                 st.text_input(
                     "Supplier Name (Manual)", 
                     value=st.session_state.supplier_input, 
                     key="temp_supplier_manual", 
                     on_change=update_supplier_state
                 )

        # Separator only if a search has happened
        if st.session_state.barcode_value.strip():
             st.markdown("---") 


        # --- 3. Start of the Main Item Entry Form ---
        with st.form("item_entry_form", clear_on_submit=True): 
            
            # --- Row 1: Qty and Expiry ---
            col1, col2 = st.columns(2)
            with col1:
                qty = st.number_input("Qty [PCS]", min_value=1, value=1, step=1)
            with col2:
                if form_type != "Damages":
                    expiry = st.date_input("Expiry Date", datetime.now().date())
                else:
                    expiry = None

            # --- Row 2: Cost, Selling (Already st.number_input) ---
            col5, col6 = st.columns(2)
            with col5:
                # This uses number keyboard by default on mobile
                cost = st.number_input("Cost", min_value=0.0, value=0.0, step=0.01)
            with col6:
                # This uses number keyboard by default on mobile
                selling = st.number_input("Selling Price", min_value=0.0, value=0.0, step=0.01)

            # Calculate and display GP%
            temp_cost = float(cost)
            temp_selling = float(selling)
                
            gp = ((temp_selling - temp_cost) / temp_cost * 100) if temp_cost else 0
            st.info(f"💹 **GP% (Profit Margin)**: {gp:.2f}%")

            # --- Remarks and Submit Button ---
            remarks = st.text_area("Remarks [if any]", value="")

            # Form submission button (only this button adds the item)
            submitted_item = st.form_submit_button(
                "➕ Add to List", 
                type="primary",
            )
            # --- End of the Item Entry Form ---

        # --------------------------------------------------------
        # --- Handle Main Form Submission ONLY on Button Click ---
        # --------------------------------------------------------
        if submitted_item:
            
            final_item_name = st.session_state.item_name_input
            final_supplier = st.session_state.supplier_input
            final_staff_name = st.session_state.staff_name 

            if not st.session_state.barcode_value.strip():
                 st.toast("❌ Please enter a Barcode before adding to the list.", icon="❌")
                 st.rerun() 
            
            if not final_staff_name.strip():
                st.toast("❌ Please enter your Staff Name before adding to the list.", icon="❌")
                st.rerun()

            success = process_item_entry(
                st.session_state.barcode_value, 
                final_item_name,                 
                qty,           
                cost,      
                selling,   
                expiry,      
                final_supplier,                  
                remarks,     
                form_type,   
                outlet_name,
                final_staff_name 
            )
            
            if success:
                 st.rerun()


        # Displaying and managing the list
        if st.session_state.submitted_items:
            st.markdown("### 🧾 Items Added (Session List)")
            df = pd.DataFrame(st.session_state.submitted_items)
            st.dataframe(df, use_container_width=True, hide_index=True)

            col_submit, col_delete = st.columns([1, 1])
            with col_submit:
                if st.button("✅ Submit All & Clear List", type="primary", help="Data is already saved to Google Sheets. This button clears the temporary list."):
                    st.success(f"✅ Temporary list of {len(st.session_state.submitted_items)} items cleared. All records are saved permanently.")
                    
                    # FINAL RESET OF ITEM LOOKUP DATA AND STAFF NAME
                    st.session_state.submitted_items = []
                    st.session_state.barcode_value = ""
                    st.session_state.item_name_input = ""
                    st.session_state.supplier_input = ""
                    st.session_state.barcode_found = False
                    st.session_state.temp_item_name_manual = "" 
                    st.session_state.temp_supplier_manual = "" 
                    st.session_state.lookup_data = pd.DataFrame() 
                    st.session_state.staff_name = "" 
                    st.rerun() 

            with col_delete:
                options = [f"{i+1}. {item['Item Name']} ({item['Qty']} pcs)" for i, item in enumerate(st.session_state.submitted_items)]
                if options:
                    to_delete = st.selectbox("Select Item to Delete from Session List", ["Select item to remove..."] + options)
                    if to_delete != "Select item to remove...":
                        if st.button("❌ Delete Selected from Session", type="secondary"):
                            index = options.index(to_delete) 
                            st.session_state.submitted_items.pop(index)
                            st.success("✅ Item removed from session list")
                            st.rerun()

    
    # ==========================================
    # CUSTOMER FEEDBACK PAGE (MODIFIED FOR GSHEETS)
    # ==========================================
    elif page == "Customer Feedback":
        outlet_name = st.session_state.selected_outlet
        st.title("📝 Customer Feedback Form")
        st.markdown(f"Submitting feedback for **{outlet_name}**")
        st.markdown("---")

        with st.form("feedback_form", clear_on_submit=True):
            name = st.text_input("Customer Name")
            
            st.markdown("🌟 **Rate Our Outlet**")
            # --- CUSTOM RATING IMPLEMENTATION ---
            rating = st.radio(
                "hidden_rating_label", # Use a label that won't show
                options=[1, 2, 3, 4, 5],
                index=4, # Default to 5
                horizontal=True, # Critical for the horizontal layout
                key="customer_rating_radio",
                label_visibility="collapsed" # Hide the label
            )
            
            feedback = st.text_area("Your Feedback (Required)")
            submitted = st.form_submit_button("📤 Submit Feedback")

        if submitted:
            if name.strip() and feedback.strip():
                
                new_feedback = {
                    "Submitted At": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Customer Name": name,
                    "Rating": f"{rating} / 5",
                    "Outlet": outlet_name,
                    "Feedback": feedback,
                }
                
                # --- 1. Save to Persistent Google Sheet (NEW STEP) ---
                try:
                    conn.append(
                        spreadsheet=st.secrets.gsheets.feedback_sheet_url, 
                        data=[list(new_feedback.values())],
                        headers=list(new_feedback.keys())
                    )
                except Exception as e:
                    st.error(f"🚨 Failed to save feedback to Google Sheet. Error: {e}")
                
                # --- 2. Save to Session State (for current display) ---
                st.session_state.submitted_feedback.append(new_feedback)
                
                st.success("✅ Feedback submitted and saved permanently to Google Sheet!")
            else:
                st.error("⚠️ Please fill **Customer Name** and **Feedback** before submitting.")

        if st.session_state.submitted_feedback:
            st.markdown("### 🗂 Recent Customer Feedback (Session Records)")
            df = pd.DataFrame(st.session_state.submitted_feedback)
            st.dataframe(df.iloc[::-1], use_container_width=True, hide_index=True)

            if st.button("🗑 Clear All Session Feedback Records", type="secondary", help="This only clears the display, the data is saved in Google Sheets."):
                st.session_state.submitted_feedback = []
                st.rerun()
                
    # ==========================================
    # VIEW SAVED DATA PAGE (NEW SECTION)
    # ==========================================
    elif page == "View Saved Data":
        st.title("📊 All Permanently Saved Data Records")
        st.markdown("---")

        # Utility function for download button
        @st.cache_data
        def convert_df_to_csv(df):
            return df.to_csv(index=False).encode('utf-8')

        # --- Inventory Data ---
        st.markdown("### 📦 Inventory Submissions (Expiry/Damages/Near Expiry)")
        
        try:
            # Read all inventory data from Google Sheet
            inventory_df = conn.read(spreadsheet=st.secrets.gsheets.inventory_sheet_url)
        except Exception as e:
            st.error(f"🚨 Error loading Inventory Data from Sheet. Please check the sheet URL/permissions. Error: {e}")
            inventory_df = pd.DataFrame()


        if not inventory_df.empty:
            # Display most recent submissions first by reversing the order
            st.dataframe(inventory_df.iloc[::-1], 
                         use_container_width=True, 
                         hide_index=True)
            
            csv_data = convert_df_to_csv(inventory_df)
            st.download_button(
                label="⬇️ Download Inventory Data as CSV",
                data=csv_data,
                file_name="inventory_data.csv",
                mime='text/csv',
                key='download_inventory_csv'
            )
            
        else:
            st.info("No inventory data found in Google Sheets.")

        st.markdown("---")

        # --- Feedback Data ---
        st.markdown("### 💬 Customer Feedback Records")
        
        try:
            # Read all feedback data from Google Sheet
            feedback_df = conn.read(spreadsheet=st.secrets.gsheets.feedback_sheet_url)
        except Exception as e:
            st.error(f"🚨 Error loading Feedback Data from Sheet. Please check the sheet URL/permissions. Error: {e}")
            feedback_df = pd.DataFrame()


        if not feedback_df.empty:
            # Display most recent feedback first by reversing the order
            st.dataframe(feedback_df.iloc[::-1], 
                         use_container_width=True, 
                         hide_index=True)
            
            csv_feedback = convert_df_to_csv(feedback_df)
            st.download_button(
                label="⬇️ Download Feedback Data as CSV",
                data=csv_feedback,
                file_name="feedback_data.csv",
                mime='text/csv',
                key='download_feedback_csv'
            )
            
        else:
            st.info("No customer feedback data found in Google Sheets.")
