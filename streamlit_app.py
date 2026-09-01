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

@st.cache_data(ttl=15)
def load_data():
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(SHEET_CSV_URL, headers=headers, timeout=10)
    response.raise_for_status()
    
    df = pd.read_csv(io.StringIO(response.text))
    df.columns = df.columns.str.strip()
    return df

try:
    df = load_data()
except Exception as e:
    st.error(f"⚠️ Data Loading Error: {e}")
    st.stop()

# --- FLEXIBLE COLUMN MATCHING ---
def find_column(df, candidates):
    for col in df.columns:
        if col.strip().lower() in [c.lower() for c in candidates]:
            return col
    return None

type_col = find_column(df, ['Work Type', 'WorkType', 'Type', 'Category', 'Work_Type'])
status_col = find_column(df, ['WI Status', 'Status', 'WIStatus', 'State'])
pic_col = find_column(df, ['PIC Name', 'PIC', 'Assigned To', 'Technician', 'PIC_Name', 'Person In Charge'])
date_col = find_column(df, ['Date/Time Received', 'Date', 'Date Received', 'Created Date', 'Received Date', 'Time Received'])

# --- DATE PARSING ---
if date_col:
    df['Parsed_Date'] = pd.to_datetime(df[date_col], errors='coerce')
    df['Year'] = df['Parsed_Date'].dt.year
    df['Month_Name'] = df['Parsed_Date'].dt.strftime('%B')

# --- SIDEBAR FILTERS ---
st.sidebar.header("Navigation & Filters")
page = st.sidebar.radio("Go to:", ["Main Overview (All Work Types)", "PPM & PIC KPIs"])

st.sidebar.markdown("---")
st.sidebar.subheader("📅 Date Filters")

# Year Filter
if date_col and not df['Year'].dropna().empty:
    available_years = sorted(df['Year'].dropna().astype(int).unique().tolist(), reverse=True)
    selected_year = st.sidebar.selectbox("Select Year:", ["All Years"] + [str(y) for y in available_years])
    
    if selected_year != "All Years":
        df = df[df['Year'] == int(selected_year)]

# Month Filter
if date_col and not df['Parsed_Date'].dropna().empty:
    month_order = ["January", "February", "March", "April", "May", "June", 
                   "July", "August", "September", "October", "November", "December"]
    present_months = df['Month_Name'].dropna().unique().tolist()
    sorted_months = [m for m in month_order if m in present_months]
    
    selected_month = st.sidebar.selectbox("Select Month:", ["All Months"] + sorted_months)
    
    if selected_month != "All Months":
        df = df[df['Month_Name'] == selected_month]

# --- DATA CATEGORIZATION ---
if type_col:
    work_type_clean = df[type_col].astype(str).str.upper().str.strip()
    
    ppm_mask = work_type_clean.str.contains(r'PPM|\bPM\b|PREVENT|PEVENT|SCHEDULED|PLANNED', regex=True)
    breakdown_mask = work_type_clean.str.contains(r'BREAKDOWN|\bBD\b|EMERGENCY|UNPLANNED', regex=True)
    cm_mask = work_type_clean.str.contains(r'\bCM\b|CORRECTIVE|REPAIR', regex=True) & (~ppm_mask) & (~breakdown_mask)
    
    ppm_data = df[ppm_mask]
    breakdown_data = df[breakdown_mask]
    cm_data = df[cm_mask]
else:
    ppm_data, breakdown_data, cm_data = pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

# Clean up helper columns from display tables
display_cols = [c for c in df.columns if c not in ['Parsed_Date', 'Year', 'Month_Name']]

# --- PAGE 1: MAIN OVERVIEW ---
if page == "Main Overview (All Work Types)":
    st.subheader("Global Maintenance Status")
    
    active_count = 0
    if status_col:
        active_count = len(df[~df[status_col].astype(str).str.upper().str.strip().isin(['CLOSED', 'COMPLETED', 'DONE'])])
        
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Active WIs", active_count)
    col2.metric("PPM WIs", len(ppm_data))
    col3.metric("Breakdown WIs", len(breakdown_data))
    col4.metric("Corrective (CM) WIs", len(cm_data))
    
    st.markdown("---")

    st.write("### Work Orders by Category")
    tab1, tab2, tab3, tab4 = st.tabs(["PPM (Preventive)", "Breakdown", "CM (Corrective)", "All Filtered Data"])
    
    with tab1:
        st.dataframe(ppm_data[display_cols] if not ppm_data.empty else ppm_data, use_container_width=True)
    with tab2:
        st.dataframe(breakdown_data[display_cols] if not breakdown_data.empty else breakdown_data, use_container_width=True)
    with tab3:
        st.dataframe(cm_data[display_cols] if not cm_data.empty else cm_data, use_container_width=True)
    with tab4:
        st.dataframe(df[display_cols] if not df.empty else df, use_container_width=True)

# --- PAGE 2: PPM & PIC KPIs ---
elif page == "PPM & PIC KPIs":
    st.subheader("PPM Tracking & PIC Performance")
    
    if not ppm_data.empty and pic_col:
        pic_list = ppm_data[pic_col].dropna().unique()
        selected_pic = st.sidebar.selectbox("Filter by PIC:", ["All PICs"] + list(pic_list))
        
        filtered_ppm = ppm_data if selected_pic == "All PICs" else ppm_data[ppm_data[pic_col] == selected_pic]
            
        total_ppm = len(filtered_ppm)
        closed_ppm = 0
        if status_col:
            closed_ppm = len(filtered_ppm[filtered_ppm[status_col].astype(str).str.upper().str.strip().isin(['CLOSED', 'COMPLETED', 'DONE'])])
            
        kpi_percentage = (closed_ppm / total_ppm * 100) if total_ppm > 0 else 0
        
        kpi_col1, kpi_col2, kpi_col3 = st.columns(3)
        kpi_col1.metric(f"Total PPM WIs ({selected_pic})", total_ppm)
        kpi_col2.metric("Completed / Closed", closed_ppm)
        kpi_col3.metric("Completion KPI %", f"{kpi_percentage:.1f}%")
        
        if total_ppm > 0 and status_col:
            fig = px.pie(filtered_ppm, names=status_col, title=f"PPM Status Distribution ({selected_pic})", hole=0.4)
            st.plotly_chart(fig, use_container_width=True)
        
        st.write(f"### Current Work Instructions for {selected_pic}")
        st.dataframe(filtered_ppm[display_cols], use_container_width=True)
    else:
        if ppm_data.empty:
            st.info("No PPM data available for the selected Year/Month filter.")
        if not pic_col:
            st.warning("Please add a column named **'PIC Name'** or **'PIC'** in your Google Sheet to enable PIC KPI filtering.")
        st.dataframe(ppm_data[display_cols] if not ppm_data.empty else ppm_data, use_container_width=True)
