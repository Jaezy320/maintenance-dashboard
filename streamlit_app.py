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
    # Headers prevent Google from blocking Python requests
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    response = requests.get(SHEET_CSV_URL, headers=headers, timeout=10)
    response.raise_for_status()
    
    df = pd.read_csv(io.StringIO(response.text))
    # Clean up column names by removing extra spaces
    df.columns = df.columns.str.strip()
    return df

try:
    df = load_data()
except Exception as e:
    st.error(f"⚠️ Data Loading Error: {e}")
    st.info("Check Google Sheet sharing settings below.")
    st.stop()

# --- SIDEBAR NAVIGATION ---
st.sidebar.header("Navigation")
page = st.sidebar.radio("Go to:", ["Main Overview (All Categories)", "PPM & PIC KPIs"])

# --- PAGE 1: MAIN OVERVIEW ---
if page == "Main Overview (All Categories)":
    st.subheader("Global Maintenance Status")
    
    # Auto-Separate the data by category
    ppm_data = df[df['Category'] == 'PPM'] if 'Category' in df.columns else pd.DataFrame()
    breakdown_data = df[df['Category'] == 'Breakdown'] if 'Category' in df.columns else pd.DataFrame()
    cm_data = df[df['Category'] == 'CM'] if 'Category' in df.columns else pd.DataFrame()
    
    # Top Metrics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Active Tasks", len(df[df['Status'] != 'Closed']) if 'Status' in df.columns else 0)
    col2.metric("PPM Tasks", len(ppm_data))
    col3.metric("Breakdowns", len(breakdown_data))
    col4.metric("Corrective (CM)", len(cm_data))
    
    st.markdown("---")
    
    # Separated Data Views
    st.write("### Filtered Task Lists")
    tab1, tab2, tab3 = st.tabs(["PPM", "Breakdown", "CM"])
    
    with tab1:
        st.dataframe(ppm_data, use_container_width=True)
    with tab2:
        st.dataframe(breakdown_data, use_container_width=True)
    with tab3:
        st.dataframe(cm_data, use_container_width=True)

# --- PAGE 2: PPM & KPI DASHBOARD ---
elif page == "PPM & PIC KPIs":
    st.subheader("PPM Tracking & PIC Performance")
    
    ppm_data = df[df['Category'] == 'PPM'] if 'Category' in df.columns else pd.DataFrame()
    
    if not ppm_data.empty and 'PIC Name' in ppm_data.columns:
        pic_list = ppm_data['PIC Name'].dropna().unique()
        selected_pic = st.sidebar.selectbox("Filter by PIC:", ["All PICs"] + list(pic_list))
        
        if selected_pic != "All PICs":
            ppm_data = ppm_data[ppm_data['PIC Name'] == selected_pic]
            
        total_ppm = len(ppm_data)
        closed_ppm = len(ppm_data[ppm_data['Status'] == 'Closed']) if 'Status' in ppm_data.columns else 0
        kpi_percentage = (closed_ppm / total_ppm * 100) if total_ppm > 0 else 0
        
        kpi_col1, kpi_col2, kpi_col3 = st.columns(3)
        kpi_col1.metric(f"Total PPM Tasks ({selected_pic})", total_ppm)
        kpi_col2.metric("Completed", closed_ppm)
        kpi_col3.metric("Completion KPI %", f"{kpi_percentage:.1f}%")
        
        if total_ppm > 0 and 'Status' in ppm_data.columns:
            fig = px.pie(ppm_data, names='Status', title=f"PPM Status Breakdown for {selected_pic}", hole=0.4)
            st.plotly_chart(fig, use_container_width=True)
        
        st.write(f"### Current Task List for {selected_pic}")
        st.dataframe(ppm_data, use_container_width=True)
    else:
        st.warning("No PPM data available or 'PIC Name' column missing.")
