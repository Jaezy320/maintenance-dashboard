import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import io

# --- PAGE SETUP ---
st.set_page_config(page_title="Mechanical Maintenance Hub", layout="wide")
st.title("🔧 Mechanical Facility Maintenance Dashboard")

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

# --- COLOR MAPPING FOR STATUS ---
COLOR_MAP = {
    "Open": "#E53E3E",
    "OPEN": "#E53E3E",
    "open": "#E53E3E",
    "In Progress": "#DD6B20",
    "IN PROGRESS": "#DD6B20",
    "in progress": "#DD6B20",
    "Pending": "#DD6B20",
    "PENDING": "#DD6B20",
    "Closed": "#3182CE",
    "CLOSED": "#3182CE",
    "closed": "#3182CE",
    "Completed": "#3182CE",
    "COMPLETED": "#3182CE",
    "completed": "#3182CE",
    "Done": "#3182CE",
    "DONE": "#3182CE"
}

# --- FLEXIBLE COLUMN MATCHING ---
def find_column(df, candidates):
    for col in df.columns:
        if col.strip().lower() in [c.lower() for c in candidates]:
            return col
    return None

type_col = find_column(df, ['Work Type', 'WorkType', 'Type', 'Category', 'Work_Type'])
status_col = find_column(df, ['WI Status', 'Status', 'WIStatus', 'State'])
pic_col = find_column(df, ['PIC Name', 'PIC', 'Assigned To', 'Technician', 'PIC_Name', 'Person In Charge'])
date_col = find_column(df, ['Date/Time Received', 'Date', 'Date Received', 'Created Date', 'Received Date'])
problem_col = find_column(df, ['Problem Description', 'Problem', 'Description', 'Issue', 'Details'])
location_col = find_column(df, ['Aras', 'Location', 'Jabatan', 'Level', 'Floor', 'Blok'])
system_col = find_column(df, ['Sistem', 'System', 'Equipment'])

# --- AUTO PIC ASSIGNMENT LOGIC ---
def auto_assign_pic(row):
    # If PIC is explicitly set in Google Sheet, retain it
    if pic_col and pd.notna(row.get(pic_col)) and str(row.get(pic_col)).strip() != "":
        return str(row.get(pic_col)).strip().upper()
    
    # Merge text fields to scan for problem/location keywords
    text_to_scan = f"{row.get(problem_col, '')} {row.get(location_col, '')} {row.get(system_col, '')}".lower()
    
    # 1. Equipment / System Keywords
    if any(k in text_to_scan for k in ['chiller', 'cooling tower']):
        return "IMRAN"
    if any(k in text_to_scan for k in ['autoclave']):
        return "AMIR"
    if any(k in text_to_scan for k in ['hydropool']):
        return "NAZRAN"
    if any(k in text_to_scan for k in ['pneumatic', 'pts', 'tube']):
        return "FARHAN"
    if any(k in text_to_scan for k in ['lpg', 'gas cylinder', 'gas tank', 'pump']):
        return "HASLA"
    if any(k in text_to_scan for k in ['lift', 'elevator', 'forklift', 'handjack', 'bas', 'bus']):
        return "SYAZWAN"
    if any(k in text_to_scan for k in ['agss', 'air compressor', 'manifold', 'terminal unit']):
        return "HAIKAL"
    if any(k in text_to_scan for k in ['avsu', 'avsum', 'pendant', 'repeater alarm']):
        return "BUKHARI"
    if any(k in text_to_scan for k in ['fire', 'smoke', 'sprinkler', 'hydrant', 'hose reel', 'alarm', 'pyrogen']):
        return "AZMI & SYAZWAN"
    if any(k in text_to_scan for k in ['stacker', 'ambulance', 'sedan', 'rehab']):
        return "NAZRAN"
        
    # 2. Location / Area Keywords
    if any(k in text_to_scan for k in ['main block level 1', 'main block aras 1', 'blok utama level 1', 'blok utama aras 1', 'level 1', 'aras 1']):
        return "AMIR & SHARY"
    if any(k in text_to_scan for k in ['pakar', 'klinik', 'oftalmologi', 'pergigian', 'orl']):
        return "FAIZ"
    if any(k in text_to_scan for k in ['aras g', 'level g', 'lobi', 'hasil', 'pendaftaran', 'kaunter']):
        return "AMIR & SHARY"
    if any(k in text_to_scan for k in ['aras 3', 'level 3', 'kecemasan', 'xray', 'x-ray', 'radiologi', 'mow']):
        return "IMRAN"
    if any(k in text_to_scan for k in ['aras 4', 'level 4', 'mot', 'pac', 'nicu', 'ccu', 'anaesthesia', 'ldu', 'bersalin']):
        return "MASLIZA"
    if any(k in text_to_scan for k in ['aras 5', 'level 5', 'icu', 'daycare', 'rawatan harian']):
        return "SHAKIR"
    if any(k in text_to_scan for k in ['aras 6', 'level 6', 'aras 7', 'level 7', 'hdw', 'got', 'dewan bedah', 'cssd', 'rhu']):
        return "FARHAN"
    if any(k in text_to_scan for k in ['aras 8', 'level 8', 'o&g', 'obstetrik', 'ginekologi']):
        return "MASLIZA"
    if any(k in text_to_scan for k in ['aras 9', 'level 9', 'aras 11', 'level 11', 'aras 16', 'level 16', 'aras 17', 'level 17', 'wad 9', 'wad 11', 'ortopedik', 'plant room', 'awsb']):
        return "AZIZI"
    if any(k in text_to_scan for k in ['aras 10', 'level 10', 'wad 10', '10a', '10b']):
        return "SHARY"
    if any(k in text_to_scan for k in ['aras 12', 'level 12', 'wad 12', 'pediatrik', 'patologi', 'aras 2', 'level 2', 'penyelidikan']):
        return "FAIZUL"
    if any(k in text_to_scan for k in ['aras 13', 'level 13', 'aras 15', 'level 15', 'kuarters', 'vip', 'eksekutif']):
        return "SHAKIR"
    if any(k in text_to_scan for k in ['aras 14', 'level 14']):
        return "SYAZWAN"
    if any(k in text_to_scan for k in ['rekod', 'perpustakaan', 'dietetik', 'sajian', 'pemandu', 'logistik', 'it']):
        return "NAZRAN"

    return "UNASSIGNED"

# Create or Update Auto-Assigned PIC Column
df['Assigned_PIC'] = df.apply(auto_assign_pic, axis=1)

# --- DATE PARSING ---
if date_col:
    df['Parsed_Date'] = pd.to_datetime(df[date_col], errors='coerce')
    df['Year'] = df['Parsed_Date'].dt.year
    df['Month_Name'] = df['Parsed_Date'].dt.strftime('%B')

# --- SIDEBAR FILTERS ---
st.sidebar.header("Navigation & Global Filters")
page = st.sidebar.radio("Go to:", ["Main Overview (All Work Types)", "PPM & PIC KPIs", "🔍 PIC Roster Directory"])

st.sidebar.markdown("---")
st.sidebar.subheader("📅 Date Filters")

if date_col and not df['Year'].dropna().empty:
    available_years = sorted(df['Year'].dropna().astype(int).unique().tolist(), reverse=True)
    selected_year = st.sidebar.selectbox("Select Year:", ["All Years"] + [str(y) for y in available_years])
    if selected_year != "All Years":
        df = df[df['Year'] == int(selected_year)]

if date_col and not df['Parsed_Date'].dropna().empty:
    month_order = ["January", "February", "March", "April", "May", "June", 
                   "July", "August", "September", "October", "November", "December"]
    present_months = df['Month_Name'].dropna().unique().tolist()
    sorted_months = [m for m in month_order if m in present_months]
    
    selected_month = st.sidebar.selectbox("Select Month:", ["All Months"] + sorted_months)
    if selected_month != "All Months":
        df = df[df['Month_Name'] == selected_month]

st.sidebar.markdown("---")
st.sidebar.subheader("🔍 Problem Description Search")

problem_keyword = ""
if problem_col:
    problem_keyword = st.sidebar.text_input("Filter by Keyword:", placeholder="e.g. leak, gas, aircon, chiller")
    if problem_keyword.strip():
        df = df[df[problem_col].astype(str).str.contains(problem_keyword, case=False, na=False)]

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

display_cols = [c for c in df.columns if c not in ['Parsed_Date', 'Year', 'Month_Name']]

# --- PAGE 1: MAIN OVERVIEW ---
if page == "Main Overview (All Work Types)":
    st.subheader("Global Mechanical Maintenance Overview")
    
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
    tab1, tab2, tab3, tab4 = st.tabs(["PPM (Preventive)", "Breakdown", "CM (Corrective)", "All Raw Data"])
    
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
    st.subheader("PPM Tracking & Mechanical PIC Performance")
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("👤 PIC Filters")
    
    master_pics = ["AMIR", "AZIZI", "AZMI", "BUKHARI", "FAIZ", "FAIZUL", "FARHAN", 
                   "HAIKAL", "HASLA", "IMRAN", "MASLIZA", "NAZRAN", "SHAKIR", "SHARY", "SYAZWAN"]

    selected_pic = st.sidebar.selectbox("Filter by PIC:", ["All PICs"] + master_pics)
    
    filtered_ppm = ppm_data
    if selected_pic != "All PICs":
        filtered_ppm = filtered_ppm[filtered_ppm['Assigned_PIC'].astype(str).str.contains(selected_pic, case=False, na=False)]
        
    total_ppm = len(filtered_ppm)
    closed_ppm = 0
    if status_col and not filtered_ppm.empty:
        closed_ppm = len(filtered_ppm[filtered_ppm[status_col].astype(str).str.upper().str.strip().isin(['CLOSED', 'COMPLETED', 'DONE'])])
        
    kpi_percentage = (closed_ppm / total_ppm * 100) if total_ppm > 0 else 0
    
    kpi_col1, kpi_col2, kpi_col3 = st.columns(3)
    kpi_col1.metric(f"Total PPM WIs ({selected_pic})", total_ppm)
    kpi_col2.metric("Completed / Closed", closed_ppm)
    kpi_col3.metric("Completion KPI %", f"{kpi_percentage:.1f}%")
    
    if total_ppm > 0 and status_col:
        fig = px.pie(
            filtered_ppm,
            names=status_col,
            color=status_col,
            color_discrete_map=COLOR_MAP,
            title=f"PPM Status Distribution ({selected_pic})",
            hole=0.4
        )
        st.plotly_chart(fig, use_container_width=True)
    
    st.write(f"### Current Work Instructions for {selected_pic}")
    if problem_keyword.strip():
        st.caption(f"🔍 Filtering tasks containing keyword: **'{problem_keyword}'**")
        
    st.dataframe(filtered_ppm[display_cols] if not filtered_ppm.empty else filtered_ppm, use_container_width=True)

# --- PAGE 3: DUTY ROSTER DIRECTORY ---
elif page == "🔍 PIC Roster Directory":
    st.subheader("📋 Hospital Shah Alam - Mechanical Team Official Duty Directory")
    
    roster_data = [
        {"Category": "System/Equipment", "Scope / Keywords": "Chiller, Cooling Tower", "PIC In-Charge": "IMRAN"},
        {"Category": "System/Equipment", "Scope / Keywords": "Autoclave", "PIC In-Charge": "AMIR"},
        {"Category": "System/Equipment", "Scope / Keywords": "Hydropool", "PIC In-Charge": "NAZRAN"},
        {"Category": "System/Equipment", "Scope / Keywords": "Pneumatic Tube (PTS)", "PIC In-Charge": "FARHAN"},
        {"Category": "System/Equipment", "Scope / Keywords": "Pump, Liquid Petroleum Gas (LPG)", "PIC In-Charge": "HASLA"},
        {"Category": "System/Equipment", "Scope / Keywords": "Lifts, Forklift, Handjack, Bus", "PIC In-Charge": "SYAZWAN"},
        {"Category": "System/Equipment", "Scope / Keywords": "Medical Gas (AGSS, Air Compressor, Manifold, Terminal Unit)", "PIC In-Charge": "HAIKAL"},
        {"Category": "System/Equipment", "Scope / Keywords": "Medical Gas (AVSU, AVSUM, Pendant, Repeater Alarm)", "PIC In-Charge": "BUKHARI"},
        {"Category": "System/Equipment", "Scope / Keywords": "Fire System (Smoke Detector, Hose Reel, Alarm, Hydrant)", "PIC In-Charge": "AZMI & SYAZWAN"},
        {"Category": "System/Equipment", "Scope / Keywords": "Stacker, Ambulances, Sedan Car", "PIC In-Charge": "NAZRAN"},
        {"Category": "Floor / Area", "Scope / Keywords": "Main Block Level 1 / Aras 1 (Blok Utama)", "PIC In-Charge": "AMIR & SHARY"},
        {"Category": "Floor / Area", "Scope / Keywords": "Blok Pakar & Specialist Clinics (Oftalmologi, Pediatrik, Pergigian, etc.)", "PIC In-Charge": "FAIZ"},
        {"Category": "Floor / Area", "Scope / Keywords": "Aras G (Main Lobby, Registration, Kaunter Hasil)", "PIC In-Charge": "AMIR & SHARY"},
        {"Category": "Floor / Area", "Scope / Keywords": "Aras 2 (Penyelidikan & Kawalan Kualiti), Aras 12 (Wad Pediatrik)", "PIC In-Charge": "FAIZUL"},
        {"Category": "Floor / Area", "Scope / Keywords": "Aras 3 (Emergency & Trauma, X-Ray, MOW)", "PIC In-Charge": "IMRAN"},
        {"Category": "Floor / Area", "Scope / Keywords": "Aras 4 (MOT, PAC, NICU, CCU, Anaesthesia), Aras 8 (Wad O&G)", "PIC In-Charge": "MASLIZA"},
        {"Category": "Floor / Area", "Scope / Keywords": "Aras 5 (ICU, Daycare), Aras 13 (Wad Executive/VIP), Aras 15 (Kuarters G)", "PIC In-Charge": "SHAKIR"},
        {"Category": "Floor / Area", "Scope / Keywords": "Aras 6 (HDW, Dewan Bedah GOT), Aras 7 (CSSD, RHU)", "PIC In-Charge": "FARHAN"},
        {"Category": "Floor / Area", "Scope / Keywords": "Aras 9 (Wad Pembedahan), Aras 11 (Wad Ortopedik), Aras 16 (AWSB), Aras 17 (Plant Room)", "PIC In-Charge": "AZIZI"},
        {"Category": "Floor / Area", "Scope / Keywords": "Aras 10 (Wad Perubatan Lelaki 10A / Isolasi 10B)", "PIC In-Charge": "SHARY"},
        {"Category": "Floor / Area", "Scope / Keywords": "Aras 14", "PIC In-Charge": "SYAZWAN"},
    ]
    
    roster_df = pd.DataFrame(roster_data)
    
    search_term = st.text_input("🔍 Quick Lookup (Type any problem, area, or equipment name):")
    if search_term.strip():
        roster_df = roster_df[roster_df['Scope / Keywords'].str.contains(search_term, case=False, na=False)]
        
    st.dataframe(roster_df, use_container_width=True)
