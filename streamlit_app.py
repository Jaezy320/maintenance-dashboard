import pandas as pd
import re

def build_location_pic_map():
    """
    Maps levels, blocks, and departments from 'senarai tempat' 
    to their designated PIC based on Hospital Shah Alam duty roster.
    """
    return {
        # --- MAIN BLOCK BY LEVEL ---
        "ARAS 1": "AMIR & SHARY", "LEVEL 1": "AMIR & SHARY", "LOBBY": "AMIR & SHARY", "KAUNTER": "AMIR & SHARY",
        "ARAS 2": "FAIZUL", "LEVEL 2": "FAIZUL", "PENYELIDIKAN": "FAIZUL",
        "ARAS 3": "IMRAN", "LEVEL 3": "IMRAN", "KECEMASAN": "IMRAN", "RADIOLOGI": "IMRAN", "MOW": "IMRAN", "MDW": "IMRAN",
        "ARAS 4": "MASLIZA", "LEVEL 4": "MASLIZA", "MOT": "MASLIZA", "PAC": "MASLIZA", "NICU": "MASLIZA", "CCU": "MASLIZA",
        "ARAS 5": "SHAKIR", "LEVEL 5": "SHAKIR", "ICU": "SHAKIR", "DAYCARE": "SHAKIR", "RAWATAN HARIAN": "SHAKIR",
        "ARAS 6": "FARHAN", "LEVEL 6": "FARHAN", "HDW": "FARHAN", "DEWAN BEDAH": "FARHAN", "GOT": "FARHAN",
        "ARAS 7": "FARHAN", "LEVEL 7": "FARHAN", "CSSD": "FARHAN", "RHU": "FARHAN",
        "ARAS 8": "MASLIZA", "LEVEL 8": "MASLIZA", "O&G": "MASLIZA", "BERSALIN": "MASLIZA", "LDU": "MASLIZA",
        "ARAS 9": "AZIZI", "LEVEL 9": "AZIZI", "WAD PEMBEDAHAN": "AZIZI",
        "ARAS 10": "SHARY", "LEVEL 10": "SHARY", "ISOLASI": "SHARY",
        "ARAS 11": "AZIZI", "LEVEL 11": "AZIZI", "ORTOPEDIK": "AZIZI",
        "ARAS 12": "FAIZUL", "LEVEL 12": "FAIZUL", "PEDIATRIK": "FAIZUL", "PATOLOGI": "FAIZUL",
        "ARAS 13": "SHAKIR", "LEVEL 13": "SHAKIR", "VIP": "SHAKIR", "EKSEKUTIF": "SHAKIR",
        "ARAS 14": "SYAZWAN", "LEVEL 14": "SYAZWAN",

        # --- OUTSIDE MAIN BLOCK & SPECIALIST CLINICS ---
        "BLOK PAKAR": "FAIZ", "KLINIK PAKAR": "FAIZ", "SPECIALIST CLINIC": "FAIZ", "OFTALMOLOGI": "FAIZ", "PERGIGIAN": "FAIZ",
        "KUARTERS": "SHAKIR", "ASRAMA": "SHAKIR", "HOUSEMAN": "SHAKIR",
        "AWSB": "AZIZI", "PLANT ROOM": "AZIZI", "EXTERNAL": "AZIZI",
        
        # --- NON-CLINICAL DEPARTMENTS ---
        "REKOD": "NAZRAN", "PERPUSTAKAAN": "NAZRAN", "DIETETIK": "NAZRAN", "SAJIAN": "NAZRAN", "LOGISTIK": "NAZRAN"
    }

def auto_assign_pic_enhanced(row, df_tempat, location_col, problem_col, system_col, existing_pic_col):
    """
    Cross-references Work Order details against 'senarai tempat' locations 
    and equipment keywords to determine the assigned PIC.
    """
    # 1. Preserve explicitly existing PIC entries
    if existing_pic_col and pd.notna(row.get(existing_pic_col)) and str(row.get(existing_pic_col)).strip() != "":
        return str(row.get(existing_pic_col)).strip().upper()

    combined_text = f"{row.get(location_col, '')} {row.get(problem_col, '')} {row.get(system_col, '')}".upper()

    # 2. System / Specialized Equipment Priority Rules
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

    # 3. Match against 'senarai tempat' Master Location Map
    location_map = build_location_pic_map()
    
    # Direct match with location dictionary keys
    for keyword, pic in location_map.items():
        if keyword in combined_text:
            return pic

    # 4. Fallback lookup by matching against values directly inside 'df_tempat'
    if not df_tempat.empty:
        for col in df_tempat.columns:
            for location_val in df_tempat[col].dropna().astype(str).unique():
                clean_val = location_val.strip().upper()
                if len(clean_val) > 3 and clean_val in combined_text:
                    # Resolve PIC via location dictionary match
                    for loc_key, pic in location_map.items():
                        if loc_key in clean_val:
                            return pic

    return "UNASSIGNED"
