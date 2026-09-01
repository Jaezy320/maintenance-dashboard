import csv
import io
import re
import pandas as pd
import plotly.express as px
import requests
import streamlit as st

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Mechanical Facility Maintenance Hub",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🔧 Mechanical Facility Maintenance Dashboard")

# --- GOOGLE SPREADSHEET CONFIGURATION ---
SPREADSHEET_ID = "1wO7tjlpFIbqVN2HVhDV9wem7KGO0rjIh_J-9vSdYgiY"


@st.cache_data(ttl=300)
def load_master_data():
  """Fetches Master Data from Google Sheets with fallback URLs and parsing."""
  urls = [
      f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv",
      f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv",
  ]

  headers = {
      "User-Agent": (
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
          " (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
      )
  }

  for url in urls:
    try:
      response = requests.get(url, headers=headers, timeout=20)
      response.raise_for_status()

      if (
          "html" in response.headers.get("Content-Type", "").lower()
          or "<html" in response.text[:200].lower()
      ):
        continue

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
          row = row + [""] * (num_cols - len(row))
        elif len(row) > num_cols:
          row = row[:num_cols]
        data.append(row)

      df = pd.DataFrame(data, columns=header)
      df = df.loc[
          :, ~df.columns.str.contains("^Unnamed", case=False, na=False)
      ]
      df = df.loc[:, df.columns != ""]
      df.columns = df.columns.astype(str).str.strip()
      df = df.loc[:, ~df.columns.duplicated()]
      return df
    except Exception:
      continue

  return pd.DataFrame()


# Load Master Data
df = load_master_data()

if df.empty:
  st.error(
      "⚠️ Unable to retrieve Master Data from Google Sheets. Ensure your sheet"
      " sharing permission is set to 'Anyone with the link can view'."
  )
  st.info(
      "💡 **Quick Fix:** In Google Sheets, click **Share** (top-right) ➔"
      " Change **General Access** to **Anyone with the link**."
  )
  st.stop()


# --- FLEXIBLE COLUMN DETECTION ---
def find_column(df_in, candidates):
  for col in df_in.columns:
    if col.strip().lower() in [c.lower() for c in candidates]:
      return col
  return None


# Explicitly mapping requested columns
wi_no_col = find_column(
    df,
    [
        "WI No.",
        "WI No",
        "WI Number",
        "WO No.",
        "WO No",
        "WO Number",
        "Work Instruction",
        "WI_No",
        "ID",
        "No WI",
        "WI NO",
        "NO. WI",
    ],
)
status_col = find_column(
    df, ["WI Status", "Status", "WIStatus", "State", "Work Order Status"]
)
problem_col = find_column(
    df,
    [
        "Problem Description",
        "Problem",
        "Description",
        "Issue",
        "Details",
        "Keterangan Masalah",
    ],
)
type_col = find_column(
    df, ["Work Type", "WorkType", "Type", "Category", "Work_Type", "Jenis Kerja"]
)
date_col = find_column(
    df,
    [
        "Date/Time Received",
        "Date Received",
        "Date",
        "Created Date",
        "Received Date",
        "Tarikh",
    ],
)
pic_col = find_column(
    df,
    [
        "pic",
        "PIC",
        "PIC List",
        "PIC Name",
        "Assigned To",
        "Technician",
        "PIC_Name",
        "Person In Charge",
        "Senarai PIC",
    ],
)

# Auxiliary Location & System Columns for Auto-Assignment Rules
location_col = find_column(
    df, ["Aras", "Location", "Jabatan", "Level", "Floor", "Blok", "Lokasi", "Tempat"]
)
system_col = find_column(df, ["Sistem", "System", "Equipment"])


# Helper function for clean string extraction
def safe_val(row, col_name):
  if col_name and col_name in row and pd.notna(row[col_name]):
    val = str(row[col_name]).strip()
    return "" if val.upper() in ["NAN", "NONE", "NULL", "-"] else val
  return ""


# --- PIC AUTO-ASSIGNMENT ENGINE ---
def get_final_pic(row):
  # 1. Use existing PIC from Master Data if present
  existing_pic = safe_val(row, pic_col)
  if existing_pic:
    return existing_pic.upper()

  # 2. Extract safe context string
  p_text = safe_val(row, problem_col)
  l_text = safe_val(row, location_col)
  s_text = safe_val(row, system_col)
  combined_text = f"{p_text} {l_text} {s_text}".upper()

  # System/Equipment Rules
  system_rules = [
      (
          r"\b(TRANSPORT|TRANSPORTATION|KENDERAAN|AMBULANCE|AMBULANS|SEDAN|BUS|BAS|VAN|CAR|KERETA|PEMANDU|DRIVER|LOGISTIK|STACKER|HYDROPOOL|FORKLIFT|HANDJACK)\b",
          "NAZRAN",
      ),
      (r"\b(CHILLER|COOLING TOWER)\b", "IMRAN"),
      (r"\b(AUTOCLAVE)\b", "AMIR"),
      (r"\b(PNEUMATIC|PTS|TUBE)\b", "FARHAN"),
      (r"\b(LPG|GAS CYLINDER|GAS TANK|PUMP)\b", "HASLA"),
      (r"\b(LIFT|ELEVATOR)\b", "SYAZWAN"),
      (r"\b(AGSS|AIR COMPRESSOR|MANIFOLD|TERMINAL UNIT)\b", "HAIKAL"),
      (r"\b(AVSU|AVSUM|PENDANT|REPEATER ALARM)\b", "BUKHARI"),
      (
          r"\b(FIRE|SMOKE|SPRINKLER|HYDRANT|HOSE REEL|PYROGEN)\b",
          "AZMI & SYAZWAN",
      ),
  ]

  for pattern, pic in system_rules:
    if re.search(pattern, combined_text):
      return pic

  # Location Rules
  location_rules = [
      (
          r"\b(ARAS\s*0?1\b|LEVEL\s*0?1\b|\bl0?1\b|MAIN BLOCK LEVEL 1|MAIN BLOCK ARAS 1|BLOK UTAMA LEVEL 1|BLOK UTAMA ARAS 1|ARAS G|LEVEL G|LOBI|HASIL|PENDAFTARAN|KAUNTER)\b",
          "AMIR & SHARY",
      ),
      (r"\b(ARAS\s*0?2\b|LEVEL\s*0?2\b|\bl0?2\b|PENYELIDIKAN)\b", "FAIZUL"),
      (
          r"\b(ARAS\s*0?3\b|LEVEL\s*0?3\b|\bl0?3\b|WAD\s*3|KECEMASAN|XRAY|X-RAY|RADIOLOGI|MOW|MDW)\b",
          "IMRAN",
      ),
      (
          r"\b(ARAS\s*0?4\b|LEVEL\s*0?4\b|\bl0?4\b|WAD\s*4|MOT|PAC|NICU|CCU|ANAESTHESIA)\b",
          "MASLIZA",
      ),
      (
          r"\b(ARAS\s*0?5\b|LEVEL\s*0?5\b|\bl0?5\b|ICU|DAYCARE|RAWATAN HARIAN)\b",
          "SHAKIR",
      ),
      (
          r"\b(ARAS\s*0?6\b|LEVEL\s*0?6\b|\bl0?6\b|HDW|GOT|DEWAN BEDAH)\b",
          "FARHAN",
      ),
      (r"\b(ARAS\s*0?7\b|LEVEL\s*0?7\b|\bl0?7\b|CSSD|RHU)\b", "FARHAN"),
      (
          r"\b(ARAS\s*0?8\b|LEVEL\s*0?8\b|\bl0?8\b|WAD\s*8|8A|8B|LDU|BERSALIN|O&G|OBSTETRIK|GINEKOLOGI)\b",
          "MASLIZA",
      ),
      (r"\b(ARAS\s*0?9\b|LEVEL\s*0?9\b|\bl0?9\b|WAD\s*9|9A|9B)\b", "AZIZI"),
      (r"\b(ARAS\s*10\b|LEVEL\s*10\b|\bl10\b|WAD\s*10|10A|10B)\b", "SHARY"),
      (
          r"\b(ARAS\s*11\b|LEVEL\s*11\b|\bl11\b|WAD\s*11|11A|11B|ORTOPEDIK)\b",
          "AZIZI",
      ),
      (
          r"\b(ARAS\s*12\b|LEVEL\s*12\b|\bl12\b|WAD\s*12|12A|12B|PEDIATRIK|PATOLOGI)\b",
          "FAIZUL",
      ),
      (
          r"\b(ARAS\s*13\b|LEVEL\s*13\b|\bl13\b|WAD\s*13|13A|13B|VIP|EKSEKUTIF|EKESEKUTIF)\b",
          "SHAKIR",
      ),
      (r"\b(ARAS\s*14\b|LEVEL\s*14\b|\bl14\b)\b", "SYAZWAN"),
      (
          r"\b(PAKAR|KLINIK|OFTALMOLOGI|PERGIGIAN|ORL|SC|SPECIALIST CLINIC)\b",
          "FAIZ",
      ),
      (r"\b(KUARTERS|ASRAMA|HOUSEMAN|HOUSEMEN)\b", "SHAKIR"),
      (r"\b(AWSB|PLANT ROOM|EXTERNAL|LUAR MAIN BLOCK|LUAR)\b", "AZIZI"),
      (r"\b(REKOD|PERPUSTAKAAN|DIETETIK|SAJIAN|IT)\b", "NAZRAN"),
  ]

  for pattern, pic in location_rules:
    if re.search(pattern, combined_text):
      return pic

  return "UNASSIGNED"


# Assign Final PIC
df["Assigned_PIC"] = df.apply(get_final_pic, axis=1)

# Target Ordered Columns as requested: WI No., WI Status, Problem Description, Work Type, Date/Time Received, pic
target_cols = [
    wi_no_col,
    status_col,
    problem_col,
    type_col,
    date_col,
    pic_col if pic_col else "Assigned_PIC",
]
display_cols = [c for c in target_cols if c and c in df.columns]

# Ensure Assigned_PIC is visible if 'pic' was not originally in the sheet
if "Assigned_PIC" not in display_cols and "Assigned_PIC" in df.columns:
  display_cols.append("Assigned_PIC")

if not display_cols:
  display_cols = df.columns.tolist()

# Parse Dates
if date_col:
  df["Parsed_Date"] = pd.to_datetime(df[date_col], errors="coerce")
  df["Year"] = df["Parsed_Date"].dt.year
  df["Month_Name"] = df["Parsed_Date"].dt.strftime("%B")

# Status Colors Mapping
COLOR_MAP = {
    "Open": "#E53E3E",
    "OPEN": "#E53E3E",
    "In Progress": "#DD6B20",
    "IN PROGRESS": "#DD6B20",
    "Pending": "#DD6B20",
    "PENDING": "#DD6B20",
    "Closed": "#3182CE",
    "CLOSED": "#3182CE",
    "Completed": "#3182CE",
    "COMPLETED": "#3182CE",
    "Done": "#3182CE",
    "DONE": "#3182CE",
}

# --- SIDEBAR & FILTERS ---
st.sidebar.header("Controls & Filters")

if st.sidebar.button("🔄 Refresh Master Data"):
  st.cache_data.clear()
  st.rerun()

page = st.sidebar.radio(
    "View Page:", ["Main Overview (Master Data)", "PPM & PIC KPIs"]
)

st.sidebar.markdown("---")

if date_col and "Year" in df.columns and not df["Year"].dropna().empty:
  years = sorted(df["Year"].dropna().astype(int).unique().tolist(), reverse=True)
  selected_year = st.sidebar.selectbox(
      "Filter Year:", ["All Years"] + [str(y) for y in years]
  )
  if selected_year != "All Years":
    df = df[df["Year"] == int(selected_year)]

if (
    date_col
    and "Month_Name" in df.columns
    and not df["Month_Name"].dropna().empty
):
  month_order = [
      "January",
      "February",
      "March",
      "April",
      "May",
      "June",
      "July",
      "August",
      "September",
      "October",
      "November",
      "December",
  ]
  present_months = [
      m for m in month_order if m in df["Month_Name"].dropna().unique()
  ]
  selected_month = st.sidebar.selectbox(
      "Filter Month:", ["All Months"] + present_months
  )
  if selected_month != "All Months":
    df = df[df["Month_Name"] == selected_month]

if problem_col:
  search_keyword = st.sidebar.text_input(
      "Search Description:", placeholder="e.g., leak, chiller, gas, ambulance"
  )
  if search_keyword.strip():
    df = df[
        df[problem_col]
        .astype(str)
        .str.contains(search_keyword, case=False, na=False)
    ]

# Categorize Work Types
if type_col:
  type_clean = df[type_col].astype(str).str.upper().str.strip()
  ppm_mask = type_clean.str.contains(r"PPM|\bPM\b|PREVENT|PLANNED", regex=True)
  breakdown_mask = type_clean.str.contains(
      r"BREAKDOWN|\bBD\b|EMERGENCY", regex=True
  )
  cm_mask = (
      type_clean.str.contains(r"\bCM\b|CORRECTIVE|REPAIR", regex=True)
      & (~ppm_mask)
      & (~breakdown_mask)
  )

  ppm_data = df[ppm_mask]
  breakdown_data = df[breakdown_mask]
  cm_data = df[cm_mask]
else:
  ppm_data, breakdown_data, cm_data = (
      pd.DataFrame(),
      pd.DataFrame(),
      pd.DataFrame(),
  )


# Excel Export Function
def download_excel(df_in, filename, label="📥 Download Excel"):
  if df_in.empty:
    return
  buffer = io.BytesIO()
  with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
    df_in.to_excel(writer, index=False)
  st.download_button(
      label=label,
      data=buffer.getvalue(),
      file_name=filename,
      mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  )


# --- PAGE 1: MAIN OVERVIEW ---
if page == "Main Overview (Master Data)":
  st.subheader("Master Data Facility Overview")

  active_count = 0
  if status_col:
    active_count = len(
        df[
            ~df[status_col]
            .astype(str)
            .str.upper()
            .str.strip()
            .isin(["CLOSED", "COMPLETED", "DONE"])
        ]
    )

  m1, m2, m3, m4 = st.columns(4)
  m1.metric("Total WIs", len(df))
  m2.metric("Active / Open WIs", active_count)
  m3.metric("PPM WIs", len(ppm_data))
  m4.metric("Breakdown / CM WIs", len(breakdown_data) + len(cm_data))

  st.markdown("---")
  tab1, tab2, tab3, tab4 = st.tabs([
      "All Master Data",
      "PPM Data",
      "Breakdown Data",
      "Corrective (CM) Data",
  ])

  with tab1:
    st.dataframe(
        df[display_cols] if not df.empty else df, use_container_width=True
    )
    download_excel(df, "Master_Data.xlsx", "📥 Export Master Data")
  with tab2:
    st.dataframe(
        ppm_data[display_cols] if not ppm_data.empty else ppm_data,
        use_container_width=True,
    )
    download_excel(ppm_data, "PPM_Data.xlsx", "📥 Export PPM Data")
  with tab3:
    st.dataframe(
        breakdown_data[display_cols] if not breakdown_data.empty else breakdown_data,
        use_container_width=True,
    )
    download_excel(breakdown_data, "Breakdown_Data.xlsx", "📥 Export Breakdown Data")
  with tab4:
    st.dataframe(
        cm_data[display_cols] if not cm_data.empty else cm_data,
        use_container_width=True,
    )
    download_excel(cm_data, "CM_Data.xlsx", "📥 Export CM Data")

# --- PAGE 2: PPM & PIC KPIS ---
elif page == "PPM & PIC KPIs":
  st.subheader("PIC Performance & PPM KPIs")

  pic_field = "Assigned_PIC" if "Assigned_PIC" in df.columns else pic_col
  unique_pics = (
      sorted([p for p in df[pic_field].dropna().unique() if p != "UNASSIGNED"])
      if pic_field
      else []
  )
  selected_pic = st.selectbox("Select PIC:", ["All PICs"] + unique_pics)

  pic_df = df if selected_pic == "All PICs" else df[df[pic_field] == selected_pic]

  total_wis = len(pic_df)
  closed_wis = 0
  if status_col and not pic_df.empty:
    closed_wis = len(
        pic_df[
            pic_df[status_col]
            .astype(str)
            .str.upper()
            .str.strip()
            .isin(["CLOSED", "COMPLETED", "DONE"])
        ]
    )

  kpi_pct = (closed_wis / total_wis * 100) if total_wis > 0 else 0

  c1, c2, c3 = st.columns(3)
  c1.metric(f"Total Work Instructions ({selected_pic})", total_wis)
  c2.metric("Closed / Completed", closed_wis)
  c3.metric("Completion KPI", f"{kpi_pct:.1f}%")

  if total_wis > 0 and status_col:
    fig = px.pie(
        pic_df,
        names=status_col,
        color=status_col,
        color_discrete_map=COLOR_MAP,
        title=f"Work Order Status Breakdown ({selected_pic})",
        hole=0.4,
    )
    st.plotly_chart(fig, use_container_width=True)

  st.dataframe(
      pic_df[display_cols] if not pic_df.empty else pic_df,
      use_container_width=True,
  )
  download_excel(
      pic_df, f"KPI_{selected_pic}.xlsx", f"📥 Export {selected_pic} Data"
  )
