import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import io

# --- PAGE SETUP ---
st.set_page_config(page_title="Facility Maintenance Hub", layout="wide")
st.title("🔧 Facility Maintenance Dashboard")

# --- LOAD DATA ---
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/1wO7tjlpFIbqVN2HVhDV9wem7KGO0rjIh_J-9vSdYgiY/gviz/tq?tqx=out:csv"

@st.cache_data(ttl=30)
def load_data():
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(SHEET_CSV_URL, headers=headers, timeout=10)
    response.raise_for_status()
    
    df = pd.read_csv(io.StringIO(response.text))
    # Remove leading/trailing spaces from column names
    df.columns = df.columns.str.strip()
    return df

try:
    df = load_data()
except Exception as e:
    st.error(f"⚠️ Data Loading Error: {e}")
    st.stop()

# --- SIDEBAR NAVIGATION ---
st.sidebar.header("Navigation")
page = st.sidebar.radio("Go to:", ["Main Overview (All Work Types)", "PPM & PIC KPIs"])

# --- PAGE 1: MAIN OVERVIEW ---
if page == "Main Overview (All Work Types)":
    st.subheader("Global Maintenance Status")
    
    # Column mappings
    type_col = 'Work Type' if 'Work Type' in df.columns else None
    status_col = 'WI Status' if 'WI Status' in df.columns else None
    
    # Filter by Work Type
    ppm_data = df[df[type_col].astype(str).str.upper().str.contains('PPM', na=False)] if type_col else pd.DataFrame()
    breakdown_data = df[df[type_col].astype(str).str.upper().str.contains('BREAKDOWN', na=False)] if type_col else pd.DataFrame()
    cm_data = df[df[type_col].astype(str).str.upper().str.contains('CM|CORRECTIVE', regex=True, na=False)] if type_col else pd.DataFrame()
    
    # Top Metrics
    col1, col2, col3, col4 = st.columns(4)
    active_count = len(df[~df[status_col].astype(str).str.upper().isin(['CLOSED', 'COMPLETED'])]) if status_col else 0
    
    col1.metric("Total Active WIs", active_count)
    col2.metric("PPM WIs", len(ppm_data))
    col3.metric("Breakdown WIs", len(breakdown_data))
    col4.metric("Corrective (CM) WIs", len(cm_data))
    
    st.markdown("---")
    
    # Separated Data Tabs
    st.write("### Work Orders by Category")
    tab1, tab2, tab3 = st.tabs(["PPM", "Breakdown", "CM"])
    
    with tab1:
        st.dataframe(ppm_data, use_container_width=True)
    with tab2:
        st.dataframe(breakdown_data, use_container_width=True)
    with tab3:
        st.dataframe(cm_data, use_container_width=True)

# --- PAGE 2: PPM & PIC KPIs ---
elif page == "PPM & PIC KPIs":
    st.subheader("PPM Tracking & PIC Performance")
    
    type_col = 'Work Type' if 'Work Type' in df.columns else None
    status_col = 'WI Status' if 'WI Status' in df.columns else None
    
    # Identify PIC Column (checks for PIC Name, PIC, or Assigned To)
    pic_col = None
    for col in ['PIC Name', 'PIC', 'Assigned To', 'Technician']:
        if col in df.columns:
            pic_col = col
            break
            
    ppm_data = df[df[type_col].astype(str).str.upper().str.contains('PPM', na=False)] if type_col else pd.DataFrame()
    
    if not ppm_data.empty and pic_col:
        pic_list = ppm_data[pic_col].dropna().unique()
        selected_pic = st.sidebar.selectbox("Filter by PIC:", ["All PICs"] + list(pic_list))
        
        if selected_pic != "All PICs":
            ppm_data = ppm_data[ppm_data[pic_col] == selected_pic]
            
        total_ppm = len(ppm_data)
        closed_ppm = len(ppm_data[ppm_data[status_col].astype(str).str.upper().isin(['CLOSED', 'COMPLETED'])]) if status_col else 0
        kpi_percentage = (closed_ppm / total_ppm * 100) if total_ppm > 0 else 0
        
        kpi_col1, kpi_col2, kpi_col3 = st.columns(3)
        kpi_col1.metric(f"Total PPM WIs ({selected_pic})", total_ppm)
        kpi_col2.metric("Completed / Closed", closed_ppm)
        kpi_col3.metric("Completion KPI %", f"{kpi_percentage:.1f}%")
        
        if total_ppm > 0 and status_col:
            fig = px.pie(ppm_data, names=status_col, title=f"PPM Status Distribution ({selected_pic})", hole=0.4)
            st.plotly_chart(fig, use_container_width=True)
        
        st.write(f"### Current Work Instructions for {selected_pic}")
        st.dataframe(ppm_data, use_container_width=True)
    else:
        if not pic_col:
            st.warning("Please add a column named **'PIC Name'** or **'PIC'** in your Google Sheet to enable PIC KPI tracking.")
        st.dataframe(ppm_data, use_container_width=True)
