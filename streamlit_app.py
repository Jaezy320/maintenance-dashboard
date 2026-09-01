import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import io
import re
import csv

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Mechanical Maintenance Hub",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🔧 Mechanical Facility Maintenance Dashboard")

# --- GOOGLE SPREADSHEET CONFIGURATION ---
SPREADSHEET_ID = "1wO7tjlpFIbqVN2HVhDV9wem7KGO0rjIh_J-9vSdYgiY"

@st.cache_data(ttl=300)
def load_master_data():
    """Fetches Master Data with extended timeout (30s) and fallback export URLs."""
    urls = [
        f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv",
        f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv"
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }
    
    for url in urls:
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            lines = response.text.splitlines()
            reader = csv.reader(lines)
            rows = [r for r in reader if any(field.strip() for field in r)]
            
            if not rows:
                continue
            
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
            df.columns = df.columns.astype(str).str.strip()
            return df
        except Exception:
            continue
            
    return pd.DataFrame()

df = load_master_data()

if df.empty:
    st.error("⚠️ Unable to retrieve Master Data from Google Sheets. Please verify connection or click 'Refresh Data' in the sidebar.")
    st.stop()

# --- FLEXIBLE COLUMN DETECTION ---
def find_column(df_in, candidates):
    for col in df_in.columns:
        if col.strip().lower() in [c.lower() for c in candidates]:
            return col
    return None

wi_no_col = find_column(df, ['WI No', 'WI Number', 'WO No', 'WO Number', 'Work Instruction', 'WI_No', 'ID', 'No WI'])
type_col = find_column(df, ['Work Type', 'WorkType', 'Type', 'Category', 'Work_Type'])
status_col = find_column(df, ['WI Status', 'Status', 'WIStatus', 'State'])
pic_col = find_column(df, ['PIC List', 'PIC Name', 'PIC', 'Assigned To', 'Technician', 'PIC_Name', 'Person In Charge', 'Senarai PIC'])
date_col = find_column(df, ['Date/Time Received', 'Date', 'Date Received', 'Created Date', 'Received Date'])
problem_col = find_column(df, ['Problem Description', 'Problem', 'Description', 'Issue', 'Details'])
location_col = find_column(df, ['Aras', 'Location', 'Jabatan', 'Level', 'Floor', 'Blok', 'Lokasi', 'Tempat'])
system_col = find_column(df, ['Sistem', 'System', 'Equipment'])

# --- PIC ASSIGNMENT ENGINE ---
def get_final_pic(row):
    # 1. Directly use PIC from Master Data if populated
    if pic_col and pd.notna(row.get(pic_col)) and str(row.get(pic_col)).strip() != "":
        val = str(row.get(pic_col)).strip().upper()
        if val not in ["NAN", "NONE", "NULL", "-", ""]:
            return val

    # 2. Fallback Regex Logic (Only if Master Data PIC field is blank)
    combined_text = f"{row.get(problem_col, '')} {row.get(location_col, '')} {row.get(system_col, '')}".upper()

    system_rules = [
        (r'\b(CHILLER|COOLING TOWER)\b', "IMRAN"),
        (r'\b(AUTOCLAVE)\b', "AMIR"),
        (r'\b(HYDROPOOL|STACKER|AMBULANCE|SEDAN)\b', "NAZRAN"),
        (r'\b(PNEUMATIC|PTS|TUBE)\b', "FARHAN"),
        (r'\b(LPG|GAS CYLINDER|GAS TANK|PUMP)\b', "HASLA"),
        (r'\b(LIFT|ELEVATOR|FORKLIFT|HANDJACK|BUS|BAS)\b', "SYAZWAN"),
        (r'\b(AGSS|AIR COMPRESSOR|MANIFOLD|TERMINAL UNIT)\b', "HAIKAL"),
        (r'\b(AVSU|AVSUM|PENDANT|REPEATER ALARM)\b', "BUKHARI"),
        (r'\b(FIRE|SMOKE|SPRINKLER|HYDRANT|HOSE REEL|PYROGEN)\b', "AZMI & SYAZWAN"),
    ]

    for pattern, pic in system_rules:
        if re.search(pattern, combined_text):
            return pic

    location_rules = [
        (r'\b(ARAS\s*0?1\b|LEVEL\s*0?1\b|\bl0?1\b|MAIN BLOCK LEVEL 1|MAIN BLOCK ARAS 1|BLOK UTAMA LEVEL 1|BLOK UTAMA ARAS 1|ARAS G|LEVEL G|LOBI|HASIL|PENDAFTARAN|KAUNTER)\b', "AMIR & SHARY"),
        (r'\b(ARAS\s*0?2\b|LEVEL\s*0?2\b|\bl0?2\b|PENYELIDIKAN)\b', "FAIZUL"),
        (r'\b(ARAS\s*0?3\b|LEVEL\s*0?3\b|\bl0?3\b|WAD\s*3|KECEMASAN|XRAY|X-RAY|RADIOLOGI|MOW|MDW)\b', "IMRAN"),
        (r'\b(ARAS\s*0?4\b|LEVEL\s*0?4\b|\bl0?4\b|WAD\s*4|MOT|PAC|NICU|CCU|ANAESTHESIA)\b', "MASLIZA"),
        (r'\b(ARAS\s*0?5\b|LEVEL\s*0?5\b|\bl0?5\b|ICU|DAYCARE|RAWATAN HARIAN)\b', "SHAKIR"),
        (r'\b(ARAS\s*0?6\b|LEVEL\s*0?6\b|\bl0?6\b|HDW|GOT|DEWAN BEDAH)\b', "FARHAN"),
        (r'\b(ARAS\s*0?7\b|LEVEL\s*0?7\b|\bl0?7\b|CSSD|RHU)\b', "FARHAN"),
        (r'\b(ARAS\s*0?8\b|LEVEL\s*0?8\b|\bl0?8\b|WAD\s*8|8A|8B|LDU|BERSALIN|O&G|OBSTETRIK|GINEKOLOGI)\b', "MASLIZA"),
        (r'\b(ARAS\s*0?9\b|LEVEL\s*0?9\b|\bl0?9\b|WAD\s*9|9A|9B)\b', "AZIZI"),
        (r'\b(ARAS\s*10\b|LEVEL\s*10\b|\bl10\b|WAD\s*10|10A|10B)\b', "SHARY"),
        (r'\b(ARAS\s*11\b|LEVEL\s*11\b|\bl11\b|WAD\s*11|11A|11B|ORTOPEDIK)\b', "AZIZI"),
        (r'\b(ARAS\s*12\b|LEVEL\s*12\b|\bl12\b|WAD\s*12|12A|12B|PEDIATRIK|PATOLOGI)\b', "FAIZUL"),
        (r'\b(ARAS\s*13\b|LEVEL\s*13\b|\bl13\b|WAD\s*13|13A|13B|VIP|EKSEKUTIF|EKESEKUTIF)\b', "SHAKIR"),
        (r'\b(ARAS\s*14\b|LEVEL\s*14\b|\bl14\b)\b', "SYAZWAN"),
        (r'\b(PAKAR|KLINIK|OFTALMOLOGI|PERGIGIAN|ORL|SC|SPECIALIST CLINIC)\b', "FAIZ"),
        (r'\b(KUARTERS|ASRAMA|HOUSEMAN|HOUSEMEN)\b', "SHAKIR"),
        (r'\b(AWSB|PLANT ROOM|EXTERNAL|LUAR MAIN BLOCK|LUAR)\b', "AZIZI"),
        (r'\b(REKOD|PERPUSTAKAAN|DIETETIK|SAJIAN|PEMANDU|LOGISTIK|IT)\b', "NAZRAN")
    ]

    for pattern, pic in location_rules:
        if re.search(pattern, combined_text):
            return pic

    return "UNASSIGNED"

# Apply Final PIC Column
df['Assigned_PIC'] = df.apply(get_final_pic, axis=1)

# Display Columns Selection
target_display_cols = []
if wi_no_col: target_display_cols.append(wi_no_col)
if type_col: target_display_cols.append(type_col)
if status_col: target_display_cols.append(status_col)
if problem_col: target_display_cols.append(problem_col)
if date_col: target_display_cols.append(date_col)
target_display_cols.append('Assigned_PIC')

display_cols = [c for c in target_display_cols if c in df.columns]
if not display_cols:
    display_cols = df.columns.tolist()

# Parse Dates Safely
if date_col:
    df['Parsed_Date'] = pd.to_datetime(df[date_col], errors='coerce')
    df['Year'] = df['Parsed_Date'].dt.year
    df['Month_Name'] = df['Parsed_Date'].dt.strftime('%B')
else:
    df['Year'] = None
    df['Month_Name'] = None

# COLOR MAP FOR STATUS
COLOR_MAP = {
    "Open": "#E53E3E", "OPEN": "#E53E3E", "open": "#E53E3E",
    "In Progress": "#DD6B20", "IN PROGRESS": "#DD6B20", "in progress": "#DD6B20",
    "Pending": "#DD6B20", "PENDING": "#DD6B20",
    "Closed": "#3182CE", "CLOSED": "#3182CE", "closed": "#3182CE",
    "Completed": "#3182CE", "COMPLETED": "#3182CE", "completed": "#3182CE",
    "Done": "#3182CE", "DONE": "#3182CE"
}

# --- SIDEBAR NAVIGATION AND FILTERS ---
st.sidebar.header("Navigation & Controls")

if st.sidebar.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.rerun()

page = st.sidebar.radio("Go to:", [
    "Main Overview (All Work Types)", 
    "PPM & PIC KPIs", 
    "🔍 PIC Roster Directory"
])

st.sidebar.markdown("---")
st.sidebar.subheader("📅 Date Filters")

if date_col and 'Year' in df.columns and not df['Year'].dropna().empty:
    available_years = sorted(df['Year'].dropna().astype(int).unique().tolist(), reverse=True)
    selected_year = st.sidebar.selectbox("Select Year:", ["All Years"] + [str(y) for y in available_years])
    if selected_year != "All Years":
        df = df[df['Year'] == int(selected_year)]

if date_col and 'Month_Name' in df.columns and not df['Month_Name'].dropna().empty:
    month_order = ["January", "February", "March", "April", "May", "June", 
                   "July", "August", "September", "October", "November", "December"]
    present_months = df['Month_Name'].dropna().unique().tolist()
    sorted_months = [m for m in month_order if m in present_months]
    
    selected_month = st.sidebar.selectbox("Select Month:", ["All Months"] + sorted_months)
    if selected_month != "All Months":
        df = df[df['Month_Name'] == selected_month]

st.sidebar.markdown("---")
st.sidebar.subheader("🔍 Keyword Search")

if problem_col:
    problem_keyword = st.sidebar.text_input("Filter Description:", placeholder="e.g. leak, gas, aircon")
    if problem_keyword.strip():
        df = df[df[problem_col].astype(str).str.contains(problem_keyword, case=False, na=False)]

# Categorize Work Types
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

# EXCEL EXPORT HELPER
def render_excel_download_button(df_in, filename="Export_Data.xlsx", label="📥 Download Excel"):
    if df_in.empty:
        return
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df_in.to_excel(writer, index=False)
    st.download_button(
        label=label,
        data=buffer.getvalue(),
        file_name=filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

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
        render_excel_download_button(ppm_data, "PPM_Work_Orders.xlsx", "📥 Export PPM Data")
    with tab2:
        st.dataframe(breakdown_data[display_cols] if not breakdown_data.empty else breakdown_data, use_container_width=True)
        render_excel_download_button(breakdown_data, "Breakdown_Work_Orders.xlsx", "📥 Export Breakdown Data")
    with tab3:
        st.dataframe(cm_data[display_cols] if not cm_data.empty else cm_data, use_container_width=True)
        render_excel_download_button(cm_data, "CM_Work_Orders.xlsx", "📥 Export CM Data")
    with tab4:
        st.dataframe(df[display_cols] if not df.empty else df, use_container_width=True)
        render_excel_download_button(df, "All_Maintenance_Data.xlsx", "📥 Export Master Data")

# --- PAGE 2: PPM & PIC KPIS ---
elif page == "PPM & PIC KPIs":
    st.subheader("PPM Tracking & Mechanical PIC Performance")
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("👤 PIC Filters")
    
    unique_pics = sorted([p for p in df['Assigned_PIC'].dropna().unique().tolist() if p != "UNASSIGNED"])
    
    selected_pic = st.sidebar.selectbox("Filter by PIC:", ["All PICs"] + unique_pics)
    
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
    st.dataframe(filtered_ppm[display_cols] if not filtered_ppm.empty else filtered_ppm, use_container_width=True)
    render_excel_download_button(filtered_ppm, f"PPM_KPI_{selected_pic}.xlsx", f"📥 Export {selected_pic} PPM Data")

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
    search_term = st.text_input("🔍 Search PIC Scope:")
    if search_term.strip():
        roster_df = roster_df[roster_df['Scope / Floor Level'].str.contains(search_term, case=False, na=False)]
        
    st.dataframe(roster_df, use_container_width=True)
    render_excel_download_button(roster_df, "Hospital_Shah_Alam_PIC_Roster.xlsx", "📥 Download PIC Roster as Excel")
