import streamlit as st
import pandas as pd
import plotly.express as px

# --- PAGE SETUP ---
st.set_page_config(page_title="Facility Maintenance Hub", layout="wide")
st.title("🔧 Facility Maintenance Dashboard")

# --- LOAD DATA ---
# Replace the URL below with your published Google Sheet CSV link
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/1wO7tjlpFIbqVN2HVhDV9wem7KGO0rjIh_J-9vSdYgiY/edit?usp=sharing"

@st.cache_data(ttl=60) # Refreshes data every 60 seconds
def load_data():
    df = pd.read_csv(SHEET_CSV_URL)
    return df

try:
    df = load_data()
except Exception as e:
    st.error("Error loading data. Please check your Google Sheet link.")
    st.stop()

# --- SIDEBAR NAVIGATION ---
st.sidebar.header("Navigation")
page = st.sidebar.radio("Go to:", ["Main Overview (All Categories)", "PPM & PIC KPIs"])

# --- PAGE 1: MAIN OVERVIEW ---
if page == "Main Overview (All Categories)":
    st.subheader("Global Maintenance Status")
    
    # Auto-Separate the data as requested
    ppm_data = df[df['Category'] == 'PPM']
    breakdown_data = df[df['Category'] == 'Breakdown']
    cm_data = df[df['Category'] == 'CM']
    
    # Top Metrics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Active Tasks", len(df[df['Status'] != 'Closed']))
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
    
    # Filter only PPM data
    ppm_data = df[df['Category'] == 'PPM']
    
    # Select a PIC to view their specific KPI
    pic_list = ppm_data['PIC Name'].dropna().unique()
    selected_pic = st.sidebar.selectbox("Filter by PIC:", ["All PICs"] + list(pic_list))
    
    if selected_pic != "All PICs":
        ppm_data = ppm_data[ppm_data['PIC Name'] == selected_pic]
        
    # Calculate KPIs for the selected view
    total_ppm = len(ppm_data)
    closed_ppm = len(ppm_data[ppm_data['Status'] == 'Closed'])
    
    # Avoid division by zero
    kpi_percentage = (closed_ppm / total_ppm * 100) if total_ppm > 0 else 0
    
    # Display KPIs
    kpi_col1, kpi_col2, kpi_col3 = st.columns(3)
    kpi_col1.metric(f"Total PPM Tasks ({selected_pic})", total_ppm)
    kpi_col2.metric("Completed", closed_ppm)
    kpi_col3.metric("Completion KPI %", f"{kpi_percentage:.1f}%")
    
    # Visual Chart
    if total_ppm > 0:
        fig = px.pie(ppm_data, names='Status', title=f"PPM Status Breakdown for {selected_pic}", hole=0.4)
        st.plotly_chart(fig, use_container_width=True)
    
    st.write(f"### Current Task List for {selected_pic}")
    st.dataframe(ppm_data[['Task ID', 'Date', 'Task Details', 'Status']], use_container_width=True)
