import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import io
import re
import csv

# --- PAGE SETUP ---
st.set_page_config(page_title="Mechanical Maintenance Hub", layout="wide")
st.title("🔧 Mechanical Facility Maintenance Dashboard")

# --- GOOGLE SHEET CSV URLS ---
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/1wO7tjlpFIbqVN2HVhDV9wem7KGO0rjIh_J-9vSdYgiY/gviz/tq?tqx=out:csv"
ASSET_2026_CSV_URL = "https://docs.google.com/spreadsheets/d/1wO7tjlpFIbqVN2HVhDV9wem7KGO0rjIh_J-9vSdYgiY/gviz/tq?tqx=out:csv&gid=123456789"

@st.cache_data(ttl=15)
def fetch_csv_data(url):
    """Helper function to fetch and clean raw CSV data safely from Google Sheets."""
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    
    lines = response.text.splitlines()
    reader = csv.reader(lines)
    rows = [r for r in reader if any(field.strip() for field in r)]
    
    if not rows:
        return pd.DataFrame()
    
    header = [str(col).strip() for col in rows[0]]
    num_cols = len(header)
    
    data = []
    for row in rows[1:]:
        if len(row) < num_cols:
            row = row + [''] * (num_cols - len(row))
        elif len(row) > num_cols:
            row = row[:num_cols]
        data.append(row)
        
    df = pd.DataFrame(data, columns=header)
    df = df.loc[:, ~df.columns.str.contains('^Unnamed', case=False, na=False)]
    df = df.loc[:, df.columns != '']
    return df

@st.cache_data(ttl=15)
def load_and_merge_data():
    df_master = fetch_csv_data(SHEET_CSV_URL)
    
    try:
        df_asset_2026 = fetch_csv_data(ASSET_2026_CSV_URL)
    except Exception:
        df_asset_2026 = pd.DataFrame()

    def find_col(df, candidates):
        for col in df.columns:
            if col.strip().lower() in [c.lower() for c in candidates]:
                return col
        return None

    master_asset_col = find_col(df_master, ['Asset No', 'Asset Number', 'Asset_No', 'No Asset', 'Asset ID', 'Asset'])
    master_loc_col = find_col(df_master, ['Aras', 'Location', 'Jabatan', 'Level', 'Floor', 'Blok', 'Lokasi'])

    asset_asset_col = find_col(df_asset_2026, ['Asset No', 'Asset Number', 'Asset_No', 'No Asset', 'Asset ID', 'Asset'])
    asset_loc_col = find_col(df_asset_2026, ['Aras', 'Location', 'Jabatan', 'Level', 'Floor', 'Blok', 'Lokasi'])

    if not master_loc_col:
        df_master['Location'] = ''
        master_loc_col = 'Location'

    if master_asset_col and asset_asset_col and asset_loc_col and not df_asset_2026.empty:
        asset_map = (
            df_asset_2026.dropna(subset=[asset_asset_col])
            .drop_duplicates(subset=[asset_asset_col], keep='first')
            .set_index(asset_asset_col)[asset_loc_col]
            .astype(str)
            .to_dict()
        )
        
        df_master[master_loc_col] = (
            df_master[master_loc_col]
            .astype(str)
            .str.strip()
            .replace(['nan', 'None', 'NaN', ''], None)
        )
        
        df_master[master_loc_col] = df_master[master_loc_col].fillna(
            df_master[master_asset_col].astype(str).str.strip().map(asset_map)
        )
        
        df_master[master_loc_col] = df_master[master_loc_col].fillna('')

    return df_master

try:
    df = load_and_merge_data()
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

wi_no_col = find_column(df, ['WI No', 'WI Number', 'WO No', 'WO Number', 'Work Instruction', 'WI_No', 'ID', 'No WI'])
type_col = find_column(df, ['Work Type', 'WorkType', 'Type', 'Category', 'Work_Type'])
status_col = find_column(df, ['WI Status', 'Status', 'WIStatus', 'State'])
pic_col = find_column(df, ['PIC Name', 'PIC', 'Assigned To', 'Technician', 'PIC_Name', 'Person In Charge'])
date_col = find_column(df, ['Date/Time Received', 'Date', 'Date Received', 'Created Date', 'Received Date'])
problem_col = find_column(df, ['Problem Description', 'Problem', 'Description', 'Issue', 'Details'])
location_col = find_column(df, ['Aras', 'Location', 'Jabatan', 'Level', 'Floor', 'Blok', 'Lokasi'])
system_col = find_column(df, ['Sistem', 'System', 'Equipment'])

# --- AUTO PIC ASSIGNMENT LOGIC ---
def auto_assign_pic(row):
    if pic_col and pd.notna(row.get(pic_col)) and str(row.get(pic_col)).strip() != "":
        return str(row.get(pic_col)).strip().upper()
    
    text_to_scan = f"{row.get(problem_col, '')} {row.get(location_col, '')} {row.get(system_col, '')}".lower()
    
    if re.search(r'\b(chiller|cooling tower)\b', text_to_scan):
        return "IMRAN"
    if re.search(r'\b(autoclave)\b', text_to_scan):
        return "AMIR"
    if re.search(r'\b(hydropool)\b', text_to_scan):
        return "NAZRAN"
    if re.search(r'\b(pneumatic|pts|tube)\b', text_to_scan):
        return "FARHAN"
    if re.search(r'\b(lpg|gas cylinder|gas tank|pump)\b', text_to_scan):
        return "HASLA"
    if re.search(r'\b(lift|elevator|forklift|handjack|bas|bus)\b', text_to_scan):
        return "SYAZWAN"
    if re.search(r'\b(agss|air compressor|manifold|terminal unit)\b', text_to_scan):
        return "HAIKAL"
    if re.search(r'\b(avsu|avsum|pendant|repeater alarm)\b', text_to_scan):
        return "BUKHARI"
    if re.search(r'\b(fire|smoke|sprinkler|hydrant|hose reel|pyrogen)\b', text_to_scan):
        return "AZMI & SYAZWAN"
    if re.search(r'\b(stacker|ambulance|sedan|rehab)\b', text_to_scan):
        return "NAZRAN"
        
    if re.search(r'\b(pakar|klinik|oftalmologi|pergigian|orl|sc|specialist clinic|special clinic)\b', text_to_scan):
        return "FAIZ"
        
    if re.search(r'\b(kuarters|asrama|houseman|housemen)\b', text_to_scan):
        return "SHAKIR"

    if re.search(r'\b(awsb|plant room|external|luar main block|luar)\b', text_to_scan):
        return "AZIZI"

    if re.search(r'\b(aras\s*0?1\b|level\s*0?1\b|\bl0?1\b|main block level 1|main block aras 1|blok utama level 1|blok utama aras 1|aras g|level g|lobi|hasil|pendaftaran|kaunter)\b', text_to_scan):
        return "AMIR & SHARY"
        
    if re.search(r'\b(aras\s*0?2\b|level\s*0?2\b|\bl0?2\b|penyelidikan)\b', text_to_scan):
        return "FAIZUL"
        
    if re.search(r'\b(aras\s*0?3\b|level\s*0?3\b|\bl0?3\b|wad\s*3|kecemasan|xray|x-ray|radiologi|mow|mdw)\b', text_to_scan):
        return "IMRAN"
        
    if re.search(r'\b(aras\s*0?4\b|level\s*0?4\b|\bl0?4\b|wad\s*4|mot|pac|nicu|ccu|anaesthesia)\b', text_to_scan):
        return "MASLIZA"
        
    if re.search(r'\b(aras\s*0?5\b|level\s*0?5\b|\bl0?5\b|icu|daycare|rawatan harian)\b', text_to_scan):
        return "SHAKIR"
        
    if re.search(r'\b(aras\s*0?6\b|level\s*0?6\b|\bl0?6\b|hdw|got|dewan bedah)\b', text_to_scan):
        return "FARHAN"
        
    if re.search(r'\b(aras\s*0?7\b|level\s*0?7\b|\bl0?7\b|cssd|rhu)\b', text_to_scan):
        return "FARHAN"
        
    if re.search(r'\b(aras\s*0?8\b|level\s*0?8\b|\bl0?8\b|wad\s*8|8a|8b|ldu|bersalin|o&g|obstetrik|ginekologi)\b', text_to_scan):
        return "MASLIZA"
        
    if re.search(r'\b(aras\s*0?9\b|level\s*0?9\b|\bl0?9\b|wad\s*9|9a|9b)\b', text_to_scan):
        return "AZIZI"
        
    if re.search(r'\b(aras\s*10\b|level\s*10\b|\bl10\b|wad\s*10|10a|10b)\b', text_to_scan):
        return "SHARY"
        
    if re.search(r'\b(aras\s*11\b|level\s*11\b|\bl11\b|wad\s*11|11a|11b|ortopedik)\b', text_to_scan):
        return "AZIZI"
        
    if re.search(r'\b(aras\s*12\b|level\s*12\b|\bl12\b|wad\s*12|12a|12b|pediatrik|patologi)\b', text_to_scan):
        return "FAIZUL"
        
    if re.search(r'\b(aras\s*13\b|level\s*13\b|\bl13\b|wad\s*13|13a|13b|vip|eksekutif|ekesekutif)\b', text_to_scan):
        return "SHAKIR"
        
    if re.search(r'\b(aras\s*14\b|level\s*14\b|\bl14\b)\b', text_to_scan):
        return "SYAZWAN"

    if re.search(r'\b(rekod|perpustakaan|dietetik|sajian|pemandu|logistik|it)\b', text_to_scan):
        return "NAZRAN"

    return "UNASSIGNED"

# Create or Update Auto-Assigned PIC Column
df['Assigned_PIC'] = df.apply(auto_assign_pic, axis=1)

# --- STRICT 5-COLUMN DASHBOARD DISPLAY SETTING ---
target_display_cols = []
if wi_no_col: target_display_cols.append(wi_no_col)
if status_col: target_display_cols.append(status_col)
if problem_col: target_display_cols.append(problem_col)
if date_col: target_display_cols.append(date_col)
target_display_cols.append('Assigned_PIC')

display_cols = [c for c in target_display_cols if c in df.columns]

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
        {"Category": "Main Block Level", "Scope / Floor Level": "Level 1 / Aras 1 / L1 (Include Aras G, Lobby)", "PIC In-Charge": "AMIR & SHARY"},
        {"Category": "Main Block Level", "Scope / Floor Level": "Level 2 / Aras 2 / L2 (Penyelidikan)", "PIC In-Charge": "FAIZUL"},
        {"Category": "Main Block Level", "Scope / Floor Level": "Level 3 / Aras 3 / L3 (Emergency, Radiologi, MOW, MDW, Wad 3 - All L3)", "PIC In-Charge": "IMRAN"},
        {"Category": "Main Block Level", "Scope / Floor Level": "Level 4 / Aras 4 / L4 (MOT, PAC, NICU, CCU, Anaesthesia)", "PIC In-Charge": "MASLIZA"},
        {"Category": "Main Block Level", "Scope / Floor Level": "Level 5 / Aras 5 / L5 (ICU, Daycare, Rawatan Harian)", "PIC In-Charge": "SHAKIR"},
        {"Category": "Main Block Level", "Scope / Floor Level": "Level 6 / Aras 6 / L6 (HDW, Dewan Bedah GOT)", "PIC In-Charge": "FARHAN"},
        {"Category": "Main Block Level", "Scope / Floor Level": "Level 7 / Aras 7 / L7 (CSSD, RHU)", "PIC In-Charge": "FARHAN"},
        {"Category": "Main Block Level", "Scope / Floor Level": "Level 8 / Aras 8 / L8 (Wad O&G, 8A, 8B, LDU, Bersalin)", "PIC In-Charge": "MASLIZA"},
        {"Category": "Main Block Level", "Scope / Floor Level": "Level 9 / Aras 9 / L9 (Wad Pembedahan, 9A, 9B)", "PIC In-Charge": "AZIZI"},
        {"Category": "Main Block Level", "Scope / Floor Level": "Level 10 / Aras 10 / L10 (Wad Perubatan Lelaki 10A / Isolasi 10B)", "PIC In-Charge": "SHARY"},
        {"Category": "Main Block Level", "Scope / Floor Level": "Level 11 / Aras 11 / L11 (Wad Ortopedik, 11A, 11B)", "PIC In-Charge": "AZIZI"},
        {"Category": "Main Block Level", "Scope / Floor Level": "Level 12 / Aras 12 / L12 (Wad Pediatrik, 12A, 12B, Patologi)", "PIC In-Charge": "FAIZUL"},
        {"Category": "Main Block Level", "Scope / Floor Level": "Level 13 / Aras 13 / L13 (Wad Executive/VIP, 13A, 13B)", "PIC In-Charge": "SHAKIR"},
        {"Category": "Main Block Level", "Scope / Floor Level": "Level 14 / Aras 14 / L14", "PIC In-Charge": "SYAZWAN"},
        {"Category": "Outside Main Block", "Scope / Floor Level": "Kuarters G, Asrama Housemen", "PIC In-Charge": "SHAKIR"},
        {"Category": "Outside Main Block", "Scope / Floor Level": "Plant Room, AWSB, External Buildings", "PIC In-Charge": "AZIZI"},
        {"Category": "Outside Main Block", "Scope / Floor Level": "Blok Pakar, Specialist Clinics (SC) - All Clinics", "PIC In-Charge": "FAIZ"},
        {"Category": "System/Equipment", "Scope / Floor Level": "Chiller, Cooling Tower", "PIC In-Charge": "IMRAN"},
        {"Category": "System/Equipment", "Scope / Floor Level": "Autoclave", "PIC In-Charge": "AMIR"},
        {"Category": "System/Equipment", "Scope / Floor Level": "Hydropool, Stacker, Ambulances, Sedan", "PIC In-Charge": "NAZRAN"},
        {"Category": "System/Equipment", "Scope / Floor Level": "Pneumatic Tube (PTS)", "PIC In-Charge": "FARHAN"},
        {"Category": "System/Equipment", "Scope / Floor Level": "Pump, Liquid Petroleum Gas (LPG)", "PIC In-Charge": "HASLA"},
        {"Category": "System/Equipment", "Scope / Floor Level": "Lifts, Forklift, Handjack, Bus", "PIC In-Charge": "SYAZWAN"},
        {"Category": "System/Equipment", "Scope / Floor Level": "Medical Gas (AGSS, Air Compressor, Manifold, Terminal Unit)", "PIC In-Charge": "HAIKAL"},
        {"Category": "System/Equipment", "Scope / Floor Level": "Medical Gas (AVSU, AVSUM, Pendant, Repeater Alarm)", "PIC In-Charge": "BUKHARI"},
        {"Category": "System/Equipment", "Scope / Floor Level": "Fire System (Smoke Detector, Hose Reel, Alarm, Hydrant)", "PIC In-Charge": "AZMI & SYAZWAN"},
    ]
    
    roster_df = pd.DataFrame(roster_data)
    
    search_term = st.text_input("🔍 Quick Lookup (Type any problem, area, or equipment name):")
    if search_term.strip():
        roster_df = roster_df[roster_df['Scope / Floor Level'].str.contains(search_term, case=False, na=False)]
        
    st.dataframe(roster_df, use_container_width=True)
