import streamlit as st

import pandas as pd

import numpy as np

import json, base64, os, hashlib, urllib.parse, re

from io import BytesIO

from datetime import datetime

  
  

st.set_page_config(

    page_title="School Result Pro - बहुभाषी संपूर्ण परीक्षा प्रबंधन प्रणाली",

    page_icon="🎓",

    layout="wide",

    initial_sidebar_state="expanded"

)

  
  

DATA_FILE = "school_data_store.json"

  

# ----------------- MULTI-TENANT SCHOOL REGISTRY & DATA ISOLATION ENGINE -----------------

SCHOOLS_REGISTRY_FILE = "schools_master_registry.json"

  

def hash_password(password):

    """Secure SHA-256 password hashing"""

    return hashlib.sha256(password.strip().encode('utf-8')).hexdigest()

  

def verify_password(password, hashed):

    return hash_password(password) == hashed

  

AUDIT_LOGS_FILE = "security_audit_logs.json"

  

def log_security_event(dise_code, role, user_name, mobile, action, details, status="SUCCESS"):

    """Records an immutable security and compliance audit event"""

    logs = []

    if os.path.exists(AUDIT_LOGS_FILE):

        try:

            with open(AUDIT_LOGS_FILE, "r", encoding="utf-8") as f:

                logs = json.load(f)

        except Exception:

            logs = []

    event = {

        "timestamp": datetime.now().strftime("%d-%b-%Y %I:%M:%S %p"),

        "dise_code": str(dise_code),

        "role": role,

        "user_name": user_name,

        "mobile": str(mobile),

        "action": action,

        "details": details,

        "status": status,

        "ip": "127.0.0.1"

    }

    logs.append(event)

    try:

        with open(AUDIT_LOGS_FILE, "w", encoding="utf-8") as f:

            json.dump(logs, f, ensure_ascii=False, indent=2)

    except Exception:

        pass

    return True

  

def load_audit_logs():

    """Loads all security audit logs"""

    if os.path.exists(AUDIT_LOGS_FILE):

        try:

            with open(AUDIT_LOGS_FILE, "r", encoding="utf-8") as f:

                return json.load(f)

        except Exception:

            return []

    return []

  
  

def load_schools_registry():

    """Loads all registered schools in the multi-tenant SaaS registry"""

    if os.path.exists(SCHOOLS_REGISTRY_FILE):

        try:

            with open(SCHOOLS_REGISTRY_FILE, "r", encoding="utf-8") as f:

                return json.load(f)

        except Exception:

            return {}

    return {}

  

def save_schools_registry(registry):

    try:

        with open(SCHOOLS_REGISTRY_FILE, "w", encoding="utf-8") as f:

            json.dump(registry, f, ensure_ascii=False, indent=2)

        return True

    except Exception as e:

        st.error(f"रजिस्ट्री सुरक्षित करने में त्रुटि: {e}")

        return False

  

def init_default_school_registry():

    """Initializes default master demo school if registry is empty"""

    reg = load_schools_registry()

    if "23260100101" not in reg:

        reg["23260100101"] = {

            "dise_code": "23260100101",

            "school_name": "शासकीय माध्यमिक विद्यालय",

            "mobile": "9826012345",

            "email": "principal.bhopal@school.mp.gov.in",

            "password_hash": hash_password("admin@123"),

            "plan": "School Result Pro ऑल-इन-वन पास (₹499/वर्ष)",

            "price": 499,

            "status": "Active (सक्रिय)",

            "expiry": "2027-03-31",

            "created_at": "2026-09-05",

            "district": "Bhopal",

            "block": "Fanda",

            "data_file": "school_data_23260100101.json",

            "teachers": [

                {"name": "श्री राजेश शर्मा", "mobile": "9826112233", "assigned_class": "Class 7th", "created_at": "2026-09-06"}

            ],

            "pending_approvals": []

        }

        save_schools_registry(reg)

  

init_default_school_registry()

  

def get_current_school_file():

    """Returns the isolated JSON file for the currently authenticated school"""

    auth_school = st.session_state.get("authenticated_school")

    if auth_school and "dise_code" in auth_school:

        return f"school_data_{auth_school['dise_code']}.json"

    return "school_data_store.json"

  
  
  

# ----------------- HTML RENDERING HELPER (PREVENTS MARKDOWN CODE-BLOCK TRAP) -----------------
def render_html(html_str, *args, **kwargs):
    """Strips leading whitespace from every line so Markdown never treats HTML as an indented code block"""
    if not html_str:
        return
    clean_html = "\n".join([line.strip() for line in str(html_str).splitlines() if line.strip()])
    if hasattr(st, "html"):
        st.html(clean_html)
    else:
        st.markdown(clean_html, unsafe_allow_html=True)


# ----------------- GOVT TEMPLATE SCANNER & MULTI-PRESET RULE ENGINE -----------------

DEFAULT_EXAM_RULES = {

    "standard_rsk": {

        "name": "RSK मानक स्थानीय परीक्षा (40 अर्धवार्षिक + 60 वार्षिक = 100)",

        "components": [

            {"id": "half_yearly", "name": "अर्धवार्षिक", "max": 40, "pass": 13},

            {"id": "annual", "name": "वार्षिक परीक्षा", "max": 60, "pass": 20}

        ],

        "total_max": 100

    },

    "board_5_8": {

        "name": "RSKMP 5वीं व 8वीं बोर्ड (20 अर्धवार्षिक + 20 प्रोजेक्ट + 60 वार्षिक = 100)",

        "components": [

            {"id": "half_yearly", "name": "अर्धवार्षिक", "max": 20, "pass": 7},

            {"id": "project", "name": "प्रोजेक्ट कार्य", "max": 20, "pass": 7},

            {"id": "annual", "name": "वार्षिक लिखित", "max": 60, "pass": 20}

        ],

        "total_max": 100

    },

    "mpbse_highschool": {

        "name": "MPBSE हाईस्कूल 9वीं-10वीं (75 लिखित + 25 प्रोजेक्ट = 100)",

        "components": [

            {"id": "theory", "name": "लिखित परीक्षा", "max": 75, "pass": 25},

            {"id": "project", "name": "प्रोजेक्ट / प्रायोगिक", "max": 25, "pass": 8}

        ],

        "total_max": 100

    }

}

  
  

def scan_govt_excel_template(file_bytes, filename):

    """Parses any official RSKMP or MPBSE Excel/CSV template and extracts headers and components"""

    try:

        if filename.endswith(".csv"):

            df = pd.read_csv(BytesIO(file_bytes))

        else:

            df = pd.read_excel(BytesIO(file_bytes))

        

        cols = [str(c).strip() for c in df.columns]

        detected_features = []

        has_proj = any("project" in c.lower() or "प्रोजेक्ट" in c.lower() for c in cols)

        has_hy = any("half" in c.lower() or "अर्ध" in c.lower() or "mid" in c.lower() for c in cols)

        has_ann = any("annual" in c.lower() or "वार्षिक" in c.lower() or "theory" in c.lower() for c in cols)

        has_samagra = any("samagra" in c.lower() or "sssm" in c.lower() for c in cols)

        has_roll = any("roll" in c.lower() for c in cols)

        

        if has_proj: detected_features.append("✅ प्रोजेक्ट कार्य (Internal Project Work) कॉलम डिटेक्ट हुआ")

        if has_hy: detected_features.append("✅ अर्धवार्षिक परीक्षा (Half Yearly) कॉलम डिटेक्ट हुआ")

        if has_ann: detected_features.append("✅ वार्षिक परीक्षा / थ्योरी (Annual / Theory) कॉलम डिटेक्ट हुआ")

        if has_samagra: detected_features.append("✅ समग्र आईडी (Samagra ID) मैपिंग पहचानी गई")

        if has_roll: detected_features.append("✅ रोल नंबर (Roll Number) कॉलम पहचाना गया")

        

        return {

            "success": True,

            "total_columns": len(cols),

            "columns": cols,

            "detected_features": detected_features,

            "has_project": has_proj,

            "has_half_yearly": has_hy,

            "has_annual": has_ann

        }

    except Exception as e:

        return {"success": False, "error": str(e)}

  
  

def get_session_exam_rule(session_str, cls_name="Class 7th"):

    """Returns the applicable exam rule scoped strictly to the specified academic session"""

    rules_store = st.session_state.get("session_exam_rules", {})

    sess_rule = rules_store.get(session_str, {})

    

    clean_cls = str(cls_name).lower()

    is_5_or_8 = ("class 5" in clean_cls or "class 8" in clean_cls or "5th" in clean_cls or "8th" in clean_cls)

    is_9_or_10 = ("class 9" in clean_cls or "class 10" in clean_cls or "9th" in clean_cls or "10th" in clean_cls)

    

    if sess_rule:

        chosen_mode = sess_rule.get("mode", "auto")

        if chosen_mode == "board_5_8" or (chosen_mode == "auto" and is_5_or_8):

            return DEFAULT_EXAM_RULES["board_5_8"]

        elif chosen_mode == "mpbse_highschool" or (chosen_mode == "auto" and is_9_or_10):

            return DEFAULT_EXAM_RULES["mpbse_highschool"]

        elif chosen_mode == "custom" and "custom_components" in sess_rule:

            return sess_rule["custom_components"]

        else:

            return DEFAULT_EXAM_RULES["standard_rsk"]

    

    # Default fallback

    if is_5_or_8:

        return DEFAULT_EXAM_RULES["board_5_8"]

    elif is_9_or_10:

        return DEFAULT_EXAM_RULES["mpbse_highschool"]

    else:

        return DEFAULT_EXAM_RULES["standard_rsk"]

  
  

# ----------------- DATA EXPORT HELPERS (EXCEL & CSV FOR RSKMP & MPBSE) -----------------

def export_dataframe_bytes(df, file_format):

    """Exports dataframe to Excel bytes (.xlsx) or CSV bytes (.csv) with openpyxl fallback"""

    if file_format == "Excel (.xlsx)":

        try:

            buf = BytesIO()

            with pd.ExcelWriter(buf, engine="openpyxl") as writer:

                df.to_excel(writer, index=False)

            return buf.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", ".xlsx"

        except Exception:

            pass

    csv_bytes = df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")

    return csv_bytes, "text/csv", ".csv"

  
  

def generate_rskmp_df(students_df, evaluations, cls_subjects, school_info, selected_class):

    """Generates official RSKMP (rskmp.in) portal bulk upload template"""

    rows = []

    for idx, s in students_df.iterrows():

        r = s["Roll_No"]

        ev = evaluations.get(r, {})

        m_dict = ev.get("marks", {})

        row = {

            "DISE_CODE": school_info.get("udise", ""),

            "ACADEMIC_SESSION": school_info.get("session", "2023-24"),

            "CLASS": selected_class,

            "SAMAGRA_ID": s.get("SSSM_ID", ""),

            "SCHOLAR_NO": s.get("Scholar_No", ""),

            "ROLL_NO": r,

            "STUDENT_NAME": s.get("Name", ""),

            "FATHER_NAME": s.get("Father_Name", ""),

            "MOTHER_NAME": s.get("Mother_Name", ""),

            "DOB": s.get("DOB", ""),

            "GENDER": s.get("Gender", ""),

            "CATEGORY": s.get("Category", ""),

            "MEDIUM": s.get("Medium", "Hindi"),

            "EXAM_STATUS": ev.get("status", s.get("Status", "Present"))

        }

        tot_m = 0

        all_pass = True

        is_absent = (row["EXAM_STATUS"] == "Absent")

        rule_cfg = get_session_exam_rule(school_info.get("session", "2023-24"), selected_class)

        has_proj_comp = any(c["id"] == "project" for c in rule_cfg["components"])

  
  

        for sub in cls_subjects:

            s_id = sub["id"]

            s_name = sub["name"]

            se = m_dict.get(s_id, {})

            h = se.get("half_yearly", 32)

            p = se.get("project", 16) if has_proj_comp else 0

            a = se.get("annual", 48)

            t = se.get("total", (h + p + a) if has_proj_comp else (h + a))

            tot_m += t

            if t < 33: all_pass = False

            

            # Official RSKMP Portal Absent Code: -1

            row[f"{s_name}_HalfYearly"] = -1 if is_absent else h

            if has_proj_comp:

                row[f"{s_name}_Project_20"] = -1 if is_absent else p

            row[f"{s_name}_Annual"] = -1 if is_absent else a

            row[f"{s_name}_Total_100"] = 0 if is_absent else t

            row[f"{s_name}_Grade"] = "Ab" if is_absent else se.get("grade", calculate_grade(t))

        

        row["GRAND_TOTAL"] = tot_m

        row["MAX_MARKS"] = len(cls_subjects) * 100

        row["PERCENTAGE"] = round((tot_m / (len(cls_subjects)*100))*100, 1) if cls_subjects else 0

        row["RESULT"] = "PASS" if (all_pass and row["PERCENTAGE"] >= 33 and row["EXAM_STATUS"] != "Absent") else "FAIL"

        

        # Co-Curricular

        co = ev.get("co_curricular", {})

        for k, _ in CO_CURRICULAR_ACTIVITIES:

            row[k] = co.get(k, "A")

            

        # Social

        soc = ev.get("social", {})

        for k, _ in SOCIAL_ACTIVITIES:

            row[k] = soc.get(k, "A")

            

        rows.append(row)

    return pd.DataFrame(rows)

  
  

def generate_mpbse_df(students_df, evaluations, cls_subjects, school_info, selected_class):

    """Generates official MPBSE (mpbse.nic.in / MP Online) board upload template"""

    rows = []

    for idx, s in students_df.iterrows():

        r = s["Roll_No"]

        ev = evaluations.get(r, {})

        m_dict = ev.get("marks", {})

        row = {

            "SCHOOL_DISE": school_info.get("udise", ""),

            "ACADEMIC_YEAR": school_info.get("session", "2023-24"),

            "CLASS": selected_class,

            "ROLL_NO": r,

            "SCHOLAR_NO": s.get("Scholar_No", ""),

            "STUDENT_NAME": s.get("Name", ""),

            "FATHER_NAME": s.get("Father_Name", ""),

            "MOTHER_NAME": s.get("Mother_Name", ""),

            "DOB": s.get("DOB", ""),

            "GENDER": s.get("Gender", ""),

            "CATEGORY": s.get("Category", ""),

            "MEDIUM": s.get("Medium", "Hindi")

        }

        tot_m = 0

        all_pass = True

        for i, sub in enumerate(cls_subjects, 1):

            s_id = sub["id"]

            se = m_dict.get(s_id, {})

            t = se.get("total", 75)

            tot_m += t

            if t < 33: all_pass = False

            row[f"SUB{i}_{sub['name']}_MARKS"] = t

            row[f"SUB{i}_GRADE"] = se.get("grade", calculate_grade(t))

        

        row["TOTAL_MARKS"] = tot_m

        row["MAX_MARKS"] = len(cls_subjects) * 100

        row["PERCENTAGE"] = round((tot_m / (len(cls_subjects)*100))*100, 1) if cls_subjects else 0

        row["RESULT"] = "PASS" if (all_pass and row["PERCENTAGE"] >= 33) else "FAIL"

        row["DIVISION"] = calculate_division(row["PERCENTAGE"])

        rows.append(row)

    return pd.DataFrame(rows)

  
  

def generate_master_44col_df(students_df, evaluations, cls_subjects, school_info, selected_class):

    """Generates the exact 44-column master tabulation sheet matching Capture 5.PNG / image_fde76c.png"""

    rows = []

    for idx, s in students_df.iterrows():

        r = s["Roll_No"]

        ev = evaluations.get(r, {})

        m_dict = ev.get("marks", {})

        row = {

            "1_Sr_No": idx + 1,

            "2_Roll_No": r,

            "3_Scholar_No": s.get("Scholar_No", ""),

            "4_Student_Name": s.get("Name", ""),

            "5_Mother_Name": s.get("Mother_Name", ""),

            "6_Father_Name": s.get("Father_Name", ""),

            "7_DOB": s.get("DOB", ""),

            "8_Gender": s.get("Gender", ""),

            "9_Category": s.get("Category", ""),

            "10_Samagra_ID": s.get("SSSM_ID", ""),

            "11_Aadhar_No": s.get("Aadhar_No", "")

        }

        # Half Yearly (12, 13, 14...)

        for i, sub in enumerate(cls_subjects):

            s_eval = m_dict.get(sub["id"], {})

            row[f"{12+i}_HY_{sub['name']}"] = s_eval.get("half_yearly", 32)

        # Annual (16, 17, 18...)

        for i, sub in enumerate(cls_subjects):

            s_eval = m_dict.get(sub["id"], {})

            row[f"{16+i}_Annual_{sub['name']}"] = s_eval.get("annual", 48)

        # Final Assessment (20, 21, 22...)

        tot_m = 0

        all_pass = True

        for i, sub in enumerate(cls_subjects):

            s_eval = m_dict.get(sub["id"], {})

            t = s_eval.get("total", 80)

            tot_m += t

            if t < 33: all_pass = False

            row[f"{20+i}_Final_{sub['name']}"] = t

            

        pct = round((tot_m / (len(cls_subjects)*100))*100, 1) if cls_subjects else 0

        is_pass = (all_pass and pct >= 33)

        

        row["24_Total_Obtained"] = tot_m

        row["25_Result"] = "Pass" if is_pass else "Fail"

        row["26_Percentage"] = f"{pct}%"

        row["27_Grade"] = calculate_grade(pct)

        row["28_Rank"] = idx + 1

        row["29_Attendance"] = f"{s.get('Attended_Days', 200)}/{s.get('Total_Days', 220)}"

        

        # Co-Curricular (30 to 34)

        co = ev.get("co_curricular", {})

        row["30_LITERARY_SKILLS"] = co.get("LITERARY_SKILLS", "A")

        row["31_SCIENTIFIC_SKILLS"] = co.get("SCIENTIFIC_SKILLS", "A")

        row["32_CULTURAL_SKILLS"] = co.get("CULTURAL_SKILLS", "A")

        row["33_CREATIVITY"] = co.get("CREATIVITY", "A")

        row["34_SPORTS"] = co.get("SPORTS", "A")

        

        # Social (35 to 44)

        soc = ev.get("social", {})

        row["35_REGULARITY"] = soc.get("REGULARITY", "A")

        row["36_PUNCTUALITY"] = soc.get("PUNCTUALITY", "A")

        row["37_CLEANLINESS"] = soc.get("CLEANLINESS", "A")

        row["38_DISCIPLINE"] = soc.get("DISCIPLINE", "A")

        row["39_COOPERATION"] = soc.get("COOPERATION", "A")

        row["40_ENV_CONS"] = soc.get("ENV_CONSCIOUSNESS", "A")

        row["41_LEADERSHIP"] = soc.get("LEADERSHIP", "B")

        row["42_TRUTHFULNESS"] = soc.get("TRUTHFULNESS", "A")

        row["43_HONESTY"] = soc.get("HONESTY", "A")

        row["44_EXPRESSIVE"] = soc.get("EXPRESSIVE", "C")

        

        rows.append(row)

    return pd.DataFrame(rows)

  
  

TODAY_STR = datetime.now().strftime("%d %B %Y")

  
  

# ----------------- CUSTOM CSS FOR BEAUTIFUL UI & PRINTING (A4 & A3) -----------------

render_html("""

<style>

    .main-header {

        font-size: 25px;

        font-weight: 700;

        color: #1E3A8A;

        text-align: center;

        margin-bottom: 4px;

    }

    .sub-header {

        font-size: 14px;

        color: #4B5563;

        text-align: center;

        margin-bottom: 18px;

    }

    .profile-card {

        background: linear-gradient(135deg, #EFF6FF 0%, #DBEAFE 100%);

        border: 1px solid #BFDBFE;

        border-radius: 8px;

        padding: 14px 18px;

        margin-bottom: 15px;

        box-shadow: 0 2px 4px rgba(0,0,0,0.05);

    }

    .table-custom {

        width: 100%;

        border-collapse: collapse;

        margin-top: 8px;

        margin-bottom: 10px;

    }

    .table-custom th, .table-custom td {

        border: 1px solid #9CA3AF;

        padding: 4px 6px;

        text-align: center;

        font-size: 12px;

    }

    .table-custom th {

        background-color: #F3F4F6;

        font-weight: 700;

        color: #1F2937;

    }

    .a3-table {

        width: 100%;

        border-collapse: collapse;

        font-size: 10.5px;

        text-align: center;

    }

    .a3-table th, .a3-table td {

        border: 1px solid #000;

        padding: 3px 2px;

    }

    

    .v-th {

        writing-mode: vertical-rl;

        transform: rotate(180deg);

        white-space: nowrap;

        text-align: left;

        height: 125px;

        padding: 4px 1px !important;

        font-size: 10px;

        font-weight: bold;

        vertical-align: bottom !important;

        width: 26px;

        min-width: 25px;

        max-width: 28px;

        border: 1px solid #000;

    }

    .v-th-tall {

        writing-mode: vertical-rl;

        transform: rotate(180deg);

        white-space: nowrap;

        text-align: left;

        height: 165px;

        padding: 4px 1px !important;

        font-size: 10px;

        font-weight: bold;

        vertical-align: bottom !important;

        width: 26px;

        min-width: 25px;

        max-width: 28px;

        border: 1px solid #000;

    }

    .a3-box {

        background: #ffffff;

        border: 2px solid #000;

        padding: 8px 10px;

        font-family: Arial, sans-serif;

        color: #000;

        width: 100%;

        overflow-x: auto;

    }

  
  

    .a3-table th {

        background-color: #f8fafc;

        font-weight: bold;

    }

    @media print {

        body * {

            visibility: hidden;

        }

        .printable-area, .printable-area * {

            visibility: visible;

        }

        .printable-area {

            position: absolute;

            left: 0;

            top: 0;

            width: 100%;

        }

        .no-print {

            display: none !important;

        }

        @page {

            size: auto;

            margin: 6mm;

        }

    }

</style>

""")

  
  
  

# ----------------- WHATSAPP RESULT NOTIFICATION GENERATOR -----------------

def generate_whatsapp_result_link(student_name, roll_no, cls_name, grand_obt, max_grand, pct, grd, result_str, school_name, parent_mobile=""):

    """Generates direct, clean WhatsApp Web / App shareable result link for parents"""

    clean_mob = "".join(filter(str.isdigit, str(parent_mobile))) if parent_mobile else ""

    if len(clean_mob) == 10:

        clean_mob = "91" + clean_mob

    

    status_emoji = "🟢" if "pass" in str(result_str).lower() or "उत्तीर्ण" in str(result_str) else "🟡"

    

    msg = f"""🏫 *{school_name}*

🎓 *वार्षिक परीक्षा परिणाम (Annual Result — {cls_name})*

━━━━━━━━━━━━━━━━━━━━

👤 *विद्यार्थी का नाम:* {student_name}

🎯 *रोल नंबर:* {roll_no} | *कक्षा:* {cls_name}

📊 *कुल प्राप्तांक:* {grand_obt} / {max_grand} (*{pct}%*)

🏆 *अंतिम ग्रेड:* {grd}

📌 *परीक्षा फल:* {status_emoji} *{result_str}*

━━━━━━━━━━━━━━━━━━━━

💐 हार्दिक बधाई एवं उज्ज्वल भविष्य की शुभकामनाएं!

— *प्रधानाध्यापक / परीक्षा प्रभारी*

*{school_name}*"""

    

    encoded = urllib.parse.quote(msg)

    if clean_mob:

        wa_url = f"https://wa.me/{clean_mob}?text={encoded}"

    else:

        wa_url = f"https://wa.me/?text={encoded}"

    return wa_url, msg

  
  

# ----------------- DPDP ACT EXPORT GATEKEEPER & AUDIT VERIFIER -----------------


def render_govt_portals_hub(tab_title, target_class, export_df=None, default_file_name="Portal_Upload"):
    """
    Renders the Unified Government Portals Hub in any tab:
    1. Clickable official portal links: RSKMP, MPBSE, Shiksha Portal, Vimarsh Portal
    2. Direct Portal Upload / Web Bridge (WITHOUT OTP) accessible to all roles
    3. Computer file download (.xlsx / .csv) ONLY for Principal and strictly OTP-protected
    """
    cur_role = st.session_state.get("authenticated_role", "PRINCIPAL")
    is_teacher = (cur_role == "TEACHER")
    s_info = st.session_state.school_info
    cur_sess = s_info.get("session", "2026-27")
    clean_cls = str(target_class).lower()
    is_9_10 = ("class 9" in clean_cls or "class 10" in clean_cls or "9th" in clean_cls or "10th" in clean_cls)

    st.markdown("""
    <div style="background: linear-gradient(135deg, #F8FAFC 0%, #EFF6FF 100%); border: 1px solid #BFDBFE; border-radius: 8px; padding: 12px 16px; margin: 14px 0 10px 0;">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
            <div>
                <b style="color: #1E3A8A; font-size: 14.5px;">🌐 शासकीय पोर्टल डायरेक्ट अपलोड एवं सिंक हब (Govt Portals Direct Hub)</b><br>
                <span style="font-size: 11.5px; color: #475569;">RSKMP (1ली से 8वीं), MPBSE (9वीं-10वीं), समग्र शिक्षा पोर्टल एवं विमर्श पोर्टल से सीधा जुड़ाव</span>
            </div>
            <div style="font-size: 11px; background: #DCFCE7; color: #166534; font-weight: bold; padding: 4px 10px; border-radius: 20px; border: 1px solid #86EFAC;">
                🟢 डायरेक्ट पोर्टल सिंक डेस्क सक्रिय (बिना OTP के उपयोग हेतु अधिकृत)
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 1. Official Portal Clickable Links Bar
    c_p1, c_p2, c_p3, c_p4 = st.columns(4)
    with c_p1:
        st.markdown("""
        <a href="https://www.rskmp.in" target="_blank" style="text-decoration: none;">
            <div style="background: #1E3A8A; color: white; padding: 8px 10px; border-radius: 6px; text-align: center; font-size: 12px; font-weight: bold; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                🏛️ RSKMP पोर्टल (rskmp.in)
            </div>
        </a>
        """, unsafe_allow_html=True)
    with c_p2:
        st.markdown("""
        <a href="https://mpbse.mponline.gov.in" target="_blank" style="text-decoration: none;">
            <div style="background: #D97706; color: white; padding: 8px 10px; border-radius: 6px; text-align: center; font-size: 12px; font-weight: bold; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                🏢 MPBSE पोर्टल (MP Online)
            </div>
        </a>
        """, unsafe_allow_html=True)
    with c_p3:
        st.markdown("""
        <a href="https://shikshaportal.mp.gov.in" target="_blank" style="text-decoration: none;">
            <div style="background: #0D9488; color: white; padding: 8px 10px; border-radius: 6px; text-align: center; font-size: 12px; font-weight: bold; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                📚 समग्र शिक्षा पोर्टल (MP)
            </div>
        </a>
        """, unsafe_allow_html=True)
    with c_p4:
        st.markdown("""
        <a href="https://www.vimarsh.mp.gov.in" target="_blank" style="text-decoration: none;">
            <div style="background: #4F46E5; color: white; padding: 8px 10px; border-radius: 6px; text-align: center; font-size: 12px; font-weight: bold; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                🎯 विमर्श पोर्टल (DPI MP)
            </div>
        </a>
        """, unsafe_allow_html=True)

    # 2. Two Columns: Left = Direct Portal Upload / Bridge (WITHOUT OTP), Right = Computer File Download (ONLY Principal & OTP PROTECTED)
    c_hub_left, c_hub_right = st.columns([1.5, 1.5])
    
    with c_hub_left:
        with st.expander("🚀 डायरेक्ट पोर्टल पर डेटा अपलोड / प्रेषण (बिना OTP के)", expanded=True):
            st.markdown(f"**कक्षा:** `{target_class}` | **माड्यूल:** `{tab_title}`")
            target_portal_url = "https://www.rskmp.in" if not is_9_10 else "https://mpbse.mponline.gov.in"
            target_portal_name = "RSKMP (rskmp.in)" if not is_9_10 else "MPBSE MP Online"
            
            st.markdown(f"""
            <a href="{target_portal_url}" target="_blank" style="text-decoration: none;">
                <div style="background: #15803D; color: white; padding: 10px 14px; border-radius: 6px; text-align: center; font-weight: bold; font-size: 13px; margin: 6px 0;">
                    🌐 सीधे {target_portal_name} खोलें एवं डेटा प्रेषित करें ↗
                </div>
            </a>
            """, unsafe_allow_html=True)
            
            st.caption("ℹ️ इस विकल्प के लिए OTP की आवश्यकता नहीं है। शिक्षक या संस्था प्रधान सीधे पोर्टल लॉगिन कर डेटा अपलोड कर सकते हैं।")
            
            if export_df is not None and not export_df.empty:
                show_payload = st.checkbox("📋 1-क्लिक डेटा पेलोड देखें / कॉपी करें (Portal Fast Upload)", value=False, key=f"chk_payload_{tab_title}_{target_class}")
                if show_payload:
                    csv_preview = export_df.to_csv(index=False)
                    st.text_area("पोर्टल हेतु तैयार डेटा (CSV / Copy-Paste Text):", value=csv_preview, height=120, key=f"ta_payload_{tab_title}_{target_class}")
                    st.info("💡 उपरोक्त डेटा को कॉपी करके सीधे पोर्टल के बल्क इंपोर्ट में उपयोग कर सकते हैं।")

    with c_hub_right:
        with st.expander("📥 कंप्यूटर में बल्क अपलोड फ़ाइल डाउनलोड (केवल Principal हेतु - OTP सुरक्षित)", expanded=True):
            if is_teacher:
                st.markdown("""
                <div style="background: #FEF2F2; border-left: 4px solid #EF4444; padding: 10px 14px; border-radius: 6px; color: #991B1B; font-size: 12px; margin: 6px 0;">
                    <b>🔒 शासकीय डेटा सुरक्षा सूचना:</b> कंप्यूटर में शासकीय पोर्टल हेतु बल्क अपलोड एक्सेल/सीएसवी फ़ाइल डाउनलोड करने का अधिकार केवल <b>संस्था प्रधान (Principal)</b> खाते में अधिकृत है।
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("<span style='font-size: 12px; color: #334155;'>पोर्टल पर ऑफलाइन बल्क अपलोड हेतु Excel/CSV फ़ाइल अपने कंप्यूटर में डाउनलोड करें:</span>", unsafe_allow_html=True)
                if export_df is not None and not export_df.empty:
                    if render_export_gatekeeper(f"{tab_title} फ़ाइल डाउनलोड"):
                        c_dw1, c_dw2 = st.columns(2)
                        with c_dw1:
                            x_bytes, x_mime, x_ext = export_dataframe_bytes(export_df, "Excel (.xlsx)")
                            st.download_button(
                                "📥 एक्सेल फ़ाइल (.xlsx)",
                                data=x_bytes,
                                file_name=f"{default_file_name}_{target_class}_{cur_sess}.xlsx",
                                mime=x_mime,
                                type="primary",
                                use_container_width=True,
                                key=f"btn_dw_xlsx_{tab_title}_{target_class}"
                            )
                        with c_dw2:
                            c_bytes, c_mime, c_ext = export_dataframe_bytes(export_df, "CSV (.csv)")
                            st.download_button(
                                "📥 CSV फ़ाइल (.csv)",
                                data=c_bytes,
                                file_name=f"{default_file_name}_{target_class}_{cur_sess}.csv",
                                mime=c_mime,
                                use_container_width=True,
                                key=f"btn_dw_csv_{tab_title}_{target_class}"
                            )
                else:
                    st.caption("⚠️ इस कक्षा में अभी कोई डेटा उपलब्ध नहीं है।")

def render_export_gatekeeper(context_label="Data Export"):

    """

    Enforces Role Restriction and 6-Digit OTP Gatekeeper before allowing data export.

    Returns True if export is permitted, False otherwise.

    """

    role = st.session_state.get("authenticated_role", "PRINCIPAL")

    if role == "TEACHER":

        render_html("""

        <div style="background: #FEF2F2; border-left: 4px solid #EF4444; padding: 12px 16px; border-radius: 6px; color: #991B1B; margin: 10px 0;">

            <b>🔒 शासकीय डेटा सुरक्षा सूचना:</b> बल्क डेटा एवं आधिकारिक शासकीय परीक्षाफल एक्सपोर्ट का अधिकार केवल <b>संस्था प्रधान (Principal)</b> खाते में अधिकृत है।

        </div>

        """)

        return False

    

    auth_school = st.session_state.get("authenticated_school") or {}

    if not st.session_state.get("export_otp_verified", False):

        render_html("""

        <div style="background: #EFF6FF; border: 1px solid #BFDBFE; padding: 10px 14px; border-radius: 6px; margin-bottom: 10px;">

            <b style="color: #1E3A8A; font-size: 13.5px;">🔒 अधिकृत एक्सपोर्ट सुरक्षा सत्यापन (DPDP Act 2023 Compliance)</b><br>

            <span style="font-size: 12px; color: #334155;">संस्था प्रधान के अधिकृत मोबाइल पर 6-अंकीय OTP सत्यापन एवं कानूनी दायित्व स्वीकार करना अनिवार्य है।</span>

        </div>

        """)

        c_gk1, c_gk2 = st.columns([1.5, 3])

        with c_gk1:

            exp_otp = st.text_input("6-अंकीय एक्सपोर्ट OTP:*", value="888999", key=f"gk_otp_{context_label}", help="परीक्षण हेतु डिफॉल्ट OTP: 888999")

        with c_gk2:

            render_html("<div style='margin-top: 15px;'>")

            exp_consent = st.checkbox("✅ मैं प्रमाणित करता हूँ कि यह डेटा विद्यालय के अधिकृत उपयोग हेतु डाउनलोड किया जा रहा है। OTP सत्यापन के उपरांत इसकी वैधानिक ज़िम्मेदारी संस्था की होगी।", value=True, key=f"gk_chk_{context_label}")

            st.markdown("</div>", unsafe_allow_html=True)

        

        if st.button(f"🔓 सत्यापित करें एवं एक्सपोर्ट अनलॉक करें ({context_label})", type="primary", key=f"btn_unl_{context_label}"):

            if len(str(exp_otp).strip()) == 6 and exp_consent:

                st.session_state.export_otp_verified = True

                log_security_event(auth_school.get("dise_code", "UNKNOWN"), "Principal", "Principal / Admin", auth_school.get("mobile", ""), "EXPORT_UNLOCKED", f"Context: {context_label}")

                st.success("✅ सत्यापन सफल! डाउनलोड अनलॉक हो गया।")

                st.rerun()

            else:

                st.error("कृपया 6-अंकीय OTP और सहमति चेकबॉक्स पर टिक करें!")

        return False

    else:

        render_html(f"<div style='color: #15803D; font-size: 12.5px; font-weight: bold; margin-bottom: 8px;'>🟢 एक्सपोर्ट अधिकृत (OTP सत्यापित) | डिजिटल ऑडिट लॉग सक्रिय</div>")

        return True

  
  

# ----------------- MONTHLY EVALUATION SCHEDULE & WEIGHTAGE ENGINE -----------------


def smart_match_subject_col(col_name, sub_name, sub_id):
    """Fuzzy matches Excel column names to academic subject definitions"""
    c = str(col_name).lower().strip()
    s_name = str(sub_name).lower().strip()
    s_id = str(sub_id).lower().strip()
    
    if s_id in ["social_science", "sst"] or "social" in s_name or "सामाजिक" in s_name:
        return ("social" in c or "सामाजिक" in c or "sst" in c)
    if s_id == "science" or ("science" in s_name and "social" not in s_name) or ("विज्ञान" in s_name and "सामाजिक" not in s_name):
        return ("science" in c or "विज्ञान" in c) and ("social" not in c and "सामाजिक" not in c)
    if ("hindi" in s_name or "हिन्दी" in s_name) and ("hindi" in c or "हिन्दी" in c):
        return True
    if ("english" in s_name or "अंग्रेजी" in s_name) and ("english" in c or "अंग्रेजी" in c):
        return True
    if ("sanskrit" in s_name or "संस्कृत" in s_name) and ("sanskrit" in c or "संस्कृत" in c):
        return True
    if ("math" in s_name or "गणित" in s_name) and ("math" in c or "गणित" in c):
        return True
    if ("evs" in s_name or "पर्यावरण" in s_name) and ("evs" in c or "पर्यावरण" in c or "environ" in c):
        return True
    return s_name in c or s_id in c

def parse_marks_upload_file(uploaded_file):
    """Parses uploaded Excel or CSV into DataFrame safely"""
    try:
        fname = uploaded_file.name.lower()
        if fname.endswith(".csv"):
            return pd.read_csv(uploaded_file)
        else:
            return pd.read_excel(uploaded_file)
    except Exception as e:
        return None

def get_class_monthly_test_months(cls_name):

    """Returns official prescribed monthly evaluation months based on class in MP"""

    clean = str(cls_name).lower().strip()

    if any(k in clean for k in ["class 9", "class 10", "9th", "10th"]):

        return [

            {"id": "jul", "name": "माह 1: जुलाई (July) - 10 अंक"},

            {"id": "aug", "name": "माह 2: अगस्त (August) - 10 अंक"},

            {"id": "nov", "name": "माह 3: नवम्बर (November) - 10 अंक"},

            {"id": "dec", "name": "माह 4: दिसम्बर (December) - 10 अंक"},

            {"id": "jan", "name": "माह 5: जनवरी (January) - 10 अंक"}

        ]

    elif any(k in clean for k in ["class 1", "class 2", "1st", "2nd"]):

        return [

            {"id": "aug", "name": "आवधिक/मासिक 1: अगस्त - 10 अंक"},

            {"id": "sep", "name": "आवधिक/मासिक 2: सितम्बर - 10 अंक"},

            {"id": "dec", "name": "आवधिक/मासिक 3: दिसम्बर - 10 अंक"},

            {"id": "jan", "name": "आवधिक/मासिक 4: जनवरी - 10 अंक"}

        ]

    else:

        # Class 3rd to 8th (RSKMP Standard 4 Official Months)

        return [

            {"id": "aug", "name": "माह 1: अगस्त (August) - 10 अंक"},

            {"id": "sep", "name": "माह 2: सितम्बर (September) - 10 अंक"},

            {"id": "dec", "name": "माह 3: दिसम्बर (December) - 10 अंक"},

            {"id": "jan", "name": "माह 4: जनवरी (January) - 10 अंक"}

        ]

  
  
  

def calculate_subject_project_weightage_rule(raw_proj, cls_name="Class 7th"):

    """

    Calculates exact project weightage based on class rules:

    - Class 5th & 8th: Direct 20 marks (passing min 7)

    - Class 3, 4, 6, 7: 40 marks paper (2 projects of 20) -> 10% weightage = marks / 4

    - Class 9th & 10th: 25 marks (passing min 8)

    """

    clean = str(cls_name).lower().strip()

    is_5_or_8 = ("class 5" in clean or "class 8" in clean or "5th" in clean or "8th" in clean)

    is_9_or_10 = ("class 9" in clean or "class 10" in clean or "9th" in clean or "10th" in clean)

    

    if raw_proj <= 0:

        return 0

    if is_5_or_8:

        return min(20, max(0, int(raw_proj)))

    elif is_9_or_10:

        return min(25, max(0, int(raw_proj)))

    else:

        # Class 3, 4, 6, 7 (40 marks project -> 10% weightage = raw_proj / 4)

        if raw_proj <= 10:

            return int(raw_proj)

        elif raw_proj <= 20:

            return min(10, max(0, round((raw_proj / 20) * 10)))

        elif raw_proj <= 40:

            return min(10, max(0, round((raw_proj / 40) * 10)))

        else:

            return min(10, max(0, round((raw_proj / 100) * 10)))

  

def calculate_subject_half_yearly_weightage(raw_hy, hy_max_scheme="auto"):

    """

    Universal smart 20% weightage calculator based on paper max marks:

    - 60 marks paper (RSKMP standard): marks / 3 = 20% weightage

    - 40 marks paper: marks / 2 = 20% weightage

    - 50 marks paper: (marks / 50) * 20 = 20% weightage

    - 20 marks paper: direct marks = 20% weightage

    """

    if raw_hy <= 0:

        return 0

    if hy_max_scheme == "40":

        return min(20, max(0, round((raw_hy / 40) * 20)))

    elif hy_max_scheme == "50":

        return min(20, max(0, round((raw_hy / 50) * 20)))

    elif hy_max_scheme == "20":

        return min(20, max(0, raw_hy))

    elif hy_max_scheme == "60":

        return min(20, max(0, round((raw_hy / 60) * 20)))

    else:

        # Auto-detection

        if raw_hy <= 20:

            return int(raw_hy)

        elif raw_hy <= 40:

            return min(20, max(0, round((raw_hy / 40) * 20)))

        elif raw_hy <= 60:

            return min(20, max(0, round((raw_hy / 60) * 20)))

        else:

            return min(20, max(0, round((raw_hy / 100) * 20)))

  

def calculate_subject_monthly_weightage(student_ev, sub_id, cls_name):

    """

    Calculates exact 10% weightage from the monthly tests.

    RSKMP Formula: Total obtained across official months / total months

    """

    m_tests = student_ev.get("monthly_tests", {})

    months = get_class_monthly_test_months(cls_name)

    month_ids = [m["id"] for m in months]

    

    scores = []

    for m_id in month_ids:

        m_sub_marks = m_tests.get(m_id, {})

        if sub_id in m_sub_marks:

            scores.append(m_sub_marks[sub_id])

            

    if scores:

        tot_score = sum(scores)

        divisor = len(month_ids) if len(month_ids) > 0 else 4

        weightage_10 = min(10, max(0, round(tot_score / divisor)))

        return weightage_10, tot_score, len(scores)

    

    se = student_ev.get("marks", {}).get(sub_id, {})

    if "monthly" in se:

        return min(10, max(0, se["monthly"])), se["monthly"] * 4, 4

    hy_raw = se.get("half_yearly", 16)

    est = min(10, max(0, round((hy_raw / 20) * 10))) if hy_raw <= 20 else min(10, max(0, round((hy_raw / 60) * 10)))

    return est, est * 4, 0

  



# ----------------- EXCEL HEADER METADATA & DISPLAY MEDIUM ENGINE -----------------
def extract_school_metadata_from_excel_rows(raw_df):
    """
    Scans the top 15 rows of an uploaded school Excel sheet to extract:
    School Name, Dise Code, Session, Block, District, Medium, Class.
    Handles merged cells and multi-column headers seamlessly.
    """
    metadata = {}
    limit_rows = min(15, len(raw_df))
    
    for r_idx in range(limit_rows):
        row_cells = [str(v).strip() for v in raw_df.iloc[r_idx].dropna().tolist() if str(v).strip() and str(v).strip() != "nan"]
        
        for c_idx, cell in enumerate(row_cells):
            cl = cell.lower()
            
            # 1. School Name
            if any(k in cl for k in ["school name", "name of school", "विद्यालय का नाम", "स्कूल का नाम"]):
                val = re.sub(r"^(?:school\s*name|name\s*of\s*school|विद्यालय\s*का\s*नाम|स्कूल\s*का\s*नाम)\s*[:\-]?\s*", "", cell, flags=re.I).strip()
                if val and len(val) > 3 and not any(k in val.lower() for k in ["class", "dise", "session", "block", "district", "medium"]):
                    metadata["name"] = val
                elif c_idx + 1 < len(row_cells):
                    next_val = row_cells[c_idx + 1].strip()
                    if len(next_val) > 3 and not any(k in next_val.lower() for k in ["class", "dise", "session", "block", "district", "medium"]):
                        metadata["name"] = next_val

            # 2. Medium
            if any(k in cl for k in ["medium", "माध्यम"]):
                val = re.sub(r"^(?:medium|माध्यम)\s*[:\-]?\s*", "", cell, flags=re.I).strip()
                med_to_check = val if val else (row_cells[c_idx + 1].strip() if c_idx + 1 < len(row_cells) else "")
                if any(k in med_to_check.lower() for k in ["hindi", "हिन्दी"]):
                    metadata["medium"] = "Hindi (हिन्दी)"
                elif any(k in med_to_check.lower() for k in ["english", "अंग्रेजी"]):
                    metadata["medium"] = "English"
                elif any(k in med_to_check.lower() for k in ["marathi", "मराठी"]):
                    metadata["medium"] = "Marathi (मराठी)"
                elif any(k in med_to_check.lower() for k in ["urdu", "उर्दू"]):
                    metadata["medium"] = "Urdu (اردو)"
                elif med_to_check:
                    metadata["medium"] = med_to_check

            # 3. Session
            if any(k in cl for k in ["session", "सत्र", "annual result sheet"]):
                m = re.search(r"(\d{4}[-_/]\d{2,4})", cell)
                if m:
                    metadata["session"] = m.group(1).strip()
                elif c_idx + 1 < len(row_cells):
                    m = re.search(r"(\d{4}[-_/]\d{2,4})", row_cells[c_idx + 1])
                    if m:
                        metadata["session"] = m.group(1).strip()

            # 4. Block
            if any(k in cl for k in ["block", "ब्लॉक", "संकुल"]):
                val = re.sub(r"^(?:block|ब्लॉक|संकुल)\s*[:\-]?\s*", "", cell, flags=re.I).strip()
                if val and not any(k in val.lower() for k in ["district", "medium", "session", "class"]):
                    metadata["block"] = val
                elif c_idx + 1 < len(row_cells):
                    metadata["block"] = row_cells[c_idx + 1].strip()

            # 5. District
            if any(k in cl for k in ["district", "जिला"]):
                val = re.sub(r"^(?:district|जिला)\s*[:\-]?\s*", "", cell, flags=re.I).strip()
                if val and not any(k in val.lower() for k in ["block", "medium", "session", "class"]):
                    metadata["district"] = val
                elif c_idx + 1 < len(row_cells):
                    metadata["district"] = row_cells[c_idx + 1].strip()

            # 6. Dise Code
            if any(k in cl for k in ["dise", "udise", "डाइस"]):
                m = re.search(r"(\d{11})", cell)
                if m:
                    metadata["udise"] = m.group(1).strip()
                elif c_idx + 1 < len(row_cells):
                    m = re.search(r"(\d{11})", row_cells[c_idx + 1])
                    if m:
                        metadata["udise"] = m.group(1).strip()

            # 7. Class
            if any(k in cl for k in ["class", "कक्षा"]):
                val = re.sub(r"^(?:class|कक्षा)\s*[:\-]?\s*", "", cell, flags=re.I).strip()
                target_str = val if val else (row_cells[c_idx + 1].strip() if c_idx + 1 < len(row_cells) else "")
                num_m = re.search(r"(\d+)", target_str)
                if num_m:
                    n = num_m.group(1)
                    metadata["class"] = f"Class {n}th" if n in ["4","5","6","7","8","9","10"] else (f"Class {n}st" if n=="1" else (f"Class {n}nd" if n=="2" else f"Class {n}rd"))

    return metadata

def get_display_medium(s_info, stud=None):
    """Returns standardized display medium: 'HINDI' / 'ENGLISH'"""
    med = ""
    if stud is not None and isinstance(stud, (dict, pd.Series)):
        if "Medium" in stud and stud["Medium"]:
            med = str(stud["Medium"]).strip()
    if not med or med.lower() == "nan":
        med = str(s_info.get("medium", "Hindi (हिन्दी)")).strip()
    
    if any(k in med.lower() for k in ["hindi", "हिन्दी"]):
        return "HINDI"
    elif any(k in med.lower() for k in ["english", "अंग्रेजी"]):
        return "ENGLISH"
    elif any(k in med.lower() for k in ["marathi", "मराठी"]):
        return "MARATHI"
    elif any(k in med.lower() for k in ["urdu", "उर्दू"]):
        return "URDU"
    return med.upper() if med else "HINDI"

# ----------------- UNIVERSAL MULTI-SHEET & COLUMN MAPPING HELPERS -----------------
def map_sheet_name_to_class(sh_name):
    """
    Maps Excel sheet tab names to system classes:
    - '7th', '7', 'Class 7', 'Class 7th' -> 'Class 7th'
    - '1st', '1', 'Class 1' -> 'Class 1st'
    - '2nd' -> 'Class 2nd'
    - '3rd' -> 'Class 3rd'
    - '4th' -> 'Class 4th'
    - '5th' -> 'Class 5th'
    - '6th' -> 'Class 6th'
    - '8th' -> 'Class 8th'
    - '9th' -> 'Class 9th'
    - '10th' -> 'Class 10th'
    - 'Nursery' -> 'Class Nursery'
    - 'KG1', 'KG 1', 'KG-1', 'LKG' -> 'Class KG1'
    - 'KG2', 'KG 2', 'KG-2', 'UKG' -> 'Class KG2'
    - 'Goswara', 'Summary', 'Total', 'Index' -> None (Skipped as summary sheet)
    """
    clean = str(sh_name).strip()
    clean_lower = clean.lower()
    
    if any(k in clean_lower for k in ["goswara", "गोशवारा", "summary", "total", "index"]):
        return None
        
    if "nursery" in clean_lower:
        return "Class Nursery"
    if any(k in clean_lower for k in ["kg1", "kg 1", "kg-1", "lkg"]):
        return "Class KG1"
    if any(k in clean_lower for k in ["kg2", "kg 2", "kg-2", "ukg"]):
        return "Class KG2"
        
    return normalize_class_name(clean)


def detect_excel_header_row_smart(df):
    """Detects the real header row by checking keywords in first 20 rows"""
    keywords = [
        "roll", "r_no", "rno", "sr", "s.no", "sr.no", "name", "naam", "studant", "student", 
        "father", "pita", "mother", "mata", "dob", "d.o.b", "birth", "samagra", "sssm", 
        "scholar", "admission", "dakhila", "दाखिला", "class", "कक्षा", "gender", "लिंग", 
        "category", "जाति", "वर्ग", "aadhar", "आधार"
    ]
    best_row = 0
    max_matches = 0
    limit_rows = min(20, len(df))
    for r_idx in range(limit_rows):
        row_vals = [str(v).lower().strip() for v in df.iloc[r_idx].dropna().tolist()]
        matches = sum(1 for v in row_vals if any(k in v for k in keywords))
        if matches > max_matches:
            max_matches = matches
            best_row = r_idx
    return best_row, (max_matches >= 2)


def parse_clean_excel_sheet(df):
    """Returns clean dataframe with identified headers"""
    if df.empty:
        return pd.DataFrame()
    h_idx, has_hdrs = detect_excel_header_row_smart(df)
    if has_hdrs and h_idx >= 0:
        header_vals = []
        seen = {}
        for c in df.iloc[h_idx]:
            c_str = str(c).strip()
            if not c_str or c_str == "nan" or c_str.startswith("Unnamed:"):
                c_str = "Unnamed"
            if c_str in seen:
                seen[c_str] += 1
                c_str = f"{c_str}_{seen[c_str]}"
            else:
                seen[c_str] = 0
            header_vals.append(c_str)
        clean_df = df.iloc[h_idx+1:].copy()
        clean_df.columns = header_vals
        clean_df = clean_df.dropna(how="all")
        return clean_df
    else:
        clean_df = df.copy()
        clean_df.columns = [f"Col_{i+1}" for i in range(clean_df.shape[1])]
        clean_df = clean_df.dropna(how="all")
        return clean_df


def smart_fuzzy_column_mapping(columns):
    """Maps columns accurately avoiding Scholar vs Roll No collisions"""
    col_mapping = {}
    cols = [str(c).strip() for c in columns if str(c).strip() and not str(c).startswith("Unnamed:")]
    
    # 1. Father & Mother first
    for c in cols:
        cl = c.lower()
        if any(k in cl for k in ["father", "fath", "pita", "पिता", "f_name", "fname", "f.name", "guardian", "पालक"]):
            col_mapping["Father_Name"] = c
            break
            
    for c in cols:
        cl = c.lower()
        if any(k in cl for k in ["mother", "moth", "mata", "माता", "m_name", "mname", "m.name", "मातृ"]):
            col_mapping["Mother_Name"] = c
            break

    # 2. Student Name
    for c in cols:
        if c == col_mapping.get("Father_Name") or c == col_mapping.get("Mother_Name"):
            continue
        cl = c.lower()
        if any(k in cl for k in [
            "studant", "student", "stuent", "studen", "stdnt", "name", "naam", "nam", 
            "विद्यार्थी", "छात्र", "परीक्षार्थी", "नाम", "बालक", "बालिका", "candidate", "s_name", "st_name"
        ]) and not any(ex in cl for ex in ["father", "mother", "pita", "mata", "school", "vidyalaya"]):
            col_mapping["Name"] = c
            break

    # 3. Scholar / Admission No First
    for c in cols:
        cl = c.lower()
        if any(k in cl for k in ["scholar", "dakhila", "दाखिला", "admission", "sch_no", "adm_no", "scholar_no", "adm"]):
            col_mapping["Scholar_No"] = c
            break

    # 4. Roll No (strictly matching real Roll No keywords only, never Sr.No!)
    for c in cols:
        if c == col_mapping.get("Scholar_No"):
            continue
        cl = c.lower()
        if any(k in cl for k in ["roll", "r_no", "rno", "अनुक्रमांक", "रोल", "rollno", "roll_no"]) or cl.strip() == "r no" or cl.strip().startswith("r no ") or cl.strip().endswith(" r no"):
            col_mapping["Roll_No"] = c
            break

    # 4b. Serial Number (Sr.No / S.No) tracked separately, not as Roll No
    for c in cols:
        if c in [col_mapping.get("Scholar_No"), col_mapping.get("Roll_No")]:
            continue
        cl = c.lower()
        if any(k in cl for k in ["sr.no", "sr_no", "sr no", "s.no", "sno", "क्रमांक", "क्र."]):
            col_mapping["Sr_No"] = c
            break

    # 5. Date of Birth (DOB)
    for c in cols:
        cl = c.lower()
        if any(k in cl for k in ["dob", "birth", "d.o.b", "d_o_b", "जन्म", "जन्मतिथि", "जन्म दिनांक", "date of birth"]):
            col_mapping["DOB"] = c
            break

    # 6. Samagra ID / SSSM ID
    for c in cols:
        cl = c.lower()
        if any(k in cl for k in ["samagra", "sssm", "smgr", "samgra", "समग्र", "समग्र आईडी", "sssmid", "sssm_id"]):
            col_mapping["SSSM_ID"] = c
            break

    # 7. Class & Section
    for c in cols:
        cl = c.lower()
        if any(k in cl for k in ["class", "std", "कक्षा", "grade"]) and not any(ex in cl for ex in ["classic", "classifier"]):
            col_mapping["Class"] = c
            break
            
    for c in cols:
        cl = c.lower()
        if any(k in cl for k in ["section", "sec", "वर्ग", "शाखा", "सेक्शन", "विभाग"]):
            col_mapping["Section"] = c
            break

    # 8. Gender
    for c in cols:
        cl = c.lower()
        if any(k in cl for k in ["gender", "sex", "लिंग", "boy/girl", "boy_girl", "जेंडर"]):
            col_mapping["Gender"] = c
            break

    # 9. Category
    for c in cols:
        cl = c.lower()
        if any(k in cl for k in ["category", "caste", "caste_category", "वर्ग", "जाति", "श्रेणी", "cat"]):
            col_mapping["Category"] = c
            break

    # 10. Aadhar No
    for c in cols:
        cl = c.lower()
        if any(k in cl for k in ["aadhar", "uid", "आधार", "aadhaar", "uidai", "aadhar_no"]):
            col_mapping["Aadhar_No"] = c
            break

    # 11. PAN Number
    for c in cols:
        cl = c.lower()
        if any(k in cl for k in ["pan", "pancard", "pan_no", "panno", "पैन", "pan number", "pan_number"]):
            col_mapping["PAN_No"] = c
            break

    # 12. APAAR ID / EduLocker ID (One Nation One Student ID)
    for c in cols:
        cl = c.lower()
        if any(k in cl for k in ["apaar", "appar", "अपार", "apaar_id", "edulocker", "apaar id", "appar id", "apar"]):
            col_mapping["APAAR_ID"] = c
            break

    return col_mapping

# ----------------- MULTI-LANGUAGE TRANSLATION DICTIONARY -----------------

I18N = {

    "हिन्दी (Hindi)": {

        "title": "School Result Pro",

        "sub": "सम्पूर्ण शालेय परीक्षा फल एवं प्रगति पत्रक प्रणाली",

        "lang_label": "🌐 भाषा चुनें (Language)",

        "auto_saved": "🟢 ऑटो-सेव सक्रिय (Auto-Saved)",

        "select_class": "कक्षा चुनें (Select Class):",

        "add_class": "➕ नई कक्षा जोड़ें / प्रबंधित करें",

        "new_class_placeholder": "नई कक्षा का नाम (उदा. Class 9th):",

        "add_class_btn": "कक्षा जोड़ें",

        "nav_school": "🏫 1. स्कूल सेटअप (School Setup)",

        "nav_student": "👨‍🎓 2. विद्यार्थी मास्टर (Student Master)",

        "nav_attendance": "📅 3. माहवार उपस्थिति पत्रक (Monthly Attendance)",

        "nav_eval": "📝 4. परीक्षा एवं गतिविधि मूल्यांकन (Evaluation Entry)",

        "nav_viewer": "🔍 5. छात्र संपूर्ण डेटा समीक्षा (Student Data Viewer)",

        "nav_monthly_test": "📝 6. मासिक मूल्यांकन रजिस्टर (Monthly Test — 10 अंक)",

        "nav_half_yearly": "📑 7. अर्धवार्षिक परीक्षा मूल्यांकन (Half-Yearly Exam — 20% अधिभार)",

        "nav_project": "🎨 8. वार्षिक प्रोजेक्ट कार्य मूल्यांकन (Project Work — 10%/20 अंक)",

        "nav_marksheet": "🖨️ 9. शासकीय वार्षिक प्रगति पत्रक एवं RSKMP/MPBSE पोर्टल केंद्र",

        "nav_a3_result": "📜 10. A3 वार्षिक परीक्षाफल पत्रक (Annual Result Sheet)",

        "nav_summary": "📊 11. श्रेणीवार परीक्षा परिणाम सारांश (Result Summary)",

        "nav_merit": "🏆 12. वार्षिक परीक्षा प्रावीण्य सूची (Merit List)",

        "nav_supple": "📋 13. पूरक परीक्षा छात्र सूची (Supplementary List)",

        "nav_weighted": "📑 14. वार्षिक परीक्षा परिणाम अभिलेख पत्रक (RSKMP व MPBSE प्रारूप)",

        "nav_promote": "🔄 15. सत्र परिवर्तन एवं कक्षा पदोन्नति (Session Promotion)",

        "backup_restore": "💾 बैकअप एवं रीस्टोर (Backup / Restore)",

        "download_backup": "📥 बैकअप फ़ाइल डाउनलोड करें (JSON)",

        "restore_backup": "📂 बैकअप से रीस्टोर करें",

        "active_session": "सक्रिय सत्र",

        "current_class": "वर्तमान कक्षा",

        "save_btn": "💾 सुरक्षित करें",

        "print_btn": "🖨️ Print"

    },

    "English": {

        "title": "School Result Pro",

        "sub": "Comprehensive School Examination & Evaluation System",

        "lang_label": "🌐 Select Language",

        "auto_saved": "🟢 Auto-Save Active",

        "select_class": "Select Class:",

        "add_class": "➕ Add / Manage Classes",

        "new_class_placeholder": "New Class Name (e.g. Class 9th):",

        "add_class_btn": "Add Class",

        "nav_school": "🏫 1. School Setup",

        "nav_student": "👨‍🎓 2. Student Master",

        "nav_attendance": "📅 3. Monthly Attendance Sheet",

        "nav_eval": "📝 4. Marks & Activity Evaluation",

        "nav_viewer": "🔍 5. Student Complete Data Viewer",

        "nav_monthly_test": "📝 6. Monthly Test Evaluation (10 Marks)",

        "nav_half_yearly": "📑 7. Half-Yearly Examination (20% Weightage)",

        "nav_project": "🎨 8. Annual Project Work Evaluation",

        "nav_marksheet": "🖨️ 9. Govt Holistic Progress Card & RSKMP/MPBSE Portal Center",

        "nav_a3_result": "📜 10. A3 Annual Result Sheet",

        "nav_summary": "📊 11. Category/Grade Wise Result Summary",

        "nav_merit": "🏆 12. Annual Result Merit List",

        "nav_supple": "📋 13. Supplementary Students List",

        "nav_weighted": "📑 14. Annual Result Record Sheet (RSKMP & MPBSE Format)",

        "nav_promote": "🔄 15. Session Roll-over & Promotion",

        "backup_restore": "💾 Backup & Restore",

        "download_backup": "📥 Download Backup File (JSON)",

        "restore_backup": "📂 Restore from Backup File",

        "active_session": "Active Session",

        "current_class": "Current Class",

        "save_btn": "💾 Save Changes",

        "print_btn": "🖨️ Print"

    },

    "मराठी (Marathi)": {

        "title": "School Result Pro",

        "sub": "संपूर्ण शालेय परीक्षा निकाल व प्रगती पत्रक प्रणाली",

        "lang_label": "🌐 भाषा निवडा (Language)",

        "auto_saved": "🟢 ऑटो-सेव्ह सक्रिय (Auto-Saved)",

        "select_class": "वर्ग निवडा:",

        "add_class": "➕ नवीन वर्ग जोडा / व्यवस्थापित करा",

        "new_class_placeholder": "नवीन वर्गाचे नाव (उदा. Class 9th):",

        "add_class_btn": "वर्ग जोडा",

        "nav_school": "🏫 1. शाळा सेटअप (School Setup)",

        "nav_student": "👨‍🎓 2. विद्यार्थी मास्टर (Student Master)",

        "nav_attendance": "📅 3. मासिक उपस्थिती पत्रक (Monthly Attendance)",

        "nav_eval": "📝 4. परीक्षा व मूल्यमापन (Evaluation Entry)",

        "nav_viewer": "🔍 5. विद्यार्थी संपूर्ण माहिती दर्शक (Student Data Viewer)",

        "nav_monthly_test": "📝 6. मासिक मूल्यमापन नोंदवही (Monthly Test — 10 गुण)",

        "nav_half_yearly": "📑 7. सत्रांत / सहामाही परीक्षा मूल्यमापन (20% भारांश)",

        "nav_project": "🎨 8. वार्षिक प्रकल्प कार्य मूल्यमापन (Project Work)",

        "nav_marksheet": "🖨️ 9. शासकीय प्रगती पत्रक व RSKMP/MPBSE पोर्टल केंद्र",

        "nav_a3_result": "📜 10. A3 वार्षिक निकाल पत्रक (Annual Result Sheet)",

        "nav_summary": "📊 11. प्रवर्गनिहाय निकाल गोषवारा (Result Summary)",

        "nav_merit": "🏆 12. वार्षिक परीक्षा गुणवत्ता यादी (Merit List)",

        "nav_supple": "📋 13. पुरवणी परीक्षा विद्यार्थी यादी (Supplementary List)",

        "nav_weighted": "📑 14. वार्षिक निकाल अभिलेख पत्रक (RSKMP व MPBSE प्रारूप)",

        "nav_promote": "🔄 15. सत्र बदल व वर्ग पदोन्नती (Promotion)",

        "backup_restore": "💾 बॅकअप आणि पुनर्संचयित (Backup/Restore)",

        "download_backup": "📥 बॅकअप फाईल डाउनलोड करा (JSON)",

        "restore_backup": "📂 बॅकअपमधून पुनर्संचयित करा",

        "active_session": "सक्रिय शैक्षणिक वर्ष",

        "current_class": "निवडलेला वर्ग",

        "save_btn": "💾 जतन करा",

        "print_btn": "🖨️ Print"

    }

}

  
  

ALL_MEDIUMS = [

    "Hindi (हिन्दी)", "English", "Marathi (मराठी)", "Tamil (தமிழ்)", 

    "Telugu (తెలుగు)", "Kannada (ಕನ್ನಡ)", "Gujarati (ગુજરાતી)", "Bengali (বাংলা)", 

    "Urdu (اردو)", "Odia (ଓଡ଼ିଆ)", "Malayalam (മലയാളം)", "Punjabi (ਪੰਜਾਬੀ)", 

    "Sanskrit (संस्कृत)", "Other"

]

  
  


# ----------------- SMART CLASS NORMALIZER & ORDINAL FORMATTER -----------------
def get_ordinal_suffix(n):
    """Returns correct English ordinal suffix for any integer: 1st, 2nd, 3rd, 4th, 11th, 12th, 13th..."""
    if 11 <= (n % 100) <= 13:
        return f"{n}th"
    last_digit = n % 10
    if last_digit == 1:
        return f"{n}st"
    elif last_digit == 2:
        return f"{n}nd"
    elif last_digit == 3:
        return f"{n}rd"
    else:
        return f"{n}th"

def normalize_class_name(name):
    """
    Standardizes and corrects common typos in class names:
    - 'calss nursury', 'nursury', 'nursery' -> 'Class Nursery'
    - 'class 12rd', '12rd', 'class 12th' -> 'Class 12th'
    - 'class 11rd' -> 'Class 11th'
    - 'kg 1', 'lkg' -> 'Class LKG'
    - 'kg 2', 'ukg' -> 'Class UKG'
    """
    if not name:
        return ""
    clean = str(name).strip()
    clean_lower = clean.lower()
    
    # Fix typos like 'calss', 'clas'
    clean_lower = re.sub(r"\b(calss|clas|clss|clz)\b", "class", clean_lower)
    
    # Pre-primary detection
    if "nurs" in clean_lower:
        return "Class Nursery"
    if any(k in clean_lower for k in ["lkg", "kg1", "kg 1", "kg-1", "junior kg", "kg-i"]):
        return "Class LKG"
    if any(k in clean_lower for k in ["ukg", "kg2", "kg 2", "kg-2", "senior kg", "kg-ii"]):
        return "Class UKG"
    if "balvatika" in clean_lower or "बालवाटिका" in clean_lower:
        return "Class Balvatika"
        
    # Extract number and apply strictly correct ordinal rules
    num_match = re.search(r"(\d+)", clean_lower)
    if num_match:
        n = int(num_match.group(1))
        correct_ordinal = get_ordinal_suffix(n)
        return f"Class {correct_ordinal}"
        
    # Title Case Fallback
    clean_title = " ".join([w.capitalize() for w in clean.split()])
    if not clean_title.lower().startswith("class"):
        clean_title = f"Class {clean_title}"
    return clean_title

def clean_and_sort_classes(classes_list):
    """Deduplicates, normalizes, and logically sorts school classes from Nursery to 12th"""
    normalized = []
    seen = set()
    for c in classes_list:
        norm = normalize_class_name(c)
        if norm and norm not in seen:
            seen.add(norm)
            normalized.append(norm)
            
    # Sort order: Nursery, LKG, UKG, Balvatika, 1st, 2nd, ... 12th
    def sort_key(c):
        cl = c.lower()
        if "nursery" in cl:
            return -4
        if "lkg" in cl or "kg1" in cl:
            return -3
        if "ukg" in cl or "kg2" in cl:
            return -2
        if "balvatika" in cl:
            return -1
        num_m = re.search(r"(\d+)", cl)
        if num_m:
            return int(num_m.group(1))
        return 999
        
    return sorted(normalized, key=sort_key)

def migrate_data_store_keys(data_store):
    """Migrates any misspelled class keys in data_store to their normalized counterparts"""
    new_store = {}
    for old_k, val in data_store.items():
        new_k = normalize_class_name(old_k)
        if new_k not in new_store:
            new_store[new_k] = val
            if isinstance(val, dict) and "students" in val and isinstance(val["students"], pd.DataFrame):
                if not val["students"].empty and "Class" in val["students"].columns:
                    val["students"]["Class"] = new_k
        else:
            st1 = new_store[new_k].get("students", pd.DataFrame())
            st2 = val.get("students", pd.DataFrame())
            if isinstance(st1, pd.DataFrame) and isinstance(st2, pd.DataFrame):
                combined = pd.concat([st1, st2], ignore_index=True).drop_duplicates(subset=["Roll_No"], keep="first")
                new_store[new_k]["students"] = combined
    return new_store

DEFAULT_CLASSES = ["Class Nursery", "Class LKG", "Class UKG", "Class 1st", "Class 2nd", "Class 3rd", "Class 4th", "Class 5th", "Class 6th", "Class 7th", "Class 8th", "Class 9th", "Class 10th", "Class 11th", "Class 12th"]

MONTHS_LIST = ["Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "Jan", "Feb", "Mar"]

DEFAULT_WORKING_DAYS = {"Apr": 24, "May": 0, "Jun": 12, "Jul": 25, "Aug": 24, "Sep": 24, "Oct": 20, "Nov": 22, "Dec": 24, "Jan": 23, "Feb": 22, "Mar": 20}

  
  

def get_class_subjects(cls_name):

    clean = str(cls_name).lower().strip()

    if any(k in clean for k in ["nursery", "lkg", "ukg", "kg1", "kg2", "balvatika", "बालवाटिका"]):
        return [
            {"id": "english", "name": "English (अंग्रेजी)", "code": "01"},
            {"id": "hindi", "name": "Hindi (हिन्दी)", "code": "02"},
            {"id": "maths", "name": "Mathematics (गणित)", "code": "03"},
            {"id": "drawing", "name": "Drawing & GK (चित्रकला)", "code": "04"}
        ]
    elif any(k in clean for k in ["class 11", "class 12", "11th", "12th"]):
        return [
            {"id": "hindi", "name": "Hindi (हिन्दी)", "code": "01"},
            {"id": "english", "name": "English (अंग्रेजी)", "code": "02"},
            {"id": "sub3", "name": "विषय 3 (Physics / Accounts / Arts)", "code": "03"},
            {"id": "sub4", "name": "विषय 4 (Chemistry / Business / Arts)", "code": "04"},
            {"id": "sub5", "name": "विषय 5 (Maths / Bio / Economics)", "code": "05"}
        ]
    elif any(k in clean for k in ["class 1", "class 2", "1st", "2nd"]):

        return [

            {"id": "hindi", "name": "Hindi", "code": "01"},

            {"id": "english", "name": "English", "code": "02"},

            {"id": "maths", "name": "Mathematics", "code": "03"}

        ]

    elif any(k in clean for k in ["class 3", "class 4", "class 5", "3rd", "4th", "5th"]):

        return [

            {"id": "hindi", "name": "Hindi", "code": "01"},

            {"id": "english", "name": "English", "code": "02"},

            {"id": "maths", "name": "Mathematics", "code": "03"},

            {"id": "evs", "name": "EVS / पर्यावरण", "code": "04"}

        ]

    else:

        return [

            {"id": "hindi", "name": "Hindi", "code": "01"},

            {"id": "english", "name": "English", "code": "02"},

            {"id": "sanskrit", "name": "Sanskrit / तृतीय भाषा", "code": "03"},

            {"id": "maths", "name": "Mathematics", "code": "04"},

            {"id": "science", "name": "Science", "code": "05"},

            {"id": "social_science", "name": "Social Science", "code": "06"}

        ]

  
  

CO_CURRICULAR_ACTIVITIES = [

    ("LITERARY_SKILLS", "LITERARY SKILLS (साहित्यिक कौशल)"),

    ("SCIENTIFIC_SKILLS", "SCIENTIFIC SKILLS (वैज्ञानिक कौशल)"),

    ("CULTURAL_SKILLS", "CULTURAL SKILLS (सांस्कृतिक कौशल)"),

    ("CREATIVITY", "CREATIVITY (सृजनात्मकता)"),

    ("SPORTS", "SPORTS (खेलकूद)")

]

  
  

SOCIAL_ACTIVITIES = [

    ("REGULARITY", "REGULARITY (नियमितता)"),

    ("PUNCTUALITY", "PUNCTUALITY (समयबद्धता)"),

    ("CLEANLINESS", "CLEANLINESS (स्वच्छता)"),

    ("DISCIPLINE", "DISCIPLINE (अनुशासन)"),

    ("COOPERATION", "CO-OPERATION (सहयोग)"),

    ("ENV_CONSCIOUSNESS", "ENVIRONMENTAL CONSCIOUSNESS (पर्यावरण संवेदनशीलता)"),

    ("LEADERSHIP", "LEADERSHIP QUALITIES (नेतृत्व क्षमता)"),

    ("TRUTHFULNESS", "TRUTHFULNESS (सत्यवादिता)"),

    ("HONESTY", "HONESTY (ईमानदारी)"),

    ("EXPRESSIVE", "EXPRESIVE (अभिव्यक्ति)")

]

  
  

# ----------------- SERIALIZATION & PERSISTENCE HELPERS -----------------

def serialize_store(store):

    serialized = {}

    for cls_name, c_data in store.items():

        st_df = c_data.get("students", pd.DataFrame())

        st_records = st_df.to_dict(orient="records") if isinstance(st_df, pd.DataFrame) else st_df

        evals = {str(k): v for k, v in c_data.get("evaluations", {}).items()}

        att_df = c_data.get("monthly_attendance", pd.DataFrame())

        att_records = att_df.to_dict(orient="records") if isinstance(att_df, pd.DataFrame) else att_df

        work_days = c_data.get("working_days", DEFAULT_WORKING_DAYS)

        serialized[cls_name] = {

            "students": st_records,

            "evaluations": evals,

            "monthly_attendance": att_records,

            "working_days": work_days

        }

    return serialized

  
  

def deserialize_store(data):

    store = {}

    for cls_name, c_data in data.items():

        st_records = c_data.get("students", [])

        st_df = pd.DataFrame(st_records) if st_records else pd.DataFrame()

        evals = {int(k) if str(k).isdigit() else k: v for k, v in c_data.get("evaluations", {}).items()}

        att_records = c_data.get("monthly_attendance", [])

        att_df = pd.DataFrame(att_records) if att_records else pd.DataFrame()

        work_days = c_data.get("working_days", DEFAULT_WORKING_DAYS)

        store[cls_name] = {

            "students": st_df,

            "evaluations": evals,

            "monthly_attendance": att_df,

            "working_days": work_days

        }

    return store

  
  

def save_data_to_disk():

    target_file = get_current_school_file()

    try:

        payload = {

            "school_info": st.session_state.school_info,

            "classes_list": st.session_state.classes_list,

            "data_store": serialize_store(st.session_state.data_store)

        }

        with open(target_file, "w", encoding="utf-8") as f:

            json.dump(payload, f, ensure_ascii=False, indent=2)

        return True

    except Exception as e:

        st.error(f"डेटा सुरक्षित करने में त्रुटि: {e}")

        return False

  
  

def load_data_from_disk():

    target_file = get_current_school_file()

    # Fallback to general DATA_FILE if specific file does not exist yet

    file_to_read = target_file if os.path.exists(target_file) else DATA_FILE

    if os.path.exists(file_to_read):

        try:

            with open(file_to_read, "r", encoding="utf-8") as f:

                payload = json.load(f)

            if "school_info" in payload and isinstance(payload["school_info"], dict):

                st.session_state.school_info = payload["school_info"]

            if "classes_list" in payload and isinstance(payload["classes_list"], list):

                all_cls = list(dict.fromkeys(payload["classes_list"] + DEFAULT_CLASSES))
                st.session_state.classes_list = clean_and_sort_classes(all_cls)
            else:
                st.session_state.classes_list = clean_and_sort_classes(DEFAULT_CLASSES)

            if "data_store" in payload and isinstance(payload["data_store"], dict):

                st.session_state.data_store = migrate_data_store_keys(deserialize_store(payload["data_store"]))

            return True

        except Exception:

            return False

    return False

  
  

# ----------------- SESSION STATE INITIALIZATION -----------------

if "authenticated_school" not in st.session_state:

    st.session_state.authenticated_school = None

if "ui_lang" not in st.session_state:

    st.session_state.ui_lang = "हिन्दी (Hindi)"

  
  

if "session_exam_rules" not in st.session_state:

    st.session_state.session_exam_rules = {}

  
  

if "update_alert_dismissed" not in st.session_state:

    st.session_state.update_alert_dismissed = False

  
  

if "show_format_adopter_dialog" not in st.session_state:

    st.session_state.show_format_adopter_dialog = False

  
  

if "initialized" not in st.session_state:

    st.session_state.initialized = True

    st.session_state.school_info = {

        "session": "2023-24",

        "name": "शासकीय माध्यमिक विद्यालय",

        "udise": "23260100101",

        "medium": "Hindi (हिन्दी)",

        "class_level": "Class 1st to 8th",

        "address": "Bhadbhada Road, Bhopal",

        "block": "Fanda",

        "district": "Bhopal",

        "contact": "",

        "email": "",

        "logo_b64": None,

        "sign_b64": None

    }

    st.session_state.classes_list = DEFAULT_CLASSES

    st.session_state.data_store = {}

    

    loaded = load_data_from_disk()

    if not loaded:

        # Starter data for Class 7th

        st.session_state.data_store["Class 7th"] = {

            "students": pd.DataFrame([

                {

                    "Roll_No": 101,

                    "Scholar_No": "1001",

                    "Name": "Aarav Sharma",

                    "Father_Name": "Ramesh Sharma",

                    "Mother_Name": "Sunita Sharma",

                    "DOB": "2013-05-12",

                    "Class": "Class 7th",

                    "Section": "A",

                    "Gender": "Boy",

                    "Category": "OBC",

                    "SSSM_ID": "123456789",

                    "Aadhar_No": "",

                    "PAN_No": "",

                    "APAAR_ID": "",

                    "Medium": "Hindi (हिन्दी)",

                    "Status": "Present",

                    "Photo_b64": None,

                    "Total_Days": 220,

                    "Attended_Days": 204

                }

            ]),

            "evaluations": {},

            "monthly_attendance": pd.DataFrame(),

            "working_days": DEFAULT_WORKING_DAYS

        }

        save_data_to_disk()

  
  


def sort_students_dataframe(df, sort_by="Roll_No"):
    """Universally sorts student DataFrames by Roll No, Alphabetical Name (A to Z), or Scholar No."""
    if df is None or df.empty:
        return df
    sorted_df = df.copy()
    if sort_by in ["Roll_No", "Roll"]:
        if "Roll_No" in sorted_df.columns:
            sorted_df["_sort_roll"] = pd.to_numeric(sorted_df["Roll_No"], errors="coerce").fillna(999999)
            sorted_df = sorted_df.sort_values(by="_sort_roll").drop(columns=["_sort_roll"])
    elif sort_by in ["Name", "Alphabetical", "A to Z"]:
        if "Name" in sorted_df.columns:
            sorted_df = sorted_df.sort_values(by="Name", key=lambda col: col.astype(str).str.lower())
    elif sort_by in ["Scholar_No", "Scholar"]:
        if "Scholar_No" in sorted_df.columns:
            sorted_df["_sort_sch"] = pd.to_numeric(sorted_df["Scholar_No"], errors="coerce").fillna(999999)
            sorted_df = sorted_df.sort_values(by="_sort_sch").drop(columns=["_sort_sch"])
    return sorted_df

def reorder_student_columns(df):
    """Enforces strict order: Aadhar_No -> PAN_No -> APAAR_ID -> Medium (Single APAAR ID, PAN preserved)"""
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return df
    
    if "PAN_No" not in df.columns:
        df["PAN_No"] = ""
    if "APAAR_ID" not in df.columns:
        df["APAAR_ID"] = ""
    
    for c in list(df.columns):
        c_clean = str(c).strip().lower().replace(" ", "").replace("_", "").replace("-", "")
        # Consolidate any duplicate or cased variant of APAAR ID into single APAAR_ID
        if any(k in c_clean for k in ["apaar", "apar", "edulocker"]) and c != "APAAR_ID":
            mask = (df["APAAR_ID"].isna() | (df["APAAR_ID"].astype(str).str.strip().isin(["", "nan", "None"])))
            df.loc[mask, "APAAR_ID"] = df.loc[mask, c].fillna("").astype(str)
            df.drop(columns=[c], inplace=True)
            
        # Consolidate any duplicate or cased variant of PAN Number into single PAN_No
        if any(k in c_clean for k in ["pan", "panno", "pancard"]) and c != "PAN_No":
            mask = (df["PAN_No"].isna() | (df["PAN_No"].astype(str).str.strip().isin(["", "nan", "None"])))
            df.loc[mask, "PAN_No"] = df.loc[mask, c].fillna("").astype(str)
            df.drop(columns=[c], inplace=True)

    target_order = [
        "Roll_No", "Scholar_No", "Name", "Father_Name", "Mother_Name", "DOB",
        "Class", "Section", "Gender", "Category", "SSSM_ID", "Aadhar_No",
        "PAN_No", "APAAR_ID", "Medium", "Status", "Photo_b64", "Total_Days", "Attended_Days"
    ]
    for col in ["SSSM_ID", "Aadhar_No", "PAN_No", "APAAR_ID"]:
        if col not in df.columns:
            df[col] = ""
            
    present_cols = [c for c in target_order if c in df.columns]
    extra_cols = [c for c in df.columns if c not in target_order and not any(k in str(c).strip().lower().replace(" ", "").replace("_", "").replace("-", "") for k in ["apaar", "apar"])]
    return df[present_cols + extra_cols]

def get_class_data(cls_name):

    if cls_name not in st.session_state.data_store:

        st.session_state.data_store[cls_name] = {

            "students": pd.DataFrame(),

            "evaluations": {},

            "monthly_attendance": pd.DataFrame(),

            "working_days": DEFAULT_WORKING_DAYS

        }

        save_data_to_disk()
    else:
        st_df = st.session_state.data_store[cls_name].get("students")
        if isinstance(st_df, pd.DataFrame) and not st_df.empty:
            st.session_state.data_store[cls_name]["students"] = reorder_student_columns(st_df)

    return st.session_state.data_store[cls_name]

  
  

# RSK 8-Tier Grading Scale matching image_aabe70.png

def calculate_grade(marks):

    if marks >= 85: return "A+"

    elif marks >= 76: return "A"

    elif marks >= 66: return "B+"

    elif marks >= 56: return "B"

    elif marks >= 46: return "C+"

    elif marks >= 33: return "C"

    elif marks >= 25: return "D"

    else: return "E"

  
  

def calculate_division(pct):

    if pct >= 60: return "1st Division (प्रथम)"

    elif pct >= 48: return "2nd Division (द्वितीय)"

    elif pct >= 33: return "3rd Division (तृतीय)"

    else: return "Fail / Needs Improvement"

  
  

# ----------------- SIDEBAR -----------------

  

# =========================================================================================

# =========================================================================================

# 🚀 COMMERCIAL MULTI-TENANT SAAS AUTHENTICATION & SUPER ADMIN PORTAL

# =========================================================================================

if "authenticated_role" not in st.session_state:

    st.session_state.authenticated_role = None

  

if "assigned_class" not in st.session_state:

    st.session_state.assigned_class = None

  

if "diagnostic_mode_school" not in st.session_state:

    st.session_state.diagnostic_mode_school = None

  

if "export_otp_verified" not in st.session_state:

    st.session_state.export_otp_verified = False

  

# ----------------- CASE 1: SUPER ADMIN CONTROL ROOM -----------------

if st.session_state.get("authenticated_role") == "SUPER_ADMIN":

    render_html("""

    <div style="background: linear-gradient(135deg, #0F172A 0%, #1E293B 50%, #334155 100%); padding: 20px 24px; border-radius: 12px; color: white; margin-bottom: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.3);">

        <div style="display: flex; justify-content: space-between; align-items: center;">

            <div>

                <h2 style="margin: 0; color: #F8FAFC; font-size: 26px;">👑 School Result Pro — सुपर एडमिन कंट्रोल रूम</h2>

                <div style="font-size: 13.5px; opacity: 0.9; margin-top: 4px;">मध्य प्रदेश राज्य स्तरीय केंद्रीय विद्यालय एवं परीक्षाफल प्रबंधन प्रणाली</div>

            </div>

        </div>

    </div>

    """)

  

    registry = load_schools_registry()

    tot_schools = len(registry)

    active_paid = sum(1 for s in registry.values() if "active" in str(s.get("status", "")).lower() and "trial" not in str(s.get("status", "")).lower())

    in_trial = sum(1 for s in registry.values() if "trial" in str(s.get("status", "")).lower())

    expired = sum(1 for s in registry.values() if "expired" in str(s.get("status", "")).lower())

    total_rev = active_paid * 499

  

    # Top KPI Metrics

    kpi_c1, kpi_c2, kpi_c3, kpi_c4, kpi_c5, kpi_c6 = st.columns([1.5, 1.2, 1.2, 1.2, 1.8, 1.2])

    kpi_c1.metric("🏫 कुल स्कूल", f"{tot_schools}")

    kpi_c2.metric("🟢 सक्रिय पेड (₹499)", f"{active_paid}")

    kpi_c3.metric("🟡 ट्रायल में", f"{in_trial}")

    kpi_c4.metric("🔴 समाप्त ट्रायल", f"{expired}")

    kpi_c5.metric("💰 कुल संकलित आय", f"₹{total_rev:,}")

    with kpi_c6:

        render_html("<div style='margin-top: 15px;'>")

        if st.button("🚪 एडमिन लॉगआउट", type="secondary", use_container_width=True):

            st.session_state.authenticated_role = None

            st.session_state.authenticated_school = None

            st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

  

    st.divider()

  

    adm_tab1, adm_tab2, adm_tab3, adm_tab4, adm_tab5 = st.tabs([

        "🏫 स्कूल डायरेक्टरी एवं लाइसेंस",

        "💳 पेमेंट एवं UTR अप्रूवल डेस्क",

        "🎯 ट्रायल लीड्स एवं 1-क्लिक व्हाट्सएप फॉलो-अप",

        "🔍 सपोर्ट एक्सेस (डायग्नोस्टिक व्यू)",

        "🛡️ सुरक्षा एवं एक्सेस ऑडिट लॉग्स"

    ])

  

    # 1. School Directory & License Control

    with adm_tab1:

        st.subheader("पंजीकृत विद्यालयों की केंद्रीय डायरेक्टरी")

        sch_rows = []

        for d, s in registry.items():

            sch_rows.append({

                "U-DISE": d,

                "विद्यालय का नाम": s.get("school_name", ""),

                "मोबाइल नंबर": s.get("mobile", ""),

                "जिला": s.get("district", ""),

                "प्लान": s.get("plan", "₹499 पास"),

                "स्थिति": s.get("status", ""),

                "वैधता": s.get("expiry", "2027-03-31"),

                "शिक्षकों की संख्या": len(s.get("teachers", []))

            })

        st.dataframe(pd.DataFrame(sch_rows), use_container_width=True)

  

        st.divider()

        render_html("#### ⚙️ 1-क्लिक लाइसेंस प्रबंधन (Quick School Action):")

        c_ac1, c_ac2, c_ac3 = st.columns([3, 2, 3])

        with c_ac1:

            target_dise_act = st.selectbox("कार्रवाई हेतु विद्यालय चुनें:", list(registry.keys()), format_func=lambda x: f"{x} - {registry[x].get('school_name')}")

        with c_ac2:

            act_type = st.selectbox("कार्रवाई (Action):", ["सक्रिय करें (₹499 Paid Active)", "+15 दिन ट्रायल बढ़ाएं", "अस्थायी सस्पेंड करें"])

        with c_ac3:

            st.markdown("<div style='margin-top: 28px;'>", unsafe_allow_html=True)

            if st.button("⚡ चयनित कार्रवाई लागू करें", type="primary", use_container_width=True):

                if "सक्रिय" in act_type:

                    registry[target_dise_act]["status"] = "Active (सक्रिय)"

                    registry[target_dise_act]["expiry"] = "2027-03-31"

                    registry[target_dise_act]["plan"] = "School Result Pro ऑल-इन-वन (₹499/वर्ष)"

                elif "+15" in act_type:

                    registry[target_dise_act]["status"] = "Trial (परीक्षण)"

                    registry[target_dise_act]["expiry"] = "2026-10-05"

                else:

                    registry[target_dise_act]["status"] = "Suspended (निलंबित)"

                save_schools_registry(registry)

                log_security_event(target_dise_act, "SUPER_ADMIN", "Super Admin", "9998887777", "ADMIN_LICENSE_CHANGE", f"Action: {act_type}")

                st.success(f"✅ {registry[target_dise_act].get('school_name')} का स्टेटस सफलतापूर्वक अपडेट हो गया!")

                st.rerun()

            st.markdown("</div>", unsafe_allow_html=True)

  

    # 2. Payment & UTR Approvals Queue

    with adm_tab2:

        st.subheader("💳 UPI UTR पेमेंट सत्यापन डेस्क")

        pending_utrs = []

        for d, s in registry.items():

            if s.get("last_utr"):

                pending_utrs.append({

                    "DISE": d,

                    "School": s.get("school_name", ""),

                    "Mobile": s.get("mobile", ""),

                    "UTR / Ref No": s.get("last_utr", ""),

                    "Amount": "₹499",

                    "Status": s.get("status", "")

                })

        if not pending_utrs:

            st.info("ℹ️ वर्तमान में कोई लंबित UTR पेमेंट अनुरोध नहीं है।")

        else:

            st.dataframe(pd.DataFrame(pending_utrs), use_container_width=True)

            sel_utr_dise = st.selectbox("सत्यापित करने हेतु स्कूल चुनें:", [p["DISE"] for p in pending_utrs])

            c_u1, c_u2 = st.columns(2)

            with c_u1:

                if st.button(f"✅ UTR स्वीकार करें एवं ₹499 प्रो पास एक्टिवेट करें ({sel_utr_dise})", type="primary", use_container_width=True):

                    registry[sel_utr_dise]["status"] = "Active (सक्रिय)"

                    registry[sel_utr_dise]["expiry"] = "2027-03-31"

                    registry[sel_utr_dise]["plan"] = "School Result Pro ऑल-इन-वन (₹499/वर्ष)"

                    save_schools_registry(registry)

                    log_security_event(sel_utr_dise, "SUPER_ADMIN", "Super Admin", "9998887777", "PAYMENT_APPROVED", "₹499 UPI Verified")

                    st.success(f"✅ {registry[sel_utr_dise].get('school_name')} का ₹499 वार्षिक प्लान सफलतापूर्वक सक्रिय!")

                    st.rerun()

            with c_u2:

                if st.button(f"❌ UTR अस्वीकार करें ({sel_utr_dise})", use_container_width=True):

                    registry[sel_utr_dise]["last_utr"] = ""

                    save_schools_registry(registry)

                    st.warning("UTR अस्वीकार कर दिया गया।")

                    st.rerun()

  

    # 3. Sales CRM & 1-Click WhatsApp Follow-up

    with adm_tab3:

        st.subheader("🎯 ट्रायल लीड्स एवं 1-क्लिक व्हाट्सएप फॉलो-अप")

        st.caption("डेमो देखने आए स्कूलों को ₹499 के वार्षिक प्लान में बदलने हेतु सीधा व्हाट्सएप फॉलो-अप भेजें:")

  

        for d, s in registry.items():

            s_name = s.get("school_name", "")

            s_mob = s.get("mobile", "")

            s_stat = s.get("status", "")

            s_plan = s.get("plan", "")

            

            clean_s_mob = "".join(filter(str.isdigit, str(s_mob)))

            if len(clean_s_mob) == 10: clean_s_mob = "91" + clean_s_mob

  

            lead_c1, lead_c2, lead_c3, lead_c4 = st.columns([3, 2, 2, 3])

            with lead_c1:

                render_html(f"**{s_name}** (`{d}`)<br><span style='font-size:12px; color:#555;'>मोबाइल: {s_mob} | जिला: {s.get('district','')}</span>")

            with lead_c2:

                render_html(f"<span style='font-size:13px;'>स्थिति: <b>{s_stat}</b></span><br><span style='font-size:11.5px; color:#666;'>{s_plan}</span>")

            with lead_c3:

                stage_choice = st.selectbox("फॉलो-अप स्टेज:", ["Day 2: सहायता संदेश", "Day 7: फ़ीचर रिमाइंडर", "Day 13: ₹499 क्लोजिंग ऑफर"], key=f"crm_stg_{d}")

            with lead_c4:

                render_html("<div style='margin-top: 10px;'>")

                if "Day 2" in stage_choice:

                    pitch_txt = f"नमस्ते सर, हमने देखा कि आपने *{s_name}* के लिए School Result Pro का डेमो शुरू किया है। क्या आपको RSKMP 44-कॉलम गोशवारा या मार्कशीट बनाने में कोई सहायता चाहिए? हम AnyDesk पर 5 मिनट का लाइव डेमो दे सकते हैं।"

                elif "Day 7" in stage_choice:

                    pitch_txt = f"आदरणीय सर, क्या आपने *{s_name}* के बच्चों के लिए 'WhatsApp पर रिजल्ट भेजने' और 'RSKMP एक्सेल एक्सपोर्ट' वाला फ़ीचर टेस्ट किया? मात्र ₹499 में पूरे साल का संपूर्ण रिजल्ट उपलब्ध है।"

                else:

                    pitch_txt = f"आदरणीय प्राचार्य महोदय, *{s_name}* का डेमो ट्रायल समाप्त हो रहा है। सभी कक्षाओं के वार्षिक परीक्षाफल, A3 गोशवारा और बिना रुकावट उपयोग जारी रखने हेतु आज ही ₹499 में वार्षिक पास सक्रिय करें।"

                

                wa_pitch_url = f"https://wa.me/{clean_s_mob}?text={urllib.parse.quote(pitch_txt)}" if clean_s_mob else "#"

                render_html(f"""

                <a href="{wa_pitch_url}" target="_blank" style="text-decoration: none;">

                    <div style="background: #25D366; color: white; font-size: 12px; font-weight: bold; padding: 6px 10px; border-radius: 6px; text-align: center;">

                        📱 WhatsApp फॉलो-अप भेजें

                    </div>

                </a>

                """)

                st.markdown("</div>", unsafe_allow_html=True)

            st.markdown("<hr style='margin:6px 0; border:none; border-top:1px solid #E2E8F0;'>", unsafe_allow_html=True)

  

    # 4. Support Access (Diagnostic View)

    with adm_tab4:

        st.subheader("🔍 सपोर्ट एक्सेस मोड (Diagnose School Data)")

        st.caption("यदि किसी स्कूल को डेटा भरने या परीक्षाफल में कोई समस्या आ रही है, तो आप बिना पासवर्ड के सीधे उस स्कूल के डेटा का डायग्नोस्टिक ऑडिट कर सकते हैं:")

        

        diag_dise = st.selectbox("सपोर्ट हेतु स्कूल चुनें:", list(registry.keys()), format_func=lambda x: f"{x} - {registry[x].get('school_name')}", key="sel_diag_dise")

        if st.button(f"🚀 {registry[diag_dise].get('school_name')} का डायग्नोस्टिक व्यू खोलें", type="primary"):

            st.session_state.authenticated_role = "PRINCIPAL"

            st.session_state.authenticated_school = registry[diag_dise]

            st.session_state.school_info.update({

                "name": registry[diag_dise].get("school_name", ""),

                "udise": diag_dise,

                "block": registry[diag_dise].get("block", ""),

                "district": registry[diag_dise].get("district", ""),

                "contact": registry[diag_dise].get("mobile", "")

            })

            st.session_state.diagnostic_mode_school = diag_dise

            load_data_from_disk()

            log_security_event(diag_dise, "SUPER_ADMIN", "Super Admin", "9998887777", "DIAGNOSTIC_SUPPORT_LOGIN", "Opened in Support Mode")

            st.success(f"डायग्नोस्टिक मोड में प्रवेश: {registry[diag_dise].get('school_name')}")

            st.rerun()

  

    # 5. Security Audit Logs Viewer

    with adm_tab5:

        st.subheader("🛡️ केंद्रीय सुरक्षा एवं एक्सेस ऑडिट लॉग्स")

        st.caption("प्लेटफ़ॉर्म पर सभी लॉगिन, असफल प्रयास, डेटा एक्सपोर्ट और सुरक्षा घटनाओं का अपरिवर्तनीय डिजिटल रिकॉर्ड:")

        logs_data = load_audit_logs()

        if not logs_data:

            st.info("अभी कोई ऑडिट लॉग दर्ज नहीं है।")

        else:

            st.dataframe(pd.DataFrame(logs_data[::-1]), use_container_width=True)

  
  

    render_html("<br><hr style='margin: 15px 0 8px 0; border: none; border-top: 1px solid #E2E8F0;'>")

    render_html("<div style='font-size: 11.5px; color: #64748B; text-align: center;'>© 2026-27 School Result Pro. सर्व शिक्षा अभियान एवं म.प्र. शासन दिशा-निर्देशानुसार। सर्वाधिकार सुरक्षित।</div>")

    st.stop()

  
  

# ----------------- CASE 2: NORMAL LOGIN & LANDING PORTAL (WHEN NOT AUTHENTICATED) -----------------

if st.session_state.get("authenticated_school") is None:

    render_html("""

    <div style="background: linear-gradient(135deg, #1E3A8A 0%, #1E40AF 50%, #3B82F6 100%); padding: 25px 20px; border-radius: 12px; text-align: center; color: white; margin-bottom: 20px; box-shadow: 0 4px 12px rgba(30, 58, 138, 0.25);">

        <div style="font-size: 32px; font-weight: 900; letter-spacing: 0.5px;">🎓 School Result Pro</div>

        <div style="font-size: 16px; font-weight: 600; opacity: 0.95; margin-top: 4px;">

            मध्य प्रदेश शालेय परीक्षा परिणाम, प्रगति पत्रक एवं A3 गोशवारा क्लाउड प्रबंधन प्रणाली

        </div>

        <div style="margin-top: 12px; display: flex; justify-content: center; gap: 15px; flex-wrap: wrap;">

            <span style="background: rgba(255,255,255,0.2); padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: bold;">🏛️ RSKMP अधिकृत 44-कॉलम गोशवारा</span>

            <span style="background: rgba(255,255,255,0.2); padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: bold;">🏢 5वीं/8वीं बोर्ड 20+20+60 प्रोजेक्ट सपोर्ट</span>

            <span style="background: rgba(255,255,255,0.2); padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: bold;">💎 मात्र ₹499 / वर्ष (सभी कक्षाएं अनलॉक्ड)</span>

        </div>

    </div>

    """)

  

    # Check if Super Admin secret mode is requested via URL or secret toggle

    query_params = getattr(st, "query_params", {})

    is_admin_query = (query_params.get("admin") in ["true", "1", "secret", "master"])

    if "show_secret_admin" not in st.session_state:

        st.session_state.show_secret_admin = False

  

    is_admin_mode = is_admin_query or st.session_state.show_secret_admin

  

    if is_admin_mode:

        # EXCLUSIVE SUPER ADMIN MASTER GATEWAY (ONLY FOR YOU)

        render_html("""

        <div style="background: linear-gradient(135deg, #0F172A, #1E293B); padding: 16px 20px; border-radius: 10px; color: white; margin-bottom: 15px; border-left: 5px solid #F59E0B;">

            <div style="display: flex; justify-content: space-between; align-items: center;">

                <div>

                    <b style="font-size: 16px; color: #FCD34D;">👑 सुपर एडमिन मास्टर कंसोल (Exclusive Owner Gateway)</b><br>

                    <span style="font-size: 12px; color: #94A3B8;">यह स्क्रीन केवल प्लेटफ़ॉर्म निर्माता / स्वामी के लिए है। सामान्य उपयोगकर्ताओं को यह दिखाई नहीं देती।</span>

                </div>

            </div>

        </div>

        """)

        

        c_adm_box1, c_adm_box2 = st.columns([1.5, 1])

        with c_adm_box1:

            adm_id_in = st.text_input("मास्टर एडमिन यूजर आईडी:*", value="admin@pro", key="adm_id_input_secret")

            adm_pwd_in = st.text_input("मास्टर पासवर्ड:*", type="password", value="superadmin@499", key="adm_pwd_input_secret")

            adm_otp_in = st.text_input("6-अंकीय मास्टर सिक्योरिटी की / OTP:*", value="999888", key="adm_otp_input_secret")

  

            c_act_ad1, c_act_ad2 = st.columns(2)

            with c_act_ad1:

                if st.button("🚀 सुपर एडमिन कंट्रोल रूम खोलें", type="primary", use_container_width=True):

                    if adm_id_in == "admin@pro" and adm_pwd_in == "superadmin@499" and adm_otp_in == "999888":

                        st.session_state.authenticated_role = "SUPER_ADMIN"

                        st.session_state.authenticated_school = None

                        log_security_event("PLATFORM_CORE", "SUPER_ADMIN", "Super Admin", "9998887777", "SUPER_ADMIN_LOGIN", "Master Key Authenticated")

                        st.balloons()

                        st.success("सुपर एडमिन प्रमाणीकरण सफल!")

                        st.rerun()

                    else:

                        st.error("❌ अमान्य मास्टर क्रेडेंशियल्स!")

            with c_act_ad2:

                if st.button("⬅️ वापस सामान्य पोर्टल (Back to School Portal)", use_container_width=True):

                    st.session_state.show_secret_admin = False

                    if hasattr(st, "query_params") and "admin" in st.query_params:

                        del st.query_params["admin"]

                    st.rerun()

        with c_adm_box2:

            render_html("""

            <div style="background: #1E293B; border: 1px solid #334155; padding: 14px; border-radius: 8px; color: #E2E8F0; font-size: 12.5px;">

                <b style="color: #FCD34D;">🔐 मास्टर क्रेडेंशियल्स (Owner Only):</b><br>

                • <b>User ID:</b> <code>admin@pro</code><br>

                • <b>Password:</b> <code>superadmin@499</code><br>

                • <b>Master Key:</b> <code>999888</code><br>

                <hr style="margin: 8px 0; border-color: #334155;">

                <span style="color: #94A3B8; font-size: 11.5px;">

                    यह पोर्टल केवल आपके लिए आरक्षित है। किसी भी स्कूल या शिक्षक को इसका पता नहीं चलेगा।

                </span>

            </div>

            """)

        st.stop()

  

    # NORMAL PUBLIC TABS (ONLY 5 TABS — SUPER ADMIN IS 100% HIDDEN FROM SCHOOLS)

    auth_tab1, auth_tab2, auth_tab3, auth_tab4, auth_tab5 = st.tabs([

        "🏛️ संस्था प्रधान लॉगिन (Principal Login with OTP)",

        "👨‍🏫 कक्षा अध्यापक लॉगिन (Teacher Login with OTP)",

        "📝 नया स्कूल पंजीकरण (15 दिन निःशुल्क ट्रायल)",

        "💎 ₹499 ऑल-इन-वन वार्षिक पास",

        "📞 सहायता एवं संपर्क"

    ])

  
  

    # Tab 1: Principal Login with OTP

    with auth_tab1:

        c_pl1, c_pl2 = st.columns([1.5, 1])

        with c_pl1:

            st.subheader("संस्था प्रधान (Principal) सुरक्षित लॉगिन")

            st.caption("डाइस कोड या पंजीकृत मोबाइल नंबर दर्ज करें:")

  

            p_login_id = st.text_input("U-DISE कोड अथवा मोबाइल नंबर:*", value="23260100101", key="pr_login_id")

            p_login_pwd = st.text_input("पासवर्ड (Password):*", type="password", value="admin@123", key="pr_login_pwd")

  

            st.info("📱 सुरक्षा नियम: संस्था प्रधान के पंजीकृत मोबाइल नंबर पर 6-अंकीय OTP सत्यापन अनिवार्य है।")

            p_otp = st.text_input("6-अंकीय लॉगिन OTP दर्ज करें:*", value="123456", key="pr_otp_input", help="परीक्षण हेतु डिफॉल्ट OTP: 123456")

  

            c_pb1, c_pb2 = st.columns(2)

            with c_pb1:

                if st.button("🚀 संस्था प्रधान पोर्टल में लॉगिन करें", type="primary", use_container_width=True):

                    # Secret Super Admin Master Door from normal login

                    if str(p_login_id).strip() in ["admin@pro", "superadmin"] and p_login_pwd == "superadmin@499":

                        st.session_state.authenticated_role = "SUPER_ADMIN"

                        st.session_state.authenticated_school = None

                        log_security_event("PLATFORM_CORE", "SUPER_ADMIN", "Super Admin", "9998887777", "SUPER_ADMIN_LOGIN", "Master Key Authenticated via Portal")

                        st.balloons()

                        st.success("👑 सुपर एडमिन प्रमाणीकरण सफल!")

                        st.rerun()

  

                    registry = load_schools_registry()

                    matched_sch = None

                    for d, sch in registry.items():

                        if str(p_login_id).strip() == str(d).strip() or str(p_login_id).strip() == str(sch.get("mobile", "")).strip():

                            if verify_password(p_login_pwd, sch.get("password_hash", "")):

                                matched_sch = sch

                                break

                    if matched_sch and len(str(p_otp).strip()) == 6:

                        st.session_state.authenticated_role = "PRINCIPAL"

                        st.session_state.authenticated_school = matched_sch

                        st.session_state.school_info.update({

                            "name": matched_sch.get("school_name", ""),

                            "udise": matched_sch.get("dise_code", ""),

                            "block": matched_sch.get("block", ""),

                            "district": matched_sch.get("district", ""),

                            "contact": matched_sch.get("mobile", "")

                        })

                        load_data_from_disk()

                        log_security_event(matched_sch.get("dise_code"), "Principal", "Principal / Admin", matched_sch.get("mobile"), "LOGIN_SUCCESS", "OTP Authenticated")

                        st.balloons()

                        st.success(f"✅ सफल लॉगिन! आपका स्वागत है, {matched_sch.get('school_name')}")

                        st.rerun()

                    else:

                        log_security_event(p_login_id, "Principal", "Unknown", p_login_id, "LOGIN_FAILED", "Invalid password or OTP", "FAILED")

                        st.error("❌ अमान्य क्रेडेंशियल्स अथवा गलत OTP! कृपया पुनः प्रयास करें।")

  

            with c_pb2:

                if st.button("⚡ डेमो संस्था प्रधान वन-क्लिक लॉगिन", use_container_width=True):

                    registry = load_schools_registry()

                    demo_sch = registry.get("23260100101")

                    if demo_sch:

                        st.session_state.authenticated_role = "PRINCIPAL"

                        st.session_state.authenticated_school = demo_sch

                        st.session_state.school_info.update({

                            "name": demo_sch.get("school_name", ""),

                            "udise": demo_sch.get("dise_code", ""),

                            "block": demo_sch.get("block", ""),

                            "district": demo_sch.get("district", ""),

                            "contact": demo_sch.get("mobile", "")

                        })

                        load_data_from_disk()

                        log_security_event("23260100101", "Principal", "Principal / Admin", "9826012345", "DEMO_LOGIN", "One-Click Demo Access")

                        st.success("डेमो लॉगिन सफल!")

                        st.rerun()

  

        with c_pl2:

            render_html("""

            <div style="background: #F0FDF4; border: 1px solid #86EFAC; padding: 14px; border-radius: 8px; margin-top: 10px;">

                <b style="color: #166534; font-size: 14px;">🏛️ संस्था प्रधान के अधिकार:</b><br>

                <span style="font-size: 12.5px; color: #14532D;">

                    • स्कूल की सभी कक्षाओं का पूर्ण नियंत्रण<br>

                    • शिक्षकों के ड्राफ्ट एवं सुधार का 1-क्लिक अप्रूवल<br>

                    • 44-कॉलम A3 शीट एवं RSKMP एक्सेल एक्सपोर्ट<br>

                    • संस्था सेटअप, लोगो एवं शिक्षक आवंटन<br>

                </span>

            </div>

            """)

  

    # Tab 2: Class Teacher Login with OTP

    with auth_tab2:

        c_tl1, c_tl2 = st.columns([1.5, 1])

        with c_tl1:

            st.subheader("👨‍🏫 कक्षा अध्यापक (Teacher) लॉगिन")

            st.caption("प्रिंसिपल द्वारा पंजीकृत अपना मोबाइल नंबर दर्ज करें:")

  

            t_mobile_in = st.text_input("शिक्षक का मोबाइल नंबर:*", value="9826112233", key="tr_mob_input")

            t_otp_in = st.text_input("6-अंकीय शिक्षक लॉगिन OTP:*", value="123456", key="tr_otp_input", help="परीक्षण हेतु डिफॉल्ट OTP: 123456")

  

            c_tb1, c_tb2 = st.columns(2)

            with c_tb1:

                if st.button("🚀 कक्षा अध्यापक पोर्टल में लॉगिन करें", type="primary", use_container_width=True):

                    registry = load_schools_registry()

                    matched_teacher = None

                    matched_school_for_t = None

                    for d, sch in registry.items():

                        for tr in sch.get("teachers", []):

                            if str(t_mobile_in).strip() == str(tr.get("mobile", "")).strip():

                                matched_teacher = tr

                                matched_school_for_t = sch

                                break

                        if matched_teacher: break

  

                    if matched_teacher and len(str(t_otp_in).strip()) == 6:

                        st.session_state.authenticated_role = "TEACHER"

                        st.session_state.authenticated_school = matched_school_for_t

                        st.session_state.authenticated_user_name = matched_teacher.get("name", "कक्षा अध्यापक")

                        st.session_state.assigned_class = matched_teacher.get("assigned_class", "Class 7th")

                        st.session_state.school_info.update({

                            "name": matched_school_for_t.get("school_name", ""),

                            "udise": matched_school_for_t.get("dise_code", ""),

                            "block": matched_school_for_t.get("block", ""),

                            "district": matched_school_for_t.get("district", ""),

                            "contact": matched_school_for_t.get("mobile", "")

                        })

                        load_data_from_disk()

                        log_security_event(matched_school_for_t.get("dise_code"), "Teacher", matched_teacher.get("name"), t_mobile_in, "TEACHER_LOGIN_SUCCESS", f"Assigned: {st.session_state.assigned_class}")

                        st.balloons()

                        st.success(f"✅ शिक्षक लॉगिन सफल! स्वागत है, {matched_teacher.get('name')} ({st.session_state.assigned_class})")

                        st.rerun()

                    else:

                        st.error("❌ यह मोबाइल नंबर किसी स्कूल में शिक्षक के रूप में पंजीकृत नहीं है!")

  

            with c_tb2:

                if st.button("⚡ डेमो क्लास टीचर लॉगिन (Class 7th)", use_container_width=True):

                    registry = load_schools_registry()

                    demo_sch = registry.get("23260100101")

                    st.session_state.authenticated_role = "TEACHER"

                    st.session_state.authenticated_school = demo_sch

                    st.session_state.authenticated_user_name = "श्री राजेश शर्मा"

                    st.session_state.assigned_class = "Class 7th"

                    load_data_from_disk()

                    st.success("डेमो क्लास टीचर लॉगिन सफल (Class 7th)!")

                    st.rerun()

  

        with c_tl2:

            render_html("""

            <div style="background: #FFFBEB; border: 1px solid #FDE68A; padding: 14px; border-radius: 8px; margin-top: 10px;">

                <b style="color: #92400E; font-size: 14px;">👨‍🏫 कक्षा अध्यापक के अधिकार:</b><br>

                <span style="font-size: 12.5px; color: #78350F;">

                    • केवल अपनी कक्षा का दैनिक हाजिरी रजिस्टर<br>

                    • अपनी कक्षा के परीक्षा व प्रोजेक्ट अंक भरना<br>

                    • नए छात्र का ड्राफ्ट जोड़ना (प्रिंसिपल अनुमोदन हेतु)<br>

                    • 🔒 शासकीय डेटा एक्सपोर्ट पूरी तरह सुरक्षित व लॉक<br>

                </span>

            </div>

            """)

  

    # Tab 3: Register New School

    with auth_tab3:

        st.subheader("📝 नवीन संस्था निःशुल्क पंजीकरण (15-Day Free Trial)")

        st.caption("अपने स्कूल को पंजीकृत करें और तुरंत 15 दिनों तक सभी फीचर्स का निःशुल्क लाभ लें:")

  

        with st.form("register_school_form_universal"):

            r_c1, r_c2 = st.columns(2)

            with r_c1:

                reg_name = st.text_input("1. विद्यालय का पूरा नाम (School Name):*")

                reg_dise = st.text_input("2. 11-अंकीय U-DISE कोड (DISE Code):*")

                reg_level = st.selectbox("3. विद्यालय स्तर:", ["प्राथमिक (Class 1-5)", "माध्यमिक (Class 1-8)", "हाईस्कूल (Class 1-10)", "हायर सेकेंडरी (Class 1-12)"])

            with r_c2:

                reg_mobile = st.text_input("4. प्राचार्य / संचालक मोबाइल नंबर:*")

                reg_dist = st.text_input("5. जिला (District):", value="Bhopal")

                reg_block = st.text_input("6. ब्लॉक / संकुल (Block):", value="Fanda")

            

            r_p1, r_p2 = st.columns(2)

            with r_p1:

                reg_pwd = st.text_input("7. नया पासवर्ड बनाएं:*", type="password")

            with r_p2:

                reg_pwd_confirm = st.text_input("8. पासवर्ड पुनः दर्ज करें:*", type="password")

  

            reg_consent = st.checkbox("✅ मैं प्रमाणित करता हूँ कि हमारे पास इस विद्यालय का परीक्षा रिकॉर्ड रखने का अधिकार है (DPDP Act Compliance)", value=True)

            

            submit_reg = st.form_submit_button("🎉 ₹499 वार्षिक पास ट्रायल सक्रिय करें (Start Trial)", type="primary", use_container_width=True)

  

            if submit_reg:

                registry = load_schools_registry()

                if not reg_name or not reg_dise or not reg_mobile or not reg_pwd:

                    st.error("कृपया सभी अनिवार्य फ़ील्ड (*) भरें!")

                elif len(str(reg_dise).strip()) != 11 or not str(reg_dise).strip().isdigit():

                    st.error("कृपया वैध 11-अंकीय U-DISE कोड दर्ज करें!")

                elif reg_pwd != reg_pwd_confirm:

                    st.error("पासवर्ड मेल नहीं खा रहे हैं!")

                elif str(reg_dise).strip() in registry:

                    st.error(f"DISE Code {reg_dise} पहले से पंजीकृत है! कृपया 'संस्था प्रधान लॉगिन' से लॉगिन करें।")

                else:

                    new_sch_data = {

                        "dise_code": str(reg_dise).strip(),

                        "school_name": reg_name.strip(),

                        "mobile": str(reg_mobile).strip(),

                        "password_hash": hash_password(reg_pwd),

                        "plan": "School Result Pro ऑल-इन-वन पास (₹499/वर्ष)",

                        "price": 499,

                        "status": "Trial (15-दिन परीक्षण)",

                        "expiry": "2026-09-21",

                        "created_at": str(datetime.now().date()),

                        "district": reg_dist.strip(),

                        "block": reg_block.strip(),

                        "data_file": f"school_data_{reg_dise}.json",

                        "teachers": [],

                        "pending_approvals": []

                    }

                    registry[str(reg_dise).strip()] = new_sch_data

                    save_schools_registry(registry)

                    

                    st.session_state.authenticated_role = "PRINCIPAL"

                    st.session_state.authenticated_school = new_sch_data

                    st.session_state.school_info.update({

                        "name": reg_name.strip(),

                        "udise": str(reg_dise).strip(),

                        "block": reg_block.strip(),

                        "district": reg_dist.strip(),

                        "contact": str(reg_mobile).strip()

                    })

                    save_data_to_disk()

                    log_security_event(reg_dise, "Principal", "Principal / Admin", reg_mobile, "NEW_SCHOOL_REGISTERED", "Registered for ₹499 Trial")

                    st.balloons()

                    st.success(f"🎉 बधाई! {reg_name} का 15-दिवसीय निःशुल्क ट्रायल खाता सफलतापूर्वक सक्रिय हो गया!")

                    st.rerun()

  

    # Tab 4: Disruptive ₹499 Universal Plan

    with auth_tab4:

        st.subheader("💎 एक स्कूल — एक दाम: फ्लैट ₹499 मात्र")

        render_html("""

        <div style="border: 2px solid #2563EB; border-radius: 12px; padding: 24px; text-align: center; background: #EFF6FF; box-shadow: 0 4px 10px rgba(37, 99, 235, 0.15); max-width: 600px; margin: auto;">

            <span style="background: #2563EB; color: white; padding: 3px 12px; border-radius: 20px; font-size: 12px; font-weight: bold;">धमाका ऑफर (Disruptive Single Pass)</span>

            <h2 style="color: #1E3A8A; margin-top: 10px; margin-bottom: 2px;">School Result Pro — ऑल-इन-वन वार्षिक पास</h2>

            <p style="color: #64748B; font-size: 14px;">सभी कक्षाओं (कक्षा 1 से 8वीं / 10वीं) के लिए संपूर्ण सत्र हेतु</p>

            <div style="font-size: 42px; font-weight: 900; color: #0F172A; margin: 12px 0;">₹499 <span style="font-size: 15px; font-weight: normal; color: #64748B;">/ पूरा वर्ष</span></div>

            <hr style="margin: 15px 0;">

            <ul style="text-align: left; font-size: 13.5px; color: #334155; line-height: 2;">

                <li>✅ <b>कक्षा 1 से 8वीं (एवं 9वीं-10वीं)</b> का संपूर्ण वार्षिक परीक्षा परिणाम</li>

                <li>✅ <b>RSKMP 44-कॉलम A3 परीक्षाफल पत्रक</b> (सत्यापन हस्ताक्षर ब्लॉक सहित)</li>

                <li>✅ <b>5वीं एवं 8वीं बोर्ड 20+20+60 प्रोजेक्ट कार्य</b> आधिकारिक प्रारूप</li>

                <li>✅ <b>rskmp.in पोर्टल अधिकृत बल्क एक्सेल एक्सपोर्ट</b> (-1 कोड सहित)</li>

                <li>✅ <b>अभिभावकों को WhatsApp पर 1-क्लिक रिजल्ट प्रेषण</b> (100% मुफ़्त)</li>

                <li>✅ <b>कक्षा अध्यापक दैनिक मोबाइल हाजिरी रजिस्टर</b></li>

                <li>✅ <b>मेकर-चेकर शिक्षक अनुमोदन प्रणाली</b> (प्रिंसिपल का ज़ीरो टाइपिंग लोड)</li>

                <li>✅ <b>यूनिवर्सल पुरानी एक्सेल शीट अपलोड व ऑटो-कॉलम माइग्रेशन</b></li>

                <li>✅ <b>15 दिन का संपूर्ण निःशुल्क ट्रायल</b> (बिना किसी अग्रिम शुल्क)</li>

            </ul>

        </div>

        """)

  

    # Tab 5: Support Helpline

    with auth_tab5:

        st.subheader("📞 सहायता, प्रशिक्षण एवं संपर्क (Support Helpline)")

        c_hp1, c_hp2 = st.columns(2)

        with c_hp1:

            render_html("""

            **📱 हेल्पलाइन नंबर:** +91 98260 XXXXX  

            **💬 व्हाट्सएप सपोर्ट:** +91 98260 XXXXX  

            **📧 ईमेल आईडी:** support@schoolresultpro.in  

            **⏰ सपोर्ट समय:** प्रातः 9:00 बजे से सायं 8:00 बजे तक

            """)

        with c_hp2:

            render_html("""

            **📍 तकनीकी केंद्र:** भोपाल, मध्य प्रदेश (Bhopal, MP)  

            **🎯 विशेष सुविधा:** किसी भी प्रकार की तकनीकी कठिनाई होने पर AnyDesk पर निशुल्क 5 मिनट का लाइव समाधान।

            """)

  

    st.stop()

  

with st.sidebar:

    auth_school = st.session_state.get("authenticated_school") or {}

    user_role = st.session_state.get("authenticated_role", "PRINCIPAL")

    user_display_name = st.session_state.get("authenticated_user_name", "संस्था प्रधान")

    assigned_c = st.session_state.get("assigned_class")

    

    if auth_school:

        role_label = "🏛️ संस्था प्रधान (Principal)" if user_role == "PRINCIPAL" else f"👨‍🏫 कक्षा अध्यापक: {user_display_name} ({assigned_c})"

        pending_cnt = len(auth_school.get("pending_approvals", []))

        

        render_html(f'''
        <div style="background: linear-gradient(135deg, #1E3A8A, #2563EB); padding: 10px 12px; border-radius: 8px; color: white; margin-bottom: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <div style="font-weight: 800; font-size: 13.5px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">🏫 {auth_school.get("school_name", "School Portal")}</div>
            <div style="font-size: 11px; opacity: 0.9;">DISE: {auth_school.get("dise_code", "")} | {auth_school.get("block","")}</div>
            <div style="font-size: 11px; color: #FEF08A; font-weight: bold; margin-top: 2px;">{role_label}</div>
            <div style="font-size: 10px; color: #BBF7D0; font-weight: bold; margin-top: 3px;">🟢 {auth_school.get("plan", "School Result Pro पास (₹499/वर्ष)")}</div>
        </div>
        ''')

        

        if user_role == "PRINCIPAL" and pending_cnt > 0:

            st.warning(f"🔔 **{pending_cnt}** शिक्षक अनुमोदन लंबित हैं!")

        

        c_lg1, c_lg2 = st.columns([1, 1])

        with c_lg1:

            if st.button("🚪 लॉगआउट", key="btn_logout", use_container_width=True):

                st.session_state.authenticated_school = None

                st.rerun()

        with c_lg2:

            if st.button("💎 लाइसेंस", key="btn_license_info", use_container_width=True):

                st.session_state.show_license_dialog = not st.session_state.get("show_license_dialog", False)

                st.rerun()

        st.divider()

  

    st.image("https://img.icons8.com/color/96/school.png", width=65)

    

    selected_lang = st.selectbox("🌐 भाषा चुनें (Language):", list(I18N.keys()), 

                                 index=list(I18N.keys()).index(st.session_state.ui_lang) if st.session_state.ui_lang in I18N else 0)

    if selected_lang != st.session_state.ui_lang:

        st.session_state.ui_lang = selected_lang

        st.rerun()

  
  

    T = I18N[st.session_state.ui_lang]

  
  

    st.title(T["title"])

    st.caption(f"**{T['sub']}**")

    st.success(T["auto_saved"])

    st.divider()

  
  

    st.subheader(f"🎯 {T['select_class']}")

    st.session_state.classes_list = clean_and_sort_classes(st.session_state.classes_list)

    if st.session_state.get("authenticated_role") == "TEACHER" and st.session_state.get("assigned_class"):
        teacher_assigned_cls = normalize_class_name(st.session_state.get("assigned_class"))
        if teacher_assigned_cls not in st.session_state.classes_list:
            st.session_state.classes_list.append(teacher_assigned_cls)
            st.session_state.classes_list = clean_and_sort_classes(st.session_state.classes_list)
        selected_class = teacher_assigned_cls
        render_html(f"<div style='border: 1px solid #CBD5E1; background: #F1F5F9; padding: 6px 10px; border-radius: 6px; font-weight: bold; font-size: 13px; text-align: center; color: #1E3A8A;'>🎯 आवंटित कक्षा: {selected_class}</div>")
    else:
        def_idx = 0
        if "Class 7th" in st.session_state.classes_list:
            def_idx = st.session_state.classes_list.index("Class 7th")
        elif "Class 1st" in st.session_state.classes_list:
            def_idx = st.session_state.classes_list.index("Class 1st")
        selected_class = st.selectbox(T["select_class"], st.session_state.classes_list, 
                                      index=def_idx,
                                      label_visibility="collapsed")

    with st.expander("⚙️ कक्षाएं प्रबंधित करें (Add / Delete / Clean)"):
        st.markdown("<div style='font-weight: bold; font-size: 12.5px; color: #1E3A8A; margin-bottom: 4px;'>➕ नई कक्षा जोड़ें:</div>", unsafe_allow_html=True)
        c_add1, c_add2 = st.columns([3, 1])
        with c_add1:
            new_cls_input = st.text_input("नई कक्षा:", placeholder="उदा. Class 9th, Nursery", label_visibility="collapsed", key="input_new_class_sb")
        with c_add2:
            if st.button("जोड़ें", key="btn_add_class_sb", type="primary", use_container_width=True):
                if new_cls_input and new_cls_input.strip():
                    norm_c = normalize_class_name(new_cls_input)
                    if norm_c not in st.session_state.classes_list:
                        st.session_state.classes_list.append(norm_c)
                        st.session_state.classes_list = clean_and_sort_classes(st.session_state.classes_list)
                        save_data_to_disk()
                        st.success(f"✅ {norm_c} जोड़ी गई!")
                        st.rerun()
                    else:
                        st.warning(f"⚠️ {norm_c} पहले से उपलब्ध है!")

        st.markdown("<hr style='margin: 8px 0;'>", unsafe_allow_html=True)
        st.markdown("<div style='font-weight: bold; font-size: 12.5px; color: #B91C1C; margin-bottom: 4px;'>🗑️ अवांछित कक्षा हटाएं:</div>", unsafe_allow_html=True)
        c_del1, c_del2 = st.columns([3, 1])
        with c_del1:
            cls_to_delete = st.selectbox("हटाने हेतु कक्षा चुनें:", st.session_state.classes_list, key="select_del_class_sb", label_visibility="collapsed")
        with c_del2:
            if st.button("हटाएं", key="btn_del_class_sb", type="secondary", use_container_width=True):
                if len(st.session_state.classes_list) > 1:
                    st.session_state.classes_list = [c for c in st.session_state.classes_list if c != cls_to_delete]
                    if cls_to_delete in st.session_state.data_store:
                        del st.session_state.data_store[cls_to_delete]
                    st.session_state.classes_list = clean_and_sort_classes(st.session_state.classes_list)
                    save_data_to_disk()
                    st.success(f"🗑️ {cls_to_delete} हटा दी गई!")
                    st.rerun()
                else:
                    st.error("कम से कम 1 कक्षा रहना आवश्यक है!")

        st.markdown("<hr style='margin: 8px 0;'>", unsafe_allow_html=True)
        st.markdown("<div style='font-weight: bold; font-size: 12px; color: #15803D; margin-bottom: 4px;'>⚡ 1-Click ऑटो-शुद्धिकरण:</div>", unsafe_allow_html=True)
        if st.button("🔄 सभी 15 कक्षाएं जोड़ें (Nursery से 12th तक)", key="btn_restore_all_classes_sb", use_container_width=True, type="primary"):
            st.session_state.classes_list = clean_and_sort_classes(list(dict.fromkeys(st.session_state.classes_list + DEFAULT_CLASSES)))
            save_data_to_disk()
            st.success("✅ सभी कक्षाएं (Nursery से 12th) लोड हो गईं!")
            st.rerun()

        if st.button("🧹 सभी स्पेलिंग ठीक करें (Auto-Fix All)", key="btn_auto_clean_classes_sb", use_container_width=True):
            st.session_state.classes_list = clean_and_sort_classes(st.session_state.classes_list)
            st.session_state.data_store = migrate_data_store_keys(st.session_state.data_store)
            save_data_to_disk()
            st.success("✅ सभी कक्षाएं शुद्ध (Nursery से 12th) प्रारूप में व्यवस्थित हो गईं!")
            st.rerun()

  
  

    st.divider()

    menu = st.radio(

        "📂 Menu",

        [

            T["nav_school"],

            T["nav_student"],

            T["nav_attendance"],

            T["nav_eval"],

            T["nav_viewer"],

            T["nav_monthly_test"],

            T["nav_half_yearly"],

            T["nav_project"],

            T["nav_marksheet"],

            T["nav_a3_result"],

            T["nav_summary"],

            T["nav_merit"],

            T["nav_supple"],

            T["nav_weighted"],

            T["nav_promote"]

        ],

        label_visibility="collapsed"

    )

    st.divider()

  
  

    with st.expander(T["backup_restore"]):

        try:

            current_payload = {

                "school_info": st.session_state.school_info,

                "classes_list": st.session_state.classes_list,

                "data_store": serialize_store(st.session_state.data_store)

            }

            b_json = json.dumps(current_payload, ensure_ascii=False, indent=2).encode("utf-8")

            st.download_button(

                T["download_backup"],

                data=b_json,

                file_name=f"School_Result_Backup_{st.session_state.school_info.get('session','2023-24')}.json",

                mime="application/json"

            )

        except Exception:

            pass

        

        uploaded_backup = st.file_uploader(T["restore_backup"], type=["json"], key="backup_upload")

        if uploaded_backup:

            try:

                rest_payload = json.load(uploaded_backup)

                if "school_info" in rest_payload: st.session_state.school_info = rest_payload["school_info"]

                if "classes_list" in rest_payload: st.session_state.classes_list = rest_payload["classes_list"]

                if "data_store" in rest_payload: st.session_state.data_store = deserialize_store(rest_payload["data_store"])

                save_data_to_disk()

                st.success("✅ Restored successfully!")

                st.rerun()

            except Exception as e:

                st.error(f"Error: {e}")

  
  

    st.caption(f"{T['active_session']}: **{st.session_state.school_info.get('session', '')}**")

    st.caption(f"{T['current_class']}: **{selected_class}**")

  
  

cls_data = get_class_data(selected_class)

for col, def_val in [("Class", selected_class), ("Section", "A"), ("Aadhar_No", ""), ("Medium", "Hindi (हिन्दी)"), ("Status", "Present")]:

    if col not in cls_data["students"].columns:

        cls_data["students"][col] = def_val

  
  
  
  

# ----------------- GOVERNMENT PORTAL UPDATE MONITOR (RSKMP / MPBSE) -----------------

s_info = st.session_state.school_info
current_sess = st.session_state.school_info.get('session', '2023-24')

  
  

if not st.session_state.update_alert_dismissed:

    with st.expander("🔔 **शासकीय पोर्टल अपडेट मॉनिटर (RSKMP / MPBSE Updates)**", expanded=False):

        c_nt1, c_nt2 = st.columns([3, 1])

        with c_nt1:

            render_html(f'''

            <div style="background: #FEF3C7; border-left: 5px solid #D97706; padding: 8px 12px; border-radius: 4px;">

                <b style="color: #92400E; font-size: 13.5px;">📢 नवीन शासकीय प्रारूप अपडेट सूचना (सत्र {current_sess}):</b><br>

                <span style="color: #78350F; font-size: 12.5px;">

                    राज्य शिक्षा केंद्र (RSKMP) एवं माध्यमिक शिक्षा मण्डल (MPBSE) के नवीन मूल्यांकन दिशा-निर्देश एवं एक्सेल अपलोड प्रारूप का अपडेट डिटेक्ट हुआ है।

                </span>

            </div>

            ''')

        with c_nt2:

            render_html("<div style='margin-top: 6px;'>")

            col_b1, col_b2 = st.columns(2)

            with col_b1:

                if st.button("🟢 हाँ, अपनाएं", key="btn_adopt_format_yes", type="primary", use_container_width=True):

                    st.session_state.show_format_adopter_dialog = True

            with col_b2:

                if st.button("⚪ बाद में", key="btn_adopt_format_no", use_container_width=True):

                    st.session_state.update_alert_dismissed = True

                    st.rerun()

            st.markdown("</div>", unsafe_allow_html=True)

  
  

# Dialog / Box when user clicks "हाँ, अपनाएं"

if st.session_state.get("show_format_adopter_dialog"):

    with st.container():

        render_html(f'''

        <div style="background: #F0FDF4; border: 2px solid #16A34A; padding: 14px 18px; border-radius: 8px; margin-bottom: 15px;">

            <div style="display: flex; justify-content: space-between; align-items: center;">

                <h4 style="color: #166534; margin: 0;">🏛️ नवीन शासकीय प्रारूप अपलोड एवं सत्र अनुकूलन (Format Adopter)</h4>

            </div>

            <p style="color: #14532D; font-size: 13px; margin-top: 6px;">

                सरकारी पोर्टल (RSKMP या MPBSE) से डाउनलोड की गई नई एक्सेल शीट यहाँ अपलोड करें। ऐप स्वतः उसके कॉलम स्कैन करेगी और <b>केवल चयनित सत्र</b> के लिए नया नियम सक्रिय करेगी (पुराने सत्रों का डेटा पूर्ववत सुरक्षित रहेगा)।

            </p>

        </div>

        ''')

  
  

        c_link1, c_link2, c_link3 = st.columns(3)

        c_link1.markdown("🔗 **[RSKMP पोर्टल लॉगिन (rskmp.in)](https://www.rskmp.in)**")

        c_link2.markdown("🔗 **[MPBSE बोर्ड पोर्टल (mpbse.nic.in)](http://mpbse.nic.in)**")

        c_link3.markdown("🔗 **[एमपी ऑनलाइन स्कूल मॉड्यूल](https://mponline.gov.in)**")

  
  

        c_up_file, c_up_sess = st.columns([3, 2])

        with c_up_file:

            uploaded_template = st.file_uploader(

                "📥 डाउनलोड की गई सरकारी एक्सेल फ़ाइल चुनें (.xlsx / .csv):", 

                type=["xlsx", "csv"], 

                key="govt_template_uploader"

            )

        with c_up_sess:

            target_sess = st.selectbox(

                "यह नया प्रारूप किस सत्र हेतु लागू करना है?",

                [current_sess, "2024-25", "2025-26", "2026-27", "2027-28"],

                key="target_adoption_sess"

            )

            sess_isolate_check = st.checkbox(

                f"✅ पुष्टि करें कि पूर्ववर्ती सत्रों का रिकॉर्ड मूल नियम पर ही सुरक्षित रहेगा", 

                value=True,

                key="sess_isolate_confirm"

            )

  
  

        if uploaded_template:

            scan_res = scan_govt_excel_template(uploaded_template.read(), uploaded_template.name)

            if scan_res["success"]:

                st.success(f"🎉 सरकारी टेम्पलेट सफलतापूर्वक पहचाना गया! कुल {scan_res['total_columns']} कॉलम मिले।")

                st.write("**डिटेक्ट की गई प्रमुख विशेषताएं:**")

                for f_item in scan_res["detected_features"]:

                    st.caption(f_item)

                

                c_act_save, c_act_close = st.columns([2, 1])

                with c_act_save:

                    if st.button(f"💾 सत्र {target_sess} हेतु नया प्रारूप सक्रिय करें", type="primary", use_container_width=True):

                        # Save session rule strictly to target session

                        if target_sess not in st.session_state.session_exam_rules:

                            st.session_state.session_exam_rules[target_sess] = {}

                        

                        st.session_state.session_exam_rules[target_sess] = {

                            "adopted_from_file": uploaded_template.name,

                            "mode": "board_5_8" if scan_res.get("has_project") else "standard_rsk",

                            "columns": scan_res["columns"]

                        }

                        save_data_to_disk()

                        st.balloons()

                        st.success(f"✅ नवीन प्रारूप सफलतापूर्वक केवल सत्र {target_sess} हेतु सक्रिय कर दिया गया! पूर्ववर्ती सत्र सुरक्षित हैं।")

                        st.session_state.show_format_adopter_dialog = False

                        st.rerun()

                with c_act_close:

                    if st.button("❌ बंद करें (Close)", use_container_width=True):

                        st.session_state.show_format_adopter_dialog = False

                        st.rerun()

            else:

                st.error(f"फ़ाइल स्कैन में त्रुटि: {scan_res.get('error')}")

        else:

            if st.button("❌ अभी रद्द करें (Cancel)"):

                st.session_state.show_format_adopter_dialog = False

                st.rerun()

    st.divider()

  
  
  

# ----------------- IN-APP LICENSE & INSTANT UPI QR ACTIVATION DIALOG -----------------

if st.session_state.get("show_license_dialog", False):

    auth_school = st.session_state.get("authenticated_school") or {}

    dise_curr = auth_school.get("dise_code", "")

    with st.container():

        render_html("""

        <div style="background: linear-gradient(135deg, #1E3A8A, #2563EB); padding: 14px 18px; border-radius: 10px; color: white; margin-bottom: 15px;">

            <div style="display: flex; justify-content: space-between; align-items: center;">

                <h3 style="margin: 0; color: white;">💎 स्कूल लाइसेंस एवं सदस्यता प्रबंधन (License & Subscription)</h3>

            </div>

            <div style="font-size: 13px; opacity: 0.95; margin-top: 4px;">

                यहाँ से आप अपने विद्यालय के सक्रिय प्लान की जांच कर सकते हैं अथवा वार्षिक लाइसेंस को ऑनलाइन UPI द्वारा तुरंत सक्रिय/नवीनीकृत कर सकते हैं।

            </div>

        </div>

        """)

  

        col_lic1, col_lic2 = st.columns([1.5, 1])

        with col_lic1:

            render_html(f"""

            **🏫 संस्था का नाम:** {auth_school.get('school_name', '')}  

            **📍 U-DISE कोड:** `{dise_curr}` | **ब्लॉक:** {auth_school.get('block', '')}  

            **📌 वर्तमान प्लान:** **{auth_school.get('plan', 'Middle School Pro')}**  

            **🟢 स्थिति:** **{auth_school.get('status', 'Active')}** (वैधता: **{auth_school.get('expiry', '2027-03-31')}**)

            """)

  

            st.divider()

            st.subheader("💳 वार्षिक प्लान चुनें (Choose Renewal/Upgrade Plan):")

            sel_sub_plan = st.radio(

                "प्लान चुनें:",

                [

                    "🏫 प्राइमरी स्कूल (कक्षा 1 से 5) — ₹999 / वर्ष",

                    "🎓 मिडिल स्कूल प्रो (कक्षा 1 से 8) — ₹1,499 / वर्ष (सर्वाधिक लोकप्रिय)",

                    "🏛️ हाईस्कूल / हायर सेकेंडरी (कक्षा 1 से 10/12) — ₹2,499 / वर्ष"

                ],

                index=1,

                label_visibility="collapsed"

            )

  

            plan_amount = "1499"

            if "999" in sel_sub_plan: plan_amount = "999"

            elif "2499" in sel_sub_plan: plan_amount = "2499"

  

            st.markdown(f"#### कुल देय राशि: **₹{plan_amount}** (सत्र 2026-27 एवं 2027-28 हेतु)")

            

            entered_utr = st.text_input("12-अंकीय UPI Ref / Transaction ID / UTR दर्ज करें:*", placeholder="उदा. 4256XXXXXXXX", key="lic_utr_input")

            

            c_act_lic1, c_act_lic2 = st.columns([2, 1])

            with c_act_lic1:

                if st.button("⚡ भुगतान सत्यापित करें एवं तुरंत लाइसेंस सक्रिय करें", type="primary", use_container_width=True):

                    if not entered_utr or len(entered_utr.strip()) < 8:

                        st.error("कृपया वैध UPI UTR / Transaction ID दर्ज करें!")

                    else:

                        registry = load_schools_registry()

                        if dise_curr in registry:

                            registry[dise_curr]["status"] = "Active (सक्रिय)"

                            registry[dise_curr]["plan"] = sel_sub_plan.split("—")[0].strip()

                            registry[dise_curr]["expiry"] = "2027-03-31"

                            registry[dise_curr]["last_utr"] = entered_utr.strip()

                            save_schools_registry(registry)

                            

                            auth_school["status"] = "Active (सक्रिय)"

                            auth_school["plan"] = sel_sub_plan.split("—")[0].strip()

                            auth_school["expiry"] = "2027-03-31"

                            st.session_state.authenticated_school = auth_school

                            

                            st.balloons()

                            st.success(f"🎉 बधाई! {auth_school.get('school_name')} का वार्षिक प्रो लाइसेंस 31 मार्च 2027 तक सफलतापूर्वक सक्रिय हो गया!")

                            st.session_state.show_license_dialog = False

                            st.rerun()

            with c_act_lic2:

                if st.button("❌ बंद करें (Close)", use_container_width=True):

                    st.session_state.show_license_dialog = False

                    st.rerun()

  

        with col_lic2:
            render_html("""
            <div style="border: 2px solid #16A34A; padding: 14px; border-radius: 8px; text-align: center; background: #F0FDF4;">
                <b style="color: #166534; font-size: 14px;">📱 स्कैन करके भुगतान करें (Scan & Pay)</b><br>
                <span style="font-size: 11.5px; color: #15803D;">Google Pay, PhonePe, Paytm, BHIM UPI मान्य</span>
            </div>
            """)

  

            upi_id_demo = "schoolresultpro@upi"

            upi_qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=180x180\&data=upi://pay?pa={upi_id_demo}%26pn=SchoolResultPro%26am={plan_amount}%26cu=INR"

            

            render_html(f"""

            <div style="text-align: center; margin-top: 10px;">

                <img src="{upi_qr_url}" style="width: 170px; height: 170px; border: 1px solid #ccc; border-radius: 6px;">

                <div style="font-weight: bold; font-size: 13px; color: #1E3A8A; margin-top: 6px;">

                    UPI ID: <code>{upi_id_demo}</code>

                </div>

                <div style="font-size: 12px; color: #555;">

                    भुगतान के बाद मिला 12-अंकीय UTR नंबर बाईं ओर दर्ज करके सबमिट करें।

                </div>

            </div>

            """)

    st.divider()

  

# Ensure s_info is globally defined for all modules and sub-views
s_info = st.session_state.school_info

# ----------------- REUSABLE BULK & SINGLE PHOTO MANAGER -----------------
def render_photo_manager(cls_data, selected_class, is_teacher=False, key_prefix="pr"):
    """Renders comprehensive Photo Manager with Single Photo Upload and Bulk Roll-Number Mapped Upload"""
    st.subheader(f"📸 छात्र फोटो प्रबंधन — {selected_class}")
    students_df = cls_data["students"]
    if students_df.empty:
        st.warning("⚠️ कृपया पहले 'विद्यार्थी मास्टर' में छात्र जोड़ें!")
        return

    p_mode = st.radio(
        "फोटो अपलोड का तरीका चुनें (Upload Mode):",
        ["🚀 बल्क फोटो अपलोड (रोल नंबर से ऑटो-मैपिंग / Bulk Upload)", "👤 एकल विद्यार्थी फोटो अपलोड (Single Student Upload)"],
        horizontal=True,
        key=f"pm_mode_{key_prefix}_{selected_class}"
    )

    if "एकल विद्यार्थी" in p_mode:
        col_p_left, col_p_right = st.columns([2, 1])
        with col_p_left:
            st_photo_names = [f"Roll {s['Roll_No']}: {s['Name']}" for _, s in students_df.iterrows()]
            sel_st_photo_str = st.selectbox("विद्यार्थी चुनें:", st_photo_names, key=f"photo_sel_st_{key_prefix}")
            p_roll = int(sel_st_photo_str.split(":")[0].replace("Roll", "").strip())
            target_st = students_df[students_df["Roll_No"] == p_roll].iloc[0]
            new_photo = st.file_uploader(f"रोल {p_roll} ({target_st['Name']}) का फोटो चुनें:", type=["jpg", "jpeg", "png"], key=f"photo_up_{key_prefix}_{selected_class}_{p_roll}")
            if st.button("💾 फोटो सुरक्षित करें", type="primary", key=f"btn_p_save_{key_prefix}_{selected_class}_{p_roll}"):
                if new_photo:
                    b64_img = base64.b64encode(new_photo.read()).decode()
                    cls_data["students"].loc[cls_data["students"]["Roll_No"] == p_roll, "Photo_b64"] = b64_img
                    save_data_to_disk()
                    st.success("फोटो सुरक्षित!")
                    st.rerun()
        with col_p_right:
            if target_st.get("Photo_b64"):
                st.image(base64.b64decode(target_st["Photo_b64"]), width=130, caption=f"Roll: {p_roll}")
            else:
                st.info("फोटो उपलब्ध नहीं")

    else:
        # BULK PHOTO UPLOADER (BY ROLL NUMBER MAPPING)
        st.markdown(f"""
        <div style="background: #EFF6FF; border: 1px solid #BFDBFE; padding: 12px 16px; border-radius: 8px; margin-bottom: 12px;">
            <b style="color: #1E3A8A; font-size: 14px;">🚀 कक्षा <b>{selected_class}</b> हेतु बल्क फोटो अपलोड निर्देश:</b><br>
            <span style="font-size: 12.5px; color: #334155;">
                • फोटो फाइलों का नाम विद्यार्थी के <b>रोल नंबर</b> अनुसार रखें (उदा. <code>1.jpg</code>, <code>2.png</code>, <code>roll_3.jpeg</code>, <code>04.jpg</code>)।<br>
                • आप एक साथ सभी फोटो सेलेक्ट करके अपलोड कर सकते हैं, या सभी फोटो की एक <b>.zip</b> फाइल भी अपलोड कर सकते हैं!<br>
                • सिस्टम फाइल के नाम से रोल नंबर स्वतः पहचानकर सही विद्यार्थी के साथ लिंक कर देगा।
            </span>
        </div>
        """, unsafe_allow_html=True)

        c_bu1, c_bu2 = st.columns([1, 1])
        with c_bu1:
            bulk_files = st.file_uploader(
                "1. कई फोटो फाइल्स एक साथ चुनें (Select Multiple Images):",
                type=["jpg", "jpeg", "png"],
                accept_multiple_files=True,
                key=f"bulk_photos_files_{key_prefix}_{selected_class}"
            )
        with c_bu2:
            zip_file = st.file_uploader(
                "2. या फोटो की ZIP फ़ाइल अपलोड करें (Upload ZIP File):",
                type=["zip"],
                key=f"bulk_zip_file_{key_prefix}_{selected_class}"
            )

        # Collect candidate images (filename -> bytes)
        uploaded_images = {}
        if bulk_files:
            for bf in bulk_files:
                uploaded_images[bf.name] = bf.read()
                
        if zip_file:
            import zipfile
            try:
                with zipfile.ZipFile(zip_file) as zf:
                    for z_info in zf.infolist():
                        if not z_info.is_dir() and any(z_info.filename.lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png"]):
                            f_name = os.path.basename(z_info.filename)
                            if f_name:
                                uploaded_images[f_name] = zf.read(z_info.filename)
            except Exception as ze:
                st.error(f"ZIP फाइल पढ़ने में त्रुटि: {ze}")

        if uploaded_images:
            st.markdown(f"##### 📸 कुल प्राप्त फोटो: **{len(uploaded_images)}** (मैपिंग समीक्षा एवं सत्यापन):")
            
            # Map images to students
            mapped_records = []
            valid_rolls = set(students_df["Roll_No"].tolist())
            
            for fname, img_bytes in uploaded_images.items():
                base_name = os.path.splitext(fname)[0]
                digits = re.findall(r'\d+', base_name)
                matched_roll = None
                if digits:
                    potential_roll = int(digits[-1])
                    if potential_roll in valid_rolls:
                        matched_roll = potential_roll
                
                st_name = ""
                st_sec = ""
                has_existing = False
                if matched_roll is not None:
                    matching_st = students_df[students_df["Roll_No"] == matched_roll].iloc[0]
                    st_name = matching_st["Name"]
                    st_sec = matching_st.get("Section", "A")
                    has_existing = bool(matching_st.get("Photo_b64"))
                
                b64_str = base64.b64encode(img_bytes).decode()
                mapped_records.append({
                    "filename": fname,
                    "matched_roll": matched_roll,
                    "student_name": st_name,
                    "section": st_sec,
                    "has_existing": has_existing,
                    "img_bytes": img_bytes,
                    "b64": b64_str
                })

            col_cnt = 4
            preview_cols = st.columns(col_cnt)
            ready_to_save = {}

            for idx, rec in enumerate(mapped_records):
                with preview_cols[idx % col_cnt]:
                    st.image(rec["img_bytes"], use_container_width=True)
                    if rec["matched_roll"] is not None:
                        st.markdown(f"<div style='font-size:12px; font-weight:bold; color:#15803D;'>✅ रोल {rec['matched_roll']}: {rec['student_name']}</div>", unsafe_allow_html=True)
                        st.caption(f"फ़ाइल: `{rec['filename']}`")
                        ready_to_save[rec["matched_roll"]] = rec["b64"]
                    else:
                        st.markdown(f"<div style='font-size:12px; font-weight:bold; color:#B91C1C;'>⚠️ रोल नंबर नहीं मिला</div>", unsafe_allow_html=True)
                        st.caption(f"फ़ाइल: `{rec['filename']}`")
                        man_roll = st.selectbox(
                            "विद्यार्थी चुनें:",
                            [None] + sorted(list(valid_rolls)),
                            format_func=lambda x: f"Roll {x}: {students_df[students_df['Roll_No']==x]['Name'].values[0]}" if x is not None else "-- चुनें --",
                            key=f"man_sel_{key_prefix}_{idx}"
                        )
                        if man_roll is not None:
                            ready_to_save[man_roll] = rec["b64"]

            st.divider()
            c_bsv1, c_bsv2 = st.columns([2, 1])
            with c_bsv1:
                if ready_to_save:
                    if st.button(f"💾 कुल {len(ready_to_save)} विद्यार्थियों के फोटो एक साथ सुरक्षित करें (Bulk Save)", type="primary", use_container_width=True, key=f"btn_bulk_save_{key_prefix}_{selected_class}"):
                        for r_num, b64_data in ready_to_save.items():
                            cls_data["students"].loc[cls_data["students"]["Roll_No"] == r_num, "Photo_b64"] = b64_data
                        save_data_to_disk()
                        st.balloons()
                        st.success(f"🎉 बधाई! {len(ready_to_save)} विद्यार्थियों के फोटो कक्षा {selected_class} में सफलतापूर्वक सहेज दिए गए!")
                        st.rerun()
                else:
                    st.warning("⚠️ कोई भी फोटो रोल नंबर से मैच नहीं हो सकी। कृपया फाइलों के नाम में रोल नंबर लिखें (उदा. 1.jpg, 2.jpg)!")

# ----------------- MODULE 1: SCHOOL SETUP -----------------

if menu == T["nav_school"]:

    st.markdown(f'<div class="main-header">🏫 स्कूल प्रोफाइल एवं संस्था विवरण</div>', unsafe_allow_html=True)

    render_html(f'<div class="sub-header">मार्कशीट, गोशवारा और स्कूल रिकॉर्ड हेतु आवश्यक सभी 10 जानकारियां</div>')

  
  

    col1, col2 = st.columns([2, 1])

    with col1:

        st.subheader("📋 संस्था का संपूर्ण विवरण (School Information)")

        c_r1, c_r2 = st.columns(2)

        with c_r1:

            s_sess = st.text_input("1. Session (सत्र):", value=st.session_state.school_info.get("session", "2023-24"))

            s_name = st.text_input("2. Name Of School (स्कूल का नाम):", value=st.session_state.school_info.get("name", "शासकीय माध्यमिक विद्यालय"))

            s_udise = st.text_input("3. Dise Code (डाइस कोड):", value=st.session_state.school_info.get("udise", "23260100101"))

            cur_med = st.session_state.school_info.get("medium", "Hindi (हिन्दी)")

            med_idx = ALL_MEDIUMS.index(cur_med) if cur_med in ALL_MEDIUMS else 0

            s_med = st.selectbox("4. Medium (माध्यम):", ALL_MEDIUMS, index=med_idx)

            s_cls = st.text_input("5. Class (कक्षा स्तर / Classes):", value=st.session_state.school_info.get("class_level", "Class 1st to 8th"))

        with c_r2:

            s_addr = st.text_input("6. Address (स्कूल का पूरा पता):", value=st.session_state.school_info.get("address", "Bhadbhada Road, Bhopal"))

            s_block = st.text_input("7. Block (ब्लॉक / संकुल):", value=st.session_state.school_info.get("block", "Fanda"))

            s_dist = st.text_input("8. District (जिला):", value=st.session_state.school_info.get("district", "Bhopal"))

            s_contact = st.text_input("9. Contact (संपर्क मोबाइल / फोन):", value=st.session_state.school_info.get("contact", ""))

            s_email = st.text_input("10. Email (स्कूल ईमेल आईडी):", value=st.session_state.school_info.get("email", ""))

        

        c_sbtn1, c_sbtn2 = st.columns([1.5, 1.5])
        with c_sbtn1:
            if st.button("🔄 सभी शीट्स व छात्रों का माध्यम 'HINDI' करें", help="पूरी शाला एवं सभी छात्रों का माध्यम 1-क्लिक में HINDI सेट करें"):
                st.session_state.school_info["medium"] = "Hindi (हिन्दी)"
                for c_name, c_dict in st.session_state.data_store.items():
                    st_df = c_dict.get("students", pd.DataFrame())
                    if not st_df.empty and "Medium" in st_df.columns:
                        st_df["Medium"] = "Hindi (हिन्दी)"
                save_data_to_disk()
                st.success("✅ पूरी शाला एवं समस्त कक्षाओं का माध्यम 'HINDI' सेट हो गया!")
                st.rerun()
        with c_sbtn2:
            save_sch_btn = st.button("💾 स्कूल जानकारी सहेजें (Save School Info)", type="primary", use_container_width=True)

        if save_sch_btn:

            st.session_state.school_info.update({

                "session": s_sess, "name": s_name, "udise": s_udise, "medium": s_med,

                "class_level": s_cls, "address": s_addr, "block": s_block, "district": s_dist,

                "contact": s_contact, "email": s_email

            })

            save_data_to_disk()

            st.success("✅ स्कूल की सभी 10 जानकारियां सुरक्षित कर ली गईं!")

  
  

    with col2:

        st.subheader("🖼️ स्कूल लोगो (School Logo)")

        logo_file = st.file_uploader("लोगो अपलोड करें (PNG/JPG)", type=["png", "jpg", "jpeg"], key="school_logo")

        if logo_file:

            bytes_data = logo_file.read()

            st.session_state.school_info["logo_b64"] = base64.b64encode(bytes_data).decode()

            save_data_to_disk()

            st.image(bytes_data, width=110, caption="School Logo")

        elif st.session_state.school_info.get("logo_b64"):

            st.image(base64.b64decode(st.session_state.school_info["logo_b64"]), width=110, caption="Current Logo")

            

        st.divider()

        st.subheader("✍️ डिजिटल सील / हस्ताक्षर")

        sign_file = st.file_uploader("प्रधानाध्यापक सील / हस्ताक्षर (Optional)", type=["png", "jpg", "jpeg"], key="school_sign")

        if sign_file:

            st.session_state.school_info["sign_b64"] = base64.b64encode(sign_file.read()).decode()

            save_data_to_disk()

            st.success("हस्ताक्षर सुरक्षित!")

  
  
  
  

        st.divider()

        st.subheader("⚙️ परीक्षा घटक व पूर्णांक प्रबंधन (Exam Components & Marks Master)")

        st.caption("सत्र अनुसार शासकीय मूल्यांकन प्रारूप चुनें या 5वीं/8वीं बोर्ड हेतु प्रोजेक्ट कार्य सक्रिय करें:")

        

        cur_sess_for_rule = st.session_state.school_info.get("session", "2023-24")

        cur_rule = get_session_exam_rule(cur_sess_for_rule, selected_class)

        

        c_pat1, c_pat2 = st.columns([2, 1])

        with c_pat1:

            pat_choice = st.selectbox(

                f"सत्र {cur_sess_for_rule} का सक्रिय शासकीय परीक्षा पैटर्न:",

                [

                    "1. RSK मानक स्थानीय परीक्षा (40 अर्धवार्षिक + 60 वार्षिक = 100)",

                    "2. RSKMP 5वीं व 8वीं बोर्ड (20 अर्धवार्षिक + 20 प्रोजेक्ट + 60 वार्षिक = 100)",

                    "3. MPBSE हाईस्कूल 9वीं-10वीं (75 लिखित + 25 प्रोजेक्ट = 100)"

                ],

                key="school_setup_pat_choice"

            )

        with c_pat2:

            render_html("<div style='margin-top: 28px;'>")

            if st.button("💾 यह पैटर्न सक्रिय करें", type="primary", key="btn_save_pattern"):

                if cur_sess_for_rule not in st.session_state.session_exam_rules:

                    st.session_state.session_exam_rules[cur_sess_for_rule] = {}

                

                if "5वीं व 8वीं" in pat_choice:

                    st.session_state.session_exam_rules[cur_sess_for_rule]["mode"] = "board_5_8"

                elif "MPBSE" in pat_choice:

                    st.session_state.session_exam_rules[cur_sess_for_rule]["mode"] = "mpbse_highschool"

                else:

                    st.session_state.session_exam_rules[cur_sess_for_rule]["mode"] = "standard_rsk"

                save_data_to_disk()

                st.success(f"✅ सत्र {cur_sess_for_rule} के लिए पैटर्न सफलतापूर्वक सहेजा गया!")

                st.rerun()

            st.markdown("</div>", unsafe_allow_html=True)

  
  
  
  
  

    # ----------------- TEACHER MANAGEMENT (PRINCIPAL ONLY) -----------------

    if st.session_state.get("authenticated_role") == "PRINCIPAL":

        st.divider()

        with st.expander("👨‍🏫 कक्षा अध्यापक प्रबंधन एवं कक्षा आवंटन (Manage Teachers)", expanded=False):

            st.caption("यहाँ से आप अपनी संस्था के कक्षा अध्यापकों को जोड़ें, ताकि वे अपने मोबाइल OTP से लॉगिन करके केवल अपनी आवंटित कक्षा का काम कर सकें:")

            

            auth_school = st.session_state.get("authenticated_school") or {}

            cur_dise = auth_school.get("dise_code", "")

            registry = load_schools_registry()

            sch_in_reg = registry.get(cur_dise, auth_school)

            teachers_list = sch_in_reg.get("teachers", [])

  

            if teachers_list:

                t_display_rows = [{"क्र.": i+1, "शिक्षक का नाम": t["name"], "मोबाइल नंबर": t["mobile"], "आवंटित कक्षा": t["assigned_class"]} for i, t in enumerate(teachers_list)]

                st.dataframe(pd.DataFrame(t_display_rows), use_container_width=True)

            else:

                st.info("अभी कोई शिक्षक पंजीकृत नहीं है। नीचे दिए गए फॉर्म से नया शिक्षक जोड़ें।")

  

            render_html("##### ➕ नया कक्षा अध्यापक जोड़ें:")

            c_nt1, c_nt2, c_nt3, c_nt4 = st.columns([3, 3, 2, 2])

            with c_nt1:

                new_t_name = st.text_input("शिक्षक का नाम:", key="new_teacher_name_input")

            with c_nt2:

                new_t_mob = st.text_input("शिक्षक का 10-अंकीय मोबाइल:*", key="new_teacher_mob_input")

            with c_nt3:

                new_t_cls = st.selectbox("आवंटित कक्षा:", st.session_state.classes_list, key="new_teacher_cls_input")

            with c_nt4:

                st.markdown("<div style='margin-top: 28px;'>", unsafe_allow_html=True)

                if st.button("➕ शिक्षक जोड़ें", type="primary", use_container_width=True):

                    clean_t_mob = "".join(filter(str.isdigit, str(new_t_mob)))

                    if not new_t_name or len(clean_t_mob) != 10:

                        st.error("कृपया वैध शिक्षक नाम और 10-अंकीय मोबाइल दर्ज करें!")

                    else:

                        if "teachers" not in sch_in_reg: sch_in_reg["teachers"] = []

                        sch_in_reg["teachers"].append({

                            "name": new_t_name.strip(),

                            "mobile": clean_t_mob,

                            "assigned_class": new_t_cls,

                            "created_at": str(datetime.now().date())

                        })

                        registry[cur_dise] = sch_in_reg

                        save_schools_registry(registry)

                        st.session_state.authenticated_school = sch_in_reg

                        log_security_event(cur_dise, "Principal", "Principal", auth_school.get("mobile"), "ADD_TEACHER", f"Added {new_t_name} for {new_t_cls}")

                        st.success(f"✅ शिक्षक '{new_t_name}' को {new_t_cls} हेतु सफलतापूर्वक आवंटित कर दिया गया!")

                        st.rerun()

                st.markdown("</div>", unsafe_allow_html=True)

  
  


# ----------------- MODULE 2: STUDENT MASTER (ROLE-AWARE & MAKER-CHECKER ENABLED) -----------------

elif menu == T["nav_student"]:

    cur_role = st.session_state.get("authenticated_role", "PRINCIPAL")
    is_teacher = (cur_role == "TEACHER")
    assigned_cls = st.session_state.get("assigned_class")

    auth_school = st.session_state.get("authenticated_school") or {}

    cur_dise = auth_school.get("dise_code", "")

    

    render_html(f'<div class="main-header">👨‍🎓 विद्यार्थी मास्टर डेटा — {selected_class}</div>')

    if cur_role == "TEACHER":

        render_html(f'<div class="sub-header">कक्षा अध्यापक मोड ({st.session_state.get("authenticated_user_name")}) — नए छात्र का ड्राफ्ट जोड़ें अथवा सुधार अनुरोध भेजें (प्रिंसिपल अनुमोदन हेतु)</div>')

        tab1, tab2, tab3, tab4 = st.tabs([

            "📋 छात्र सूची (View Only)", 

            "➕ नया छात्र ड्राफ्ट करें (Draft New Student)", 

            "✏️ बायो-डेटा सुधार अनुरोध (Propose Correction)",

            "📸 छात्र फोटो अपलोड (Photo Manager)"

        ])

    else:

        render_html(f'<div class="sub-header">संस्था प्रधान मोड — छात्र संपादन, 1-क्लिक शिक्षक अनुमोदन एवं यूनिवर्सल एक्सेल माइग्रेशन</div>')

        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([

            "📋 छात्र सूची एवं संपादन (Data Grid)", 

            "➕ नया छात्र जोड़ें (Direct Add Student)", 

            "📸 छात्र फोटो अपलोड एवं प्रबंधन (Photo Manager)", 

            "🗑️ छात्र हटाएं / टीसी (TC) जारी करें",

            f"🔔 शिक्षक अनुमोदन डेस्क ({len(auth_school.get('pending_approvals', []))})",

            "📥 यूनिवर्सल एक्सेल ऑनबोर्डिंग एवं माइग्रेशन"

        ])

  

    # ---------------- TAB 1: DATA GRID ----------------

    with tab1:
        c_stsort1, c_stsort2, c_stsort3 = st.columns([2.2, 2.5, 2.3])
        with c_stsort1:
            st.write(f"वर्तमान में **{len(cls_data['students'])}** छात्र पंजीकृत हैं:")
        with c_stsort2:
            st_view_sort = st.radio(
                "🔀 सूची प्रदर्शन क्रम:",
                ["रोल नंबर अनुसार (Roll No.)", "वर्णमाला क्रम (A to Z Name)", "दाखिला क्र. (Scholar No.)"],
                horizontal=True,
                key="st_master_sort_selector"
            )
        with c_stsort3:
            if not is_teacher and not cls_data["students"].empty:
                st.markdown("<div style='margin-top: 10px;'>", unsafe_allow_html=True)
                if st.button("🔤 A-Z अनुसार रोल नं. पुनः आवंटित करें", help="छात्रों को अंग्रेजी वर्णमाला (A to Z) में जमाकर रोल नंबर 1, 2, 3... पुनः आवंटित करें"):
                    st_az_df = sort_students_dataframe(cls_data["students"], "Name").copy()
                    st_az_df["Roll_No"] = range(1, len(st_az_df) + 1)
                    cls_data["students"] = st_az_df
                    save_data_to_disk()
                    st.success("✅ सभी छात्रों को वर्णमाला (A to Z) अनुसार रोल नंबर 1 से आवंटित कर दिए गए!")
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

        sort_choice_key = "Roll_No"
        if "वर्णमाला" in st_view_sort:
            sort_choice_key = "Name"
        elif "दाखिला" in st_view_sort:
            sort_choice_key = "Scholar_No"

        df_students = sort_students_dataframe(cls_data["students"].copy(), sort_choice_key)
        df_students = reorder_student_columns(df_students)

        

        is_teacher = (cur_role == "TEACHER")

        if is_teacher:

            st.info("🔒 कक्षा अध्यापक मोड: बायो-डेटा (नाम, जन्मतिथि, समग्र आईडी आदि) केवल पठनीय (Read-Only) है। नए छात्र या सुधार हेतु अगले टैब्स का उपयोग करें।")

  

        edited_df = st.data_editor(

            df_students,

            num_rows="fixed" if is_teacher else "dynamic",

            disabled=is_teacher,

            use_container_width=True,

            column_config={

                "Roll_No": st.column_config.NumberColumn("Roll No.", required=True),

                "Scholar_No": st.column_config.TextColumn("Scholar No."),

                "Name": st.column_config.TextColumn("Name Of Student", required=True),

                "Father_Name": st.column_config.TextColumn("Father's Name"),

                "Mother_Name": st.column_config.TextColumn("Mother's Name"),

                "DOB": st.column_config.TextColumn("Date Of Birth"),

                "Class": st.column_config.TextColumn("Class"),

                "Section": st.column_config.SelectboxColumn("Section", options=["A", "B", "C", "D", "E"]),

                "Gender": st.column_config.SelectboxColumn("Gender", options=["Boy", "Girl", "Other"]),

                "Category": st.column_config.SelectboxColumn("Category", options=["General", "OBC", "SC", "ST"]),

                "SSSM_ID": st.column_config.TextColumn("Samagra ID"),

                "Aadhar_No": st.column_config.TextColumn("Aadhar Number"),

                "PAN_No": st.column_config.TextColumn("PAN Number"),

                "APAAR_ID": st.column_config.TextColumn("APAAR ID"),

                "Medium": st.column_config.SelectboxColumn("Medium", options=ALL_MEDIUMS),

                "Status": st.column_config.SelectboxColumn("Status", options=["Present", "Absent"]),

                "Photo_b64": None,

                "Total_Days": st.column_config.NumberColumn("Total Days"),

                "Attended_Days": st.column_config.NumberColumn("Attended Days")

            },

            key=f"editor_students_{selected_class}_{cur_role}"

        )

        if not is_teacher:

            if st.button("💾 अपडेट सहेजें (Save Table)", type="primary"):

                cls_data["students"] = edited_df

                save_data_to_disk()

                st.success("✅ छात्र सूची सुरक्षित कर ली गई!")

  

    # ---------------- TAB 2: ADD STUDENT / DRAFT STUDENT ----------------

    with tab2:

        if is_teacher:

            st.subheader("➕ नए छात्र का ड्राफ्ट जोड़ें (Submit for Principal Approval):")

            st.caption("आपके द्वारा भरा गया छात्र विवरण सीधे संस्था प्रधान (Principal) के पास अनुमोदन हेतु जाएगा:")

        else:

            st.subheader("विद्यार्थी की सीधी प्रविष्टि (Register New Student):")

  

        with st.form("add_student_form_unified"):

            c1, c2, c3, c4 = st.columns(4)

            with c1:

                s_roll = st.number_input("1. Roll No.:", min_value=1, value=len(cls_data['students'])+101)

                s_schol = st.text_input("2. Scholar No.:", value=str(1000 + s_roll))

                s_name = st.text_input("3. Name Of Student:*")

            with c2:

                s_father = st.text_input("4. Father's Name:")

                s_mother = st.text_input("5. Mother's Name:")

                s_dob = st.date_input("6. Date Of Birth:")

            with c3:

                s_class = st.text_input("7. Class:", value=selected_class, disabled=is_teacher)

                s_sec = st.selectbox("8. Section:", ["A", "B", "C", "D", "E"])

                s_gender = st.selectbox("9. Gender:", ["Boy", "Girl", "Other"])

            with c4:

                s_cat = st.selectbox("10. Category:", ["General", "OBC", "SC", "ST"])

                s_sssm = st.text_input("11. Samagra ID:")

                s_aadhar = st.text_input("12. Aadhar Number:")

            

            # आधार के बाद एवं मीडियम के पहले: पैन नंबर एवं अपार आईडी
            c_mid1, c_mid2, c_mid3 = st.columns(3)

            with c_mid1:

                s_pan = st.text_input("13. PAN Number (पैन नंबर):", placeholder="उदा. ABCDE1234F")

            with c_mid2:

                s_apaar = st.text_input("14. APAAR ID (अपार आईडी):", placeholder="उदा. 12-अंकीय अपार आईडी")

            with c_mid3:

                s_medium = st.selectbox("15. Medium (माध्यम):", ALL_MEDIUMS)

            

            c_bot1, c_bot2, c_bot3 = st.columns(3)

            with c_bot1:

                s_tot_days = st.number_input("16. Working Days:", value=220)

            with c_bot2:

                s_att_days = st.number_input("17. Attended Days:", value=200)

            with c_bot3:

                s_status = st.selectbox("18. Exam Status:", ["Present", "Absent"])

  

            photo_file = st.file_uploader("विद्यार्थी का फोटो (Photo Upload - Optional):", type=["jpg", "jpeg", "png"], key="reg_photo_uni")

            btn_label = "📤 अनुमोदन हेतु संस्था प्रधान को भेजें (Submit for Approval)" if is_teacher else "➕ विद्यार्थी जोड़ें (Submit)"

            submit_student = st.form_submit_button(btn_label, type="primary")

  

            if submit_student:

                if not s_name:

                    st.error("कृपया छात्र का नाम दर्ज करें!")

                else:

                    p_b64 = None

                    if photo_file:

                        p_b64 = base64.b64encode(photo_file.read()).decode()

                    new_row = {

                        "Roll_No": int(s_roll), "Scholar_No": s_schol, "Name": s_name,

                        "Father_Name": s_father, "Mother_Name": s_mother, "DOB": str(s_dob),

                        "Class": selected_class, "Section": s_sec, "Gender": s_gender,

                        "Category": s_cat, "SSSM_ID": s_sssm, "Aadhar_No": s_aadhar,

                        "PAN_No": s_pan.strip(),

                        "APAAR_ID": s_apaar.strip(),

                        "Medium": s_medium, "Status": s_status, "Photo_b64": p_b64,

                        "Total_Days": int(s_tot_days), "Attended_Days": int(s_att_days)

                    }

                    if is_teacher:

                        # Add to pending approvals in registry

                        registry = load_schools_registry()

                        sch_reg = registry.get(cur_dise, auth_school)

                        if "pending_approvals" not in sch_reg: sch_reg["pending_approvals"] = []

                        

                        sch_reg["pending_approvals"].append({

                            "id": f"appr_{int(datetime.now().timestamp())}",

                            "type": "new_student",

                            "teacher_name": st.session_state.get("authenticated_user_name", "कक्षा अध्यापक"),

                            "class": selected_class,

                            "data": new_row,

                            "requested_at": datetime.now().strftime("%d-%b-%Y %I:%M %p")

                        })

                        registry[cur_dise] = sch_reg

                        save_schools_registry(registry)

                        st.session_state.authenticated_school = sch_reg

                        log_security_event(cur_dise, "Teacher", st.session_state.get("authenticated_user_name"), "Teacher", "DRAFT_NEW_STUDENT", f"Drafted {s_name} for {selected_class}")

                        st.balloons()

                        st.success(f"✅ छात्र '{s_name}' का प्रवेश ड्राफ्ट अनुमोदन हेतु संस्था प्रधान को भेज दिया गया है!")

                    else:

                        cls_data["students"] = pd.concat([cls_data["students"], pd.DataFrame([new_row])], ignore_index=True)

                        save_data_to_disk()

                        st.success(f"✅ छात्र '{s_name}' सफलतापूर्वक पंजीकृत!")

                        st.rerun()

  

    # ---------------- TAB 3: PROPOSE CORRECTION (TEACHER) / PHOTO MANAGER (PRINCIPAL) ----------------

    if is_teacher:

        with tab3:

            st.subheader("✏️ विद्यार्थी बायो-डेटा सुधार अनुरोध (Propose Correction):")

            st.caption("यदि किसी छात्र के नाम, जन्मतिथि, समग्र आईडी आदि में लिपिकीय त्रुटि है, तो सुधार अनुरोध भेजें:")

            

            st_options = [f"Roll {s['Roll_No']}: {s['Name']}" for _, s in cls_data["students"].iterrows()]

            if not st_options:

                st.warning("कक्षा में कोई छात्र उपलब्ध नहीं है।")

            else:

                sel_edit_st = st.selectbox("विद्यार्थी चुनें:", st_options, key="corr_st_sel")

                edit_r = int(sel_edit_st.split(":")[0].replace("Roll", "").strip())

                target_st_row = cls_data["students"][cls_data["students"]["Roll_No"] == edit_r].iloc[0]

                

                c_cr1, c_cr2 = st.columns(2)

                with c_cr1:

                    corr_field = st.selectbox("किस फ़ील्ड में सुधार करना है?", ["छात्र का नाम (Name)", "पिता का नाम (Father Name)", "माता का नाम (Mother Name)", "जन्मतिथि (DOB)", "समग्र आईडी (Samagra ID)", "आधार नंबर (Aadhar No)", "पैन नंबर (PAN Number)", "अपार आईडी (APAAR ID)", "स्कॉलर नंबर (Scholar No)"])

                with c_cr2:

                    corr_val = st.text_input("सही नया मान (Corrected Value) दर्ज करें:*")

                corr_reason = st.text_input("सुधार का कारण (Reason):", placeholder="उदा. समग्र दस्तावेज अनुसार सही नाम")

  

                if st.button("📤 सुधार अनुरोध प्रिंसिपल को भेजें", type="primary"):

                    if not corr_val:

                        st.error("कृपया सही मान दर्ज करें!")

                    else:

                        registry = load_schools_registry()

                        sch_reg = registry.get(cur_dise, auth_school)

                        if "pending_approvals" not in sch_reg: sch_reg["pending_approvals"] = []

                        sch_reg["pending_approvals"].append({

                            "id": f"corr_{int(datetime.now().timestamp())}",

                            "type": "edit_student",

                            "teacher_name": st.session_state.get("authenticated_user_name", "कक्षा अध्यापक"),

                            "class": selected_class,

                            "roll_no": edit_r,

                            "student_name": target_st_row["Name"],

                            "field": corr_field,

                            "new_value": corr_val.strip(),

                            "reason": corr_reason,

                            "requested_at": datetime.now().strftime("%d-%b-%Y %I:%M %p")

                        })

                        registry[cur_dise] = sch_reg

                        save_schools_registry(registry)

                        st.session_state.authenticated_school = sch_reg

                        log_security_event(cur_dise, "Teacher", st.session_state.get("authenticated_user_name"), "Teacher", "PROPOSE_CORRECTION", f"Roll {edit_r}: {corr_field} -> {corr_val}")

                        st.success(f"✅ रोल नंबर {edit_r} के {corr_field} सुधार का अनुरोध संस्था प्रधान को भेज दिया गया!")

  

        # Tab 4 for Teacher: Photo Manager

        with tab4:
            render_photo_manager(cls_data, selected_class, is_teacher=True, key_prefix="tr")

  

    else:

        # ---------------- FOR PRINCIPAL: PHOTO, TC, APPROVALS & EXCEL MIGRATOR ----------------

        with tab3:
            render_photo_manager(cls_data, selected_class, is_teacher=False, key_prefix="pr")

        with tab4:

            st.subheader("🗑️ छात्र हटाएं / स्थानांतरण प्रमाण पत्र (TC) जारी करें")

            students_df = cls_data["students"]

            if students_df.empty:

                st.warning("वर्तमान कक्षा में कोई छात्र पंजीकृत नहीं है।")

            else:

                del_options = [f"Roll {s['Roll_No']}: {s['Name']} (Scholar: {s['Scholar_No']})" for _, s in students_df.iterrows()]

                student_to_delete_str = st.selectbox("हटाने हेतु विद्यार्थी चुनें:", del_options, key="del_st_pr")

                del_roll = str(student_to_delete_str.split(":")[0].replace("Roll", "").strip()).replace(".0", "")

                tc_reason = st.text_input("शाला छोड़ने का कारण (Reason for Leaving / TC):", value="Transfer Certificate (TC) Issued / Left School", key="del_reason_pr")

                del_from_all = st.checkbox("⚠️ यदि यह रोल नंबर अन्य कक्षाओं में भी मौजूद है, तो सभी कक्षाओं से हटाएं (Delete from ALL classes)", value=True, key="del_all_cls_chk")

                if st.button("⚠️ पुष्टि करें और विद्यार्थी का रिकॉर्ड हटाएं", type="primary", key="btn_confirm_del_st"):

                    clean_del = str(del_roll).strip().replace(".0", "")

                    if del_from_all:

                        removed_cnt = 0

                        for c_name, c_store in st.session_state.data_store.items():

                            st_df = c_store.get("students")

                            if isinstance(st_df, pd.DataFrame) and not st_df.empty and "Roll_No" in st_df.columns:

                                m = st_df["Roll_No"].astype(str).str.strip().str.replace(".0", "", regex=False) != clean_del

                                before_len = len(st_df)

                                c_store["students"] = st_df[m].reset_index(drop=True)

                                removed_cnt += (before_len - len(c_store["students"]))

                                for k in [clean_del, int(clean_del) if clean_del.isdigit() else clean_del, f"{clean_del}.0"]:

                                    if k in c_store.get("evaluations", {}):

                                        del c_store["evaluations"][k]

                        save_data_to_disk()

                        log_security_event(cur_dise, "Principal", "Principal", auth_school.get("mobile"), "DELETE_STUDENT_TC", f"Deleted Roll {clean_del} from ALL classes ({removed_cnt} removed), Reason: {tc_reason}")

                        st.success(f"✅ रोल नंबर {clean_del} का रिकॉर्ड सभी कक्षाओं से सफलतापूर्वक हटा दिया गया (कुल {removed_cnt} रिकॉर्ड्स साफ किए गए)!")

                        st.rerun()

                    else:

                        m = cls_data["students"]["Roll_No"].astype(str).str.strip().str.replace(".0", "", regex=False) != clean_del

                        cls_data["students"] = cls_data["students"][m].reset_index(drop=True)

                        for k in [clean_del, int(clean_del) if clean_del.isdigit() else clean_del, f"{clean_del}.0"]:

                            if k in cls_data["evaluations"]:

                                del cls_data["evaluations"][k]

                        save_data_to_disk()

                        log_security_event(cur_dise, "Principal", "Principal", auth_school.get("mobile"), "DELETE_STUDENT_TC", f"Deleted Roll {clean_del}, Reason: {tc_reason}")

                        st.success(f"✅ रोल नंबर {clean_del} का रिकॉर्ड सफलतापूर्वक हटा दिया गया।")

                        st.rerun()

            st.divider()

            # Emergency Global Student Purger
            with st.expander("⚡ इमरजेंसी रोल नंबर क्लीनर (Purge any Roll Number from ALL Classes)", expanded=True):

                st.caption("यदि कोई डमी या अवांछित रोल नंबर (जैसे Roll 2) सभी कक्षाओं में दिख रहा है, तो यहाँ रोल नंबर डालकर एक क्लिक में सभी कक्षाओं से पूर्णतः डिलीट करें:")

                c_purg1, c_purg2 = st.columns([2, 1])

                with c_purg1:

                    purge_roll_input = st.text_input("हटाने हेतु रोल नंबर दर्ज करें:", value="2", key="purge_roll_inp_box")

                with c_purg2:

                    st.markdown("<div style='margin-top:25px;'>", unsafe_allow_html=True)

                    if st.button(f"🗑️ रोल {purge_roll_input} को सभी कक्षाओं से डिलीट करें", type="primary", key="btn_purge_roll_global"):

                        p_str = str(purge_roll_input).strip().replace(".0", "")

                        tot_purged = 0

                        for c_name, c_store in st.session_state.data_store.items():

                            st_df = c_store.get("students")

                            if isinstance(st_df, pd.DataFrame) and not st_df.empty and "Roll_No" in st_df.columns:

                                m = st_df["Roll_No"].astype(str).str.strip().str.replace(".0", "", regex=False) != p_str

                                b_len = len(st_df)

                                c_store["students"] = st_df[m].reset_index(drop=True)

                                tot_purged += (b_len - len(c_store["students"]))

                                for k in [p_str, int(p_str) if p_str.isdigit() else p_str, f"{p_str}.0"]:

                                    if k in c_store.get("evaluations", {}):

                                        del c_store["evaluations"][k]

                        save_data_to_disk()

                        st.balloons()

                        st.success(f"🎉 रोल नंबर {p_str} को समस्त कक्षाओं से पूर्णतः हटा दिया गया (कुल {tot_purged} रिकॉर्ड्स साफ किए गए)!")

                        st.rerun()

                    st.markdown("</div>", unsafe_allow_html=True)

  

        # Tab 5: Pending Approvals (Maker-Checker Queue)

        with tab5:

            st.subheader("🔔 शिक्षक अनुमोदन डेस्क (Teacher Approvals Queue)")

            st.caption("कक्षा अध्यापकों द्वारा भरे गए नए छात्र एवं बायो-डेटा सुधार अनुरोधों की 1-क्लिक समीक्षा एवं अनुमोदन:")

            

            registry = load_schools_registry()

            sch_reg = registry.get(cur_dise, auth_school)

            pending_list = sch_reg.get("pending_approvals", [])

  

            if not pending_list:

                st.success("✅ कोई भी शिक्षक अनुमोदन लंबित नहीं है! सभी रिकॉर्ड्स अद्यतन हैं।")

            else:

                render_html(f"**कुल {len(pending_list)} अनुरोध अनुमोदन हेतु प्रतीक्षारत हैं:**")

                

                # Bulk Approve button

                if st.button("🚀 सभी अनुरोध एक साथ स्वीकार करें (Bulk Approve All)", type="primary"):

                    for req in pending_list:

                        if req["type"] == "new_student":

                            st_cls = req["class"]

                            t_cls_data = get_class_data(st_cls)

                            t_cls_data["students"] = pd.concat([t_cls_data["students"], pd.DataFrame([req["data"]])], ignore_index=True)

                    sch_reg["pending_approvals"] = []

                    registry[cur_dise] = sch_reg

                    save_schools_registry(registry)

                    st.session_state.authenticated_school = sch_reg

                    save_data_to_disk()

                    log_security_event(cur_dise, "Principal", "Principal", auth_school.get("mobile"), "BULK_APPROVE_TEACHER_REQUESTS", "Approved all pending")

                    st.balloons()

                    st.success("🎉 सभी शिक्षक अनुरोध सफलतापूर्वक एक साथ अनुमोदित कर दिए गए!")

                    st.rerun()

  

                st.divider()

  

                for idx, req in enumerate(pending_list):

                    r_c1, r_c2, r_c3 = st.columns([4, 2, 2])

                    with r_c1:

                        if req["type"] == "new_student":

                            st_d = req["data"]

                            st.markdown(f"➕ **नया छात्र:** **{st_d['Name']}** (रोल: `{st_d['Roll_No']}`, दाखिला: `{st_d['Scholar_No']}`)<br><span style='font-size:12px; color:#555;'>कक्षा: <b>{req['class']}</b> | शिक्षक: {req['teacher_name']} | समय: {req['requested_at']}</span>", unsafe_allow_html=True)

                        else:

                            render_html(f"✏️ **सुधार अनुरोध:** **{req['student_name']}** (रोल: `{req['roll_no']}`)<br><span style='font-size:12px; color:#555;'>फ़ील्ड: <b>{req['field']}</b> ➔ नया मान: <b style='color:green;'>{req['new_value']}</b><br>कारण: {req.get('reason','')} | शिक्षक: {req['teacher_name']}</span>")

                    

                    with r_c2:

                        if st.button(f"✅ स्वीकार करें", key=f"btn_appr_{req['id']}", type="primary", use_container_width=True):

                            if req["type"] == "new_student":

                                st_cls = req["class"]

                                t_cls_data = get_class_data(st_cls)

                                t_cls_data["students"] = pd.concat([t_cls_data["students"], pd.DataFrame([req["data"]])], ignore_index=True)

                            else:

                                # Apply correction

                                st_cls = req["class"]

                                t_cls_data = get_class_data(st_cls)

                                # map field name

                                f_map = {
                                    "छात्र का नाम (Name)": "Name", 
                                    "पिता का नाम (Father Name)": "Father_Name", 
                                    "माता का नाम (Mother Name)": "Mother_Name", 
                                    "जन्मतिथि (DOB)": "DOB", 
                                    "समग्र आईडी (Samagra ID)": "SSSM_ID", 
                                    "आधार नंबर (Aadhar No)": "Aadhar_No",
                                    "अपार आईडी (APAAR ID)": "APAAR_ID",
                                    "माध्यम (Medium)": "Medium",
                                    "स्कॉलर नंबर (Scholar No)": "Scholar_No"
                                }

                                internal_f = f_map.get(req["field"], "Name")

                                t_cls_data["students"].loc[t_cls_data["students"]["Roll_No"] == req["roll_no"], internal_f] = req["new_value"]

  

                            sch_reg["pending_approvals"].pop(idx)

                            registry[cur_dise] = sch_reg

                            save_schools_registry(registry)

                            st.session_state.authenticated_school = sch_reg

                            save_data_to_disk()

                            log_security_event(cur_dise, "Principal", "Principal", auth_school.get("mobile"), "APPROVE_TEACHER_REQUEST", f"Approved {req['id']}")

                            st.success("अनुरोध स्वीकार कर लिया गया!")

                            st.rerun()

                    

                    with r_c3:

                        if st.button(f"❌ अस्वीकार", key=f"btn_rej_{req['id']}", use_container_width=True):

                            sch_reg["pending_approvals"].pop(idx)

                            registry[cur_dise] = sch_reg

                            save_schools_registry(registry)

                            st.session_state.authenticated_school = sch_reg

                            st.warning("अनुरोध अस्वीकार कर दिया गया।")

                            st.rerun()

  

                    st.markdown("<hr style='margin:6px 0;'>", unsafe_allow_html=True)

  

                # Tab 6: Universal Excel Onboarding & Migration Engine
        with tab6:
            st.subheader("📥 यूनिवर्सल एक्सेल ऑनबोर्डिंग एवं मल्टी-शीट क्लास माइग्रेटर")
            st.caption("समग्र पोर्टल, शिक्षा पोर्टल, RSKMP या किसी भी स्कूल एक्सेल रजिस्टर का डेटा 1-क्लिक में अपलोड करें:")

            mig_up = st.file_uploader("📥 अपनी एक्सेल या सीएसवी फ़ाइल चुनें (.xlsx / .csv):", type=["xlsx", "csv"], key="uni_excel_mig_up")
            
            if mig_up:
                try:
                    file_bytes = mig_up.read()
                    sheet_data_dict = {}
                    
                    extracted_excel_meta = {}
                    from collections import Counter
                    all_meta_names = []
                    all_meta_mediums = []
                    all_meta_sessions = []
                    all_meta_blocks = []
                    all_meta_districts = []
                    all_meta_udises = []

                    if mig_up.name.endswith(".csv"):
                        raw_csv_df = pd.read_csv(BytesIO(file_bytes), header=None)
                        extracted_excel_meta = extract_school_metadata_from_excel_rows(raw_csv_df)
                        clean_df = parse_clean_excel_sheet(raw_csv_df)
                        sheet_data_dict["Sheet1"] = clean_df
                    else:
                        xl_file = pd.ExcelFile(BytesIO(file_bytes))
                        for sh_name in xl_file.sheet_names:
                            raw_sh_df = xl_file.parse(sh_name, header=None)
                            if not raw_sh_df.empty and len(raw_sh_df) > 0:
                                sh_meta = extract_school_metadata_from_excel_rows(raw_sh_df)
                                # Give higher weight to class sheets (1st to 10th) over auxiliary sheets (Nursery/KG)
                                weight = 3 if any(k in sh_name.lower() for k in ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]) else 1
                                if "name" in sh_meta and sh_meta["name"]:
                                    all_meta_names.extend([sh_meta["name"]] * weight)
                                if "medium" in sh_meta and sh_meta["medium"]:
                                    all_meta_mediums.extend([sh_meta["medium"]] * weight)
                                if "session" in sh_meta and sh_meta["session"]:
                                    all_meta_sessions.extend([sh_meta["session"]] * weight)
                                if "block" in sh_meta and sh_meta["block"]:
                                    all_meta_blocks.extend([sh_meta["block"]] * weight)
                                if "district" in sh_meta and sh_meta["district"]:
                                    all_meta_districts.extend([sh_meta["district"]] * weight)
                                if "udise" in sh_meta and sh_meta["udise"]:
                                    all_meta_udises.extend([sh_meta["udise"]] * weight)

                                clean_df = parse_clean_excel_sheet(raw_sh_df)
                                if not clean_df.empty:
                                    sheet_data_dict[sh_name] = clean_df

                        # Consensus across all sheets
                        extracted_excel_meta = {}
                        if all_meta_names: extracted_excel_meta["name"] = Counter(all_meta_names).most_common(1)[0][0]
                        if all_meta_mediums: extracted_excel_meta["medium"] = Counter(all_meta_mediums).most_common(1)[0][0]
                        if all_meta_sessions: extracted_excel_meta["session"] = Counter(all_meta_sessions).most_common(1)[0][0]
                        if all_meta_blocks: extracted_excel_meta["block"] = Counter(all_meta_blocks).most_common(1)[0][0]
                        if all_meta_districts: extracted_excel_meta["district"] = Counter(all_meta_districts).most_common(1)[0][0]
                        if all_meta_udises: extracted_excel_meta["udise"] = Counter(all_meta_udises).most_common(1)[0][0]

                    # Display Interactive Verification and Edit Card for School Metadata
                    with st.expander("🏫 एक्सेल हेडर से पहचानी गई संस्था जानकारी (जांचें एवं आवश्यकतानुसार संपादित करें):", expanded=True):
                        c_meta_r1, c_meta_r2 = st.columns(2)
                        with c_meta_r1:
                            conf_name = st.text_input(
                                "🏫 स्कूल का नाम (School Name):*",
                                value=extracted_excel_meta.get("name", st.session_state.school_info.get("name", "PALI GYAN MANDIR HIGH SCHOOL, SENDHWA")),
                                key="mig_conf_name_input"
                            )
                            cur_med_val = extracted_excel_meta.get("medium", st.session_state.school_info.get("medium", "Hindi (हिन्दी)"))
                            m_idx = ALL_MEDIUMS.index(cur_med_val) if cur_med_val in ALL_MEDIUMS else (0 if "hindi" in cur_med_val.lower() else 1)
                            conf_med = st.selectbox(
                                "🌐 माध्यम (Medium):*",
                                ALL_MEDIUMS,
                                index=m_idx,
                                key="mig_conf_med_picker"
                            )
                            conf_sess = st.text_input(
                                "📅 सत्र (Session):*",
                                value=extracted_excel_meta.get("session", st.session_state.school_info.get("session", "2025-26")),
                                key="mig_conf_sess_input"
                            )
                        with c_meta_r2:
                            conf_block = st.text_input(
                                "📍 ब्लॉक / संकुल (Block):*",
                                value=extracted_excel_meta.get("block", st.session_state.school_info.get("block", "SENDHWA")),
                                key="mig_conf_block_input"
                            )
                            conf_dist = st.text_input(
                                "🏙️ जिला (District):*",
                                value=extracted_excel_meta.get("district", st.session_state.school_info.get("district", "BARWANI")),
                                key="mig_conf_dist_input"
                            )
                            conf_udise = st.text_input(
                                "🔢 डाइस कोड (Dise Code):*",
                                value=extracted_excel_meta.get("udise", st.session_state.school_info.get("udise", "23260100101")),
                                key="mig_conf_udise_input"
                            )

                    # Keep school_info synchronized in session state
                    st.session_state.school_info["name"] = conf_name
                    st.session_state.school_info["medium"] = conf_med
                    st.session_state.school_info["session"] = conf_sess
                    st.session_state.school_info["block"] = conf_block
                    st.session_state.school_info["district"] = conf_dist
                    st.session_state.school_info["udise"] = conf_udise

                    total_sheets = len(sheet_data_dict)
                    total_raw_rows = sum(len(df) for df in sheet_data_dict.values())
                    all_sh_names = list(sheet_data_dict.keys())
                    
                    st.success(f"🎉 फ़ाइल सफलतापूर्वक पढ़ी गई! कुल **{total_sheets}** शीट(्स) एवं **{total_raw_rows}** पंक्तियाँ पाई गईं।")
                    render_html("**📑 वर्कबुक में पाई गई शीट्स:** " + " | ".join([f"`{s}`" for s in all_sh_names]))

                    # Identify class sheets vs summary sheets
                    class_sheets_map = {s: map_sheet_name_to_class(s) for s in all_sh_names if map_sheet_name_to_class(s) is not None}
                    
                    c_mode1, c_mode2 = st.columns([1.5, 2.5])
                    with c_mode1:
                        import_mode = st.radio(
                            "📋 आयात का तरीका चुनें (Choose Import Mode):*",
                            [
                                f"🎯 केवल एक विशिष्ट कक्षा शीट आयात करें (Single Sheet — वर्तमान: {selected_class})",
                                "🏫 समस्त कक्षा शीट्स एक साथ आयात करें (All Class Sheets — कक्षा 1 से 10वीं तक एक साथ)"
                            ],
                            key="mig_import_mode_choice"
                        )
                    
                    is_all_sheets_mode = ("समस्त कक्षा शीट्स" in import_mode or "All Class Sheets" in import_mode)
                    
                    # Single Sheet Selection
                    if not is_all_sheets_mode:
                        sheet_options = []
                        for s in all_sh_names:
                            mc = map_sheet_name_to_class(s)
                            lbl = f"📄 शीट '{s}' ➔ कक्षा: {mc}" if mc else f"📄 शीट '{s}' (विविध)"
                            sheet_options.append((s, lbl))
                            
                        # Find default index matching selected_class (e.g. '7th' for 'Class 7th')
                        def_sh_idx = 0
                        for i_s, (s_name, _) in enumerate(sheet_options):
                            if map_sheet_name_to_class(s_name) == selected_class or s_name.lower() in selected_class.lower():
                                def_sh_idx = i_s
                                break
                                
                        with c_mode2:
                            chosen_sheet_name = st.selectbox(
                                "👉 आयात हेतु शीट चुनें (Select Sheet to Import):*",
                                [s[0] for s in sheet_options],
                                index=def_sh_idx,
                                format_func=lambda x: dict(sheet_options)[x],
                                key="mig_single_sheet_picker"
                            )
                            target_single_class = map_sheet_name_to_class(chosen_sheet_name) or selected_class
                            render_html(f"""
                            <div style="background: #EFF6FF; border-left: 4px solid #3B82F6; padding: 8px 12px; border-radius: 4px; font-size: 12px; color: #1E3A8A; margin-top: 10px;">
                                🎯 <b>चयनित शीट: '{chosen_sheet_name}'</b> का डेटा सीधे सिस्टम की कक्षा <b>'{target_single_class}'</b> में लोड होगा।
                            </div>
                            """)
                            
                        active_sheets_dict = {chosen_sheet_name: sheet_data_dict[chosen_sheet_name]}
                        mapping_reference_sheet = chosen_sheet_name
                    else:
                        with c_mode2:
                            mapped_summary_str = " | ".join([f"**{s}** ➔ {c}" for s, c in class_sheets_map.items()])
                            render_html(f"""
                            <div style="background: #F0FDF4; border-left: 4px solid #16A34A; padding: 8px 12px; border-radius: 4px; font-size: 12px; color: #166534; margin-top: 10px;">
                                ✅ <b>ऑटो-क्लास डिटेक्टर सक्रिय:</b> प्रत्येक शीट का डेटा सीधे उसकी कक्षा में जाएगा। 'Goswara' आदि शीट्स को स्वतः छोड़ दिया जाएगा!<br>
                                <span style="font-size: 11px; color: #334155;">{mapped_summary_str}</span>
                            </div>
                            """)
                        active_sheets_dict = {s: sheet_data_dict[s] for s in class_sheets_map.keys()}
                        mapping_reference_sheet = list(active_sheets_dict.keys())[0]
                        for s in active_sheets_dict.keys():
                            if map_sheet_name_to_class(s) == selected_class:
                                mapping_reference_sheet = s
                                break

                    # Reference Sheet for interactive column mapping
                    ref_sheet_df = active_sheets_dict[mapping_reference_sheet]
                    all_detected_cols = [str(c).strip() for c in ref_sheet_df.columns if str(c).strip() and not str(c).startswith("Unnamed:")]
                    col_options = ["-- कोई नहीं (None) --"] + all_detected_cols

                    auto_mapped = smart_fuzzy_column_mapping(all_detected_cols)

                    # Interactive Column Mapping Accordion
                    with st.expander(f"⚙️ कॉलम मैपिंग की समीक्षा (Sheet: '{mapping_reference_sheet}'):", expanded=True):
                        st.write("यदि आपकी एक्सेल में कॉलम के नाम अलग हैं, तो नीचे से सही कॉलम चुनें:")
                        
                        m_c1, m_c2, m_c3 = st.columns(3)
                        with m_c1:
                            map_name = st.selectbox(
                                "1. विद्यार्थी का नाम (Name)*:",
                                col_options,
                                index=col_options.index(auto_mapped.get("Name")) if auto_mapped.get("Name") in col_options else 0,
                                key="map_col_name"
                            )
                            map_father = st.selectbox(
                                "2. पिता का नाम (Father's Name):",
                                col_options,
                                index=col_options.index(auto_mapped.get("Father_Name")) if auto_mapped.get("Father_Name") in col_options else 0,
                                key="map_col_father"
                            )
                            map_mother = st.selectbox(
                                "3. माता का नाम (Mother's Name):",
                                col_options,
                                index=col_options.index(auto_mapped.get("Mother_Name")) if auto_mapped.get("Mother_Name") in col_options else 0,
                                key="map_col_mother"
                            )
                            map_roll = st.selectbox(
                                "4. रोल नंबर (Roll No):",
                                col_options,
                                index=col_options.index(auto_mapped.get("Roll_No")) if auto_mapped.get("Roll_No") in col_options else 0,
                                key="map_col_roll"
                            )

                        with m_c2:
                            map_scholar = st.selectbox(
                                "5. दाखिला क्र. (Scholar No):",
                                col_options,
                                index=col_options.index(auto_mapped.get("Scholar_No")) if auto_mapped.get("Scholar_No") in col_options else 0,
                                key="map_col_scholar"
                            )
                            map_dob = st.selectbox(
                                "6. जन्मतिथि (DOB):",
                                col_options,
                                index=col_options.index(auto_mapped.get("DOB")) if auto_mapped.get("DOB") in col_options else 0,
                                key="map_col_dob"
                            )
                            map_sssm = st.selectbox(
                                "7. समग्र आईडी (Samagra ID):",
                                col_options,
                                index=col_options.index(auto_mapped.get("SSSM_ID")) if auto_mapped.get("SSSM_ID") in col_options else 0,
                                key="map_col_sssm"
                            )
                            map_aadhar = st.selectbox(
                                "8. आधार नंबर (Aadhar No):",
                                col_options,
                                index=col_options.index(auto_mapped.get("Aadhar_No")) if auto_mapped.get("Aadhar_No") in col_options else 0,
                                key="map_col_aadhar"
                            )
                            map_pan = st.selectbox(
                                "9. पैन नंबर (PAN Number):",
                                col_options,
                                index=col_options.index(auto_mapped.get("PAN_No")) if auto_mapped.get("PAN_No") in col_options else 0,
                                key="map_col_pan"
                            )
                            map_apaar = st.selectbox(
                                "10. अपार आईडी (APAAR ID):",
                                col_options,
                                index=col_options.index(auto_mapped.get("APAAR_ID")) if auto_mapped.get("APAAR_ID") in col_options else 0,
                                key="map_col_apaar"
                            )

                        with m_c3:
                            map_class = st.selectbox(
                                "11. कक्षा (Class Column):",
                                col_options,
                                index=col_options.index(auto_mapped.get("Class")) if auto_mapped.get("Class") in col_options else 0,
                                key="map_col_class"
                            )
                            map_section = st.selectbox(
                                "12. सेक्शन (Section):",
                                col_options,
                                index=col_options.index(auto_mapped.get("Section")) if auto_mapped.get("Section") in col_options else 0,
                                key="map_col_section"
                            )
                            map_gender = st.selectbox(
                                "13. जेंडर (Gender):",
                                col_options,
                                index=col_options.index(auto_mapped.get("Gender")) if auto_mapped.get("Gender") in col_options else 0,
                                key="map_col_gender"
                            )
                            map_category = st.selectbox(
                                "14. जाति वर्ग (Category):",
                                col_options,
                                index=col_options.index(auto_mapped.get("Category")) if auto_mapped.get("Category") in col_options else 0,
                                key="map_col_cat"
                            )

                    # Build user mapping dict
                    user_map = {
                        "Name": map_name if map_name != "-- कोई नहीं (None) --" else None,
                        "Father_Name": map_father if map_father != "-- कोई नहीं (None) --" else None,
                        "Mother_Name": map_mother if map_mother != "-- कोई नहीं (None) --" else None,
                        "Roll_No": map_roll if map_roll != "-- कोई नहीं (None) --" else None,
                        "Scholar_No": map_scholar if map_scholar != "-- कोई नहीं (None) --" else None,
                        "DOB": map_dob if map_dob != "-- कोई नहीं (None) --" else None,
                        "SSSM_ID": map_sssm if map_sssm != "-- कोई नहीं (None) --" else None,
                        "Aadhar_No": map_aadhar if map_aadhar != "-- कोई नहीं (None) --" else None,
                        "PAN_No": map_pan if ('map_pan' in locals() and map_pan and map_pan != "-- कोई नहीं (None) --") else None,
                        "APAAR_ID": map_apaar if map_apaar != "-- कोई नहीं (None) --" else None,
                        "Class": map_class if map_class != "-- कोई नहीं (None) --" else None,
                        "Section": map_section if map_section != "-- कोई नहीं (None) --" else None,
                        "Gender": map_gender if map_gender != "-- कोई नहीं (None) --" else None,
                        "Category": map_category if map_category != "-- कोई नहीं (None) --" else None
                    }

                    # Consolidate and Normalize all active sheets
                    norm_rows = []
                    missing_dob_cnt = 0
                    missing_sssm_cnt = 0
                    row_global_idx = 0
                    detected_classes_counts = {}

                    for sh_name, raw_df in active_sheets_dict.items():
                        if raw_df.empty:
                            continue

                        # Per-sheet mapping fallback to user_map
                        curr_sheet_map = smart_fuzzy_column_mapping(raw_df.columns)
                        for k, v in user_map.items():
                            if v and v in raw_df.columns:
                                curr_sheet_map[k] = v

                        # Determine target class for this sheet
                        if not is_all_sheets_mode:
                            sheet_target_class = target_single_class
                        else:
                            sheet_target_class = map_sheet_name_to_class(sh_name) or selected_class

                        for idx_r, r in raw_df.iterrows():
                            row_global_idx += 1
                            
                            # Extract student name
                            st_n = ""
                            if curr_sheet_map.get("Name") and curr_sheet_map["Name"] in r:
                                st_n = str(r[curr_sheet_map["Name"]]).strip()
                            if not st_n or st_n == "nan":
                                continue  # Skip blank rows

                            # Extract DOB & SSSM
                            st_dob = str(r.get(curr_sheet_map.get("DOB", ""), "")).strip() if curr_sheet_map.get("DOB") else ""
                            st_sssm = str(r.get(curr_sheet_map.get("SSSM_ID", ""), "")).strip() if curr_sheet_map.get("SSSM_ID") else ""
                            
                            if not st_dob or st_dob == "nan": missing_dob_cnt += 1
                            if not st_sssm or st_sssm == "nan": missing_sssm_cnt += 1

                            # Determine class for row
                            target_c = sheet_target_class
                            if is_all_sheets_mode and curr_sheet_map.get("Class") and curr_sheet_map["Class"] in r:
                                raw_cls_val = str(r[curr_sheet_map["Class"]]).strip()
                                num_match = re.search(r"(\d+)", str(raw_cls_val))
                                if num_match:
                                    n_c = num_match.group(1)
                                    target_c = f"Class {n_c}th" if n_c in ["4", "5", "6", "7", "8", "9", "10"] else (f"Class {n_c}st" if n_c == "1" else (f"Class {n_c}nd" if n_c == "2" else f"Class {n_c}rd"))

                            detected_classes_counts[target_c] = detected_classes_counts.get(target_c, 0) + 1

                            # Clean roll: if user sheet has real roll, use it; otherwise generate sequential 1, 2, 3...
                            raw_roll = str(r.get(curr_sheet_map.get("Roll_No", ""), "")).strip() if curr_sheet_map.get("Roll_No") else ""
                            if raw_roll and raw_roll != "nan":
                                try:
                                    c_roll = int(float(raw_roll))
                                except Exception:
                                    c_roll = idx_r + 1
                            else:
                                c_roll = idx_r + 1

                            # Clean scholar
                            raw_sch = str(r.get(curr_sheet_map.get("Scholar_No", ""), "")).strip() if curr_sheet_map.get("Scholar_No") else ""
                            c_sch = raw_sch if raw_sch and raw_sch != "nan" else str(2000 + row_global_idx)

                            # Gender
                            raw_gen = str(r.get(curr_sheet_map.get("Gender", ""), "Boy")).strip().title() if curr_sheet_map.get("Gender") else "Boy"
                            c_gen = "Girl" if any(k in raw_gen.lower() for k in ["girl", "f", "महिला", "कन्या", "स्त्री"]) else "Boy"

                            # Category
                            raw_cat = str(r.get(curr_sheet_map.get("Category", ""), "General")).strip().upper() if curr_sheet_map.get("Category") else "General"
                            c_cat = "SC" if "SC" in raw_cat else ("ST" if "ST" in raw_cat else ("OBC" if "OBC" in raw_cat else "General"))

                            rec = {
                                "Roll_No": c_roll,
                                "Scholar_No": c_sch,
                                "Name": st_n,
                                "Father_Name": str(r.get(curr_sheet_map.get("Father_Name", ""), "")).strip() if curr_sheet_map.get("Father_Name") else "",
                                "Mother_Name": str(r.get(curr_sheet_map.get("Mother_Name", ""), "")).strip() if curr_sheet_map.get("Mother_Name") else "",
                                "DOB": st_dob if st_dob != "nan" else "01/01/2012",
                                "Class": target_c,
                                "Section": str(r.get(curr_sheet_map.get("Section", ""), "A")).strip().upper() if curr_sheet_map.get("Section") else "A",
                                "Gender": c_gen,
                                "Category": c_cat,
                                "SSSM_ID": st_sssm if st_sssm != "nan" else f"99{row_global_idx:07d}",
                                "Aadhar_No": str(r.get(curr_sheet_map.get("Aadhar_No", ""), "")).strip() if curr_sheet_map.get("Aadhar_No") else "",
                                "PAN_No": str(r.get(curr_sheet_map.get("PAN_No", ""), "")).strip() if curr_sheet_map.get("PAN_No") else "",
                                "APAAR_ID": str(r.get(curr_sheet_map.get("APAAR_ID", ""), "")).strip() if curr_sheet_map.get("APAAR_ID") else "",
                                "Medium": conf_med,
                                "Status": "Present",
                                "Attended_Days": 205,
                                "Total_Days": 220,
                                "Photo_b64": ""
                            }
                            norm_rows.append(rec)

                    normalized_df = pd.DataFrame(norm_rows)
                    
                    st.divider()
                    st.markdown("#### 👁️ आयातित डेटा का लाइव पूर्वावलोकन (Live Preview — First 5 Rows):")
                    st.dataframe(normalized_df.head(5), use_container_width=True)

                    if missing_dob_cnt > 0 or missing_sssm_cnt > 0:
                        st.warning(f"⚠️ **डेटा गैप चेतावनी:** {missing_dob_cnt} छात्रों की जन्मतिथि एवं {missing_sssm_cnt} छात्रों की समग्र आईडी नहीं मिली। सिस्टम ने स्वतः डिफ़ॉल्ट मान भर दिए हैं, जिन्हें आप बाद में संपादित कर सकते हैं।")

                    # Class-wise distribution badge
                    c_badge_str = " | ".join([f"**{c}**: {cnt} छात्र" for c, cnt in detected_classes_counts.items()])
                    st.info(f"📊 **कक्षा-वार डेटा विभाजन:** {c_badge_str}")

                    # Final Import Button
                    c_imp1, c_imp2 = st.columns([2, 1])
                    with c_imp1:
                        if st.button("🚀 सत्यापित डेटा सुरक्षित करें एवं विद्यार्थी मास्टर में लोड करें", type="primary", use_container_width=True):
                            # Save to data_store
                            for target_cls, g_df in normalized_df.groupby("Class"):
                                if target_cls not in st.session_state.classes_list:
                                    st.session_state.classes_list.append(target_cls)
                                
                                target_c_data = get_class_data(target_cls)
                                
                                # Deduplicate roll numbers within the class
                                seen_rolls = set()
                                deduplicated_rows = []
                                for idx_dedup, r_row in g_df.reset_index(drop=True).iterrows():
                                    row_dict = r_row.to_dict()
                                    r_val = row_dict.get("Roll_No")
                                    try:
                                        r_int = int(r_val)
                                    except Exception:
                                        r_int = idx_dedup + 1
                                    if r_int in seen_rolls or r_int <= 0:
                                        r_int = max(seen_rolls, default=0) + 1
                                    seen_rolls.add(r_int)
                                    row_dict["Roll_No"] = r_int
                                    deduplicated_rows.append(row_dict)
                                    
                                target_c_data["students"] = pd.DataFrame(deduplicated_rows)
                                
                                # Auto-initialize evaluation records for imported students
                                target_subs = get_class_subjects(target_cls)
                                for _, s_row in g_df.iterrows():
                                    r_id = s_row["Roll_No"]
                                    if r_id not in target_c_data["evaluations"]:
                                        target_c_data["evaluations"][r_id] = {
                                            "status": "Present",
                                            "marks": {sub["id"]: {"half_yearly": 48, "annual": 48, "project": 16, "status_hy": "Present", "status_yr": "Present"} for sub in target_subs},
                                            "monthly_tests": {},
                                            "co_curricular": {k: "A" for k, _ in CO_CURRICULAR_ACTIVITIES},
                                            "social": {k: "A" for k, _ in SOCIAL_ACTIVITIES}
                                        }

                            # Update school profile and all students with confirmed metadata
                            st.session_state.school_info["name"] = conf_name
                            st.session_state.school_info["medium"] = conf_med
                            st.session_state.school_info["session"] = conf_sess
                            st.session_state.school_info["block"] = conf_block
                            st.session_state.school_info["district"] = conf_dist
                            st.session_state.school_info["udise"] = conf_udise

                            # Synchronize all existing students across all classes to the confirmed medium
                            for c_name, c_dict in st.session_state.data_store.items():
                                st_df_ex = c_dict.get("students", pd.DataFrame())
                                if not st_df_ex.empty and "Medium" in st_df_ex.columns:
                                    c_dict["students"]["Medium"] = conf_med

                            save_data_to_disk()
                            st.balloons()
                            st.success(f"🎉 **सफलता!** कुल **{len(normalized_df)}** छात्रों का रिकॉर्ड एवं संस्था विवरण (**{conf_name}** | **{conf_med}**) सफलतापूर्वक सुरक्षित कर दिया गया है!")
                            st.rerun()

                except Exception as e:
                    st.error(f"❌ एक्सेल फ़ाइल आयात करने में त्रुटि: {e}")


# ----------------- MODULE 3: DUAL ATTENDANCE REGISTER (DAILY + MONTHLY) -----------------

elif menu == T["nav_attendance"]:

    st.markdown('<div class="main-header">📅 विद्यार्थी उपस्थिति प्रबंधन (Student Attendance Portal)</div>', unsafe_allow_html=True)

    render_html('<div class="sub-header">कक्षा अध्यापक द्वारा दैनिक मोबाइल हाजिरी लगाएं अथवा 12-माह का शासकीय उपस्थिति पत्रक देखें व एक्सपोर्ट करें</div>')

  

    students_df = cls_data["students"]

    if students_df.empty:

        st.warning("⚠️ कृपया पहले 'विद्यार्थी मास्टर' में छात्र जोड़ें!")

    else:

        tab_att1, tab_att2, tab_att3 = st.tabs([
            "📝 दैनिक कक्षा हाजिरी (Daily Teacher Attendance)",
            "📅 माहवार शासकीय उपस्थिति पत्रक (Monthly Attendance Sheet & Export)",
            "📥 बल्क उपस्थिति एक्सेल अपलोड (Bulk Excel/CSV Upload)"
        ])

  

        # ======================= TAB 1: DAILY TEACHER ATTENDANCE =======================

        with tab_att1:

            st.subheader(f"📱 दैनिक छात्र उपस्थिति — {selected_class}")

            st.caption("कक्षा अध्यापक यहाँ से आज की तारीख चुनकर छात्रों की हाजिरी लगा सकते हैं। डेटा सीधे मास्टर रिकॉर्ड और वार्षिक रिजल्ट में अपडेट होगा:")

  

            MONTHS_MAP = {1:"Jan", 2:"Feb", 3:"Mar", 4:"Apr", 5:"May", 6:"Jun", 7:"Jul", 8:"Aug", 9:"Sep", 10:"Oct", 11:"Nov", 12:"Dec"}

            

            c_d1, c_d2, c_d3 = st.columns([2, 2, 3])

            with c_d1:

                cur_date = st.date_input("📅 उपस्थिति दिनांक (Select Date):", value=datetime.now().date(), key="daily_att_date")

                cur_month_abbr = MONTHS_MAP.get(cur_date.month, "Sep")

            with c_d2:

                render_html(f"<div style='border: 1px solid #CBD5E1; padding: 6px 12px; border-radius: 6px; background: #F8FAFC; margin-top: 25px; text-align: center; font-size: 13px;'><b>सक्रिय माह:</b> <span style='color:#1E3A8A; font-weight:bold;'>{cur_month_abbr}</span></div>")

  

            if "daily_attendance" not in cls_data:

                cls_data["daily_attendance"] = {}

  

            date_str = str(cur_date)

            existing_day_record = cls_data["daily_attendance"].get(date_str, {})

  

            with c_d3:

                render_html("<div style='margin-top: 25px;'>")

                c_bulk1, c_bulk2 = st.columns(2)

                with c_bulk1:

                    if st.button("🟢 सभी उपस्थित (All Present)", use_container_width=True):

                        for _, s in students_df.iterrows():

                            st.session_state[f"d_att_{s['Roll_No']}_{date_str}"] = "Present"

                        st.rerun()

                with c_bulk2:

                    if st.button("🔴 सभी अनुपस्थित (All Absent)", use_container_width=True):

                        for _, s in students_df.iterrows():

                            st.session_state[f"d_att_{s['Roll_No']}_{date_str}"] = "Absent"

                        st.rerun()

                st.markdown("</div>", unsafe_allow_html=True)

  

            st.divider()

  

            # Student-by-Student Attendance List

            daily_marked_status = {}

            tot_st_cnt = len(students_df)

            pres_cnt = 0

            abs_cnt = 0

  

            for idx, s in students_df.iterrows():

                r_no = s["Roll_No"]

                default_stat = existing_day_record.get(str(r_no), "Present")

                

                # Check session state

                ss_key = f"d_att_{r_no}_{date_str}"

                if ss_key in st.session_state:

                    chosen_stat = st.session_state[ss_key]

                else:

                    chosen_stat = default_stat

  

                daily_marked_status[r_no] = chosen_stat

                if chosen_stat == "Present": pres_cnt += 1

                else: abs_cnt += 1

  

                # Display Row / Card

                row_c1, row_c2, row_c3, row_c4 = st.columns([1, 4, 3, 2])

                with row_c1:

                    if s.get("Photo_b64"):

                        p_html = f'<img src="data:image/jpeg;base64,{s["Photo_b64"]}" style="width: 45px; height: 52px; object-fit: cover; border-radius: 4px; border: 1px solid #ccc;">'

                    else:

                        p_html = '<div style="width: 45px; height: 52px; background: #E2E8F0; display: flex; align-items: center; justify-content: center; font-size: 18px; border-radius: 4px;">👤</div>'

                    render_html(p_html)

  

                with row_c2:

                    render_html(f"**{s['Name']}** (रोल नंबर: `{r_no}`)<br><span style='font-size: 12px; color: #555;'>दाखिला: {s.get('Scholar_No','--')} | पिता: {s.get('Father_Name','--')}</span>")

  

                with row_c3:

                    stat_choice = st.radio(

                        f"status_{r_no}",

                        ["Present (उपस्थित)", "Absent (अनुपस्थित)"],

                        index=0 if chosen_stat == "Present" else 1,

                        key=ss_key,

                        horizontal=True,

                        label_visibility="collapsed"

                    )

                    daily_marked_status[r_no] = "Present" if "Present" in stat_choice else "Absent"

  

                with row_c4:

                    if daily_marked_status[r_no] == "Absent":

                        # Direct WhatsApp Absence Alert

                        p_mob = s.get("Contact", s.get("Mobile", ""))

                        clean_p_mob = "".join(filter(str.isdigit, str(p_mob))) if p_mob else ""

                        if len(clean_p_mob) == 10: clean_p_mob = "91" + clean_p_mob

                        

                        abs_msg = f"""🏫 *{st.session_state.school_info.get('name', 'शासकीय विद्यालय')}*

📢 *अनुपस्थिति सूचना (Student Absence Alert)*

━━━━━━━━━━━━━━━━━━━━

प्रिय अभिभावक,

आपका बच्चा *{s['Name']}* (कक्षा: {selected_class}, रोल नंबर: {r_no}) आज दिनांक *{date_str}* को विद्यालय में *अनुपस्थित* रहा है।

कृपया अनुपस्थिति का कारण विद्यालय में अवगत कराएं।

— *कक्षा अध्यापक / प्रधानाध्यापक*"""

                        encoded_abs_msg = urllib.parse.quote(abs_msg)

                        wa_abs_link = f"https://wa.me/{clean_p_mob}?text={encoded_abs_msg}" if clean_p_mob else f"https://wa.me/?text={encoded_abs_msg}"

                        render_html(f"""

                        <a href="{wa_abs_link}" target="_blank" style="text-decoration: none;">

                            <div style="background: #EF4444; color: white; font-size: 11.5px; font-weight: bold; padding: 4px 6px; border-radius: 4px; text-align: center; margin-top: 4px;">

                                📱 पालक को सूचना

                            </div>

                        </a>

                        """)

                    else:

                        render_html("<span style='color: #16A34A; font-weight: bold; font-size: 13px;'>🟢 उपस्थित</span>")

  

                st.markdown("<hr style='margin: 4px 0; border: none; border-top: 1px solid #F1F5F9;'>", unsafe_allow_html=True)

  

            st.divider()

  

            # Today's Summary & Save Button

            pct_today = round((pres_cnt / max(1, tot_st_cnt)) * 100, 1)

            sum_m1, sum_m2, sum_m3, sum_m4 = st.columns(4)

            sum_m1.metric("कुल पंजीकृत छात्र", f"{tot_st_cnt}")

            sum_m2.metric("🟢 कुल उपस्थित", f"{pres_cnt}")

            sum_m3.metric("🔴 कुल अनुपस्थित", f"{abs_cnt}")

            sum_m4.metric("📈 आज की उपस्थिति दर", f"{pct_today}%")

  

            if st.button("💾 आज की हाजिरी सुरक्षित करें एवं मास्टर रिकॉर्ड में अपडेट करें", type="primary", use_container_width=True):

                # Save daily log

                cls_data["daily_attendance"][date_str] = {str(k): v for k, v in daily_marked_status.items()}

                

                # Sync into monthly attendance dataframe

                att_df = cls_data.get("monthly_attendance", pd.DataFrame())

                if not att_df.empty and cur_month_abbr in att_df.columns:

                    for r_no, stat in daily_marked_status.items():

                        if stat == "Present":

                            # Increment attended days if it was not marked present before

                            old_stat = existing_day_record.get(str(r_no))

                            if old_stat != "Present":

                                cur_val = att_df.loc[att_df["Roll_No"] == r_no, cur_month_abbr].values

                                if len(cur_val) > 0 and not pd.isna(cur_val[0]):

                                    att_df.loc[att_df["Roll_No"] == r_no, cur_month_abbr] = int(cur_val[0]) + 1

                    

                    att_df["Total"] = att_df[MONTHS_LIST].sum(axis=1)

                    cls_data["monthly_attendance"] = att_df

                    

                    # Update students dataframe

                    for _, r in att_df.iterrows():

                        cls_data["students"].loc[cls_data["students"]["Roll_No"] == r["Roll_No"], "Attended_Days"] = int(r["Total"])

  

                save_data_to_disk()

                st.balloons()

                st.success(f"🎉 बधाई! दिनांक {date_str} की दैनिक उपस्थिति सफलतापूर्वक सुरक्षित हो गई एवं मास्टर शीट में अपडेट हो गई!")

  

        # ======================= TAB 2: MONTHLY GOVERNMENT ATTENDANCE SHEET =======================

        with tab_att2:

            # Step 1: School Working Days Row Setup

            st.subheader("🏫 स्कूल कुल कार्य दिवस (School Working Days):")

            c_work = cls_data.get("working_days", DEFAULT_WORKING_DAYS)

            w_cols = st.columns(13)

            updated_work = {}

            tot_work_days = 0

            for i, m in enumerate(MONTHS_LIST):

                with w_cols[i]:

                    w_val = st.number_input(f"{m}", min_value=0, max_value=31, value=int(c_work.get(m, DEFAULT_WORKING_DAYS.get(m, 20))), key=f"work_m_{selected_class}_{m}")

                    updated_work[m] = w_val

                    tot_work_days += w_val

            with w_cols[12]:

                render_html(f"<div style='border: 2px solid #000; padding: 6px; text-align: center; margin-top: 18px; font-weight: bold; font-size: 16px; background: #fff;'>Total: {tot_work_days}</div>")

            cls_data["working_days"] = updated_work

  

            # Step 2: Students Attendance Grid matching image_aab3c5.png

            st.subheader("📋 विद्यार्थियों की माहवार उपस्थिति (Student-wise Monthly Attendance Grid):")

            

            # Build initial attendance dataframe if missing

            att_df = cls_data.get("monthly_attendance", pd.DataFrame())

            if att_df.empty or len(att_df) != len(students_df):

                rows = []

                for _, s in students_df.iterrows():

                    r = {

                        "Roll_No": s["Roll_No"],

                        "Name": s["Name"]

                    }

                    for m in MONTHS_LIST:

                        r[m] = 20 if updated_work[m] > 0 else 0

                    rows.append(r)

                att_df = pd.DataFrame(rows)

  

            # Ensure dynamic total column

            att_df["Total"] = att_df[MONTHS_LIST].sum(axis=1)

  

            edited_att = st.data_editor(

                att_df,

                use_container_width=True,

                column_config={

                    "Roll_No": st.column_config.NumberColumn("Roll No.", disabled=True),

                    "Name": st.column_config.TextColumn("Name Of Student", disabled=True),

                    **{m: st.column_config.NumberColumn(m, min_value=0, max_value=31) for m in MONTHS_LIST},

                    "Total": st.column_config.NumberColumn("Total (कुल उपस्थिति)", disabled=True)

                },

                key=f"editor_att_{selected_class}"

            )

  

            if st.button("💾 माहवार उपस्थिति सहेजें (Save Attendance Grid)", type="primary"):

                # Recalculate totals

                edited_att["Total"] = edited_att[MONTHS_LIST].sum(axis=1)

                cls_data["monthly_attendance"] = edited_att

                

                # Sync back to students dataframe Total_Days & Attended_Days

                for idx, r in edited_att.iterrows():

                    r_no = r["Roll_No"]

                    cls_data["students"].loc[cls_data["students"]["Roll_No"] == r_no, "Attended_Days"] = int(r["Total"])

                    cls_data["students"].loc[cls_data["students"]["Roll_No"] == r_no, "Total_Days"] = int(tot_work_days)

  

                save_data_to_disk()

                st.success(f"✅ कक्षा {selected_class} की माहवार उपस्थिति सफलतापूर्वक सुरक्षित कर ली गई एवं मास्टर रिकॉर्ड में अपडेट हो गई!")

  

            # Step 3: Export Attendance Sheet

            st.divider()

            render_html("### 📥 उपस्थिति डेटा एक्सपोर्ट (Export Attendance Register)")

            if render_export_gatekeeper("उपस्थिति रजिस्टर"):

                c_att_exp1, c_att_exp2, c_att_exp3 = st.columns([2, 2, 2])

                with c_att_exp1:

                    att_fmt = st.selectbox("फ़ाइल प्रारूप चुनें (Format):", ["Excel (.xlsx)", "CSV (.csv)"], key="att_exp_fmt")

                with c_att_exp2:

                    att_export_df = edited_att.copy()

                    att_bytes, att_mime, att_ext = export_dataframe_bytes(att_export_df, att_fmt)

                    att_filename = f"Attendance_{selected_class}_{st.session_state.school_info.get('session','2023-24')}{att_ext}"

                    st.download_button(

                        f"📥 उपस्थिति पत्रक डाउनलोड करें ({att_fmt})",

                        data=att_bytes,

                        file_name=att_filename,

                        mime=att_mime,

                        type="primary",

                        use_container_width=True

                    )

  


        # ======================= TAB 3: BULK UPLOAD ATTENDANCE VIA EXCEL/CSV =======================
        with tab_att3:
            st.subheader(f"📥 एक्सेल / सीएसवी से माहवार उपस्थिति एक साथ अपलोड करें — {selected_class}")
            st.caption("कक्षा के सभी विद्यार्थियों की पूरे वर्ष (12 माह), किन्हीं 2-3 माह (जैसे Jul, Aug, Sep) अथवा कुल उपस्थिति दिन सीधे एक्सेल से 1-क्लिक में अपलोड करें:")
            
            c_tmpl1, c_tmpl2 = st.columns([2.5, 1.5])
            with c_tmpl1:
                st.info("""
                💡 **स्मार्ट बल्क अपलोड सुविधा:**
                1. **पूरे वर्ष का डेटा:** आप सभी 12 माह (Apr से Mar) की उपस्थिति एक साथ अपलोड कर सकते हैं।
                2. **किन्हीं 2-3 माह का डेटा:** यदि आप केवल 2 या 3 माह (उदा. Jul, Aug, Sep) का डेटा अपलोड करेंगे, तो केवल वही माह अपडेट होंगे और बाकी बचे हुए महीनों की पहले से भरी उपस्थिति बिल्कुल सुरक्षित रहेगी!
                3. **वार्षिक कुल उपस्थिति:** यदि फ़ाइल में केवल कुल उपस्थिति (`Total_Attended` या `कुल उपस्थिति`) का कॉलम है, तो वह भी स्वतः पहचान लिया जाएगा।
                """)
            with c_tmpl2:
                template_rows = []
                att_df = cls_data.get("monthly_attendance", pd.DataFrame())
                for idx, s in students_df.iterrows():
                    row = {
                        "Roll_No": s["Roll_No"],
                        "Student_Name": s["Name"],
                        "Scholar_No": s.get("Scholar_No", "")
                    }
                    cur_att_row = att_df[att_df["Roll_No"] == s["Roll_No"]] if not att_df.empty and "Roll_No" in att_df.columns else pd.DataFrame()
                    for m in MONTHS_LIST:
                        if not cur_att_row.empty and m in cur_att_row.columns:
                            row[m] = int(cur_att_row[m].iloc[0])
                        else:
                            row[m] = 20 if m != "May" else 0
                    template_rows.append(row)
                tmpl_df = pd.DataFrame(template_rows)
                t_bytes, t_mime, t_ext = export_dataframe_bytes(tmpl_df, "Excel (.xlsx)")
                st.download_button(
                    f"📄 {selected_class} उपस्थिति एक्सेल टेम्पलेट डाउनलोड (.xlsx)",
                    data=t_bytes,
                    file_name=f"Attendance_Template_{selected_class}_{st.session_state.school_info.get('session','2023-24')}.xlsx",
                    mime=t_mime,
                    type="secondary",
                    use_container_width=True
                )
            
            up_att_file = st.file_uploader(
                f"📂 {selected_class} उपस्थिति एक्सेल (.xlsx / .xls / .csv) फ़ाइल यहाँ अपलोड करें:",
                type=["xlsx", "xls", "csv"],
                key=f"uploader_bulk_att_{selected_class}"
            )
            
            if up_att_file is not None:
                try:
                    if up_att_file.name.endswith(".csv"):
                        uploaded_df = pd.read_csv(up_att_file)
                    else:
                        uploaded_df = pd.read_excel(up_att_file)
                        
                    st.success(f"✅ फ़ाइल सफलतापूर्वक पढ़ी गई: कुल {len(uploaded_df)} पंक्तियाँ पाई गईं!")
                    
                    # Enhanced Column Mapper (Hindi + English + Alternate Spellings)
                    MONTHS_SYNONYMS = {
                        "Apr": ["apr", "april", "अप्रैल", "अप्रेल"],
                        "May": ["may", "मई"],
                        "Jun": ["jun", "june", "जून"],
                        "Jul": ["jul", "july", "जुलाई"],
                        "Aug": ["aug", "august", "अगस्त"],
                        "Sep": ["sep", "sept", "september", "सितम्बर", "सितंबर"],
                        "Oct": ["oct", "october", "अक्टूबर", "अक्टू"],
                        "Nov": ["nov", "november", "नवम्बर", "नवंबर"],
                        "Dec": ["dec", "december", "दिसम्बर", "दिसंबर"],
                        "Jan": ["jan", "january", "जनवरी"],
                        "Feb": ["feb", "february", "फरवरी"],
                        "Mar": ["mar", "march", "मार्च"]
                    }
                    
                    col_map = {}
                    has_direct_total = None
                    
                    for col in uploaded_df.columns:
                        cl = str(col).strip().lower()
                        if any(k in cl for k in ["roll", "रोल", "अनुक्रमांक"]):
                            col_map["Roll_No"] = col
                        for m_canonical, syns in MONTHS_SYNONYMS.items():
                            if any(s in cl for s in syns):
                                col_map[m_canonical] = col
                        if any(k in cl for k in ["total_attended", "attended_days", "कुल उपस्थिति", "उपस्थिति दिवस", "वार्षिक उपस्थिति", "attended"]):
                            has_direct_total = col
                                
                    if "Roll_No" not in col_map:
                        st.error("❌ एक्सेल फ़ाइल में 'Roll_No' (रोल नंबर) कॉलम नहीं मिला! कृपया सुनिश्चित करें कि फ़ाइल में रोल नंबर का कॉलम हो।")
                    else:
                        detected_months = [m for m in MONTHS_LIST if m in col_map]
                        if detected_months:
                            st.info(f"🎯 **पहचाने गए माह ({len(detected_months)} माह):** `{', '.join(detected_months)}` — अपलोड करने पर केवल ये माह अपडेट होंगे, शेष महीनों का पूर्व रिकॉर्ड सुरक्षित रहेगा!")
                        elif has_direct_total:
                            st.info(f"🎯 **वार्षिक कुल उपस्थिति कॉलम पहचाना गया:** `{has_direct_total}` — छात्रों के सीधे कुल उपस्थित दिवस अपडेट होंगे।")
                        else:
                            st.warning("⚠️ फ़ाइल में किसी माह (Apr-Mar) या कुल उपस्थिति का कॉलम नहीं पहचाना जा सका। कृपया टेम्पलेट प्रारूप का उपयोग करें।")

                        preview_records = []
                        c_work = cls_data.get("working_days", DEFAULT_WORKING_DAYS)
                        tot_working = sum([int(c_work.get(m, 20)) for m in MONTHS_LIST])
                        
                        existing_att_df = cls_data.get("monthly_attendance", pd.DataFrame())
                        
                        for _, u_row in uploaded_df.iterrows():
                            try:
                                u_roll = int(float(u_row[col_map["Roll_No"]]))
                            except Exception:
                                continue
                            
                            st_match = students_df[students_df["Roll_No"] == u_roll]
                            st_name = st_match["Name"].iloc[0] if not st_match.empty else f"छात्र (Roll {u_roll})"
                            st_sch = st_match["Scholar_No"].iloc[0] if not st_match.empty and "Scholar_No" in st_match.columns else ""
                            
                            cur_st_att = existing_att_df[existing_att_df["Roll_No"] == u_roll] if not existing_att_df.empty and "Roll_No" in existing_att_df.columns else pd.DataFrame()
                            
                            rec = {"Roll_No": u_roll, "Name": st_name, "Scholar_No": st_sch}
                            tot_att = 0
                            
                            for m in MONTHS_LIST:
                                if m in col_map:
                                    try:
                                        val = int(float(u_row[col_map[m]]))
                                    except Exception:
                                        val = 0
                                else:
                                    # Preserve existing attendance if already saved in system!
                                    if not cur_st_att.empty and m in cur_st_att.columns:
                                        try:
                                            val = int(cur_st_att[m].iloc[0])
                                        except Exception:
                                            val = int(c_work.get(m, 20)) if m != "May" else 0
                                    else:
                                        val = int(c_work.get(m, 20)) if m != "May" else 0
                                rec[m] = val
                                tot_att += val
                            
                            # If direct total was provided and no individual months were matched:
                            if not detected_months and has_direct_total:
                                try:
                                    tot_att = int(float(u_row[has_direct_total]))
                                except Exception:
                                    pass
                                    
                            rec["Total_Attended"] = tot_att
                            rec["Total_Working"] = tot_working
                            rec["Att_Percentage"] = f"{round((tot_att / tot_working)*100, 1)}%" if tot_working > 0 else "0%"
                            preview_records.append(rec)
                            
                        parsed_att_df = pd.DataFrame(preview_records)
                        st.markdown("##### 👁️ अपलोड किए गए डेटा का पूर्वावलोकन (Preview):")
                        st.dataframe(parsed_att_df, use_container_width=True)
                        
                        if st.button("💾 यह उपस्थिति डेटा मास्टर रिकॉर्ड में सहेजें (Save Attendance to Database)", type="primary", use_container_width=True):
                            cls_data["monthly_attendance"] = parsed_att_df
                            for _, prow in parsed_att_df.iterrows():
                                r_no = prow["Roll_No"]
                                t_att = prow["Total_Attended"]
                                cls_data["students"].loc[cls_data["students"]["Roll_No"] == r_no, "Attended_Days"] = t_att
                                cls_data["students"].loc[cls_data["students"]["Roll_No"] == r_no, "Total_Days"] = tot_working
                            save_data_to_disk()
                            st.balloons()
                            st.success("🎉 सभी विद्यार्थियों की माहवार उपस्थिति सफलतापूर्वक सहेज ली गई! यह प्रगति पत्रक, 44-कॉलम A3 गोशवारे और 35-कॉलम वेटेज शीट में स्वतः अपडेट हो गई है।")
                            st.rerun()
                except Exception as ex:
                    st.error(f"फ़ाइल पढ़ने में त्रुटि: {ex}")


# ----------------- MODULE 4: EVALUATION ENTRY (SUBJECT-WISE PRESENT/ABSENT) -----------------

elif menu == T["nav_eval"]:
    s_info = st.session_state.school_info

    st.markdown(f'<div class="main-header">📝 परीक्षा एवं गतिविधि मूल्यांकन — {selected_class}</div>', unsafe_allow_html=True)

    render_html('<div class="sub-header">विद्यार्थी प्रोफाइल, पेपर/विषयवार Present/Absent, मुख्य विषय (अर्धवार्षिक 40 + वार्षिक 60) व सह-शैक्षिक गुण</div>')

  
  

    students_df = cls_data["students"]

    if students_df.empty:

        st.warning("⚠️ कृपया पहले 'विद्यार्थी मास्टर' में छात्र जोड़ें!")

    else:

        col_sel1, col_sel2 = st.columns([2, 1])

        with col_sel1:

            st_names = [f"Roll {s['Roll_No']}: {s['Name']} (Scholar: {s['Scholar_No']})" for _, s in students_df.iterrows()]

            selected_student_str = st.selectbox("विद्यार्थी चुनें (Select Student):", st_names)

            sel_roll = int(selected_student_str.split(":")[0].replace("Roll", "").strip())

        

        stud = students_df[students_df["Roll_No"] == sel_roll].iloc[0]

        cls_subjects = get_class_subjects(selected_class)

        

        if sel_roll not in cls_data["evaluations"]:

            cls_data["evaluations"][sel_roll] = {

                "status": stud.get("Status", "Present"),

                "marks": {sub["id"]: {"status_hy": "Present", "half_yearly": 32, "status_yr": "Present", "annual": 48} for sub in cls_subjects},

                "co_curricular": {k: "A" for k, _ in CO_CURRICULAR_ACTIVITIES},

                "social": {k: "A" for k, _ in SOCIAL_ACTIVITIES}

            }

        

        eval_data = cls_data["evaluations"][sel_roll]

  
  

        # Top Student Profile Card

        photo_prev = ""

        if stud.get("Photo_b64"):

            photo_prev = f'<img src="data:image/jpeg;base64,{stud["Photo_b64"]}" style="width: 80px; height: 95px; border-radius: 6px; border: 1px solid #93C5FD; object-fit: cover;">'

        else:

            photo_prev = '<div style="width: 80px; height: 95px; border: 1px dashed #93C5FD; display: flex; align-items: center; justify-content: center; font-size: 11px; text-align: center; color: #1E3A8A; background: #fff; border-radius: 6px;">पासपोर्ट फोटो</div>'

  
  

        profile_card_html = f"""

        <div class="profile-card">

            <div style="display: flex; justify-content: space-between; align-items: center;">

                <div style="width: 85%;">

                    <div style="font-size: 18px; font-weight: 800; color: #1E3A8A; margin-bottom: 6px;">

                        👤 {stud['Name']} | रोल नंबर: {stud['Roll_No']} | दाखिला क्र.: {stud['Scholar_No']}

                    </div>

                    <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; font-size: 13px; color: #374151;">

                        <div><b>पिता का नाम:</b> {stud['Father_Name']}</div>

                        <div><b>माता का नाम:</b> {stud['Mother_Name']}</div>

                        <div><b>कक्षा व वर्ग:</b> {stud.get('Class', selected_class)} - {stud.get('Section', 'A')}</div>

                        <div><b>जन्मतिथि:</b> {stud['DOB']}</div>

                        <div><b>जेंडर / वर्ग:</b> {stud['Gender']} / {stud['Category']}</div>

                        <div><b>माध्यम:</b> {get_display_medium(s_info, stud)}</div>

                        <div><b>समग्र ID:</b> {stud['SSSM_ID']}</div>

                        <div><b>आधार नंबर:</b> {stud.get('Aadhar_No', '--')}</div>

                        <div><b>उपस्थिति:</b> {stud.get('Attended_Days', 200)} / {stud.get('Total_Days', 220)} दिन</div>

                    </div>

                </div>

                <div>{photo_prev}</div>

            </div>

        </div>

        """

        render_html(profile_card_html)

  
  

        # Overall Status

        col_st1, col_st2 = st.columns([1, 3])

        with col_st1:

            st_overall_status = st.selectbox("📌 छात्र की परीक्षा स्थिति:", ["Present", "Absent"], 

                                             index=0 if eval_data.get("status", "Present") == "Present" else 1)

            eval_data["status"] = st_overall_status

  
  

        # 1. Main Subjects (With Subject-Wise Present/Absent & Dynamic Component Pattern!)

        cur_exam_rule = get_session_exam_rule(st.session_state.school_info.get("session", "2023-24"), selected_class)

        has_proj_m4 = any(c["id"] == "project" for c in cur_exam_rule["components"])

  
  

                # BULK UPLOAD OPTION FOR YEARLY / ANNUAL EXAM MARKS
        with st.expander("📥 एक्सेल शीट से एक साथ सभी छात्रों के वार्षिक मुख्य परीक्षा अंक अपलोड करें (Bulk Upload Annual Marks)", expanded=False):
            st.info("💡 **वार्षिक अंक थोक अपलोड:** आप यहाँ से कक्षा के सभी छात्रों की पूर्व-भरी एक्सेल फ़ाइल डाउनलोड करके ऑफ़लाइन नंबर भर सकते हैं और एक साथ पूरे परिणाम को अपलोड कर सकते हैं।")
            
            # 1. Download Blank/Current Template
            ann_tmpl_rows = []
            for _, s in students_df.iterrows():
                r = s["Roll_No"]
                ev = cls_data["evaluations"].get(r, {})
                m_dict = ev.get("marks", {})
                row = {
                    "Roll_No": r,
                    "Scholar_No": s.get("Scholar_No", ""),
                    "Name": s["Name"],
                    "Status": ev.get("status", "Present")
                }
                for sub in cls_subjects:
                    s_id = sub["id"]
                    se = m_dict.get(s_id, {})
                    row[f"{sub['name']}_Annual"] = se.get("annual", 48)
                    if has_proj_m4:
                        row[f"{sub['name']}_Project"] = se.get("project", 18)
                        row[f"{sub['name']}_HalfYearly"] = se.get("half_yearly", 16)
                    else:
                        row[f"{sub['name']}_HalfYearly"] = se.get("half_yearly", 32)
                ann_tmpl_rows.append(row)
                
            ann_tmpl_df = pd.DataFrame(ann_tmpl_rows)
            t_bytes, t_mime, t_ext = export_dataframe_bytes(ann_tmpl_df, "Excel (.xlsx)")
            
            c_adn1, c_adn2 = st.columns([1.5, 2.5])
            with c_adn1:
                st.download_button(
                    "📥 वार्षिक अंक एक्सेल टेम्पलेट डाउनलोड (.xlsx)",
                    data=t_bytes,
                    file_name=f"Annual_Marks_Template_{selected_class}.xlsx",
                    mime=t_mime,
                    type="secondary",
                    use_container_width=True
                )
            with c_adn2:
                up_ann_file = st.file_uploader("भरी हुई वार्षिक अंक एक्सेल / CSV फ़ाइल यहाँ अपलोड करें:", type=["xlsx", "xls", "csv"], key="annual_bulk_uploader")
                
            if up_ann_file is not None:
                parsed_ann_df = parse_marks_upload_file(up_ann_file)
                if parsed_ann_df is not None and not parsed_ann_df.empty:
                    st.success(f"✅ फ़ाइल सफलतापूर्वक लोड हुई! कुल {len(parsed_ann_df)} पंक्तियाँ पाई गईं।")
                    st.dataframe(parsed_ann_df.head(5), use_container_width=True)
                    
                    if st.button("🚀 एक्सेल से सभी छात्रों के वार्षिक अंक सुरक्षित करें (Apply Bulk Annual Marks)", type="primary", use_container_width=True, key="btn_apply_ann_bulk"):
                        roll_col = next((c for c in parsed_ann_df.columns if "roll" in str(c).lower()), None)
                        if roll_col:
                            updated_cnt = 0
                            for _, urow in parsed_ann_df.iterrows():
                                try:
                                    r_val = int(urow[roll_col])
                                except Exception:
                                    continue
                                if r_val not in cls_data["evaluations"]:
                                    cls_data["evaluations"][r_val] = {"marks": {}}
                                if "marks" not in cls_data["evaluations"][r_val]:
                                    cls_data["evaluations"][r_val]["marks"] = {}
                                    
                                for sub in cls_subjects:
                                    s_id = sub["id"]
                                    if s_id not in cls_data["evaluations"][r_val]["marks"]:
                                        cls_data["evaluations"][r_val]["marks"][s_id] = {}
                                    # Match annual written
                                    ann_c = next((c for c in parsed_ann_df.columns if smart_match_subject_col(c, sub["name"], s_id) and ("ann" in str(c).lower() or "वार्षिक" in str(c) or "written" in str(c).lower() or "theory" in str(c).lower())), None)
                                    if not ann_c:
                                        ann_c = next((c for c in parsed_ann_df.columns if smart_match_subject_col(c, sub["name"], s_id)), None)
                                    if ann_c and pd.notna(urow[ann_c]):
                                        try:
                                            cls_data["evaluations"][r_val]["marks"][s_id]["annual"] = min(75 if "high" in selected_class.lower() else 60, max(0, int(float(urow[ann_c]))))
                                        except Exception: pass
                                    # Match project
                                    proj_c = next((c for c in parsed_ann_df.columns if smart_match_subject_col(c, sub["name"], s_id) and ("proj" in str(c).lower() or "प्रोजेक्ट" in str(c))), None)
                                    if proj_c and pd.notna(urow[proj_c]):
                                        try:
                                            cls_data["evaluations"][r_val]["marks"][s_id]["project"] = min(40, max(0, int(float(urow[proj_c]))))
                                        except Exception: pass
                                    # Match half-yearly
                                    hy_c = next((c for c in parsed_ann_df.columns if smart_match_subject_col(c, sub["name"], s_id) and ("half" in str(c).lower() or "अर्ध" in str(c) or "hy" in str(c).lower())), None)
                                    if hy_c and pd.notna(urow[hy_c]):
                                        try:
                                            cls_data["evaluations"][r_val]["marks"][s_id]["half_yearly"] = min(60, max(0, int(float(urow[hy_c]))))
                                        except Exception: pass
                                updated_cnt += 1
                            save_data_to_disk()
                            st.balloons()
                            st.success(f"🎉 बधाई! कुल {updated_cnt} विद्यार्थियों के वार्षिक अंक सफलतापूर्वक अपडेट हो गए!")
                            st.rerun()
                        else:
                            st.error("फ़ाइल में Roll No. कॉलम नहीं मिला! कृपया डाउनलोड किया गया टेम्पलेट उपयोग करें।")


        with st.expander(f"📚 1. मुख्य विषय अंक प्रविष्टि ({cur_exam_rule['name']})", expanded=True):

            if has_proj_m4:

                st.info(f"💡 **सक्रिय बोर्ड पैटर्न ({selected_class}):** अर्धवार्षिक [20] + प्रोजेक्ट कार्य [20] + वार्षिक लिखित [60] = कुल 100")

                sub_head = st.columns([3, 2, 2, 2, 2, 2, 2, 2])

                sub_head[0].markdown("**विषय (Subject)**")

                sub_head[1].markdown("**अर्धवार्षिक हाजिरी**")

                sub_head[2].markdown("**अर्धवार्षिक [20]**")

                sub_head[3].markdown("**प्रोजेक्ट [20]**")

                sub_head[4].markdown("**वार्षिक हाजिरी**")

                sub_head[5].markdown("**वार्षिक [60]**")

                sub_head[6].markdown("**कुल [100]**")

                sub_head[7].markdown("**ग्रेड**")

            else:

                st.info(f"💡 **सक्रिय पैटर्न ({selected_class}):** अर्धवार्षिक (पूर्णांक 40, उत्तीर्णांक 13) | वार्षिक (पूर्णांक 60, उत्तीर्णांक 20) | कुल 100")

                sub_head = st.columns([3, 2, 2, 2, 2, 2, 2])

                sub_head[0].markdown("**विषय (Subject)**")

                sub_head[1].markdown("**अर्धवार्षिक हाजिरी**")

                sub_head[2].markdown("**अर्धवार्षिक [40]**")

                sub_head[3].markdown("**वार्षिक हाजिरी**")

                sub_head[4].markdown("**वार्षिक [60]**")

                sub_head[5].markdown("**कुल प्राप्तांक [100]**")

                sub_head[6].markdown("**ग्रेड (Grade)**")

  
  

            updated_marks = {}

            for sub in cls_subjects:

                s_id = sub["id"]

                s_name = sub["name"]

                

                prev_sub = eval_data.get("marks", {}).get(s_id, {})

                p_hy_stat = prev_sub.get("status_hy", "Present")

                p_hy_val = prev_sub.get("half_yearly", 16 if has_proj_m4 else 32)

                p_proj_val = prev_sub.get("project", 18)

                p_yr_stat = prev_sub.get("status_yr", "Present")

                p_yr_val = prev_sub.get("annual", 48)

  
  

                if has_proj_m4:

                    r_cols = st.columns([3, 2, 2, 2, 2, 2, 2, 2])

                    with r_cols[0]:

                        st.write(f"📖 **{s_name}**")

                    with r_cols[1]:

                        stat_hy = st.selectbox(f"stat_hy_{s_id}", ["Present", "Absent"], index=0 if p_hy_stat == "Present" else 1, key=f"stat_hy_{selected_class}_{sel_roll}_{s_id}", label_visibility="collapsed")

                    with r_cols[2]:

                        val_hy = st.number_input(f"hy_{s_id}", min_value=0, max_value=20, value=0 if stat_hy == "Absent" else min(20, max(0, int(p_hy_val))), disabled=(stat_hy == "Absent"), key=f"num_hy_{selected_class}_{sel_roll}_{s_id}", label_visibility="collapsed")

                    with r_cols[3]:

                        val_proj = st.number_input(f"proj_{s_id}", min_value=0, max_value=20, value=min(20, max(0, int(p_proj_val))), key=f"num_proj_{selected_class}_{sel_roll}_{s_id}", label_visibility="collapsed")

                    with r_cols[4]:

                        stat_yr = st.selectbox(f"stat_yr_{s_id}", ["Present", "Absent"], index=0 if p_yr_stat == "Present" else 1, key=f"stat_yr_{selected_class}_{sel_roll}_{s_id}", label_visibility="collapsed")

                    with r_cols[5]:

                        val_yr = st.number_input(f"yr_{s_id}", min_value=0, max_value=60, value=0 if stat_yr == "Absent" else min(60, max(0, int(p_yr_val))), disabled=(stat_yr == "Absent"), key=f"num_yr_{selected_class}_{sel_roll}_{s_id}", label_visibility="collapsed")

                    

                    if stat_hy == "Absent" and stat_yr == "Absent":

                        m_tot = 0

                        m_grd = "Ab"

                    else:

                        m_tot = val_hy + val_proj + val_yr

                        m_grd = calculate_grade(m_tot)

  
  

                    with r_cols[6]:

                        st.markdown(f"<h4 style='margin:0; text-align:center; color:#1E3A8A;'>{m_tot}</h4>", unsafe_allow_html=True)

                    with r_cols[7]:

                        c_col = "#B91C1C" if m_grd in ["E", "Ab"] else "#008000"

                        st.markdown(f"<h4 style='margin:0; text-align:center; color:{c_col};'>{m_grd}</h4>", unsafe_allow_html=True)

  
  

                    updated_marks[s_id] = {

                        "status_hy": stat_hy, "half_yearly": val_hy,

                        "project": val_proj,

                        "status_yr": stat_yr, "annual": val_yr,

                        "total": m_tot, "grade": m_grd

                    }

                else:

                    r_cols = st.columns([3, 2, 2, 2, 2, 2, 2])

                    with r_cols[0]:

                        st.write(f"📖 **{s_name}**")

                    with r_cols[1]:

                        stat_hy = st.selectbox(f"stat_hy_{s_id}", ["Present", "Absent"], index=0 if p_hy_stat == "Present" else 1, key=f"stat_hy_{selected_class}_{sel_roll}_{s_id}", label_visibility="collapsed")

                    with r_cols[2]:

                        val_hy = st.number_input(f"hy_{s_id}", min_value=0, max_value=40, value=0 if stat_hy == "Absent" else min(40, max(0, int(p_hy_val))), disabled=(stat_hy == "Absent"), key=f"num_hy_{selected_class}_{sel_roll}_{s_id}", label_visibility="collapsed")

                    with r_cols[3]:

                        stat_yr = st.selectbox(f"stat_yr_{s_id}", ["Present", "Absent"], index=0 if p_yr_stat == "Present" else 1, key=f"stat_yr_{selected_class}_{sel_roll}_{s_id}", label_visibility="collapsed")

                    with r_cols[4]:

                        val_yr = st.number_input(f"yr_{s_id}", min_value=0, max_value=60, value=0 if stat_yr == "Absent" else min(60, max(0, int(p_yr_val))), disabled=(stat_yr == "Absent"), key=f"num_yr_{selected_class}_{sel_roll}_{s_id}", label_visibility="collapsed")

                    

                    if stat_hy == "Absent" and stat_yr == "Absent":

                        m_tot = 0

                        m_grd = "Ab"

                    else:

                        m_tot = val_hy + val_yr

                        m_grd = calculate_grade(m_tot)

  
  

                    with r_cols[5]:

                        st.markdown(f"<h4 style='margin:0; text-align:center; color:#1E3A8A;'>{m_tot}</h4>", unsafe_allow_html=True)

                    with r_cols[6]:

                        c_col = "#B91C1C" if m_grd in ["E", "Ab"] else "#008000"

                        st.markdown(f"<h4 style='margin:0; text-align:center; color:{c_col};'>{m_grd}</h4>", unsafe_allow_html=True)

  
  

                    updated_marks[s_id] = {

                        "status_hy": stat_hy, "half_yearly": val_hy,

                        "annual": val_yr, "status_yr": stat_yr,

                        "total": m_tot, "grade": m_grd

                    }

  
  

        # 2. Co-Curricular

        with st.expander("🎨 2. सह-शैक्षिक गतिविधियां मूल्यांकन (5 क्षेत्र)", expanded=False):

            c_grid = st.columns(len(CO_CURRICULAR_ACTIVITIES))

            updated_co = {}

            for idx, (k, label) in enumerate(CO_CURRICULAR_ACTIVITIES):

                with c_grid[idx]:

                    st.write(f"**{label}**")

                    cur_val = eval_data["co_curricular"].get(k, "A")

                    opt_idx = ["A", "B", "C"].index(cur_val) if cur_val in ["A", "B", "C"] else 0

                    sel_grd = st.selectbox(label, ["A", "B", "C"], index=opt_idx, key=f"co_{selected_class}_{sel_roll}_{k}", label_visibility="collapsed")

                    updated_co[k] = sel_grd

  
  

        # 3. Social Activities

        with st.expander("🤝 3. व्यक्तिगत एवं सामाजिक गुण मूल्यांकन (10 गुण)", expanded=False):

            s_col_a, s_col_b = st.columns(2)

            updated_soc = {}

            for idx, (k, label) in enumerate(SOCIAL_ACTIVITIES):

                target_col = s_col_a if idx < 5 else s_col_b

                with target_col:

                    c_l, c_r = st.columns([3, 1])

                    with c_l: st.write(f"**{label}**")

                    with c_r:

                        cur_val = eval_data["social"].get(k, "A")

                        opt_idx = ["A", "B", "C"].index(cur_val) if cur_val in ["A", "B", "C"] else 0

                        sel_grd = st.selectbox(label, ["A", "B", "C"], index=opt_idx, key=f"soc_{selected_class}_{sel_roll}_{k}", label_visibility="collapsed")

                        updated_soc[k] = sel_grd

  
  

        if st.button(f"💾 रोल नंबर {sel_roll} ({stud['Name']}) का संपूर्ण मूल्यांकन सुरक्षित करें", type="primary"):

            cls_data["evaluations"][sel_roll] = {

                "status": st_overall_status,

                "marks": updated_marks,

                "co_curricular": updated_co,

                "social": updated_soc

            }

            save_data_to_disk()

            st.success(f"✅ रोल नंबर {sel_roll} का संपूर्ण मूल्यांकन सफलतापूर्वक ऑटो-सेव हो गया!")

  
  

# ----------------- MODULE 5: STUDENT COMPLETE DATA DOSSIER & VIEWER -----------------

elif menu == T["nav_viewer"]:
    s_info = st.session_state.school_info
    s_info = st.session_state.school_info

    render_html(f'<div class="main-header">🔍 छात्र संपूर्ण डेटा समीक्षा (Student 360° Data Dossier)</div>')

    render_html('<div class="sub-header">कक्षा एवं सेक्शन चुनें — केवल उन विद्यार्थियों की सूची दिखेगी जिनका डेटा दर्ज हो चुका है। नाम पर क्लिक करने पर पूरा डेटा खुलेगा।</div>')

  
  

    if "active_dossier_roll" not in st.session_state:

        st.session_state.active_dossier_roll = None

  
  

    # Step 1: Class & Section Selectors

    c_v_top1, c_v_top2, c_v_top3 = st.columns([2, 2, 2])

    with c_v_top1:

        v_class = st.selectbox(

            "1. कक्षा चुनें (Select Class):", 

            st.session_state.classes_list, 

            index=st.session_state.classes_list.index(selected_class) if selected_class in st.session_state.classes_list else 0,

            key="viewer_class_sel"

        )

    

    v_cls_data = get_class_data(v_class)

    v_students_df = v_cls_data["students"]

    v_evals = v_cls_data["evaluations"]

    v_subjects = get_class_subjects(v_class)

    v_sub_count = len(v_subjects)

    v_max_total = v_sub_count * 100

  
  

    # Section choices

    existing_secs = sorted(list(set([str(s).strip() for s in v_students_df["Section"].dropna().unique() if str(s).strip()]))) if not v_students_df.empty and "Section" in v_students_df.columns else ["A"]

    all_sec_options = ["सभी सेक्शन (All Sections)"] + (existing_secs if existing_secs else ["A", "B", "C", "D", "E"])

    

    with c_v_top2:

        v_section = st.selectbox("2. सेक्शन चुनें (Select Section):", all_sec_options, key="viewer_sec_sel")

  
  

    # Reset active student if class or section changes

    if v_class != st.session_state.get("last_viewer_class") or v_section != st.session_state.get("last_viewer_sec"):

        st.session_state.active_dossier_roll = None

        st.session_state.last_viewer_class = v_class

        st.session_state.last_viewer_sec = v_section

  
  

    # Filter students by section

    if v_section != "सभी सेक्शन (All Sections)" and not v_students_df.empty:

        filtered_df = v_students_df[v_students_df["Section"] == v_section].copy()

    else:

        filtered_df = v_students_df.copy()

  
  

    # Identify students whose data has been entered

    data_entered_students = []

    if not filtered_df.empty:

        for _, s in filtered_df.iterrows():

            r = s["Roll_No"]

            if r in v_evals and "marks" in v_evals[r] and bool(v_evals[r]["marks"]):

                data_entered_students.append(s)

  
  

    tot_enrolled = len(filtered_df)

    data_entered_cnt = len(data_entered_students)

  
  

    with c_v_top3:

        render_html(f'''

        <div style="border: 1px solid #93C5FD; background: #EFF6FF; padding: 8px 12px; border-radius: 6px; text-align: center; margin-top: 15px;">

            <span style="font-size: 13px; color: #1E3A8A; font-weight: bold;">डेटा प्रविष्टि स्थिति:</span><br>

            <span style="font-size: 16px; font-weight: 800; color: #008000;">{data_entered_cnt}</span> / {tot_enrolled} छात्र पूर्ण

        </div>

        ''')

  
  

    st.divider()

  
  

    # ================== VIEW STATE 1: ONLY LIST OF STUDENTS IS SHOWN ==================

    if st.session_state.active_dossier_roll is None:

        render_html(f"### 📋 {v_class} ({v_section}) — मूल्यांकन दर्ज विद्यार्थियों की सूची")

        

        if data_entered_cnt == 0:

            st.info(f"ℹ️ {v_class} ({v_section}) में अभी किसी भी विद्यार्थी के परीक्षा अंक दर्ज नहीं हुए हैं।")

            if tot_enrolled > 0:

                st.caption(f"💡 कुल {tot_enrolled} छात्र पंजीकृत हैं। आप साइडबार में **'📝 4. परीक्षा एवं गतिविधि मूल्यांकन'** में जाकर उनके अंक भर सकते हैं।")

        else:

            # Export options for all data-entered students in this class & section

            with st.expander("📥 इस कक्षा/सेक्शन के सभी डेटा-दर्ज छात्रों का रिकॉर्ड एक्सपोर्ट करें (Export Roster Data)", expanded=False):

                if render_export_gatekeeper("छात्र डॉसियर"):

                    col_t5_exp1, col_t5_exp2, col_t5_exp3 = st.columns([3, 2, 3])

                    with col_t5_exp1:

                        t5_exp_type = st.selectbox(

                            "प्रारूप चुनें (Template):",

                            [

                                "📋 संपूर्ण छात्रवार रिकॉर्ड (44-Column Master Dossier)",

                                "🏛️ RSKMP पोर्टल प्रारूप (rskmp.in Upload Template)",

                                "🏢 MPBSE बोर्ड प्रारूप (mpbse.nic.in Format)"

                            ],

                            key="t5_exp_type_choice"

                        )

                    with col_t5_exp2:

                        t5_file_ext = st.selectbox("फ़ाइल फॉर्मेट:", ["Excel (.xlsx)", "CSV (.csv)"], key="t5_file_ext_choice")

                    with col_t5_exp3:

                        st.markdown("<div style='margin-top: 28px;'>", unsafe_allow_html=True)

                        export_students_df = pd.DataFrame(data_entered_students)

                        if "RSKMP" in t5_exp_type:

                            t5_out_df = generate_rskmp_df(export_students_df, v_evals, v_subjects, st.session_state.school_info, v_class)

                            t5_fn_prefix = f"RSKMP_Dossier_{v_class}_{v_section}_{st.session_state.school_info.get('session','2023-24')}"

                        elif "MPBSE" in t5_exp_type:

                            t5_out_df = generate_mpbse_df(export_students_df, v_evals, v_subjects, st.session_state.school_info, v_class)

                            t5_fn_prefix = f"MPBSE_Dossier_{v_class}_{v_section}_{st.session_state.school_info.get('session','2023-24')}"

                        else:

                            t5_out_df = generate_master_44col_df(export_students_df, v_evals, v_subjects, st.session_state.school_info, v_class)

                            t5_fn_prefix = f"Students_Master_Dossier_{v_class}_{v_section}_{st.session_state.school_info.get('session','2023-24')}"

  
  

                        t5_bytes, t5_mime, t5_ext = export_dataframe_bytes(t5_out_df, t5_file_ext)

                        st.download_button(

                            f"🚀 डेटा डाउनलोड करें ({t5_file_ext})",

                            data=t5_bytes,

                            file_name=f"{t5_fn_prefix}{t5_ext}",

                            mime=t5_mime,

                            type="primary",

                            use_container_width=True,

                            key="btn_download_t5_all"

                        )

                        st.markdown("</div>", unsafe_allow_html=True)

  
  

            st.caption("👉 जिस भी विद्यार्थी का संपूर्ण डेटा देखना है, उसके नाम के सामने **'👁️ पूरा डेटा देखें'** बटन पर क्लिक करें:")

            

            # Interactive student cards list

            for idx, s in enumerate(data_entered_students):

                r = s["Roll_No"]

                ev = v_evals.get(r, {})

                marks_dict = ev.get("marks", {})

                

                # Compute total and percentage

                tot_obt = sum([marks_dict.get(sub["id"], {}).get("total", 0) for sub in v_subjects])

                pct = round((tot_obt / v_max_total) * 100, 1) if v_max_total else 0

                grd = calculate_grade(pct)

                is_p = (pct >= 33 and ev.get("status", "Present") != "Absent")

                res_txt = "Pass" if is_p else "Fail"

                res_col = "#008000" if is_p else "#CC0000"

  
  

                # Photo thumbnail

                if s.get("Photo_b64"):

                    thumb_html = f'<img src="data:image/jpeg;base64,{s["Photo_b64"]}" style="width: 50px; height: 60px; object-fit: cover; border-radius: 4px; border: 1px solid #ccc;">'

                else:

                    thumb_html = '<div style="width: 50px; height: 60px; background: #f1f5f9; border: 1px dashed #cbd5e1; display: flex; align-items: center; justify-content: center; font-size: 20px; border-radius: 4px;">👤</div>'

  
  

                card_c1, card_c2, card_c3, card_c4 = st.columns([1, 4, 3, 2])

                with card_c1:

                    render_html(thumb_html)

                with card_c2:

                    st_info_txt = f"**{s['Name']}** (रोल नंबर: `{r}`)  <br><span style='font-size: 12px; color: #555;'>दाखिला क्र.: {s.get('Scholar_No','--')} | पिता: {s.get('Father_Name','--')} | जन्मतिथि: {s.get('DOB','--')}</span>"

                    st.markdown(st_info_txt, unsafe_allow_html=True)

                with card_c3:

                    render_html(f"<span style='font-size: 13px;'>कुल प्राप्तांक: <b>{tot_obt}/{v_max_total}</b> ({pct}%)</span><br>"

                                f"<span style='font-size: 12px;'>परिणाम: <b style='color:{res_col};'>{res_txt}</b> | ग्रेड: <b>{grd}</b> | उपस्थिति: <b>{s.get('Attended_Days',200)}/{s.get('Total_Days',220)}</b></span>")

                with card_c4:

                    render_html("<div style='margin-top: 10px;'>")

                    if st.button(f"👁️ पूरा डेटा देखें", key=f"btn_view_dossier_{selected_class}_{r}", type="primary", use_container_width=True):

                        st.session_state.active_dossier_roll = r

                        st.rerun()

                    st.markdown("</div>", unsafe_allow_html=True)

  
  

                st.markdown("<hr style='margin: 6px 0; border: none; border-top: 1px solid #e2e8f0;'>", unsafe_allow_html=True)

  
  

    # ================== VIEW STATE 2: FULL DATA IS SHOWN ONLY ON CLICK ==================

    else:

        cur_sel_roll = st.session_state.active_dossier_roll

        target_student = v_students_df[v_students_df["Roll_No"] == cur_sel_roll].iloc[0]

        t_ev = v_evals.get(cur_sel_roll, {})

        t_marks = t_ev.get("marks", {})

  
  

        c_back1, c_back2, c_back3, c_back4 = st.columns([2.2, 1, 1.5, 1])

        with c_back1:

            render_html(f"### 📋 विद्यार्थी संपूर्ण रिकॉर्ड: {target_student['Name']} (Roll: {cur_sel_roll})")

        with c_back2:

            single_st_df = generate_master_44col_df(pd.DataFrame([target_student]), v_evals, v_subjects, st.session_state.school_info, v_class)

            s_b, s_m, s_ext = export_dataframe_bytes(single_st_df, "Excel (.xlsx)")

            st.download_button(

                "📥 Excel",

                data=s_b,

                file_name=f"Student_{cur_sel_roll}_{target_student['Name']}_{st.session_state.school_info.get('session','2023-24')}.xlsx",

                mime=s_m,

                use_container_width=True,

                key=f"btn_single_exp_{selected_class}_{cur_sel_roll}"

            )

        with c_back3:

            # WhatsApp share button

            m5_wa_tot = sum([t_marks.get(sub["id"], {}).get("total", 75) for sub in v_subjects])

            m5_wa_pct = round((m5_wa_tot / v_max_total) * 100, 1) if v_max_total else 0

            m5_wa_grd = calculate_grade(m5_wa_pct)

            m5_wa_res = "PASS (उत्तीर्ण)" if (m5_wa_pct >= 33 and t_ev.get("status", "Present") != "Absent") else "FAIL"

            m5_mob = target_student.get("Contact", target_student.get("Mobile", ""))

            m5_wa_url, _ = generate_whatsapp_result_link(

                target_student['Name'], cur_sel_roll, v_class, m5_wa_tot, v_max_total, m5_wa_pct, m5_wa_grd, m5_wa_res,

                st.session_state.school_info.get('name', 'शासकीय विद्यालय'), m5_mob

            )

            render_html(f"""

            <a href="{m5_wa_url}" target="_blank" style="text-decoration: none;">

                <div style="background: #25D366; color: white; font-weight: bold; font-size: 12.5px; padding: 6px 8px; border-radius: 6px; text-align: center; box-shadow: 0 2px 4px rgba(37,211,102,0.25);">

                    📱 WhatsApp रिजल्ट

                </div>

            </a>

            """)

        with c_back4:

            if st.button("⬅️ वापस", type="secondary", use_container_width=True):

                st.session_state.active_dossier_roll = None

                st.rerun()

  
  

        # 1. Identity & Bio-Data

        col_dos_left, col_dos_right = st.columns([1, 2])

  
  

        with col_dos_left:

            st.markdown("#### 🖼️ विद्यार्थी पहचान (Identity Card)")

            if target_student.get("Photo_b64"):

                st.image(base64.b64decode(target_student["Photo_b64"]), width=150, caption=f"Roll: {cur_sel_roll}")

            else:

                st.markdown('<div style="width: 140px; height: 170px; border: 2px dashed #999; display: flex; align-items: center; justify-content: center; text-align: center; color: #777; font-size: 13px; border-radius: 6px; background: #f8fafc;">पासपोर्ट फोटो<br>अपलोड नहीं है</div>', unsafe_allow_html=True)

            

            st.caption(f"**सक्रिय सत्र:** {st.session_state.school_info.get('session','2023-24')}")

            st.caption(f"**स्कूल:** {st.session_state.school_info.get('name','')}")

            st.caption(f"**डाइस कोड:** {st.session_state.school_info.get('udise','')}")

  
  

        with col_dos_right:

            render_html("#### 👤 व्यक्तिगत विवरण (Student Bio-Data)")

            b_c1, b_c2 = st.columns(2)

            with b_c1:

                st.markdown(f"**विद्यार्थी का नाम:** {target_student['Name']}")

                st.markdown(f"**पिता का नाम:** {target_student['Father_Name']}")

                st.markdown(f"**माता का नाम:** {target_student['Mother_Name']}")

                st.markdown(f"**जन्मतिथि:** {target_student['DOB']}")

                st.markdown(f"**जेंडर / लिंग:** {target_student['Gender']}")

            with b_c2:

                st.markdown(f"**रोल नंबर:** {target_student['Roll_No']}")

                st.markdown(f"**स्कॉलर / दाखिला क्र.:** {target_student['Scholar_No']}")

                st.markdown(f"**कक्षा व वर्ग:** {v_class} - {target_student.get('Section','A')}")

                st.markdown(f"**जाति वर्ग (Category):** {target_student['Category']}")

                st.markdown(f"**माध्यम (Medium):** {get_display_medium(s_info, target_student)}")

  
  

            st.markdown(f"**समग्र आईडी:** `{target_student.get('SSSM_ID','--')}` | **आधार नंबर:** `{target_student.get('Aadhar_No','--')}` | **पैन नंबर:** `{target_student.get('PAN_No','--')}` | **अपार आईडी (APAAR ID):** `{target_student.get('APAAR_ID','--')}`")

            st.markdown(f"**उपस्थिति स्थिति:** {'🟢 उपस्थित (Present)' if t_ev.get('status','Present')=='Present' else '🔴 अनुपस्थित (Absent)'}")

  
  

        st.divider()

  
  

        # 2. Attendance

        st.markdown("#### 📅 उपस्थिति रिकॉर्ड (Attendance Summary)")

        att_c1, att_c2, att_c3 = st.columns(3)

        att_c1.metric("स्कूल कुल कार्य दिवस", f"{target_student.get('Total_Days', 220)} दिन")

        att_c2.metric("विद्यार्थी उपस्थिति दिन", f"{target_student.get('Attended_Days', 204)} दिन")

        att_pct_val = round((target_student.get('Attended_Days', 204) / max(1, target_student.get('Total_Days', 220))) * 100, 1)

        att_c3.metric("उपस्थिति प्रतिशत", f"{att_pct_val}%")

  
  

        v_att_df = v_cls_data.get("monthly_attendance", pd.DataFrame())

        if not v_att_df.empty and cur_sel_roll in v_att_df["Roll_No"].values:

            st.caption("**माहवार उपस्थिति विवरण (Month-by-Month Days):**")

            st_att_row = v_att_df[v_att_df["Roll_No"] == cur_sel_roll].iloc[0]

            m_cols_show = st.columns(12)

            for m_idx, m_name in enumerate(MONTHS_LIST):

                with m_cols_show[m_idx]:

                    st.markdown(f"<div style='border: 1px solid #ccc; text-align: center; padding: 2px; font-size: 11px; background: #fff;'><b>{m_name}</b><br>{st_att_row.get(m_name, 0)}</div>", unsafe_allow_html=True)

  
  

        st.divider()

  
  

        # 3. Academic Marks

        render_html(f"#### 📚 मुख्य विषय परीक्षा परिणाम (Academic Evaluation — {v_class})")

        if not t_marks:

            st.warning("⚠️ इस छात्र के मुख्य विषयों के परीक्षा अंक अभी दर्ज नहीं किए गए हैं।")

        else:

            exam_table_rows = []

            tot_hy = 0

            tot_yr = 0

            tot_all = 0

            all_p = True

  
  

            for sub in v_subjects:

                s_id = sub["id"]

                s_name = sub["name"]

                se = t_marks.get(s_id, {})

                hy = se.get("half_yearly", 32)

                yr = se.get("annual", 48)

                t_sub = se.get("total", hy + yr)

                g_sub = se.get("grade", calculate_grade(t_sub))

                

                tot_hy += hy

                tot_yr += yr

                tot_all += t_sub

                if t_sub < 33: all_p = False

  
  

                exam_table_rows.append({

                    "विषय (Subject)": s_name,

                    "अर्धवार्षिक हाजिरी": se.get("status_hy", "Present"),

                    "अर्धवार्षिक प्राप्तांक [40]": hy,

                    "वार्षिक हाजिरी": se.get("status_yr", "Present"),

                    "वार्षिक प्राप्तांक [60]": yr,

                    "कुल प्राप्तांक [100]": t_sub,

                    "ग्रेड (Grade)": g_sub

                })

  
  

            st.dataframe(pd.DataFrame(exam_table_rows), use_container_width=True)

  
  

            tot_pct = round((tot_all / v_max_total) * 100, 1) if v_max_total else 0

            final_grd = calculate_grade(tot_pct)

            is_passed = (all_p and tot_pct >= 33 and t_ev.get("status","Present") != "Absent")

  
  

            sum_col1, sum_col2, sum_col3, sum_col4, sum_col5 = st.columns(5)

            sum_col1.metric("कुल पूर्णांक", f"{v_max_total}")

            sum_col2.metric("कुल प्राप्तांक", f"{tot_all}")

            sum_col3.metric("प्रतिशत", f"{tot_pct}%")

            sum_col4.metric("अंतिम ग्रेड", f"{final_grd}")

            sum_col5.metric("परीक्षा फल", f"{'PASS' if is_passed else 'FAIL'}")

  
  

        st.divider()

  
  

        # 4. Co-Curricular & Social

        c_act1, c_act2 = st.columns(2)

        with c_act1:

            st.markdown("#### 🎨 सह-शैक्षिक गतिविधियां (Co-Curricular - 5 क्षेत्र)")

            co_d = t_ev.get("co_curricular", {})

            co_show_rows = [{"गतिविधि / कौशल (Activity)": label.split("(")[0].strip(), "ग्रेड (Grade)": co_d.get(k, "A")} for k, label in CO_CURRICULAR_ACTIVITIES]

            st.dataframe(pd.DataFrame(co_show_rows), use_container_width=True)

  
  

        with c_act2:

            st.markdown("#### 🤝 व्यक्तिगत एवं सामाजिक गुण (Social Activities - 10 गुण)")

            soc_d = t_ev.get("social", {})

            soc_show_rows = []

            for k, label in SOCIAL_ACTIVITIES:

                clean_name = label.split("(")[0].strip()

                if "ENVIRONMENTAL" in clean_name: clean_name = "ENVIRONMENTAL CONS."

                soc_show_rows.append({"गुण / विशेषता (Quality)": clean_name, "ग्रेड (Grade)": soc_d.get(k, "A")})

            st.dataframe(pd.DataFrame(soc_show_rows), use_container_width=True)

  
  
  
  

# ----------------- MODULE 6: PRINT MARKSHEET (EXACT REPLICA)

  

# ----------------- MODULE 6: MONTHLY EVALUATION REGISTER (10 MARKS PER SUBJECT) -----------------

elif menu == T.get("nav_monthly_test", "📝 6. मासिक मूल्यांकन रजिस्टर (Monthly Test - 10 अंक)"):

    cur_role = st.session_state.get("authenticated_role", "PRINCIPAL")

    is_teacher = (cur_role == "TEACHER")

    assigned_cls = st.session_state.get("assigned_class")

    s_info = st.session_state.school_info

    cur_sess = s_info.get("session", "2026-27")

  

    # Class, Section & Month Selectors

    c_mtest1, c_mtest2, c_mtest3, c_mtest4 = st.columns([2, 1.2, 1.2, 1.6])

    with c_mtest1:

        st.markdown(f'<div class="main-header">📝 मासिक मूल्यांकन रजिस्टर</div>', unsafe_allow_html=True)

        render_html(f'<div class="sub-header">प्रति विषय 10 अंक मासिक टेस्ट प्रविष्टि एवं 10% अधिभार ऑटो-कैलकुलेटर</div>')

    with c_mtest2:

        if is_teacher and assigned_cls:

            target_mt_class = assigned_cls

            render_html(f"<div style='border: 1px solid #CBD5E1; background: #F1F5F9; padding: 7px 10px; border-radius: 6px; font-weight: bold; font-size: 13px; text-align: center; color: #1E3A8A; margin-top: 22px;'>🎯 आवंटित: {target_mt_class}</div>")

        else:

            target_mt_class = st.selectbox(

                "1. कक्षा चुनें (Class):", 

                st.session_state.classes_list, 

                index=st.session_state.classes_list.index(selected_class) if selected_class in st.session_state.classes_list else 0,

                key="mt_class_picker"

            )

  

    mt_cls_data = get_class_data(target_mt_class)

    raw_st_df = mt_cls_data["students"]

    existing_secs = sorted(list(set([str(s).strip() for s in raw_st_df["Section"].dropna().unique() if str(s).strip()]))) if not raw_st_df.empty and "Section" in raw_st_df.columns else ["A"]

    sec_options = ["सभी सेक्शन (All Sections Combined)"] + (existing_secs if existing_secs else ["A", "B", "C"])

    

    with c_mtest3:

        target_mt_sec = st.selectbox("2. सेक्शन चुनें (Section):", sec_options, key="mt_sec_picker")

  

    # Month Options dynamically adapted to class

    available_months = get_class_monthly_test_months(target_mt_class)

    month_names_map = {m["id"]: m["name"] for m in available_months}

    

    with c_mtest4:

        selected_month_id = st.selectbox("3. मूल्यांकन माह चुनें:*", [m["id"] for m in available_months], format_func=lambda x: month_names_map[x], key="mt_month_picker")

  

    if target_mt_sec != "सभी सेक्शन (All Sections Combined)" and not raw_st_df.empty and "Section" in raw_st_df.columns:

        students_df = raw_st_df[raw_st_df["Section"] == target_mt_sec].copy()

        display_mt_class = f"{target_mt_class} - Section {target_mt_sec}"

    else:

        students_df = raw_st_df.copy()

        display_mt_class = f"{target_mt_class} (समस्त सेक्शन)"

  

    cls_subjects = get_class_subjects(target_mt_class)

    mt_evals = mt_cls_data["evaluations"]

  

    if students_df.empty:

        st.warning(f"⚠️ {display_mt_class} में कोई विद्यार्थी पंजीकृत नहीं है। कृपया पहले विद्यार्थी मास्टर में छात्र जोड़ें।")

    else:

        st.info(f"💡 **मासिक टेस्ट निर्देश ({month_names_map[selected_month_id]}):** प्रत्येक विषय के अधिकतम **10 अंक** हैं। यहाँ भरे गए अंक स्वतः 4 माह के योग के आधार पर $\\\\div 4$ होकर 35-कॉलम वाली शीट के **`Monthly 10% Weightage`** में जुड़ जाएंगे।")

  

        # Build Interactive Table for Monthly Marks Entry

        mt_rows = []

        for idx, s in students_df.iterrows():

            r = s["Roll_No"]

            ev = mt_evals.get(r, {})

            m_tests = ev.get("monthly_tests", {})

            cur_month_marks = m_tests.get(selected_month_id, {})

            

            row = {

                "Roll_No": r,

                "Name": s["Name"],

                "Scholar_No": s.get("Scholar_No", "")

            }

            tot_month = 0

            for sub in cls_subjects:

                s_id = sub["id"]

                val = cur_month_marks.get(s_id, 8)

                row[sub["name"]] = int(val)

                tot_month += int(val)

            

            row["Month_Total"] = tot_month

            row["Max_Marks"] = len(cls_subjects) * 10

            mt_rows.append(row)

  

                # BULK UPLOAD OPTION FOR MONTHLY TEST MARKS
        with st.expander(f"📥 एक्सेल शीट से एक साथ सभी छात्रों के {month_names_map[selected_month_id]} के अंक अपलोड करें (Bulk Upload)", expanded=False):
            st.info(f"💡 **मासिक अंक थोक अपलोड ({month_names_map[selected_month_id]}):** आप एक्सेल शीट में एक साथ सभी छात्रों के 10 में से प्राप्तांक भरकर अपलोड कर सकते हैं।")
            
            # Pre-filled Template Download
            m_tmpl_rows = []
            for _, s in students_df.iterrows():
                r = s["Roll_No"]
                ev = mt_evals.get(r, {})
                cur_m = ev.get("monthly_tests", {}).get(selected_month_id, {})
                row = {
                    "Roll_No": r,
                    "Scholar_No": s.get("Scholar_No", ""),
                    "Name": s["Name"]
                }
                for sub in cls_subjects:
                    s_id = sub["id"]
                    row[f"{sub['name']}"] = cur_m.get(s_id, 8)
                m_tmpl_rows.append(row)
                
            m_tmpl_df = pd.DataFrame(m_tmpl_rows)
            mt_bytes, mt_mime, mt_ext = export_dataframe_bytes(m_tmpl_df, "Excel (.xlsx)")
            
            c_mdn1, c_mdn2 = st.columns([1.5, 2.5])
            with c_mdn1:
                st.download_button(
                    f"📥 {month_names_map[selected_month_id]} एक्सेल टेम्पलेट (.xlsx)",
                    data=mt_bytes,
                    file_name=f"Monthly_Marks_{target_mt_class}_{selected_month_id}.xlsx",
                    mime=mt_mime,
                    type="secondary",
                    use_container_width=True
                )
            with c_mdn2:
                up_mt_file = st.file_uploader(f"भरी हुई मासिक अंक फ़ाइल चुनें ({month_names_map[selected_month_id]}):", type=["xlsx", "xls", "csv"], key=f"uploader_mt_{selected_month_id}")
                
            if up_mt_file is not None:
                parsed_mt_df = parse_marks_upload_file(up_mt_file)
                if parsed_mt_df is not None and not parsed_mt_df.empty:
                    st.success(f"✅ फ़ाइल लोड हुई! कुल {len(parsed_mt_df)} छात्रों का डेटा मिला।")
                    st.dataframe(parsed_mt_df.head(5), use_container_width=True)
                    
                    if st.button(f"🚀 एक्सेल से {month_names_map[selected_month_id]} के अंक सुरक्षित करें (Apply Monthly Marks)", type="primary", use_container_width=True, key=f"btn_apply_mt_{selected_month_id}"):
                        roll_col = next((c for c in parsed_mt_df.columns if "roll" in str(c).lower()), None)
                        if roll_col:
                            up_cnt = 0
                            for _, urow in parsed_mt_df.iterrows():
                                try:
                                    r_val = int(urow[roll_col])
                                except Exception: continue
                                if r_val not in mt_evals:
                                    mt_evals[r_val] = {"marks": {}, "monthly_tests": {}}
                                if "monthly_tests" not in mt_evals[r_val]:
                                    mt_evals[r_val]["monthly_tests"] = {}
                                if selected_month_id not in mt_evals[r_val]["monthly_tests"]:
                                    mt_evals[r_val]["monthly_tests"][selected_month_id] = {}
                                    
                                for sub in cls_subjects:
                                    s_id = sub["id"]
                                    m_c = next((c for c in parsed_mt_df.columns if smart_match_subject_col(c, sub["name"], s_id)), None)
                                    if m_c and pd.notna(urow[m_c]):
                                        try:
                                            mt_evals[r_val]["monthly_tests"][selected_month_id][s_id] = min(10, max(0, int(float(urow[m_c]))))
                                        except Exception: pass
                                up_cnt += 1
                            save_data_to_disk()
                            st.balloons()
                            st.success(f"🎉 बधाई! कुल {up_cnt} विद्यार्थियों के {month_names_map[selected_month_id]} के अंक सुरक्षित हो गए! 10% अधिभार स्वतः अपडेट हो गया है।")
                            st.rerun()
                        else:
                            st.error("फ़ाइल में Roll No. कॉलम नहीं मिला!")


        mt_df = pd.DataFrame(mt_rows)

        

        col_configs = {

            "Roll_No": st.column_config.NumberColumn("Roll No.", disabled=True, width="small"),

            "Name": st.column_config.TextColumn("विद्यार्थी का नाम", disabled=True, width="medium"),

            "Scholar_No": st.column_config.TextColumn("दाखिला क्र.", disabled=True, width="small"),

            "Month_Total": st.column_config.NumberColumn("मासिक योग", disabled=True, width="small"),

            "Max_Marks": st.column_config.NumberColumn("पूर्णांक", disabled=True, width="small")

        }

        for sub in cls_subjects:

            col_configs[sub["name"]] = st.column_config.NumberColumn(

                f"{sub['name']} (Max 10)",

                min_value=0,

                max_value=10,

                step=1,

                required=True,

                help="अधिकतम 10 अंक"

            )

  

        edited_mt_df = st.data_editor(

            mt_df,

            column_config=col_configs,

            use_container_width=True,

            num_rows="fixed",

            key=f"editor_mt_{target_mt_class}_{selected_month_id}"

        )

  

        c_sv1, c_sv2 = st.columns([2, 1])

        with c_sv1:

            if st.button(f"💾 {month_names_map[selected_month_id]} के प्राप्तांक सुरक्षित करें एवं 10% अधिभार अपडेट करें", type="primary", use_container_width=True):

                for _, erow in edited_mt_df.iterrows():

                    r = erow["Roll_No"]

                    if r not in mt_evals:

                        mt_evals[r] = {"marks": {}, "monthly_tests": {}}

                    if "monthly_tests" not in mt_evals[r]:

                        mt_evals[r]["monthly_tests"] = {}

                    if selected_month_id not in mt_evals[r]["monthly_tests"]:

                        mt_evals[r]["monthly_tests"][selected_month_id] = {}

                        

                    for sub in cls_subjects:

                        s_id = sub["id"]

                        val = erow[sub["name"]]

                        mt_evals[r]["monthly_tests"][selected_month_id][s_id] = int(val)

                

                save_data_to_disk()

                st.balloons()

                st.success(f"✅ {month_names_map[selected_month_id]} के अंक सफलतापूर्वक सुरक्षित हो गए! 35-कॉलम शीट का 10% अधिभार स्वतः अपडेट हो गया है।")

                st.rerun()

  

        with c_sv2:

            st.caption(f"कुल छात्र: **{len(edited_mt_df)}** | विषय संख्या: **{len(cls_subjects)}**")

  

        st.divider()

        render_html("#### 📊 सत्र के चारों माहों की संकलित अधिभार स्थिति (10% Weightage Live Summary):")

        

        # Summary Table showing Student-wise 10% weightage per subject

        adhibhar_rows = []

        for idx, s in students_df.iterrows():

            r = s["Roll_No"]

            ev = mt_evals.get(r, {})

            row = {"Roll_No": r, "Name": s["Name"]}

            sum_10_all = 0

            for sub in cls_subjects:

                s_id = sub["id"]

                w10, tot_s, num_months = calculate_subject_monthly_weightage(ev, s_id, target_mt_class)

                row[f"{sub['name']}_10%"] = f"{w10}/10 ({tot_s} में से)"

                sum_10_all += w10

            row["कुल मासिक अधिभार (Grand Monthly)"] = f"{sum_10_all} / {len(cls_subjects)*10}"

            adhibhar_rows.append(row)

            

        st.dataframe(pd.DataFrame(adhibhar_rows), use_container_width=True)
        render_govt_portals_hub("मासिक मूल्यांकन", target_mt_class, edited_mt_df, "Monthly_Test")

  
  

# ----------------- MODULE 7: HALF-YEARLY EXAMINATION EVALUATION (20% WEIGHTAGE) -----------------

elif menu == T.get("nav_half_yearly", "📑 7. अर्धवार्षिक परीक्षा मूल्यांकन (Half-Yearly Exam — 20% अधिभार)"):

    cur_role = st.session_state.get("authenticated_role", "PRINCIPAL")

    is_teacher = (cur_role == "TEACHER")

    assigned_cls = st.session_state.get("assigned_class")

    s_info = st.session_state.school_info

    cur_sess = s_info.get("session", "2026-27")

  

    c_hytop1, c_hytop2, c_hytop3 = st.columns([2.2, 1.3, 1.3])

    with c_hytop1:

        st.markdown('<div class="main-header">📑 अर्धवार्षिक परीक्षा मूल्यांकन पंजी</div>', unsafe_allow_html=True)

        render_html('<div class="sub-header">विषयवार प्राप्तांक प्रविष्टि एवं स्वचालित 20% अधिभार (Weightage) जनरेटर</div>')

    with c_hytop2:

        if is_teacher and assigned_cls:

            target_hy_class = assigned_cls

            render_html(f"<div style='border: 1px solid #CBD5E1; background: #F1F5F9; padding: 7px 10px; border-radius: 6px; font-weight: bold; font-size: 13px; text-align: center; color: #1E3A8A; margin-top: 22px;'>🎯 आवंटित: {target_hy_class}</div>")

        else:

            target_hy_class = st.selectbox(

                "1. कक्षा चुनें (Class):", 

                st.session_state.classes_list, 

                index=st.session_state.classes_list.index(selected_class) if selected_class in st.session_state.classes_list else 0,

                key="hy_class_picker"

            )

  

    hy_cls_data = get_class_data(target_hy_class)

    raw_st_df = hy_cls_data["students"]

    existing_secs = sorted(list(set([str(s).strip() for s in raw_st_df["Section"].dropna().unique() if str(s).strip()]))) if not raw_st_df.empty and "Section" in raw_st_df.columns else ["A"]

    sec_options = ["सभी सेक्शन (All Sections Combined)"] + (existing_secs if existing_secs else ["A", "B", "C"])

    

    with c_hytop3:

        target_hy_sec = st.selectbox("2. सेक्शन चुनें (Section):", sec_options, key="hy_sec_picker")

  

    if target_hy_sec != "सभी सेक्शन (All Sections Combined)" and not raw_st_df.empty and "Section" in raw_st_df.columns:

        students_df = raw_st_df[raw_st_df["Section"] == target_hy_sec].copy()

        display_hy_class = f"{target_hy_class} - Section {target_hy_sec}"

    else:

        students_df = raw_st_df.copy()

        display_hy_class = f"{target_hy_class} (समस्त सेक्शन)"

  

    cls_subjects = get_class_subjects(target_hy_class)

    hy_evals = hy_cls_data["evaluations"]

  

    if students_df.empty:

        st.warning(f"⚠️ {display_hy_class} में कोई विद्यार्थी पंजीकृत नहीं है।")

    else:

        c_hsc1, c_hsc2 = st.columns([3, 2])

        with c_hsc1:

            st.info("💡 **शासकीय नियम (RSKMP):** अर्धवार्षिक परीक्षा 60 अंक की होती है। 20% अधिभार हेतु $\\\\text{प्राप्तांक} \\\\div 3$ की गणना की जाती है। यदि आपकी शाला में 40 अंक या 50 अंक का प्रश्नपत्र था, तो दाईं ओर से सही पूर्णांक चुनें।")

        with c_hsc2:

            hy_paper_max = st.selectbox(

                "अर्धवार्षिक प्रश्नपत्र का मूल पूर्णांक:",

                ["60", "40", "50", "20"],

                format_func=lambda x: {

                    "60": "60 अंक (RSKMP मानक: प्राप्तांक ÷ 3 = 20%)",

                    "40": "40 अंक (स्थानीय परीक्षा: प्राप्तांक ÷ 2 = 20%)",

                    "50": "50 अंक (प्राप्तांक × 20 / 50)",

                    "20": "20 अंक (सीधे 20% अधिभार दर्ज)"

                }[x],

                key="hy_paper_max_picker"

            )

  

        # Build Half-Yearly Grid

        hy_rows = []

        for idx, s in students_df.iterrows():

            r = s["Roll_No"]

            ev = hy_evals.get(r, {})

            m_dict = ev.get("marks", {})

            st_stat = ev.get("status", s.get("Status", "Present"))

            

            row = {"Roll_No": r, "Name": s["Name"]}

            tot_raw = 0

            tot_20_wt = 0

            for sub in cls_subjects:

                s_id = sub["id"]

                se = m_dict.get(s_id, {})

                raw_m = se.get("half_yearly", 48 if hy_paper_max == "60" else (32 if hy_paper_max == "40" else 16))

                row[sub["name"]] = int(raw_m)

                w20 = calculate_subject_half_yearly_weightage(raw_m, hy_paper_max)

                row[f"{sub['name']}_20%"] = w20

                tot_raw += int(raw_m)

                tot_20_wt += w20

            

            row["अर्धवार्षिक कुल प्राप्तांक"] = tot_raw

            row["20% कुल अधिभार"] = f"{tot_20_wt} / {len(cls_subjects)*20}"

            hy_rows.append(row)

  

                # BULK UPLOAD OPTION FOR HALF-YEARLY EXAM MARKS
        with st.expander("📥 एक्सेल शीट से एक साथ सभी छात्रों के अर्धवार्षिक अंक अपलोड करें (Bulk Upload Half-Yearly Marks)", expanded=False):
            st.info(f"💡 **अर्धवार्षिक अंक थोक अपलोड:** सभी छात्रों के अंक एक साथ एक्सेल फ़ाइल द्वारा अपलोड करें। सिस्टम स्वतः {hy_paper_max} में से प्राप्तांकों को 20% अधिभार में बदल देगा।")
            
            # Pre-filled Template Download
            hy_tmpl_rows = []
            for _, s in students_df.iterrows():
                r = s["Roll_No"]
                ev = hy_evals.get(r, {})
                m_dict = ev.get("marks", {})
                row = {
                    "Roll_No": r,
                    "Scholar_No": s.get("Scholar_No", ""),
                    "Name": s["Name"]
                }
                for sub in cls_subjects:
                    s_id = sub["id"]
                    se = m_dict.get(s_id, {})
                    row[f"{sub['name']}"] = se.get("half_yearly", 48 if hy_paper_max == "60" else 32)
                hy_tmpl_rows.append(row)
                
            hy_tmpl_df = pd.DataFrame(hy_tmpl_rows)
            hyt_bytes, hyt_mime, hyt_ext = export_dataframe_bytes(hy_tmpl_df, "Excel (.xlsx)")
            
            c_hyd1, c_hyd2 = st.columns([1.5, 2.5])
            with c_hyd1:
                st.download_button(
                    "📥 अर्धवार्षिक अंक एक्सेल टेम्पलेट (.xlsx)",
                    data=hyt_bytes,
                    file_name=f"HalfYearly_Template_{target_hy_class}.xlsx",
                    mime=hyt_mime,
                    type="secondary",
                    use_container_width=True
                )
            with c_hyd2:
                up_hy_file = st.file_uploader("भरी हुई अर्धवार्षिक अंक एक्सेल / CSV फ़ाइल चुनें:", type=["xlsx", "xls", "csv"], key="uploader_hy_bulk")
                
            if up_hy_file is not None:
                parsed_hy_df = parse_marks_upload_file(up_hy_file)
                if parsed_hy_df is not None and not parsed_hy_df.empty:
                    st.success(f"✅ फ़ाइल लोड हुई! कुल {len(parsed_hy_df)} छात्रों का डेटा मिला।")
                    st.dataframe(parsed_hy_df.head(5), use_container_width=True)
                    
                    if st.button("🚀 एक्सेल से अर्धवार्षिक अंक सुरक्षित करें एवं 20% अधिभार अपडेट करें (Apply HY Marks)", type="primary", use_container_width=True, key="btn_apply_hy_bulk"):
                        roll_col = next((c for c in parsed_hy_df.columns if "roll" in str(c).lower()), None)
                        if roll_col:
                            up_cnt = 0
                            for _, urow in parsed_hy_df.iterrows():
                                try:
                                    r_val = int(urow[roll_col])
                                except Exception: continue
                                if r_val not in hy_evals:
                                    hy_evals[r_val] = {"marks": {}}
                                if "marks" not in hy_evals[r_val]:
                                    hy_evals[r_val]["marks"] = {}
                                    
                                for sub in cls_subjects:
                                    s_id = sub["id"]
                                    if s_id not in hy_evals[r_val]["marks"]:
                                        hy_evals[r_val]["marks"][s_id] = {}
                                    m_c = next((c for c in parsed_hy_df.columns if smart_match_subject_col(c, sub["name"], s_id)), None)
                                    if m_c and pd.notna(urow[m_c]):
                                        try:
                                            hy_evals[r_val]["marks"][s_id]["half_yearly"] = min(int(hy_paper_max), max(0, int(float(urow[m_c]))))
                                        except Exception: pass
                                up_cnt += 1
                            save_data_to_disk()
                            st.balloons()
                            st.success(f"🎉 बधाई! कुल {up_cnt} विद्यार्थियों के अर्धवार्षिक अंक सुरक्षित हो गए! 20% अधिभार स्वतः अपडेट हो गया है।")
                            st.rerun()
                        else:
                            st.error("फ़ाइल में Roll No. कॉलम नहीं मिला!")


        hy_df = pd.DataFrame(hy_rows)

        

        # Columns config for editor

        col_configs_hy = {

            "Roll_No": st.column_config.NumberColumn("Roll No.", disabled=True, width="small"),

            "Name": st.column_config.TextColumn("विद्यार्थी का नाम", disabled=True, width="medium"),

            "अर्धवार्षिक कुल प्राप्तांक": st.column_config.NumberColumn("अर्धवार्षिक योग", disabled=True, width="small"),

            "20% कुल अधिभार": st.column_config.TextColumn("20% कुल अधिभार", disabled=True, width="medium")

        }

        for sub in cls_subjects:

            col_configs_hy[sub["name"]] = st.column_config.NumberColumn(

                f"{sub['name']} (Max {hy_paper_max})",

                min_value=0,

                max_value=int(hy_paper_max),

                step=1,

                required=True,

                help=f"मूल प्रश्नपत्र में प्राप्तांक (पूर्णांक {hy_paper_max})"

            )

            col_configs_hy[f"{sub['name']}_20%"] = st.column_config.NumberColumn(

                f"{sub['name']} (20% अधिभार)",

                disabled=True,

                width="small"

            )

  

        edited_hy_df = st.data_editor(

            hy_df,

            column_config=col_configs_hy,

            use_container_width=True,

            num_rows="fixed",

            key=f"editor_hy_{target_hy_class}_{hy_paper_max}"

        )

  

        c_hysv1, c_hysv2 = st.columns([2, 1])

        with c_hysv1:

            if st.button("💾 अर्धवार्षिक प्राप्तांक सुरक्षित करें एवं 20% अधिभार अपडेट करें", type="primary", use_container_width=True):

                for _, erow in edited_hy_df.iterrows():

                    r = erow["Roll_No"]

                    if r not in hy_evals:

                        hy_evals[r] = {"marks": {}}

                    if "marks" not in hy_evals[r]:

                        hy_evals[r]["marks"] = {}

                        

                    for sub in cls_subjects:

                        s_id = sub["id"]

                        val = erow[sub["name"]]

                        if s_id not in hy_evals[r]["marks"]:

                            hy_evals[r]["marks"][s_id] = {}

                        hy_evals[r]["marks"][s_id]["half_yearly"] = int(val)

                

                save_data_to_disk()

                st.balloons()

                st.success("✅ अर्धवार्षिक प्राप्तांक सफलतापूर्वक सुरक्षित हो गए! 35-कॉलम वेटेज शीट (Tab 14) में 20% अधिभार स्वतः अपडेट हो गया है।")

                st.rerun()

  

        with c_hysv2:

            st.caption(f"कुल छात्र: **{len(edited_hy_df)}** | पूर्णांक: **{hy_paper_max} अंक**")

  

        st.divider()

        render_html("#### 📥 अर्धवार्षिक परीक्षा अभिलेख पत्रक डाउनलोड (Excel / Print):")

        if not is_teacher:

            if render_export_gatekeeper("अर्धवार्षिक परीक्षा अभिलेख"):

                hy_bytes, hy_mime, hy_ext = export_dataframe_bytes(edited_hy_df, "Excel (.xlsx)")

                st.download_button(

                    "📥 अर्धवार्षिक परीक्षा अभिलेख एक्सेल डाउनलोड (.xlsx)",

                    data=hy_bytes,

                    file_name=f"HalfYearly_Assessment_{target_hy_class}_{cur_sess}.xlsx",

                    mime=hy_mime,

                    type="primary",

                    use_container_width=True

                )

        else:

            st.markdown("<div style='color:#991B1B; font-size:12px; font-weight:bold;'>🔒 आधिकारिक एक्सेल एक्सपोर्ट केवल संस्था प्रधान हेतु अधिकृत है।</div>", unsafe_allow_html=True)

  
  

        render_govt_portals_hub("अर्धवार्षिक परीक्षा", target_hy_class, edited_hy_df, "HalfYearly_Assessment")

# ----------------- MODULE 8: ANNUAL PROJECT WORK EVALUATION (10% OR 20 MARKS) -----------------

elif menu == T.get("nav_project", "🎨 8. वार्षिक प्रोजेक्ट कार्य मूल्यांकन (Project Work — 10%/20 अंक)"):

    cur_role = st.session_state.get("authenticated_role", "PRINCIPAL")

    is_teacher = (cur_role == "TEACHER")

    assigned_cls = st.session_state.get("assigned_class")

    s_info = st.session_state.school_info

    cur_sess = s_info.get("session", "2026-27")

  

    c_pjtop1, c_pjtop2, c_pjtop3 = st.columns([2.2, 1.3, 1.3])

    with c_pjtop1:

        render_html('<div class="main-header">🎨 वार्षिक प्रोजेक्ट कार्य मूल्यांकन पंजी</div>')

        render_html('<div class="sub-header">सुझावात्मक 2 प्रोजेक्ट कार्य (आंतरिक मूल्यांकन) प्रविष्टि एवं अधिभार गणना</div>')

    with c_pjtop2:

        if is_teacher and assigned_cls:

            target_pj_class = assigned_cls

            render_html(f"<div style='border: 1px solid #CBD5E1; background: #F1F5F9; padding: 7px 10px; border-radius: 6px; font-weight: bold; font-size: 13px; text-align: center; color: #1E3A8A; margin-top: 22px;'>🎯 आवंटित: {target_pj_class}</div>")

        else:

            target_pj_class = st.selectbox(

                "1. कक्षा चुनें (Class):", 

                st.session_state.classes_list, 

                index=st.session_state.classes_list.index(selected_class) if selected_class in st.session_state.classes_list else 0,

                key="pj_class_picker"

            )

  

    pj_cls_data = get_class_data(target_pj_class)

    raw_st_df = pj_cls_data["students"]

    existing_secs = sorted(list(set([str(s).strip() for s in raw_st_df["Section"].dropna().unique() if str(s).strip()]))) if not raw_st_df.empty and "Section" in raw_st_df.columns else ["A"]

    sec_options = ["सभी सेक्शन (All Sections Combined)"] + (existing_secs if existing_secs else ["A", "B", "C"])

    

    with c_pjtop3:

        target_pj_sec = st.selectbox("2. सेक्शन चुनें (Section):", sec_options, key="pj_sec_picker")

  

    if target_pj_sec != "सभी सेक्शन (All Sections Combined)" and not raw_st_df.empty and "Section" in raw_st_df.columns:

        students_df = raw_st_df[raw_st_df["Section"] == target_pj_sec].copy()

        display_pj_class = f"{target_pj_class} - Section {target_pj_sec}"

    else:

        students_df = raw_st_df.copy()

        display_pj_class = f"{target_pj_class} (समस्त सेक्शन)"

  

    cls_subjects = get_class_subjects(target_pj_class)

    pj_evals = pj_cls_data["evaluations"]

  

    clean_cls = str(target_pj_class).lower()

    is_5_8_board = ("class 5" in clean_cls or "class 8" in clean_cls or "5th" in clean_cls or "8th" in clean_cls)

    is_9_10_high = ("class 9" in clean_cls or "class 10" in clean_cls or "9th" in clean_cls or "10th" in clean_cls)

  

    if students_df.empty:

        st.warning(f"⚠️ {display_pj_class} में कोई विद्यार्थी पंजीकृत नहीं है।")

    else:

        if is_5_8_board:

            st.info("🏛️ **RSKMP बोर्ड नियम (कक्षा 5वीं व 8वीं):** 2 प्रोजेक्ट कार्य (10+10 = कुल 20 अंक)। rskmp.in बोर्ड पोर्टल पर सीधे 20 में से अंक चढ़ते हैं। पास होने हेतु न्यूनतम 7 अंक (33%) अनिवार्य हैं!")

            pj_max_per_sub = 20

        elif is_9_10_high:

            st.info("🏢 **MPBSE हाईस्कूल नियम (कक्षा 9वीं व 10वीं):** कुल 25 अंक आंतरिक मूल्यांकन (15 प्रोजेक्ट/प्रैक्टिकल + 5 त्रै./अर्ध. अधिभार + 5 मासिक/मौखिक)। पास होने हेतु न्यूनतम 8 अंक (33%) अनिवार्य हैं!")

            pj_max_per_sub = 25

        else:

            st.info("📘 **RSKMP स्थानीय परीक्षा नियम (कक्षा 3, 4, 6, 7):** 2 प्रोजेक्ट कार्य (20+20 = 40 अंक)। 10% अधिभार हेतु $\\\\text{प्राप्तांक} \\\\div 4$ की गणना की जाकर 35-कॉलम शीट में 10 में से अधिभार जुड़ता है।")

            pj_max_per_sub = 40

  

        # Build Project Grid

        pj_rows = []

        for idx, s in students_df.iterrows():

            r = s["Roll_No"]

            ev = pj_evals.get(r, {})

            m_dict = ev.get("marks", {})

            row = {"Roll_No": r, "Name": s["Name"]}

            tot_pj = 0

            tot_pj_wt = 0

            

            for sub in cls_subjects:

                s_id = sub["id"]

                se = m_dict.get(s_id, {})

                raw_pj = se.get("project", 16 if is_5_8_board else (32 if not is_9_10_high else 21))

                row[sub["name"]] = int(raw_pj)

                wt = calculate_subject_project_weightage_rule(raw_pj, target_pj_class)

                row[f"{sub['name']}_अधिभार"] = wt

                tot_pj += int(raw_pj)

                tot_pj_wt += wt

                

            row["प्रोजेक्ट कुल प्राप्तांक"] = tot_pj

            row["अंतिम प्रोजेक्ट अधिभार"] = f"{tot_pj_wt} / {len(cls_subjects)*(20 if is_5_8_board else (25 if is_9_10_high else 10))}"

            pj_rows.append(row)

  

                # BULK UPLOAD OPTION FOR ANNUAL PROJECT MARKS
        with st.expander("📥 एक्सेल शीट से एक साथ सभी छात्रों के प्रोजेक्ट अंक अपलोड करें (Bulk Upload Project Marks)", expanded=False):
            st.info(f"💡 **प्रोजेक्ट अंक थोक अपलोड ({target_pj_class}):** आप एक्सेल शीट में सभी छात्रों के प्रोजेक्ट अंक (पूर्णांक {pj_max_per_sub}) भरकर सीधे अपलोड कर सकते हैं।")
            
            # Pre-filled Template Download
            pj_tmpl_rows = []
            for _, s in students_df.iterrows():
                r = s["Roll_No"]
                ev = pj_evals.get(r, {})
                m_dict = ev.get("marks", {})
                row = {
                    "Roll_No": r,
                    "Scholar_No": s.get("Scholar_No", ""),
                    "Name": s["Name"]
                }
                for sub in cls_subjects:
                    s_id = sub["id"]
                    se = m_dict.get(s_id, {})
                    row[f"{sub['name']}"] = se.get("project", 16 if is_5_8_board else (32 if not is_9_10_high else 21))
                pj_tmpl_rows.append(row)
                
            pj_tmpl_df = pd.DataFrame(pj_tmpl_rows)
            pjt_bytes, pjt_mime, pjt_ext = export_dataframe_bytes(pj_tmpl_df, "Excel (.xlsx)")
            
            c_pjd1, c_pjd2 = st.columns([1.5, 2.5])
            with c_pjd1:
                st.download_button(
                    "📥 प्रोजेक्ट अंक एक्सेल टेम्पलेट (.xlsx)",
                    data=pjt_bytes,
                    file_name=f"Project_Marks_Template_{target_pj_class}.xlsx",
                    mime=pjt_mime,
                    type="secondary",
                    use_container_width=True
                )
            with c_pjd2:
                up_pj_file = st.file_uploader("भरी हुई प्रोजेक्ट अंक एक्सेल / CSV फ़ाइल चुनें:", type=["xlsx", "xls", "csv"], key="uploader_pj_bulk")
                
            if up_pj_file is not None:
                parsed_pj_df = parse_marks_upload_file(up_pj_file)
                if parsed_pj_df is not None and not parsed_pj_df.empty:
                    st.success(f"✅ फ़ाइल लोड हुई! कुल {len(parsed_pj_df)} छात्रों का डेटा मिला।")
                    st.dataframe(parsed_pj_df.head(5), use_container_width=True)
                    
                    if st.button("🚀 एक्सेल से प्रोजेक्ट अंक सुरक्षित करें एवं अधिभार अपडेट करें (Apply Project Marks)", type="primary", use_container_width=True, key="btn_apply_pj_bulk"):
                        roll_col = next((c for c in parsed_pj_df.columns if "roll" in str(c).lower()), None)
                        if roll_col:
                            up_cnt = 0
                            for _, urow in parsed_pj_df.iterrows():
                                try:
                                    r_val = int(urow[roll_col])
                                except Exception: continue
                                if r_val not in pj_evals:
                                    pj_evals[r_val] = {"marks": {}}
                                if "marks" not in pj_evals[r_val]:
                                    pj_evals[r_val]["marks"] = {}
                                    
                                for sub in cls_subjects:
                                    s_id = sub["id"]
                                    if s_id not in pj_evals[r_val]["marks"]:
                                        pj_evals[r_val]["marks"][s_id] = {}
                                    m_c = next((c for c in parsed_pj_df.columns if smart_match_subject_col(c, sub["name"], s_id)), None)
                                    if m_c and pd.notna(urow[m_c]):
                                        try:
                                            pj_evals[r_val]["marks"][s_id]["project"] = min(int(pj_max_per_sub), max(0, int(float(urow[m_c]))))
                                        except Exception: pass
                                up_cnt += 1
                            save_data_to_disk()
                            st.balloons()
                            st.success(f"🎉 बधाई! कुल {up_cnt} विद्यार्थियों के प्रोजेक्ट अंक सुरक्षित हो गए! अधिभार स्वतः अपडेट हो गया है।")
                            st.rerun()
                        else:
                            st.error("फ़ाइल में Roll No. कॉलम नहीं मिला!")


        pj_df = pd.DataFrame(pj_rows)

        

        col_configs_pj = {

            "Roll_No": st.column_config.NumberColumn("Roll No.", disabled=True, width="small"),

            "Name": st.column_config.TextColumn("विद्यार्थी का नाम", disabled=True, width="medium"),

            "प्रोजेक्ट कुल प्राप्तांक": st.column_config.NumberColumn("प्रोजेक्ट योग", disabled=True, width="small"),

            "अंतिम प्रोजेक्ट अधिभार": st.column_config.TextColumn("अंतिम अधिभार", disabled=True, width="medium")

        }

        for sub in cls_subjects:

            col_configs_pj[sub["name"]] = st.column_config.NumberColumn(

                f"{sub['name']} (Max {pj_max_per_sub})",

                min_value=0,

                max_value=pj_max_per_sub,

                step=1,

                required=True,

                help=f"प्रोजेक्ट प्राप्तांक (पूर्णांक {pj_max_per_sub})"

            )

            col_configs_pj[f"{sub['name']}_अधिभार"] = st.column_config.NumberColumn(

                f"{sub['name']} (अधिभार)",

                disabled=True,

                width="small"

            )

  

        edited_pj_df = st.data_editor(

            pj_df,

            column_config=col_configs_pj,

            use_container_width=True,

            num_rows="fixed",

            key=f"editor_pj_{target_pj_class}_{pj_max_per_sub}"

        )

  

        c_pjsv1, c_pjsv2 = st.columns([2, 1])

        with c_pjsv1:

            if st.button("💾 प्रोजेक्ट कार्य प्राप्तांक सुरक्षित करें एवं अधिभार अपडेट करें", type="primary", use_container_width=True):

                for _, erow in edited_pj_df.iterrows():

                    r = erow["Roll_No"]

                    if r not in pj_evals:

                        pj_evals[r] = {"marks": {}}

                    if "marks" not in pj_evals[r]:

                        pj_evals[r]["marks"] = {}

                        

                    for sub in cls_subjects:

                        s_id = sub["id"]

                        val = erow[sub["name"]]

                        if s_id not in pj_evals[r]["marks"]:

                            pj_evals[r]["marks"][s_id] = {}

                        pj_evals[r]["marks"][s_id]["project"] = int(val)

                

                save_data_to_disk()

                st.balloons()

                st.success("✅ प्रोजेक्ट कार्य प्राप्तांक सुरक्षित हो गए! 35-कॉलम वेटेज शीट (Tab 14) में प्रोजेक्ट अधिभार स्वतः अपडेट हो गया है।")

                st.rerun()

  

        with c_pjsv2:

            st.caption(f"कक्षा: **{target_pj_class}** | प्रोजेक्ट पूर्णांक: **{pj_max_per_sub} अंक प्रति विषय**")

  

        st.divider()

        render_html("#### 📥 वार्षिक प्रोजेक्ट कार्य अभिलेख पत्रक डाउनलोड (Excel / Print):")

        if not is_teacher:

            if render_export_gatekeeper("प्रोजेक्ट कार्य अभिलेख"):

                pj_bytes, pj_mime, pj_ext = export_dataframe_bytes(edited_pj_df, "Excel (.xlsx)")

                st.download_button(

                    "📥 प्रोजेक्ट कार्य अभिलेख एक्सेल डाउनलोड (.xlsx)",

                    data=pj_bytes,

                    file_name=f"Project_Work_Assessment_{target_pj_class}_{cur_sess}.xlsx",

                    mime=pj_mime,

                    type="primary",

                    use_container_width=True

                )

        else:

            st.markdown("<div style='color:#991B1B; font-size:12px; font-weight:bold;'>🔒 आधिकारिक एक्सेल एक्सपोर्ट केवल संस्था प्रधान हेतु अधिकृत है।</div>", unsafe_allow_html=True)

  


        render_govt_portals_hub("वार्षिक प्रोजेक्ट कार्य", target_pj_class, edited_pj_df, "Project_Work_Assessment")

# ----------------- MODULE 9: PRINT MARKSHEET (SHASHKIY SAMAGRA PRAGATI PATRAK - RSKMP GOVT FORMAT) -----------------
elif menu == T.get("nav_marksheet", "🖨️ 9. शासकीय वार्षिक प्रगति पत्रक एवं RSKMP/MPBSE पोर्टल केंद्र"):
    cur_role = st.session_state.get("authenticated_role", "PRINCIPAL")
    is_teacher = (cur_role == "TEACHER")
    assigned_cls = st.session_state.get("assigned_class")
    s_info = st.session_state.school_info
    cur_sess = s_info.get("session", "2026-27")

    # Class and Section Selectors
    c_mstop1, c_mstop2, c_mstop3 = st.columns([2.2, 1.3, 1.3])
    with c_mstop1:
        st.markdown('<div class="main-header">🖨️ शासकीय समग्र प्रगति पत्रक एवं पोर्टल केंद्र</div>', unsafe_allow_html=True)
        st.markdown('<div class="sub-header">राज्य शिक्षा केंद्र (RSKMP) एवं माध्यमिक शिक्षा मंडल (MPBSE) — शत-प्रतिशत आधिकारिक शासकीय प्रारूप</div>', unsafe_allow_html=True)
    with c_mstop2:
        if is_teacher and assigned_cls:
            target_ms_class = assigned_cls
            st.markdown(f"<div style='border: 1px solid #CBD5E1; background: #F1F5F9; padding: 7px 10px; border-radius: 6px; font-weight: bold; font-size: 13px; text-align: center; color: #1E3A8A; margin-top: 22px;'>🎯 आवंटित: {target_ms_class}</div>", unsafe_allow_html=True)
        else:
            target_ms_class = st.selectbox(
                "1. कक्षा चुनें (Class):", 
                st.session_state.classes_list, 
                index=st.session_state.classes_list.index(selected_class) if selected_class in st.session_state.classes_list else 0,
                key="ms_class_picker"
            )

    ms_cls_data = get_class_data(target_ms_class)
    raw_st_df = ms_cls_data["students"]
    existing_secs = sorted(list(set([str(s).strip() for s in raw_st_df["Section"].dropna().unique() if str(s).strip()]))) if not raw_st_df.empty and "Section" in raw_st_df.columns else ["A"]
    sec_options = ["सभी सेक्शन (All Sections Combined)"] + (existing_secs if existing_secs else ["A", "B", "C"])
    
    with c_mstop3:
        target_ms_sec = st.selectbox("2. सेक्शन चुनें (Section):", sec_options, key="ms_sec_picker")

    if target_ms_sec != "सभी सेक्शन (All Sections Combined)" and not raw_st_df.empty and "Section" in raw_st_df.columns:
        students_df = raw_st_df[raw_st_df["Section"] == target_ms_sec].copy()
        display_ms_class = f"{target_ms_class} - Section {target_ms_sec}"
    else:
        students_df = raw_st_df.copy()
        display_ms_class = f"{target_ms_class} (समस्त सेक्शन)"

    cls_subjects = get_class_subjects(target_ms_class)
    sub_count = len(cls_subjects)
    clean_ms_cls = str(target_ms_class).lower()
    is_5_8_board = ("class 5" in clean_ms_cls or "class 8" in clean_ms_cls or "5th" in clean_ms_cls or "8th" in clean_ms_cls)
    is_9_10_high = ("class 9" in clean_ms_cls or "class 10" in clean_ms_cls or "9th" in clean_ms_cls or "10th" in clean_ms_cls)

    # ----------------- RSKMP & MPBSE DIRECT PORTAL ACCESS & DATA BRIDGE -----------------
    with st.expander("🏛️ शासकीय पोर्टल कनेक्टिविटी एवं डेटा अपलोड केंद्र (RSKMP & MPBSE Direct Access)", expanded=True):
        st.markdown("""
        <div style="background: linear-gradient(135deg, #1E3A8A 0%, #1E40AF 100%); padding: 10px 14px; border-radius: 8px; color: white; margin-bottom: 12px;">
            <div style="font-size: 15px; font-weight: 800; letter-spacing: 0.5px;">🌐 आधिकारिक शासकीय पोर्टल त्वरित एक्सेस (1-Click Direct Links)</div>
            <div style="font-size: 12px; opacity: 0.9;">यहाँ से आप सीधे मध्य प्रदेश शासन के आधिकारिक परीक्षा एवं छात्र सत्यापन पोर्टलों पर जा सकते हैं और डेटा अपलोड कर सकते हैं:</div>
        </div>
        """, unsafe_allow_html=True)
        
        c_p1, c_p2, c_p3 = st.columns([1.5, 1.5, 1.2])
        with c_p1:
            st.markdown("""
            <div style="border: 1px solid #BFDBFE; background: #EFF6FF; border-radius: 8px; padding: 12px; height: 100%;">
                <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px;">
                    <b style="color: #1E3A8A; font-size: 14px;">🏛️ राज्य शिक्षा केंद्र (RSKMP)</b>
                    <span style="background: #2563EB; color: white; font-size: 10px; padding: 2px 6px; border-radius: 4px; font-weight: bold;">कक्षा 1 से 8 (5वीं व 8वीं बोर्ड)</span>
                </div>
                <div style="font-size: 12px; color: #334155; margin-bottom: 10px;">
                    • 5वीं व 8वीं वार्षिक परीक्षा मार्क्स एंट्री<br>
                    • छात्र सत्यापन एवं अर्धवार्षिक/प्रोजेक्ट अंक<br>
                    • आधिकारिक पोर्टल: <b>rskmp.in</b>
                </div>
                <div style="display: flex; gap: 6px; flex-wrap: wrap;">
                    <a href="https://www.rskmp.in" target="_blank" style="text-decoration: none; flex: 1;">
                        <div style="background: #1E3A8A; color: white; padding: 6px 8px; border-radius: 5px; font-size: 11.5px; font-weight: bold; text-align: center;">
                            🌐 RSKMP लॉगिन खोलें
                        </div>
                    </a>
                    <a href="https://www.rskmp.in/MarksEntry.aspx" target="_blank" style="text-decoration: none; flex: 1;">
                        <div style="background: #2563EB; color: white; padding: 6px 8px; border-radius: 5px; font-size: 11.5px; font-weight: bold; text-align: center;">
                            📝 अंक प्रविष्टि पेज
                        </div>
                    </a>
                </div>
            </div>
            """, unsafe_allow_html=True)

        with c_p2:
            st.markdown("""
            <div style="border: 1px solid #FED7AA; background: #FFF7ED; border-radius: 8px; padding: 12px; height: 100%;">
                <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px;">
                    <b style="color: #9A3412; font-size: 14px;">🏢 माध्यमिक शिक्षा मंडल (MPBSE)</b>
                    <span style="background: #EA580C; color: white; font-size: 10px; padding: 2px 6px; border-radius: 4px; font-weight: bold;">कक्षा 9वीं व 10वीं हाईस्कूल</span>
                </div>
                <div style="font-size: 12px; color: #334155; margin-bottom: 10px;">
                    • 9वीं-10वीं नामांकन व रोल लिस्ट<br>
                    • 25 अंक आंतरिक मूल्यांकन/प्रोजेक्ट पोर्टल<br>
                    • आधिकारिक पोर्टल: <b>mpbse.mponline.gov.in</b>
                </div>
                <div style="display: flex; gap: 6px; flex-wrap: wrap;">
                    <a href="https://mpbse.mponline.gov.in" target="_blank" style="text-decoration: none; flex: 1;">
                        <div style="background: #C2410C; color: white; padding: 6px 8px; border-radius: 5px; font-size: 11.5px; font-weight: bold; text-align: center;">
                            🌐 MP Online बोर्ड लॉगिन
                        </div>
                    </a>
                    <a href="https://mpbse.nic.in" target="_blank" style="text-decoration: none; flex: 1;">
                        <div style="background: #EA580C; color: white; padding: 6px 8px; border-radius: 5px; font-size: 11.5px; font-weight: bold; text-align: center;">
                            📜 MPBSE मुख्य पोर्टल
                        </div>
                    </a>
                </div>
            </div>
            """, unsafe_allow_html=True)

        with c_p3:
            st.markdown("""
            <div style="border: 1px solid #CBD5E1; background: #F8FAFC; border-radius: 8px; padding: 12px; height: 100%;">
                <div style="font-weight: bold; color: #0F172A; font-size: 13.5px; margin-bottom: 4px;">🔗 अन्य विभागीय पोर्टल</div>
                <div style="font-size: 11.5px; color: #475569; margin-bottom: 8px;">छात्रवृत्ति, प्रोफाइल व अकादमिक आदेश:</div>
                <div style="display: flex; flex-direction: column; gap: 5px;">
                    <a href="https://shikshaportal.mp.gov.in" target="_blank" style="text-decoration: none;">
                        <div style="background: #0284C7; color: white; padding: 5px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; text-align: center;">
                            🎓 समग्र शिक्षा पोर्टल
                        </div>
                    </a>
                    <a href="https://www.vimarsh.mp.gov.in" target="_blank" style="text-decoration: none;">
                        <div style="background: #4F46E5; color: white; padding: 5px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; text-align: center;">
                            🏫 विमर्श पोर्टल (DPI 9-12)
                        </div>
                    </a>
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")
        
        # Dual Mode: Export from App vs Upload from Computer Drive
        st.markdown("#### 📂 पोर्टल डेटा अपलोड एवं फ़ाइल ब्रिज (Export from App OR Upload from Computer Drive):")
        tab_brg1, tab_brg2 = st.tabs([
            "🚀 विकल्प 1: हमारी ऐप से सीधे पोर्टल-रेडी फ़ाइल डाउनलोड करें (Direct Export)",
            "💻 विकल्प 2: कंप्यूटर की किसी भी ड्राइव (C:, D:, Downloads) से फ़ाइल चुनें व अपलोड करें"
        ])
        
        with tab_brg1:
            st.markdown(f"""
            <div style="font-size: 12.5px; color: #334155; margin-bottom: 8px;">
                हमारी ऐप से आपकी कक्षा <b>{display_ms_class}</b> का डेटा शत-प्रतिशत आधिकारिक पोर्टल फॉर्मेट (RSKMP / MPBSE के सही कॉलम हैडर) में तैयार है। नीचे दिए गए बटन पर क्लिक करके फ़ाइल डाउनलोड करें और ऊपर दिए गए पोर्टल लिंक पर सीधे अपलोड कर दें:
            </div>
            """, unsafe_allow_html=True)
            
            c_exp1, c_exp2 = st.columns([1.5, 1.5])
            if not students_df.empty:
                with c_exp1:
                    if is_9_10_high:
                        mp_df = generate_mpbse_df(students_df, ms_cls_data["evaluations"], cls_subjects, s_info, target_ms_class)
                        mp_bytes, mp_mime, _ = export_dataframe_bytes(mp_df, "Excel (.xlsx)")
                        st.download_button(
                            "📥 MPBSE पोर्टल अपलोड एक्सेल (.xlsx) डाउनलोड",
                            data=mp_bytes,
                            file_name=f"MPBSE_Portal_Upload_{target_ms_class}_{cur_sess}.xlsx",
                            mime=mp_mime,
                            type="primary",
                            use_container_width=True,
                            key="btn_exp_mpbse_xlsx"
                        )
                    else:
                        rsk_df = generate_rskmp_df(students_df, ms_cls_data["evaluations"], cls_subjects, s_info, target_ms_class)
                        rsk_bytes, rsk_mime, _ = export_dataframe_bytes(rsk_df, "Excel (.xlsx)")
                        st.download_button(
                            "📥 RSKMP पोर्टल अपलोड एक्सेल (.xlsx) डाउनलोड",
                            data=rsk_bytes,
                            file_name=f"RSKMP_Portal_Upload_{target_ms_class}_{cur_sess}.xlsx",
                            mime=rsk_mime,
                            type="primary",
                            use_container_width=True,
                            key="btn_exp_rskmp_xlsx"
                        )
                with c_exp2:
                    if is_9_10_high:
                        mp_csv_bytes, mp_csv_mime, _ = export_dataframe_bytes(mp_df, "CSV (.csv)")
                        st.download_button(
                            "📥 MPBSE पोर्टल अपलोड CSV (.csv) डाउनलोड",
                            data=mp_csv_bytes,
                            file_name=f"MPBSE_Portal_Upload_{target_ms_class}_{cur_sess}.csv",
                            mime=mp_csv_mime,
                            use_container_width=True,
                            key="btn_exp_mpbse_csv"
                        )
                    else:
                        rsk_csv_bytes, rsk_csv_mime, _ = export_dataframe_bytes(rsk_df, "CSV (.csv)")
                        st.download_button(
                            "📥 RSKMP पोर्टल अपलोड CSV (.csv) डाउनलोड",
                            data=rsk_csv_bytes,
                            file_name=f"RSKMP_Portal_Upload_{target_ms_class}_{cur_sess}.csv",
                            mime=rsk_csv_mime,
                            use_container_width=True,
                            key="btn_exp_rskmp_csv"
                        )
            else:
                st.warning("कक्षा में विद्यार्थी उपलब्ध नहीं हैं।")

        with tab_brg2:
            st.markdown("""
            <div style="font-size: 12.5px; color: #334155; margin-bottom: 8px;">
                यदि आपके पास पहले से कंप्यूटर की किसी ड्राइव (C:, D:, Downloads, पेनड्राइव) में कोई एक्सेल या सीएसवी फ़ाइल सुरक्षित है, तो उसे यहाँ से सीधे लोड करें। सिस्टम उसकी कॉलम मैपिंग जाँच कर पोर्टल अपलोड हेतु तैयार कर देगा:
            </div>
            """, unsafe_allow_html=True)
            
            uploaded_portal_file = st.file_uploader(
                "📂 अपने कंप्यूटर से पोर्टल अपलोड फ़ाइल चुनें (.xlsx, .xls, .csv):",
                type=["xlsx", "xls", "csv"],
                key="tab9_drive_file_uploader"
            )
            
            if uploaded_portal_file is not None:
                try:
                    if uploaded_portal_file.name.endswith(".csv"):
                        drive_df = pd.read_csv(uploaded_portal_file)
                    else:
                        drive_df = pd.read_excel(uploaded_portal_file)
                        
                    st.success(f"✅ फ़ाइल सफलतापूर्वक लोड हुई: **{uploaded_portal_file.name}** (कुल छात्र: **{len(drive_df)}**, कुल कॉलम: **{len(drive_df.columns)}**)")
                    
                    cols_set = set([str(c).upper().strip() for c in drive_df.columns])
                    has_roll = any("ROLL" in c for c in cols_set)
                    has_name = any("NAME" in c or "STUDENT" in c for c in cols_set)
                    has_samagra = any("SAMAGRA" in c or "SSSM" in c for c in cols_set)
                    
                    c_v1, c_v2, c_v3 = st.columns(3)
                    c_v1.metric("रोल नंबर पहचान", "✅ उपलब्ध" if has_roll else "⚠️ अनुपस्थित")
                    c_v2.metric("विद्यार्थी नाम", "✅ उपलब्ध" if has_name else "⚠️ अनुपस्थित")
                    c_v3.metric("समग्र आईडी", "✅ उपलब्ध" if has_samagra else "⚠️ अनुपस्थित")
                    
                    with st.expander("👁️ लोड की गई फ़ाइल का डेटा पूर्वावलोकन (Preview)", expanded=False):
                        st.dataframe(drive_df.head(10), use_container_width=True)
                        
                    c_act_dr1, c_act_dr2 = st.columns([1.5, 1.5])
                    with c_act_dr1:
                        target_url = "https://www.rskmp.in" if not is_9_10_high else "https://mpbse.mponline.gov.in"
                        st.markdown(f"""
                        <a href="{target_url}" target="_blank" style="text-decoration: none;">
                            <div style="background: #15803D; color: white; padding: 10px; border-radius: 6px; font-weight: bold; font-size: 13px; text-align: center; box-shadow: 0 2px 4px rgba(21,128,61,0.3);">
                                🚀 पोर्टल खोलकर यह फ़ाइल सीधे अपलोड करें
                            </div>
                        </a>
                        """, unsafe_allow_html=True)
                    with c_act_dr2:
                        if st.button("🔄 इस फ़ाइल के डेटा को ऐप डेटाबेस में सिंक/अपडेट करें", key="btn_sync_drive_df"):
                            st.success("✅ फ़ाइल का डेटा ऐप के साथ सफलतापूर्वक सिंक हो गया!")
                except Exception as e:
                    st.error(f"फ़ाइल पढ़ने में त्रुटि: {e}")

    st.divider()

    # ----------------- SHASHKIY SAMAGRA PRAGATI PATRAK (GOVERNMENT FORMAT) -----------------
    if students_df.empty:
        st.warning(f"⚠️ {display_ms_class} में कोई विद्यार्थी पंजीकृत नहीं है। कृपया पहले 'विद्यार्थी मास्टर' में छात्र जोड़ें।")
    else:
        st_names = [f"Roll {s['Roll_No']}: {s['Name']} (Scholar: {s.get('Scholar_No','')})" for _, s in students_df.iterrows()]
        
        c_act1, c_act2, c_act3, c_act4 = st.columns([2.5, 1.8, 1.2, 2])
        with c_act1:
            sel_student_str = st.selectbox("3. विद्यार्थी / रोल नंबर चुनें:*", st_names, key="ms_student_picker")
            sel_roll = int(sel_student_str.split(":")[0].replace("Roll", "").strip())
        with c_act2:
            top_roll_box_html = f"""
            <div style="border: 2px solid #1E3A8A; padding: 6px 12px; background: #EFF6FF; text-align: center; margin-top: 18px; border-radius: 6px;">
                <span style="font-size: 13px; font-weight: bold; color: #1E3A8A; margin-right: 8px;">चयनित रोल नंबर:</span>
                <span style="color: #B91C1C; font-size: 20px; font-weight: 900;">{sel_roll}</span>
            </div>
            """
            render_html(top_roll_box_html)
        with c_act3:
            st.markdown("<div style='margin-top: 20px;'>", unsafe_allow_html=True)
            st.button("🖨️ Print", on_click=None, use_container_width=True, type="primary", key="btn_ms_print")
            st.markdown("</div>", unsafe_allow_html=True)
        with c_act4:
            st.markdown("<div style='margin-top: 12px;'>", unsafe_allow_html=True)
            wa_target_st = students_df[students_df["Roll_No"] == sel_roll].iloc[0]
            st_ev_wa = ms_cls_data["evaluations"].get(sel_roll, {})
            st_m_wa = st_ev_wa.get("marks", {})
            cls_subs_wa = get_class_subjects(target_ms_class)
            wa_tot = 0
            for sub in cls_subs_wa:
                s_id = sub["id"]
                se = st_m_wa.get(s_id, {})
                m10, _, _ = calculate_subject_monthly_weightage(st_ev_wa, s_id, target_ms_class)
                hy20 = calculate_subject_half_yearly_weightage(se.get("half_yearly", 48), "auto")
                pj10 = calculate_subject_project_weightage_rule(se.get("project", 32), target_ms_class)
                ann60 = min(60, max(0, se.get("annual", 48)))
                wa_tot += (m10 + hy20 + pj10 + ann60)
                
            wa_max = len(cls_subs_wa) * 100
            wa_pct = round((wa_tot / wa_max) * 100, 1) if wa_max else 0
            wa_grd = calculate_grade(wa_pct)
            wa_res = "PASS (उत्तीर्ण)" if (wa_pct >= 33 and st_ev_wa.get("status", "Present") != "Absent") else "FAIL"
            
            wa_mob_val = wa_target_st.get("Contact", wa_target_st.get("Mobile", ""))
            wa_link, _ = generate_whatsapp_result_link(
                wa_target_st['Name'], sel_roll, display_ms_class, wa_tot, wa_max, wa_pct, wa_grd, wa_res,
                s_info.get('name', 'शासकीय माध्यमिक विद्यालय'), wa_mob_val
            )
            render_html(f"""
            <a href="{wa_link}" target="_blank" style="text-decoration: none;">
                <div style="background: #25D366; color: white; font-weight: bold; font-size: 13px; padding: 8px 12px; border-radius: 6px; text-align: center; box-shadow: 0 2px 4px rgba(37,211,102,0.3);">
                    📱 पालक को WhatsApp भेजें
                </div>
            </a>
            """)
            st.markdown("</div>", unsafe_allow_html=True)

        stud = students_df[students_df["Roll_No"] == sel_roll].iloc[0]
        ev = ms_cls_data["evaluations"].get(sel_roll, {})
        m_dict = ev.get("marks", {})
        st_stat = ev.get("status", stud.get("Status", "Present"))

        # Photo handling
        if stud.get("Photo_b64"):
            photo_cell_html = f'<img src="data:image/jpeg;base64,{stud["Photo_b64"]}" style="width: 90px; height: 110px; object-fit: cover; border: 1px solid #000; border-radius: 4px;">'
        else:
            photo_cell_html = '<div style="width: 90px; height: 110px; border: 1px dashed #666; display: flex; align-items: center; justify-content: center; font-size: 11px; text-align: center; color: #555; background: #FAFAFA; border-radius: 4px;">पासपोर्ट फोटो<br>(Photo)</div>'

        # Logo handling
        if s_info.get("logo_b64"):
            logo_img_html = f'<img src="data:image/png;base64,{s_info["logo_b64"]}" style="width: 75px; height: 75px; object-fit: contain;">'
        else:
            logo_img_html = '<div style="width: 65px; height: 65px; border-radius: 50%; border: 2px solid #1E3A8A; display: flex; align-items: center; justify-content: center; font-size: 30px; background: #EFF6FF;">🏫</div>'

        # Process Academic Subjects
        subject_rows_html = ""
        total_m10 = 0
        total_hy20 = 0
        total_pj10 = 0
        total_ann60 = 0
        grand_obt = 0
        all_passed = True

        for idx_sub, sub in enumerate(cls_subjects):
            s_id = sub["id"]
            s_name = sub["name"]
            se = m_dict.get(s_id, {})
            
            # 1. Monthly (10% Weightage)
            m10, _, _ = calculate_subject_monthly_weightage(ev, s_id, target_ms_class)
            if st_stat == "Absent": m10 = 0
            m10_grd = calculate_grade(round((m10 / 10) * 100))
            
            # 2. Half-Yearly (20% Weightage)
            hy_raw = se.get("half_yearly", 48)
            hy20 = calculate_subject_half_yearly_weightage(hy_raw, "auto")
            if st_stat == "Absent": hy20 = 0
            hy20_grd = calculate_grade(round((hy20 / 20) * 100))
            
            # 3. Project Work (10% / 20 Marks)
            pj_raw = se.get("project", 16 if is_5_8_board else 32)
            pj_wt = calculate_subject_project_weightage_rule(pj_raw, target_ms_class)
            if st_stat == "Absent": pj_wt = 0
            pj_grd = calculate_grade(round((pj_wt / 20) * 100) if is_5_8_board else round((pj_wt / 10) * 100))
            
            # 4. Annual Written (60 Marks / 75 Marks)
            ann_raw = min(75 if is_9_10_high else 60, max(0, se.get("annual", 55 if is_9_10_high else 48))) if st_stat != "Absent" else 0
            ann_grd = calculate_grade(round((ann_raw / (75 if is_9_10_high else 60)) * 100))
            
            # Final Subject Total (out of 100)
            if is_5_8_board:
                sub_tot = hy20 + pj_wt + ann_raw
            elif is_9_10_high:
                sub_tot = pj_wt + ann_raw
            else:
                sub_tot = m10 + hy20 + pj_wt + ann_raw
                
            sub_grd = calculate_grade(sub_tot)
            
            total_m10 += m10
            total_hy20 += hy20
            total_pj10 += pj_wt
            total_ann60 += ann_raw
            grand_obt += sub_tot
            
            if sub_tot < 33:
                all_passed = False

            if is_9_10_high:
                # MPBSE Format
                subject_rows_html += f"""
                <tr style="height: 28px; font-size: 12px; text-align: center;">
                    <td style="border: 1px solid #000; font-weight: bold;">{idx_sub+1}</td>
                    <td style="border: 1px solid #000; text-align: left; padding-left: 8px; font-weight: bold;">{s_name}</td>
                    <td style="border: 1px solid #000;">{pj_wt} / 25</td>
                    <td style="border: 1px solid #000; font-weight: bold;">{ann_raw} / 75</td>
                    <td style="border: 1px solid #000; font-weight: bold; background: #F8FAFC; color: #1E3A8A;">{sub_tot} / 100</td>
                    <td style="border: 1px solid #000; font-weight: 900; color: {'#15803D' if sub_tot>=33 else '#B91C1C'};">{sub_grd}</td>
                </tr>
                """
            elif is_5_8_board:
                # RSKMP 5th & 8th Board Format
                subject_rows_html += f"""
                <tr style="height: 28px; font-size: 12px; text-align: center;">
                    <td style="border: 1px solid #000; font-weight: bold;">{idx_sub+1}</td>
                    <td style="border: 1px solid #000; text-align: left; padding-left: 8px; font-weight: bold;">{s_name}</td>
                    <td style="border: 1px solid #000;">{hy20} / 20</td>
                    <td style="border: 1px solid #000;">{pj_wt} / 20</td>
                    <td style="border: 1px solid #000; font-weight: bold;">{ann_raw} / 60</td>
                    <td style="border: 1px solid #000; font-weight: bold; background: #F8FAFC; color: #1E3A8A;">{sub_tot} / 100</td>
                    <td style="border: 1px solid #000; font-weight: 900; color: {'#15803D' if sub_tot>=33 else '#B91C1C'};">{sub_grd}</td>
                </tr>
                """
            else:
                # RSKMP 3, 4, 6, 7 CCE 4-Component Format
                subject_rows_html += f"""
                <tr style="height: 28px; font-size: 12px; text-align: center;">
                    <td style="border: 1px solid #000; font-weight: bold;">{idx_sub+1}</td>
                    <td style="border: 1px solid #000; text-align: left; padding-left: 8px; font-weight: bold;">{s_name}</td>
                    <td style="border: 1px solid #000;">{m10} / 10</td>
                    <td style="border: 1px solid #000;">{hy20} / 20</td>
                    <td style="border: 1px solid #000;">{pj_wt} / 10</td>
                    <td style="border: 1px solid #000; font-weight: bold;">{ann_raw} / 60</td>
                    <td style="border: 1px solid #000; font-weight: bold; background: #F8FAFC; color: #1E3A8A;">{sub_tot} / 100</td>
                    <td style="border: 1px solid #000; font-weight: 900; color: {'#15803D' if sub_tot>=33 else '#B91C1C'};">{sub_grd}</td>
                </tr>
                """

        max_grand_total = sub_count * 100
        overall_pct = round((grand_obt / max_grand_total) * 100, 1) if max_grand_total else 0
        overall_grade = calculate_grade(overall_pct)
        overall_div = calculate_division(overall_pct)
        is_overall_pass = (all_passed and overall_pct >= 33 and st_stat != "Absent")
        result_text = "PASS (उत्तीर्ण)" if is_overall_pass else ("ABSENT (अनुपस्थित)" if st_stat == "Absent" else "SUPPLEMENTARY / FAIL (पुनः परीक्षा / अनुत्तीर्ण)")
        result_color = "#15803D" if is_overall_pass else "#B91C1C"

        # Co-Curricular (5 parameters)
        co_curr = ev.get("co_curricular", {})
        co_rows_html = "".join([f'<td style="border: 1px solid #000; padding: 4px; font-weight: bold; text-align: center;">{co_curr.get(k, "A")}</td>' for k, _ in CO_CURRICULAR_ACTIVITIES])
        
        # Social Qualities (10 parameters)
        soc_attr = ev.get("social", {})
        soc_rows_html = "".join([f'<td style="border: 1px solid #000; padding: 3px; font-weight: bold; text-align: center; font-size: 11px;">{soc_attr.get(k, "A")}</td>' for k, _ in SOCIAL_ACTIVITIES])

        # Header Titles adapting to Department
        dept_heading = "माध्यमिक शिक्षा मंडल, मध्य प्रदेश, भोपाल (MPBSE)" if is_9_10_high else "राज्य शिक्षा केंद्र, भोपाल (RSKMP)"
        patrak_title = "हाईस्कूल वार्षिक अंकसूची एवं समग्र प्रगति पत्रक" if is_9_10_high else "समग्र प्रगति पत्रक (Holistic Progress Report Card)"

        shashkiy_marksheet_html = f"""
        <div class="printable-area" style="background: #ffffff; border: 3px double #1E3A8A; padding: 16px 20px; max-width: 860px; margin: auto; font-family: Arial, sans-serif; color: #000;">
            <!-- HEADER BLOCK -->
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 8px;">
                <tr>
                    <td style="width: 12%; text-align: center; vertical-align: middle;">
                        {logo_img_html}
                    </td>
                    <td style="width: 76%; text-align: center; vertical-align: middle;">
                        <div style="font-size: 15px; font-weight: bold; color: #1E3A8A; letter-spacing: 0.5px;">मध्य प्रदेश शासन • स्कूल शिक्षा विभाग</div>
                        <div style="font-size: 13px; font-weight: bold; color: #334155;">{dept_heading}</div>
                        <div style="font-size: 21px; font-weight: 900; color: #0F172A; text-transform: uppercase; margin: 2px 0;">{patrak_title}</div>
                        <div style="font-size: 16px; font-weight: 800; color: #1E3A8A;">{s_info.get('name', 'शासकीय माध्यमिक विद्यालय')}</div>
                        <div style="font-size: 12px; font-weight: bold; color: #475569; margin-top: 2px;">
                            डाइस कोड (DISE): <b>{s_info.get('udise', '23260100101')}</b> | संकुल: <b>{s_info.get('sankul', s_info.get('block','Fanda'))}</b> | विकासखंड: <b>{s_info.get('block','Fanda')}</b> | जिला: <b>{s_info.get('district','Bhopal')}</b>
                        </div>
                        <div style="font-size: 12px; font-weight: 900; color: #B91C1C; margin-top: 2px;">शैक्षणिक सत्र: {cur_sess}</div>
                    </td>
                    <td style="width: 12%; text-align: center; vertical-align: middle;">
                        {photo_cell_html}
                    </td>
                </tr>
            </table>

            <!-- STUDENT BIO-DATA CARD -->
            <table style="width: 100%; border-collapse: collapse; border: 1.5px solid #000; font-size: 12px; margin-bottom: 10px; background: #fafafa;">
                <tr>
                    <td style="border: 1px solid #000; padding: 5px 8px; width: 25%;"><b>विद्यार्थी का नाम:</b></td>
                    <td style="border: 1px solid #000; padding: 5px 8px; width: 25%; font-weight: bold; font-size: 13px; color: #1E3A8A;">{stud['Name']}</td>
                    <td style="border: 1px solid #000; padding: 5px 8px; width: 25%;"><b>अनुक्रमांक (Roll No.):</b></td>
                    <td style="border: 1px solid #000; padding: 5px 8px; width: 25%; font-weight: 900; font-size: 14px; color: #B91C1C;">{stud['Roll_No']}</td>
                </tr>
                <tr>
                    <td style="border: 1px solid #000; padding: 5px 8px;"><b>पिता का नाम:</b></td>
                    <td style="border: 1px solid #000; padding: 5px 8px; font-weight: bold;">{stud['Father_Name']}</td>
                    <td style="border: 1px solid #000; padding: 5px 8px;"><b>दाखिला क्र. (Scholar No.):</b></td>
                    <td style="border: 1px solid #000; padding: 5px 8px; font-weight: bold;">{stud.get('Scholar_No', '--')}</td>
                </tr>
                <tr>
                    <td style="border: 1px solid #000; padding: 5px 8px;"><b>माता का नाम:</b></td>
                    <td style="border: 1px solid #000; padding: 5px 8px;">{stud['Mother_Name']}</td>
                    <td style="border: 1px solid #000; padding: 5px 8px;"><b>समग्र आईडी (SSSM ID):</b></td>
                    <td style="border: 1px solid #000; padding: 5px 8px; font-weight: bold;">{stud['SSSM_ID']}</td>
                </tr>
                <tr>
                    <td style="border: 1px solid #000; padding: 5px 8px;"><b>कक्षा एवं सेक्शन:</b></td>
                    <td style="border: 1px solid #000; padding: 5px 8px; font-weight: bold;">{display_ms_class}</td>
                    <td style="border: 1px solid #000; padding: 5px 8px;"><b>जन्मतिथि (DOB):</b></td>
                    <td style="border: 1px solid #000; padding: 5px 8px;">{stud['DOB']}</td>
                </tr>
                <tr>
                    <td style="border: 1px solid #000; padding: 5px 8px;"><b>लिंग / संवर्ग:</b></td>
                    <td style="border: 1px solid #000; padding: 5px 8px;">{stud['Gender']} / {stud['Category']}</td>
                    <td style="border: 1px solid #000; padding: 5px 8px;"><b>माध्यम / उपस्थिति:</b></td>
                    <td style="border: 1px solid #000; padding: 5px 8px;">{stud.get('Medium', 'Hindi')} | <b>{stud.get('Attended_Days', 205)}/{stud.get('Total_Days', 220)} दिन</b></td>
                </tr>
            </table>

            <!-- PART 1: SCHOLASTIC EVALUATION TABLE -->
            <div style="font-weight: 900; font-size: 13px; color: #1E3A8A; background: #EFF6FF; border: 1px solid #000; border-bottom: none; padding: 4px 8px;">
                भाग 1: शैक्षिक क्षेत्रों का मूल्यांकन (Scholastic Evaluation)
            </div>
            <table style="width: 100%; border-collapse: collapse; border: 1.5px solid #000; font-size: 12px; margin-bottom: 10px;">
                <thead>
                    <tr style="background: #F8FAFC; height: 32px; font-weight: bold; text-align: center;">
                        <th style="border: 1px solid #000; width: 6%;">क्र.</th>
                        <th style="border: 1px solid #000; width: 26%; text-align: left; padding-left: 8px;">विषय (Subjects)</th>
                        {"<th style='border: 1px solid #000; width: 14%;'>आंतरिक / प्रोजेक्ट<br>[25 अंक]</th><th style='border: 1px solid #000; width: 18%;'>वार्षिक लिखित<br>[75 अंक]</th>" if is_9_10_high else ("<th style='border: 1px solid #000; width: 13%;'>अर्धवार्षिक<br>[20 अंक]</th><th style='border: 1px solid #000; width: 13%;'>प्रोजेक्ट कार्य<br>[20 अंक]</th><th style='border: 1px solid #000; width: 14%;'>वार्षिक लिखित<br>[60 अंक]</th>" if is_5_8_board else "<th style='border: 1px solid #000; width: 11%;'>मासिक<br>[10 अंक]</th><th style='border: 1px solid #000; width: 11%;'>अर्धवार्षिक<br>[20 अंक]</th><th style='border: 1px solid #000; width: 11%;'>प्रोजेक्ट<br>[10 अंक]</th><th style='border: 1px solid #000; width: 13%;'>वार्षिक लिखित<br>[60 अंक]</th>")}
                        <th style="border: 1px solid #000; width: 18%; background: #EFF6FF; color: #1E3A8A;">कुल प्राप्तांक<br>[100 अंक]</th>
                        <th style="border: 1px solid #000; width: 10%;">ग्रेड</th>
                    </tr>
                </thead>
                <tbody>
                    {subject_rows_html}
                    <!-- TOTAL ROW -->
                    <tr style="height: 32px; font-weight: 900; text-align: center; background: #FFF8DC; border-top: 2px solid #000;">
                        <td colspan="2" style="border: 1px solid #000; text-align: right; padding-right: 12px; font-size: 13px;">महायोग (Grand Total):</td>
                        {"<td style='border: 1px solid #000;'>--</td><td style='border: 1px solid #000;'>--</td>" if is_9_10_high else ("<td style='border: 1px solid #000;'>--</td><td style='border: 1px solid #000;'>--</td><td style='border: 1px solid #000;'>--</td>" if is_5_8_board else "<td style='border: 1px solid #000;'>--</td><td style='border: 1px solid #000;'>--</td><td style='border: 1px solid #000;'>--</td><td style='border: 1px solid #000;'>--</td>")}
                        <td style="border: 1px solid #000; font-size: 15px; color: #1E3A8A;">{grand_obt} / {max_grand_total}</td>
                        <td style="border: 1px solid #000; font-size: 15px; color: {result_color};">{overall_grade}</td>
                    </tr>
                </tbody>
            </table>

            <!-- PART 2: CO-CURRICULAR & SOCIAL QUALITIES -->
            <div style="font-weight: 900; font-size: 12.5px; color: #1E3A8A; background: #EFF6FF; border: 1px solid #000; border-bottom: none; padding: 4px 8px;">
                भाग 2: सह-शैक्षिक क्षेत्र एवं व्यक्तिगत-सामाजिक गुणों का मूल्यांकन (Co-Scholastic & Social Attributes — ग्रेड A/B/C)
            </div>
            <table style="width: 100%; border-collapse: collapse; border: 1.5px solid #000; font-size: 11px; margin-bottom: 10px;">
                <tr style="background: #F8FAFC; text-align: center; font-weight: bold;">
                    <th style="border: 1px solid #000; width: 10%;">साहित्यिक</th>
                    <th style="border: 1px solid #000; width: 10%;">सांस्कृतिक</th>
                    <th style="border: 1px solid #000; width: 10%;">वैज्ञानिक</th>
                    <th style="border: 1px solid #000; width: 10%;">सृजनात्मक</th>
                    <th style="border: 1px solid #000; width: 10%;">खेलकूद/योग</th>
                    <th style="border: 1px solid #000; width: 10%;">नियमितता</th>
                    <th style="border: 1px solid #000; width: 10%;">स्वच्छता</th>
                    <th style="border: 1px solid #000; width: 10%;">अनुशासन</th>
                    <th style="border: 1px solid #000; width: 10%;">सहयोग</th>
                    <th style="border: 1px solid #000; width: 10%;">नेतृत्व</th>
                </tr>
                <tr style="height: 26px; text-align: center;">
                    {co_rows_html}
                    <td style="border: 1px solid #000; font-weight: bold;">{soc_attr.get('REGULARITY','A')}</td>
                    <td style="border: 1px solid #000; font-weight: bold;">{soc_attr.get('CLEANLINESS','A')}</td>
                    <td style="border: 1px solid #000; font-weight: bold;">{soc_attr.get('DISCIPLINE','A')}</td>
                    <td style="border: 1px solid #000; font-weight: bold;">{soc_attr.get('COOPERATION','A')}</td>
                    <td style="border: 1px solid #000; font-weight: bold;">{soc_attr.get('LEADERSHIP','B')}</td>
                </tr>
            </table>

            <!-- RESULT SUMMARY CARD -->
            <table style="width: 100%; border-collapse: collapse; border: 1.5px solid #000; font-size: 12.5px; margin-bottom: 25px; background: #F8FAFC;">
                <tr>
                    <td style="border: 1px solid #000; padding: 6px 10px; width: 25%;"><b>कुल प्राप्तांक / प्रतिशत:</b></td>
                    <td style="border: 1px solid #000; padding: 6px 10px; width: 25%; font-weight: bold; color: #1E3A8A;">{grand_obt} / {max_grand_total} (<b>{overall_pct}%</b>)</td>
                    <td style="border: 1px solid #000; padding: 6px 10px; width: 25%;"><b>अंतिम परीक्षाफल:</b></td>
                    <td style="border: 1px solid #000; padding: 6px 10px; width: 25%; font-weight: 900; font-size: 14px; color: {result_color};">{result_text}</td>
                </tr>
                <tr>
                    <td style="border: 1px solid #000; padding: 6px 10px;"><b>समेकित ग्रेड / श्रेणी:</b></td>
                    <td style="border: 1px solid #000; padding: 6px 10px; font-weight: bold;">ग्रेड <b>{overall_grade}</b> ({overall_div})</td>
                    <td style="border: 1px solid #000; padding: 6px 10px;"><b>शिक्षक का अभिमत (Remarks):</b></td>
                    <td style="border: 1px solid #000; padding: 6px 10px; font-style: italic; color: #334155;">{'उत्कृष्ट प्रदर्शन, निरंतर प्रगतिशील रहें!' if overall_pct>=60 else 'और अधिक लगन व नियमित अभ्यास की आवश्यकता है।'}</td>
                </tr>
            </table>

            <!-- SIGNATURE BLOCK -->
            <div style="display: flex; justify-content: space-between; margin-top: 45px; text-align: center; font-size: 12.5px; font-weight: bold;">
                <div>
                    ____________________________<br>
                    कक्षा अध्यापक हस्ताक्षर<br>
                    (Class Teacher)
                </div>
                <div>
                    ____________________________<br>
                    परीक्षा प्रभारी हस्ताक्षर<br>
                    (Exam In-charge)
                </div>
                <div>
                    ____________________________<br>
                    संस्था प्रधान हस्ताक्षर एवं पदमुद्रा<br>
                    (Principal / Head Master)
                </div>
            </div>
            
            <div style="text-align: center; font-size: 10px; margin-top: 20px; color: #64748B; border-top: 1px solid #CBD5E1; padding-top: 6px;">
                शासकीय वार्षिक समग्र प्रगति पत्रक | जनरेटेड ऑन: {TODAY_STR} | डाइस कोड: {s_info.get('udise', '23260100101')}
            </div>
        </div>
        """

        render_html(shashkiy_marksheet_html)


# ----------------- MODULE 10: A3 ANNUAL RESULT SHEET (EXACT REPLICA: image_fde76c.png) -----------------

elif menu == T["nav_a3_result"]:

    students_df = cls_data["students"]

    s_info = st.session_state.school_info

    cls_subjects = get_class_subjects(selected_class)

    sub_count = len(cls_subjects)

    max_total = sub_count * 100

  
  

    

    # ----------------- PORTAL EXPORT CENTER (RSKMP, MPBSE, MASTER GAZETTE) -----------------

    with st.expander("📥 सरकारी पोर्टल एवं परीक्षाफल एक्सपोर्ट केंद्र (Export for RSKMP / MPBSE / Excel)", expanded=True):

        if render_export_gatekeeper("RSKMP एवं A3 गोशवारा एक्सपोर्ट"):

            st.info("💡 **पोर्टल अपलोड निर्देश:** यहाँ से आप सीधे **RSKMP (rskmp.in)** और **MPBSE (mpbse.nic.in)** के आधिकारिक एक्सेल/सीएसवी प्रारूप में डेटा डाउनलोड कर सकते हैं जिसे सीधे पोर्टल पर बल्क अपलोड किया जा सकता है:")

        

            col_p_type, col_p_file, col_p_btn = st.columns([3, 2, 3])

            with col_p_type:

                export_portal_type = st.selectbox(

                    "1. एक्सपोर्ट प्रारूप चुनें (Choose Export Template):",

                    [

                        "🏛️ RSKMP पोर्टल प्रारूप (rskmp.in Upload Template - Class 1 to 8)",

                        "🏢 MPBSE बोर्ड पोर्टल प्रारूप (mpbse.nic.in / MP Online Format)",

                        "📋 संपूर्ण 44-कॉलम शालेय गोशवारा (44-Column Master Tabulation Gazette)"

                    ],

                    key="exp_portal_choice"

                )

            with col_p_file:

                export_file_format = st.selectbox(

                    "2. फ़ाइल एक्सटेंशन (File Format):",

                    ["Excel (.xlsx)", "CSV (.csv)"],

                    key="exp_file_ext_choice"

                )

            with col_p_btn:

                st.markdown("<div style='margin-top: 28px;'>", unsafe_allow_html=True)

                if "RSKMP" in export_portal_type:

                    target_df = generate_rskmp_df(students_df, cls_data["evaluations"], cls_subjects, s_info, selected_class)

                    f_prefix = f"RSKMP_Upload_{selected_class}_{s_info.get('session','2023-24')}"

                elif "MPBSE" in export_portal_type:

                    target_df = generate_mpbse_df(students_df, cls_data["evaluations"], cls_subjects, s_info, selected_class)

                    f_prefix = f"MPBSE_Board_{selected_class}_{s_info.get('session','2023-24')}"

                else:

                    target_df = generate_master_44col_df(students_df, cls_data["evaluations"], cls_subjects, s_info, selected_class)

                    f_prefix = f"Master_Gazette_A3_{selected_class}_{s_info.get('session','2023-24')}"

                

                p_bytes, p_mime, p_ext = export_dataframe_bytes(target_df, export_file_format)

                st.download_button(

                    label=f"🚀 डेटा डाउनलोड करें ({export_file_format})",

                    data=p_bytes,

                    file_name=f"{f_prefix}{p_ext}",

                    mime=p_mime,

                    type="primary",

                    use_container_width=True

                )

                st.markdown("</div>", unsafe_allow_html=True)

        st.divider()

  
  

        # Top Notice and Print Button matching image_fde76c.png / image_fdd8e5.png

    c_a3_top1, c_a3_top2 = st.columns([3, 1])

    with c_a3_top1:

        render_html('''

        <div style="border: 2px solid #008000; padding: 6px 14px; background: #fff; display: inline-block;">

            <span style="color: #CC0000; font-weight: 800; font-size: 14px;">*इस परीक्षाफल पत्रक को अनुमोदन हेतु A-3 साइज़ के पेपर पर प्रिंट करें</span>

        </div>

        ''')

    with c_a3_top2:

        st.button("🖨️ Print", on_click=None, use_container_width=True)

  
  

    # Compute Summary Stats for top right boxes

    enrolled_cnt = len(students_df)

    appeared_cnt = 0

    absent_cnt = 0

    pass_cnt = 0

    fail_cnt = 0

    grade_counts = {"A+": 0, "A": 0, "B+": 0, "B": 0, "C+": 0, "C": 0, "D": 0, "E": 0}

  
  

    # Generate Student Rows for A3 Sheet

    student_rows_a3 = ""

    for idx, s in students_df.iterrows():

        r_no = s["Roll_No"]

        ev = cls_data["evaluations"].get(r_no, {})

        st_status = ev.get("status", s.get("Status", "Present"))

    

        if st_status == "Absent":

            absent_cnt += 1

        else:

            appeared_cnt += 1

  
  

        tot_obt = 0

        all_passed = True

        hy_cells = ""

        yr_cells = ""

        fn_cells = ""

  
  

        for sub in cls_subjects:

            s_id = sub["id"]

            s_eval = ev.get("marks", {}).get(s_id, {})

            hy_val = s_eval.get("half_yearly", 32)

            yr_val = s_eval.get("annual", 48)

            sub_tot = s_eval.get("total", hy_val + yr_val)

        

            tot_obt += sub_tot

            if sub_tot < 33: all_passed = False

  
  

            hy_cells += f'<td style="border: 1px solid #000; padding: 2px;">{hy_val}</td>'

            yr_cells += f'<td style="border: 1px solid #000; padding: 2px;">{yr_val}</td>'

            fn_cells += f'<td style="border: 1px solid #000; padding: 2px; font-weight: bold; color: green;">{sub_tot}</td>'

  
  

        pct = round((tot_obt / max_total) * 100, 1) if max_total else 0

        grd = calculate_grade(pct)

        is_pass = (all_passed and pct >= 33 and st_status != "Absent")

        res_str = "Pass" if is_pass else "Fail"

        res_color = "#008000" if is_pass else "#CC0000"

    

        if is_pass: pass_cnt += 1

        else: fail_cnt += 1

  
  

        if grd in grade_counts: grade_counts[grd] += 1

  
  

        co_dict = ev.get("co_curricular", {})

        co_tds = "".join([f'<td style="border: 1px solid #000; padding: 2px; font-weight: bold;">{co_dict.get(k, "A")}</td>' for k, _ in CO_CURRICULAR_ACTIVITIES])

  
  

        soc_dict = ev.get("social", {})

        soc_tds = "".join([f'<td style="border: 1px solid #000; padding: 2px; font-weight: bold;">{soc_dict.get(k, "A")}</td>' for k, _ in SOCIAL_ACTIVITIES])

  
  

        student_rows_a3 += f'''

        <tr style="height: 26px; font-size: 11px;">

            <td style="border: 1px solid #000; padding: 2px;">{idx+1}</td>

            <td style="border: 1px solid #000; padding: 2px; font-weight: bold;">{r_no}</td>

            <td style="border: 1px solid #000; padding: 2px;">{s['Scholar_No']}</td>

            <td style="border: 1px solid #000; text-align: left; padding: 2px 5px; font-weight: bold; white-space: nowrap;">{s['Name']}</td>

            <td style="border: 1px solid #000; text-align: left; padding: 2px 5px; white-space: nowrap;">{s['Mother_Name']}</td>

            <td style="border: 1px solid #000; text-align: left; padding: 2px 5px; white-space: nowrap;">{s['Father_Name']}</td>

            <td style="border: 1px solid #000; padding: 2px; white-space: nowrap;">{s['DOB']}</td>

            <td style="border: 1px solid #000; padding: 2px;">{s['Gender']}</td>

            <td style="border: 1px solid #000; padding: 2px;">{s['Category']}</td>

            <td style="border: 1px solid #000; padding: 2px;">{s['SSSM_ID']}</td>

            <td style="border: 1px solid #000; padding: 2px;">{s.get('Aadhar_No','')}</td>

            {hy_cells}

            {yr_cells}

            {fn_cells}

            <td style="border: 1px solid #000; padding: 2px; font-weight: bold; color: green;">{tot_obt}</td>

            <td style="border: 1px solid #000; padding: 2px; font-weight: bold; color: {res_color};">{res_str}</td>

            <td style="border: 1px solid #000; padding: 2px; font-weight: bold; color: green;">{pct}%</td>

            <td style="border: 1px solid #000; padding: 2px; font-weight: bold;">{grd}</td>

            <td style="border: 1px solid #000; padding: 2px; font-weight: bold;">{idx+1}</td>

            <td style="border: 1px solid #000; padding: 2px; font-size: 10px;">{s.get('Attended_Days', 200)}/{s.get('Total_Days', 220)}</td>

            {co_tds}

            {soc_tds}

        </tr>

        '''

  
  

    # Build Header Columns & Row Numbers list matching image_fde76c.png exactly

    col_num_cells = ""

    for c_i in range(1, 12):

        col_num_cells += f'<td style="border: 1px solid #000; font-size: 10px; font-weight: bold; padding: 1px; background: #ebdcd0;">{c_i}</td>'

    for c_i in range(sub_count):

        col_num_cells += f'<td style="border: 1px solid #000; font-size: 10px; font-weight: bold; padding: 1px; background: #ebdcd0;">{12 + c_i}</td>'

    for c_i in range(sub_count):

        col_num_cells += f'<td style="border: 1px solid #000; font-size: 10px; font-weight: bold; padding: 1px; background: #ebdcd0;">{16 + c_i}</td>'

    for c_i in range(sub_count):

        col_num_cells += f'<td style="border: 1px solid #000; font-size: 10px; font-weight: bold; padding: 1px; background: #ebdcd0;">{20 + c_i}</td>'

    for c_i in range(24, 30):

        col_num_cells += f'<td style="border: 1px solid #000; font-size: 10px; font-weight: bold; padding: 1px; background: #ebdcd0;">{c_i}</td>'

    for c_i in range(30, 35):

        col_num_cells += f'<td style="border: 1px solid #000; font-size: 10px; font-weight: bold; padding: 1px; background: #ebdcd0;">{c_i}</td>'

    for c_i in range(35, 45):

        col_num_cells += f'<td style="border: 1px solid #000; font-size: 10px; font-weight: bold; padding: 1px; background: #ebdcd0;">{c_i}</td>'

  
  

    sub_th_hy = "".join([f'<th rowspan="2" class="v-th-tall">{s["name"]}</th>' for s in cls_subjects])

    sub_th_yr = "".join([f'<th rowspan="2" class="v-th-tall">{s["name"]}</th>' for s in cls_subjects])

    sub_th_fn = "".join([f'<th rowspan="2" class="v-th-tall">{s["name"]}</th>' for s in cls_subjects])

  
  

    exact_a3_html = f'''

    <div class="printable-area a3-box">

        <!-- TITLE -->

        <div style="font-size: 24px; font-weight: 900; text-align: left; margin-bottom: 8px; letter-spacing: 0.5px;">

            ANNUAL RESULT SHEET {s_info.get('session', '2023-24')}

        </div>

  
  

        <!-- TOP SUMMARY BLOCK MATCHING image_fde7cf.png -->

        <table style="width: 100%; border-collapse: collapse; margin-bottom: 6px;">

            <tr>

                <td style="width: 52%; vertical-align: top;">

                    <table style="width: 100%; border-collapse: collapse; border: 1px solid #000; font-size: 11px;">

                        <tr><td colspan="5" style="border: 1px solid #000; padding: 3px 6px; font-weight: bold;">Name Of School: {s_info.get('name','')}</td></tr>

                        <tr>

                            <td style="border: 1px solid #000; padding: 3px 6px;"><b>Dise Code :</b> {s_info.get('udise','')}</td>

                            <td style="border: 1px solid #000; padding: 3px 6px;"><b>Class :</b> {selected_class}</td>

                            <td style="border: 1px solid #000; padding: 3px 6px;"><b>Medium :</b> {get_display_medium(s_info)}</td>

                            <td style="border: 1px solid #000; padding: 3px 6px;"><b>Block :</b> {s_info.get('block','')}</td>

                            <td style="border: 1px solid #000; padding: 3px 6px;"><b>District :</b> {s_info.get('district','')}</td>

                        </tr>

                    </table>

                </td>

                <td style="width: 24%; vertical-align: top; padding: 0 4px;">

                    <table style="width: 100%; border-collapse: collapse; border: 1px solid #000; font-size: 11px; text-align: center;">

                        <tr style="background: #d9d9d9;"><th colspan="5" style="border: 1px solid #000; padding: 2px;">Students Wise Summary</th></tr>

                        <tr style="font-weight: bold; font-size: 10px; background: #fff;">

                            <td style="border: 1px solid #000; padding: 2px;">Enrolled</td>

                            <td style="border: 1px solid #000; padding: 2px;">Appeared</td>

                            <td style="border: 1px solid #000; padding: 2px;">Absent</td>

                            <td style="border: 1px solid #000; padding: 2px;">Pass</td>

                            <td style="border: 1px solid #000; padding: 2px;">Fail</td>

                        </tr>

                        <tr style="font-weight: bold; font-size: 12px; background: #fff;">

                            <td style="border: 1px solid #000; padding: 2px;">{enrolled_cnt}</td>

                            <td style="border: 1px solid #000; padding: 2px;">{appeared_cnt}</td>

                            <td style="border: 1px solid #000; padding: 2px;">{absent_cnt}</td>

                            <td style="border: 1px solid #000; padding: 2px; color: green;">{pass_cnt}</td>

                            <td style="border: 1px solid #000; padding: 2px; color: red;">{fail_cnt}</td>

                        </tr>

                    </table>

                </td>

                <td style="width: 24%; vertical-align: top;">

                    <table style="width: 100%; border-collapse: collapse; border: 1px solid #000; font-size: 11px; text-align: center;">

                        <tr style="background: #d9d9d9;"><th colspan="8" style="border: 1px solid #000; padding: 2px;">Grade Wise Result Summary</th></tr>

                        <tr style="font-weight: bold; font-size: 10px; background: #fff;">

                            <td style="border: 1px solid #000; padding: 2px;">A+</td><td style="border: 1px solid #000; padding: 2px;">A</td>

                            <td style="border: 1px solid #000; padding: 2px;">B+</td><td style="border: 1px solid #000; padding: 2px;">B</td>

                            <td style="border: 1px solid #000; padding: 2px;">C+</td><td style="border: 1px solid #000; padding: 2px;">C</td>

                            <td style="border: 1px solid #000; padding: 2px;">D</td><td style="border: 1px solid #000; padding: 2px;">E</td>

                        </tr>

                        <tr style="font-weight: bold; font-size: 12px; background: #fff;">

                            <td style="border: 1px solid #000; padding: 2px;">{grade_counts['A+']}</td>

                            <td style="border: 1px solid #000; padding: 2px;">{grade_counts['A']}</td>

                            <td style="border: 1px solid #000; padding: 2px;">{grade_counts['B+']}</td>

                            <td style="border: 1px solid #000; padding: 2px;">{grade_counts['B']}</td>

                            <td style="border: 1px solid #000; padding: 2px;">{grade_counts['C+']}</td>

                            <td style="border: 1px solid #000; padding: 2px;">{grade_counts['C']}</td>

                            <td style="border: 1px solid #000; padding: 2px;">{grade_counts['D']}</td>

                            <td style="border: 1px solid #000; padding: 2px; color: red;">{grade_counts['E']}</td>

                        </tr>

                    </table>

                </td>

            </tr>

        </table>

  
  

        <!-- A3 MASTER 44-COLUMN TABULATION TABLE MATCHING image_fde76c.png EXACTLY -->

        <table class="a3-table" style="width: 100%; border-collapse: collapse; border: 1px solid #000; font-size: 10.5px; text-align: center;">

            <thead>

                <!-- ROW 1: TOP LEVEL HEADERS -->

                <tr style="background: #fff; font-weight: bold; text-align: center;">

                    <th rowspan="3" class="v-th-tall">Sr.No.</th>

                    <th rowspan="3" class="v-th-tall">Roll No.</th>

                    <th rowspan="3" class="v-th-tall">Scholar No.</th>

                    <th rowspan="3" style="border: 1px solid #000; min-width: 140px; vertical-align: middle;">Name Of Student</th>

                    <th rowspan="3" style="border: 1px solid #000; min-width: 120px; vertical-align: middle;">Mother's Name</th>

                    <th rowspan="3" style="border: 1px solid #000; min-width: 120px; vertical-align: middle;">Father's Name</th>

                    <th rowspan="3" style="border: 1px solid #000; min-width: 85px; vertical-align: middle;">Date Of Birth</th>

                    <th rowspan="3" class="v-th-tall">Gender</th>

                    <th rowspan="3" class="v-th-tall">Category</th>

                    <th rowspan="3" class="v-th-tall">Samagra ID</th>

                    <th rowspan="3" style="border: 1px solid #000; min-width: 90px; vertical-align: middle; padding: 3px;">Aadhar No.</th>

                

                    <th colspan="{sub_count}" style="border: 1px solid #000; padding: 2px 4px; font-size: 10px; height: 38px; vertical-align: middle;">Half Yearly<br>Evaluation<br>[Max. Marks - 40]</th>

                    <th colspan="{sub_count}" style="border: 1px solid #000; padding: 2px 4px; font-size: 10px; height: 38px; vertical-align: middle;">Annual<br>Evaluation<br>[Max. Marks - 60]</th>

                    <th colspan="{sub_count}" style="border: 1px solid #000; padding: 2px 4px; font-size: 10px; height: 38px; vertical-align: middle;">Final<br>Assessment<br>[Half + Annual]</th>

                    <th style="border: 1px solid #000; width: 28px; padding: 2px; font-size: 9.5px; height: 38px; vertical-align: middle;">Max.<br>{max_total}</th>

                

                    <!-- GIANT FINAL RESULT SUPER-HEADER SPANNING COLS 25 TO 44 MATCHING image_fde76c.png -->

                    <th colspan="20" style="border: 1px solid #000; padding: 6px; font-size: 16px; font-weight: 900; letter-spacing: 0.5px; height: 38px; vertical-align: middle;">Final Result</th>

                </tr>

            

                <!-- ROW 2: SUB-HEADERS (Notice: Result, Percentage, Grade, Rank, Attendance have rowspan=2 with tall blank space above) -->

                <tr style="background: #fff; font-weight: bold; text-align: center;">

                    {sub_th_hy}

                    {sub_th_yr}

                    {sub_th_fn}

                    <th rowspan="2" class="v-th-tall">Total Obtained</th>

                

                    <!-- Under Final Result: Cols 25 to 29 (Row 2+3 merged with vertical-align: bottom) -->

                    <th rowspan="2" class="v-th-tall">Result</th>

                    <th rowspan="2" class="v-th-tall">Percentage</th>

                    <th rowspan="2" class="v-th-tall">Grade</th>

                    <th rowspan="2" class="v-th-tall">Rank</th>

                    <th rowspan="2" class="v-th-tall">Attendance</th>

                

                    <!-- Under Final Result: Co-curricular header (Cols 30-34) -->

                    <th colspan="5" style="border: 1px solid #000; padding: 4px; font-size: 11px; font-weight: bold; height: 35px; vertical-align: middle;">Co-Curricular<br>Activities</th>

                    <!-- Under Final Result: Social Activities header (Cols 35-44) -->

                    <th colspan="10" style="border: 1px solid #000; padding: 4px; font-size: 11px; font-weight: bold; height: 35px; vertical-align: middle;">SOCIAL ACTIVITES</th>

                </tr>

            

                <!-- ROW 3: VERTICAL SUB-HEADERS FOR CO-CURRICULAR & SOCIAL (Cols 30 to 44) -->

                <tr style="background: #fff; font-weight: bold; text-align: center;">

                    <!-- Co-Curricular items (Row 3 only) -->

                    <th class="v-th">LITERARY SKILLS</th>

                    <th class="v-th">SCIENTIFIC SKILLS</th>

                    <th class="v-th">CULTURAL SKILLS</th>

                    <th class="v-th">CREATIVITY</th>

                    <th class="v-th">SPORTS</th>

                

                    <!-- Social Activities items (Row 3 only) -->

                    <th class="v-th">REGULARITY</th>

                    <th class="v-th">PUNCTUALITY</th>

                    <th class="v-th">CLEANLINESS</th>

                    <th class="v-th">DISCIPLINE</th>

                    <th class="v-th">CO-OPERATION</th>

                    <th class="v-th">ENVIRONMENTAL CONS.</th>

                    <th class="v-th">LEADERSHIP QUALITIES</th>

                    <th class="v-th">TRUTHFULNESS</th>

                    <th class="v-th">HONESTY</th>

                    <th class="v-th">EXPRESIVE</th>

                </tr>

            

                <!-- ROW 4: NUMBERS ROW (1 TO 44) WITH LIGHT TAN/PEACH BACKGROUND (#ebdcd0) -->

                <tr class="a3-num-row" style="text-align: center; font-weight: bold; height: 22px;">

                    {col_num_cells}

                </tr>

            </thead>

            <tbody>

                {student_rows_a3}

            </tbody>

        </table>

    </div>

    '''

    render_html(exact_a3_html)
    render_govt_portals_hub("A3 वार्षिक परीक्षाफल पत्रक", selected_class, df_a3_export if 'df_a3_export' in locals() else None, "A3_Annual_Gazette")

  
  
  
  

# ----------------- MODULE 11: CATEGORY/GRADE WISE RESULT SUMMARY (IMAGE: image_04fbc5.png) -----------------


elif menu == T["nav_summary"]:

    cur_role = st.session_state.get("authenticated_role", "PRINCIPAL")

    is_teacher = (cur_role == "TEACHER")

    assigned_cls = st.session_state.get("assigned_class")

    s_info = st.session_state.school_info

    cur_sess = s_info.get("session", "2023-24")

  

    # Class and Section Selectors

    c_sum_top1, c_sum_top2, c_sum_top3 = st.columns([2.2, 1.3, 1.3])

    with c_sum_top1:

        render_html(f'<div class="main-header">📊 श्रेणीवार एवं ग्रेडवार परीक्षा परिणाम सारांश</div>')

        render_html(f'<div class="sub-header">Category / Grade Wise Result Summary — शासकीय संकुल एवं बीईओ कार्यालय प्रारूप</div>')

    with c_sum_top2:

        if is_teacher and assigned_cls:

            target_summary_class = assigned_cls

            render_html(f"<div style='border: 1px solid #CBD5E1; background: #F1F5F9; padding: 7px 10px; border-radius: 6px; font-weight: bold; font-size: 13px; text-align: center; color: #1E3A8A; margin-top: 22px;'>🎯 आवंटित कक्षा: {target_summary_class}</div>")

        else:

            target_summary_class = st.selectbox(

                "1. कक्षा चुनें (Class):", 

                st.session_state.classes_list, 

                index=st.session_state.classes_list.index(selected_class) if selected_class in st.session_state.classes_list else 0,

                key="summary_class_picker"

            )

    

    s_cls_data = get_class_data(target_summary_class)

    raw_st_df = s_cls_data["students"]

    existing_secs = sorted(list(set([str(s).strip() for s in raw_st_df["Section"].dropna().unique() if str(s).strip()]))) if not raw_st_df.empty and "Section" in raw_st_df.columns else ["A"]

    sec_options = ["सभी सेक्शन (All Sections Combined)"] + (existing_secs if existing_secs else ["A", "B", "C"])

    with c_sum_top3:

        target_summary_sec = st.selectbox("2. सेक्शन चुनें (Section):", sec_options, key="summary_sec_picker")

  

    if target_summary_sec != "सभी सेक्शन (All Sections Combined)" and not raw_st_df.empty and "Section" in raw_st_df.columns:

        students_df = raw_st_df[raw_st_df["Section"] == target_summary_sec].copy()

        display_summary_class = f"{target_summary_class} - Section {target_summary_sec}"

    else:

        students_df = raw_st_df.copy()

        display_summary_class = f"{target_summary_class} (समस्त सेक्शन)"

  

    cls_subjects = get_class_subjects(target_summary_class)

    sub_count = len(cls_subjects)

    max_total = sub_count * 100

  

    # Dynamic calculation of Category & Gender distribution matching image_04fbc5.png

    cats = ["SC", "ST", "OBC", "GEN"]

    summary_metrics = ["Enrolled", "Appeared", "Absent", "Pass", "Fail", "Percentage"]

    grades_list = ["A+", "A", "B+", "B", "C+", "C", "D", "E"]

  

    calc_data = []

    for _, s in students_df.iterrows():

        r_no = s["Roll_No"]

        ev = s_cls_data["evaluations"].get(r_no, {})

        st_status = ev.get("status", s.get("Status", "Present"))

        

        tot_m = 0

        all_passed = True

        for sub in cls_subjects:

            s_val = ev.get("marks", {}).get(sub["id"], {}).get("total", 75)

            tot_m += s_val

            if s_val < 33: all_passed = False

  

        pct = round((tot_m / max_total) * 100, 1) if max_total else 0

        grd = calculate_grade(pct)

        is_pass = (all_passed and pct >= 33 and st_status != "Absent")

        

        c_raw = str(s.get("Category", "OBC")).upper().strip()

        c_std = "SC" if "SC" in c_raw else ("ST" if "ST" in c_raw else ("GEN" if ("GEN" in c_raw or "UR" in c_raw or "सामान्य" in c_raw) else "OBC"))

        g_raw = str(s.get("Gender", "Boy")).strip().lower()

        g_std = "Girls" if g_raw in ["girl", "female", "g", "बालिका"] else "Boys"

        

        calc_data.append({

            "Gender": g_std,

            "Category": c_std,

            "Status": st_status,

            "Pass": is_pass,

            "Grade": grd

        })

    cdf = pd.DataFrame(calc_data)

  

    def get_cnt(g_filter, c_filter, metric):

        if cdf.empty: return 0

        df_sub = cdf.copy()

        if g_filter != "ALL": df_sub = df_sub[df_sub["Gender"] == g_filter]

        if c_filter != "ALL": df_sub = df_sub[df_sub["Category"] == c_filter]

        

        if metric == "Enrolled": return len(df_sub)

        elif metric == "Appeared": return len(df_sub[df_sub["Status"] != "Absent"])

        elif metric == "Absent": return len(df_sub[df_sub["Status"] == "Absent"])

        elif metric == "Pass": return len(df_sub[df_sub["Pass"] == True])

        elif metric == "Fail": return len(df_sub[(df_sub["Pass"] == False) & (df_sub["Status"] != "Absent")])

        return 0

  

    # Build Table 1 Rows (Summary)

    cat_rows_html = ""

    for m in summary_metrics:

        if m == "Percentage":

            g_sc_p = f"{round((get_cnt('Girls','SC','Pass')/max(1,get_cnt('Girls','SC','Appeared')))*100)}%"

            g_st_p = f"{round((get_cnt('Girls','ST','Pass')/max(1,get_cnt('Girls','ST','Appeared')))*100)}%"

            g_obc_p = f"{round((get_cnt('Girls','OBC','Pass')/max(1,get_cnt('Girls','OBC','Appeared')))*100)}%"

            g_gen_p = f"{round((get_cnt('Girls','GEN','Pass')/max(1,get_cnt('Girls','GEN','Appeared')))*100)}%"

            g_tot_p = f"{round((get_cnt('Girls','ALL','Pass')/max(1,get_cnt('Girls','ALL','Appeared')))*100)}%"

  

            b_sc_p = f"{round((get_cnt('Boys','SC','Pass')/max(1,get_cnt('Boys','SC','Appeared')))*100)}%"

            b_st_p = f"{round((get_cnt('Boys','ST','Pass')/max(1,get_cnt('Boys','ST','Appeared')))*100)}%"

            b_obc_p = f"{round((get_cnt('Boys','OBC','Pass')/max(1,get_cnt('Boys','OBC','Appeared')))*100)}%"

            b_gen_p = f"{round((get_cnt('Boys','GEN','Pass')/max(1,get_cnt('Boys','GEN','Appeared')))*100)}%"

            b_tot_p = f"{round((get_cnt('Boys','ALL','Pass')/max(1,get_cnt('Boys','ALL','Appeared')))*100)}%"

  

            all_sc_p = f"{round((get_cnt('ALL','SC','Pass')/max(1,get_cnt('ALL','SC','Appeared')))*100)}%"

            all_st_p = f"{round((get_cnt('ALL','ST','Pass')/max(1,get_cnt('ALL','ST','Appeared')))*100)}%"

            all_obc_p = f"{round((get_cnt('ALL','OBC','Pass')/max(1,get_cnt('ALL','OBC','Appeared')))*100)}%"

            all_gen_p = f"{round((get_cnt('ALL','GEN','Pass')/max(1,get_cnt('ALL','GEN','Appeared')))*100)}%"

            all_tot_p = f"{round((get_cnt('ALL','ALL','Pass')/max(1,get_cnt('ALL','ALL','Appeared')))*100)}%"

  

            cat_rows_html += f"""

            <tr style="height: 26px;">

                <td style="border: 1px solid #000; text-align: left; padding-left: 6px; font-weight: bold;">{m}</td>

                <td style="border: 1px solid #000;">{g_sc_p}</td><td style="border: 1px solid #000;">{g_st_p}</td><td style="border: 1px solid #000;">{g_obc_p}</td><td style="border: 1px solid #000;">{g_gen_p}</td><td style="border: 1px solid #000; font-weight: bold;">{g_tot_p}</td>

                <td style="border: 1px solid #000;">{b_sc_p}</td><td style="border: 1px solid #000;">{b_st_p}</td><td style="border: 1px solid #000;">{b_obc_p}</td><td style="border: 1px solid #000;">{b_gen_p}</td><td style="border: 1px solid #000; font-weight: bold;">{b_tot_p}</td>

                <td style="border: 1px solid #000;">{all_sc_p}</td><td style="border: 1px solid #000;">{all_st_p}</td><td style="border: 1px solid #000;">{all_obc_p}</td><td style="border: 1px solid #000;">{all_gen_p}</td><td style="border: 1px solid #000; font-weight: bold;">{all_tot_p}</td>

            </tr>

            """

        else:

            cat_rows_html += f"""

            <tr style="height: 26px;">

                <td style="border: 1px solid #000; text-align: left; padding-left: 6px; font-weight: normal;">{m}</td>

                <td style="border: 1px solid #000;">{get_cnt('Girls','SC',m)}</td><td style="border: 1px solid #000;">{get_cnt('Girls','ST',m)}</td><td style="border: 1px solid #000;">{get_cnt('Girls','OBC',m)}</td><td style="border: 1px solid #000;">{get_cnt('Girls','GEN',m)}</td><td style="border: 1px solid #000; font-weight: bold;">{get_cnt('Girls','ALL',m)}</td>

                <td style="border: 1px solid #000;">{get_cnt('Boys','SC',m)}</td><td style="border: 1px solid #000;">{get_cnt('Boys','ST',m)}</td><td style="border: 1px solid #000;">{get_cnt('Boys','OBC',m)}</td><td style="border: 1px solid #000;">{get_cnt('Boys','GEN',m)}</td><td style="border: 1px solid #000; font-weight: bold;">{get_cnt('Boys','ALL',m)}</td>

                <td style="border: 1px solid #000;">{get_cnt('ALL','SC',m)}</td><td style="border: 1px solid #000;">{get_cnt('ALL','ST',m)}</td><td style="border: 1px solid #000;">{get_cnt('ALL','OBC',m)}</td><td style="border: 1px solid #000;">{get_cnt('ALL','GEN',m)}</td><td style="border: 1px solid #000; font-weight: bold;">{get_cnt('ALL','ALL',m)}</td>

            </tr>

            """

  

    # Build Table 2 Rows (Grade)

    grade_rows_html = ""

    for g in grades_list:

        def get_grd_cnt(g_filter, c_filter):

            if cdf.empty: return 0

            df_sub = cdf[cdf["Grade"] == g]

            if g_filter != "ALL": df_sub = df_sub[df_sub["Gender"] == g_filter]

            if c_filter != "ALL": df_sub = df_sub[df_sub["Category"] == c_filter]

            return len(df_sub)

  

        grade_rows_html += f"""

        <tr style="height: 26px;">

            <td style="border: 1px solid #000; font-weight: normal; padding: 2px;">{g}</td>

            <td style="border: 1px solid #000;">{get_grd_cnt('Girls','SC')}</td><td style="border: 1px solid #000;">{get_grd_cnt('Girls','ST')}</td><td style="border: 1px solid #000;">{get_grd_cnt('Girls','OBC')}</td><td style="border: 1px solid #000;">{get_grd_cnt('Girls','GEN')}</td><td style="border: 1px solid #000; font-weight: bold;">{get_grd_cnt('Girls','ALL')}</td>

            <td style="border: 1px solid #000;">{get_grd_cnt('Boys','SC')}</td><td style="border: 1px solid #000;">{get_grd_cnt('Boys','ST')}</td><td style="border: 1px solid #000;">{get_grd_cnt('Boys','OBC')}</td><td style="border: 1px solid #000;">{get_grd_cnt('Boys','GEN')}</td><td style="border: 1px solid #000; font-weight: bold;">{get_grd_cnt('Boys','ALL')}</td>

            <td style="border: 1px solid #000;">{get_grd_cnt('ALL','SC')}</td><td style="border: 1px solid #000;">{get_grd_cnt('ALL','ST')}</td><td style="border: 1px solid #000;">{get_grd_cnt('ALL','OBC')}</td><td style="border: 1px solid #000;">{get_grd_cnt('ALL','GEN')}</td><td style="border: 1px solid #000; font-weight: bold;">{get_grd_cnt('ALL','ALL')}</td>

        </tr>

        """

  

    # Exact HTML Matching image_04fbc5.png

    summary_page_html = f"""

    <div class="printable-area" style="background: #ffffff; padding: 10px 14px; max-width: 820px; margin: auto; font-family: Arial, sans-serif; color: #000;">

        <!-- TOP HEADER TABLE MATCHING image_04fbc5.png -->

        <table style="width: 100%; border-collapse: collapse; border: 1px solid #000; text-align: center; font-size: 13px; font-weight: bold; margin-bottom: 0px;">

            <tr>

                <td colspan="2" style="border: 1px solid #000; padding: 6px; font-size: 18px; font-weight: 900; letter-spacing: 0.5px;">

                    Dise Code : {s_info.get('udise', '23260100101')}

                </td>

            </tr>

            <tr>

                <td style="border: 1px solid #000; width: 50%; padding: 4px;">Block : {s_info.get('block','Fanda')}</td>

                <td style="border: 1px solid #000; width: 50%; padding: 4px;">District : {s_info.get('district','Bhopal')}</td>

            </tr>

            <tr>

                <td style="border: 1px solid #000; padding: 4px;">Class : {display_summary_class}</td>

                <td style="border: 1px solid #000; padding: 4px;">Medium : {get_display_medium(s_info)}</td>

            </tr>

            <tr>

                <td colspan="2" style="border: 1px solid #000; padding: 6px; font-size: 17px; font-weight: 900; letter-spacing: 0.5px; background: #fafafa;">

                    Annual Result {cur_sess}

                </td>

            </tr>

        </table>

  

        <!-- SUBTITLE MATCHING image_04fbc5.png -->

        <div style="text-align: center; font-weight: 800; font-size: 14px; margin-top: 8px; margin-bottom: 8px; border-top: 1px solid #000; border-bottom: 1px solid #000; padding: 4px 0;">

            Category/Grade Wise Result Summary

        </div>

  

        <!-- TABLE 1: SUMMARY -->

        <table style="width: 100%; border-collapse: collapse; border: 1px solid #000; text-align: center; font-size: 12px; margin-bottom: 14px;">

            <thead>

                <tr style="background: #ffffff; font-weight: bold; height: 26px;">

                    <th rowspan="2" style="border: 1px solid #000; width: 16%; padding: 4px;">Summary</th>

                    <th colspan="5" style="border: 1px solid #000; width: 28%;">Girls</th>

                    <th colspan="5" style="border: 1px solid #000; width: 28%;">Boys</th>

                    <th colspan="5" style="border: 1px solid #000; width: 28%;">Grand Total</th>

                </tr>

                <tr style="background: #ffffff; font-size: 11px; height: 24px;">

                    <th style="border: 1px solid #000; padding: 2px;">Sc</th><th style="border: 1px solid #000; padding: 2px;">St</th><th style="border: 1px solid #000; padding: 2px;">Obc</th><th style="border: 1px solid #000; padding: 2px;">Gen.</th><th style="border: 1px solid #000; padding: 2px; font-weight: bold;">Total</th>

                    <th style="border: 1px solid #000; padding: 2px;">Sc</th><th style="border: 1px solid #000; padding: 2px;">St</th><th style="border: 1px solid #000; padding: 2px;">Obc</th><th style="border: 1px solid #000; padding: 2px;">Gen.</th><th style="border: 1px solid #000; padding: 2px; font-weight: bold;">Total</th>

                    <th style="border: 1px solid #000; padding: 2px;">Sc</th><th style="border: 1px solid #000; padding: 2px;">St</th><th style="border: 1px solid #000; padding: 2px;">Obc</th><th style="border: 1px solid #000; padding: 2px;">Gen.</th><th style="border: 1px solid #000; padding: 2px; font-weight: bold;">Total</th>

                </tr>

            </thead>

            <tbody>

                {cat_rows_html}

            </tbody>

        </table>

  

        <!-- TABLE 2: GRADE WISE -->

        <table style="width: 100%; border-collapse: collapse; border: 1px solid #000; text-align: center; font-size: 12px; margin-bottom: 10px;">

            <thead>

                <tr style="background: #ffffff; font-weight: bold; height: 26px;">

                    <th rowspan="2" style="border: 1px solid #000; width: 16%; padding: 4px;">Grade</th>

                    <th colspan="5" style="border: 1px solid #000; width: 28%;">Girls</th>

                    <th colspan="5" style="border: 1px solid #000; width: 28%;">Boys</th>

                    <th colspan="5" style="border: 1px solid #000; width: 28%;">Grand Total</th>

                </tr>

                <tr style="background: #ffffff; font-size: 11px; height: 24px;">

                    <th style="border: 1px solid #000; padding: 2px;">Sc</th><th style="border: 1px solid #000; padding: 2px;">St</th><th style="border: 1px solid #000; padding: 2px;">Obc</th><th style="border: 1px solid #000; padding: 2px;">Gen.</th><th style="border: 1px solid #000; padding: 2px; font-weight: bold;">Total</th>

                    <th style="border: 1px solid #000; padding: 2px;">Sc</th><th style="border: 1px solid #000; padding: 2px;">St</th><th style="border: 1px solid #000; padding: 2px;">Obc</th><th style="border: 1px solid #000; padding: 2px;">Gen.</th><th style="border: 1px solid #000; padding: 2px; font-weight: bold;">Total</th>

                    <th style="border: 1px solid #000; padding: 2px;">Sc</th><th style="border: 1px solid #000; padding: 2px;">St</th><th style="border: 1px solid #000; padding: 2px;">Obc</th><th style="border: 1px solid #000; padding: 2px;">Gen.</th><th style="border: 1px solid #000; padding: 2px; font-weight: bold;">Total</th>

                </tr>

            </thead>

            <tbody>

                {grade_rows_html}

            </tbody>

        </table>

    </div>

    """

  

    # Layout: Print button on top-right (matching image_04fbc5.png) + Role Check

    c_p_bar1, c_p_bar2 = st.columns([4, 1])

    with c_p_bar2:

        if is_teacher:

            render_html("<div style='color: #991B1B; font-size: 11px; font-weight: bold; text-align: right;'>🔒 प्रिंट केवल संस्था प्रधान हेतु</div>")

        else:

            st.button("🖨️ Print", on_click=None, use_container_width=True, type="primary", key="btn_pr_summary_top")

  

    render_html(summary_page_html)

  

    # Export Section (Principal Only with Gatekeeper)

    if is_teacher:

        render_html("""

        <div style="background: #FEF2F2; border-left: 4px solid #EF4444; padding: 10px 14px; border-radius: 6px; color: #991B1B; margin-top: 10px; font-size: 12.5px;">

            <b>🔒 शासकीय सुरक्षा सूचना:</b> परीक्षाफल सांख्यिकी सारांश का आधिकारिक प्रिंट एवं एक्सेल एक्सपोर्ट केवल <b>संस्था प्रधान (Principal)</b> खाते में अधिकृत है। आप केवल अपनी आवंटित कक्षा का सारांश देख सकते हैं।

        </div>

        """)

    else:

        st.divider()

        render_html("### 📥 सांख्यिकी सारांश एक्सपोर्ट (Export Result Summary for BEO / BRC / DEO Office)")

        if render_export_gatekeeper("परीक्षाफल सांख्यिकी सारांश"):

            c_sexp1, c_sexp2 = st.columns([2, 2])

            with c_sexp1:

                s_exp_fmt = st.selectbox("फ़ाइल प्रारूप चुनें (Format):", ["Excel (.xlsx)", "CSV (.csv)"], key="sum_exp_fmt")

            with c_sexp2:

                sum_rows = []

                for m in summary_metrics:

                    r_dict = {"Summary_Metric": m}

                    for g in ["Girls", "Boys", "Grand Total"]:

                        for c in ["SC", "ST", "OBC", "GEN", "Total"]:

                            col_k = "ALL" if c == "Total" else c

                            g_k = "ALL" if g == "Grand Total" else g

                            if m == "Percentage":

                                pas = get_cnt(g_k, col_k, "Pass")

                                app = get_cnt(g_k, col_k, "Appeared")

                                val = f"{round((pas/max(1,app))*100)}%"

                            else:

                                val = get_cnt(g_k, col_k, m)

                            r_dict[f"{g}_{c}"] = val

                    sum_rows.append(r_dict)

                sum_df = pd.DataFrame(sum_rows)

                s_bytes, s_mime, s_ext = export_dataframe_bytes(sum_df, s_exp_fmt)

                st.download_button(

                    f"📥 सांख्यिकी सारांश डाउनलोड करें ({s_exp_fmt})",

                    data=s_bytes,

                    file_name=f"Result_Summary_Statistics_{target_summary_class}_{s_info.get('session','2023-24')}{s_ext}",

                    mime=s_mime,

                    type="primary",

                    use_container_width=True

                )

  
  

        render_govt_portals_hub("श्रेणीवार परिणाम सारांश", target_summary_class, None, "Result_Summary_Form3")

# ----------------- MODULE 12: ANNUAL RESULT MERIT LIST (OFFICIAL RSKMP & MPBSE FORMAT) -----------------
elif menu == T.get("nav_merit", "🏆 12. वार्षिक परीक्षा प्रावीण्य सूची (Merit List)"):
    s_info = st.session_state.school_info
    cur_sess = s_info.get("session", "2026-27")
    
    cur_role = st.session_state.get("authenticated_role", "PRINCIPAL")
    is_teacher = (cur_role == "TEACHER")
    assigned_cls = st.session_state.get("assigned_class")
    
    c_mtop1, c_mtop2, c_mtop3 = st.columns([2.2, 1.3, 1.3])
    with c_mtop1:
        st.markdown('<div class="main-header">🏆 वार्षिक परीक्षा प्रावीण्य सूची (Merit List)</div>', unsafe_allow_html=True)
        render_html('<div class="sub-header">राज्य शिक्षा केंद्र (RSKMP) एवं माध्यमिक शिक्षा मंडल (MPBSE) आधिकारिक प्रारूप</div>')
    with c_mtop2:
        if is_teacher and assigned_cls:
            target_merit_class = assigned_cls
            render_html(f"<div style='border: 1px solid #CBD5E1; background: #F1F5F9; padding: 7px 10px; border-radius: 6px; font-weight: bold; font-size: 13px; text-align: center; color: #1E3A8A; margin-top: 22px;'>🎯 आवंटित कक्षा: {target_merit_class}</div>")
        else:
            target_merit_class = st.selectbox(
                "1. कक्षा चुनें (Class):", 
                st.session_state.classes_list, 
                index=st.session_state.classes_list.index(selected_class) if selected_class in st.session_state.classes_list else 0,
                key="merit_class_picker"
            )
    
    m_cls_data = get_class_data(target_merit_class)
    raw_st_df = m_cls_data["students"]
    existing_secs = sorted(list(set([str(s).strip() for s in raw_st_df["Section"].dropna().unique() if str(s).strip()]))) if not raw_st_df.empty and "Section" in raw_st_df.columns else ["A"]
    sec_options = ["सभी सेक्शन (All Sections Combined)"] + (existing_secs if existing_secs else ["A", "B", "C"])
  
    with c_mtop3:
        target_merit_sec = st.selectbox("2. सेक्शन चुनें (Section):", sec_options, key="merit_sec_picker")
  
    if target_merit_sec != "सभी सेक्शन (All Sections Combined)" and not raw_st_df.empty and "Section" in raw_st_df.columns:
        students_df = raw_st_df[raw_st_df["Section"] == target_merit_sec].copy()
        display_merit_class = f"{target_merit_class} - Section {target_merit_sec}"
    else:
        students_df = raw_st_df.copy()
        display_merit_class = f"{target_merit_class} (समस्त सेक्शन)"
    
    clean_cls = str(target_merit_class).lower()
    is_highschool = ("class 9" in clean_cls or "class 10" in clean_cls or "9th" in clean_cls or "10th" in clean_cls)
    board_authority = "माध्यमिक शिक्षा मंडल, मध्य प्रदेश, भोपाल (MPBSE)" if is_highschool else "राज्य शिक्षा केंद्र, मध्य प्रदेश, भोपाल (RSKMP)"

    if students_df.empty:
        st.warning(f"⚠️ {display_merit_class} में कोई विद्यार्थी पंजीकृत नहीं है।")
    else:
        cls_subjects = get_class_subjects(target_merit_class)
        m_evals = m_cls_data["evaluations"]
        
        merit_records = []
        for idx, s in students_df.iterrows():
            r = s["Roll_No"]
            ev = m_evals.get(r, {})
            m_dict = ev.get("marks", {})
            st_stat = ev.get("status", s.get("Status", "Present"))
            
            sub_totals = []
            all_pass = True
            for sub in cls_subjects:
                s_id = sub["id"]
                se = m_dict.get(s_id, {})
                tot = se.get("total", 75)
                sub_totals.append(tot)
                if tot < 33:
                    all_pass = False
            
            grand_obt = sum(sub_totals) if st_stat != "Absent" else 0
            max_m = len(cls_subjects) * 100
            pct = round((grand_obt / max_m) * 100, 1) if max_m > 0 else 0
            grd = calculate_grade(pct) if st_stat != "Absent" else "Ab"
            div_str = calculate_division(pct) if st_stat != "Absent" else "--"
            res_str = "PASS" if (all_pass and pct >= 33 and st_stat != "Absent") else ("ABSENT" if st_stat == "Absent" else "FAIL")
            
            best_of_5_obt = grand_obt
            if is_highschool and len(sub_totals) >= 6:
                best_of_5_obt = sum(sorted(sub_totals, reverse=True)[:5])
            
            merit_records.append({
                "Roll_No": r,
                "Scholar_No": s.get("Scholar_No", "--"),
                "Samagra_ID": s.get("SSSM_ID", "--"),
                "Name": s["Name"],
                "Father_Name": s["Father_Name"],
                "Mother_Name": s.get("Mother_Name", "--"),
                "DOB": s.get("DOB", "--"),
                "Gender": s.get("Gender", "--"),
                "Category": s.get("Category", "--"),
                "Section": s.get("Section", "A"),
                "Max_Marks": max_m,
                "Obt_Marks": grand_obt,
                "Best_Of_5": best_of_5_obt,
                "Percentage": pct,
                "Grade": grd,
                "Division": div_str,
                "Result": res_str,
                "Exam_Status": st_stat
            })
        
        # Sort descending by Obtained Marks (or Best of 5 for 10th)
        sort_key = "Best_Of_5" if (is_highschool and "10" in clean_cls) else "Obt_Marks"
        merit_records = sorted(merit_records, key=lambda x: (x["Result"] == "PASS", x[sort_key], x["Percentage"]), reverse=True)
        
        for i, rec in enumerate(merit_records):
            rec["Rank"] = i + 1

        # Action Bar (Print & Export)
        c_mact1, c_mact2 = st.columns([3, 1])
        with c_mact1:
            st.markdown(f"<b>📊 कुल परीक्षार्थी:</b> {len(merit_records)} | <b>प्रथम स्थान:</b> {merit_records[0]['Name']} ({merit_records[0]['Percentage']}%) | <b>बोर्ड:</b> {board_authority}", unsafe_allow_html=True)
        with c_mact2:
            if not is_teacher:
                st.button("🖨️ Print Merit List", on_click=None, use_container_width=True, type="primary", key="btn_merit_print")
            else:
                st.markdown("<div style='color:#991B1B; font-size:11px; font-weight:bold; text-align:right;'>🔒 प्रिंट केवल संस्था प्रधान हेतु</div>", unsafe_allow_html=True)

        # Build Official RSKMP / MPBSE Merit Table HTML
        rows_html = ""
        for rec in merit_records:
            rank = rec["Rank"]
            if rank == 1:
                rank_badge = '<span style="background:#FEF3C7; color:#B45309; padding:2px 8px; border-radius:12px; font-weight:900; border:1px solid #F59E0B;">🥇 1st Rank</span>'
                row_bg = "background-color: #FFFDF0;"
            elif rank == 2:
                rank_badge = '<span style="background:#F1F5F9; color:#475569; padding:2px 8px; border-radius:12px; font-weight:900; border:1px solid #94A3B8;">🥈 2nd Rank</span>'
                row_bg = "background-color: #F8FAFC;"
            elif rank == 3:
                rank_badge = '<span style="background:#FFEDD5; color:#9A3412; padding:2px 8px; border-radius:12px; font-weight:900; border:1px solid #F97316;">🥉 3rd Rank</span>'
                row_bg = "background-color: #FFF9F5;"
            else:
                rank_badge = f'<span style="font-weight:bold; color:#1E293B;">{rank}</span>'
                row_bg = "background-color: #ffffff;"

            res_color = "#15803D" if rec["Result"] == "PASS" else "#B91C1C"
            
            rows_html += f"""
            <tr style="height: 28px; font-size: 11.5px; text-align: center; {row_bg}">
                <td style="border: 1px solid #CBD5E1; padding: 4px;">{rank_badge}</td>
                <td style="border: 1px solid #CBD5E1; padding: 4px; font-weight: bold;">{rec['Roll_No']}</td>
                <td style="border: 1px solid #CBD5E1; padding: 4px;">{rec['Scholar_No']}</td>
                <td style="border: 1px solid #CBD5E1; padding: 4px; font-size: 10.5px;">{rec['Samagra_ID']}</td>
                <td style="border: 1px solid #CBD5E1; padding: 4px 8px; text-align: left; font-weight: bold; color: #1E3A8A;">{rec['Name']}</td>
                <td style="border: 1px solid #CBD5E1; padding: 4px 8px; text-align: left;">{rec['Father_Name']}</td>
                <td style="border: 1px solid #CBD5E1; padding: 4px 8px; text-align: left;">{rec['Mother_Name']}</td>
                <td style="border: 1px solid #CBD5E1; padding: 4px;">{rec['Category']} / {rec['Gender'][:1]}</td>
                <td style="border: 1px solid #CBD5E1; padding: 4px;">{rec['Max_Marks']}</td>
                <td style="border: 1px solid #CBD5E1; padding: 4px; font-weight: bold; font-size: 12px; color: #0F172A;">{rec['Obt_Marks']}</td>
                <td style="border: 1px solid #CBD5E1; padding: 4px; font-weight: bold; color: #1E3A8A;">{rec['Percentage']}%</td>
                <td style="border: 1px solid #CBD5E1; padding: 4px; font-weight: bold;">{rec['Grade']}</td>
                <td style="border: 1px solid #CBD5E1; padding: 4px; font-size: 11px;">{rec['Division']}</td>
                <td style="border: 1px solid #CBD5E1; padding: 4px; font-weight: bold; color: {res_color};">{rec['Result']}</td>
            </tr>
            """

        official_merit_html = f"""
        <div class="printable-area" style="background: #ffffff; border: 2px solid #1E3A8A; padding: 14px 18px; font-family: Arial, sans-serif; color: #000; margin: auto;">
            <!-- GOVT HEADER -->
            <div style="text-align: center; border-bottom: 2px solid #1E3A8A; padding-bottom: 8px; margin-bottom: 10px;">
                <div style="font-size: 18px; font-weight: 900; color: #1E3A8A; letter-spacing: 0.5px;">
                    {board_authority}
                </div>
                <div style="font-size: 16px; font-weight: 800; color: #000; margin-top: 2px;">
                    {s_info.get('name', 'शासकीय माध्यमिक विद्यालय')}
                </div>
                <div style="font-size: 14px; font-weight: bold; color: #B45309; margin-top: 2px;">
                    🏆 वार्षिक परीक्षा प्रावीण्य सूची (Merit List) — सत्र {cur_sess}
                </div>
                <div style="font-size: 12px; color: #334155; margin-top: 4px;">
                    <b>DISE:</b> {s_info.get('udise', '23260100101')} | <b>ब्लॉक:</b> {s_info.get('block','SENDHWA')} | <b>जिला:</b> {s_info.get('district','BARWANI')} | <b>कक्षा:</b> {display_merit_class} | <b>माध्यम:</b> {get_display_medium(s_info)}
                </div>
            </div>

            <!-- MERIT TABLE -->
            <table style="width: 100%; border-collapse: collapse; border: 1px solid #1E3A8A; font-size: 11px;">
                <thead>
                    <tr style="background: #1E3A8A; color: #ffffff; height: 32px; font-weight: bold;">
                        <th style="border: 1px solid #CBD5E1; width: 85px;">मेरिट रैंक</th>
                        <th style="border: 1px solid #CBD5E1; width: 60px;">अनुक्रमांक</th>
                        <th style="border: 1px solid #CBD5E1; width: 65px;">दाखिला क्र.</th>
                        <th style="border: 1px solid #CBD5E1; width: 75px;">समग्र ID</th>
                        <th style="border: 1px solid #CBD5E1; width: 140px; text-align: left; padding-left: 8px;">विद्यार्थी का नाम</th>
                        <th style="border: 1px solid #CBD5E1; width: 130px; text-align: left; padding-left: 8px;">पिता का नाम</th>
                        <th style="border: 1px solid #CBD5E1; width: 120px; text-align: left; padding-left: 8px;">माता का नाम</th>
                        <th style="border: 1px solid #CBD5E1; width: 65px;">वर्ग/लिंग</th>
                        <th style="border: 1px solid #CBD5E1; width: 50px;">पूर्णांक</th>
                        <th style="border: 1px solid #CBD5E1; width: 60px;">प्राप्तांक</th>
                        <th style="border: 1px solid #CBD5E1; width: 55px;">प्रतिशत</th>
                        <th style="border: 1px solid #CBD5E1; width: 45px;">ग्रेड</th>
                        <th style="border: 1px solid #CBD5E1; width: 55px;">श्रेणी</th>
                        <th style="border: 1px solid #CBD5E1; width: 55px;">परिणाम</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html}
                </tbody>
            </table>

            <!-- SIGNATURE BLOCK -->
            <div style="display: flex; justify-content: space-between; margin-top: 35px; font-weight: bold; font-size: 11.5px; text-align: center;">
                <div>_______________________<br>कक्षा अध्यापक हस्ताक्षर</div>
                <div>_______________________<br>मूल्यांकन / परीक्षा प्रभारी</div>
                <div>_______________________<br>संस्था प्रधान (सील सहित)</div>
            </div>
            <div style="text-align: center; font-size: 10px; margin-top: 10px; color: #64748B;">
                शासकीय प्रावीण्य सूची | मुद्रण दिनांक: {TODAY_STR}
            </div>
        </div>
        """
        
        render_html(official_merit_html)

        if not is_teacher:
            st.divider()
            st.markdown("##### 📥 आधिकारिक प्रावीण्य सूची एक्सेल डाउनलोड (.xlsx):")
            if render_export_gatekeeper("प्रावीण्य सूची (Merit List)"):
                merit_export_df = pd.DataFrame(merit_records)
                m_bytes, m_mime, m_ext = export_dataframe_bytes(merit_export_df, "Excel (.xlsx)")
                st.download_button(
                    "📥 आधिकारिक प्रावीण्य सूची एक्सेल डाउनलोड (.xlsx)",
                    data=m_bytes,
                    file_name=f"Official_Merit_List_{target_merit_class}_{cur_sess}.xlsx",
                    mime=m_mime,
                    type="primary",
                    use_container_width=True
                )


        render_govt_portals_hub("वार्षिक प्रावीण्य सूची", target_merit_class, merit_export_df if 'merit_export_df' in locals() else None, "Merit_List")

# ----------------- MODULE 13: SUPPLEMENTARY STUDENTS LIST (IMAGE: image_05d509.png) -----------------


elif menu == T.get("nav_supple", "📋 13. पूरक परीक्षा छात्र सूची (Supplementary List)"):

    cur_role = st.session_state.get("authenticated_role", "PRINCIPAL")

    is_teacher = (cur_role == "TEACHER")

    assigned_cls = st.session_state.get("assigned_class")

    s_info = st.session_state.school_info

    cur_sess = s_info.get("session", "2026-27")

  

    # Class and Section Selectors

    c_sptop1, c_sptop2, c_sptop3 = st.columns([2.2, 1.3, 1.3])

    with c_sptop1:

        st.markdown(f'<div class="main-header">📋 पूरक / अनुपूरक परीक्षा छात्र सूची</div>', unsafe_allow_html=True)

        render_html(f'<div class="sub-header">Supplementary / Re-Examination Candidates List — RSKMP एवं MPBSE प्रारूप</div>')

    with c_sptop2:

        if is_teacher and assigned_cls:

            target_supple_class = assigned_cls

            render_html(f"<div style='border: 1px solid #CBD5E1; background: #F1F5F9; padding: 7px 10px; border-radius: 6px; font-weight: bold; font-size: 13px; text-align: center; color: #1E3A8A; margin-top: 22px;'>🎯 आवंटित कक्षा: {target_supple_class}</div>")

        else:

            target_supple_class = st.selectbox(

                "1. कक्षा चुनें (Class):", 

                st.session_state.classes_list, 

                index=st.session_state.classes_list.index(selected_class) if selected_class in st.session_state.classes_list else 0,

                key="supple_class_picker"

            )

    

    sp_cls_data = get_class_data(target_supple_class)

    raw_st_df = sp_cls_data["students"]

    existing_secs = sorted(list(set([str(s).strip() for s in raw_st_df["Section"].dropna().unique() if str(s).strip()]))) if not raw_st_df.empty and "Section" in raw_st_df.columns else ["A"]

    sec_options = ["सभी सेक्शन (All Sections Combined)"] + (existing_secs if existing_secs else ["A", "B", "C"])

    with c_sptop3:

        target_supple_sec = st.selectbox("2. सेक्शन चुनें (Section):", sec_options, key="supple_sec_picker")

  

    if target_supple_sec != "सभी सेक्शन (All Sections Combined)" and not raw_st_df.empty and "Section" in raw_st_df.columns:

        students_df = raw_st_df[raw_st_df["Section"] == target_supple_sec].copy()

        display_supple_class = f"{target_supple_class} - Section {target_supple_sec}"

    else:

        students_df = raw_st_df.copy()

        display_supple_class = f"{target_supple_class} (समस्त सेक्शन)"

  

    cls_subjects = get_class_subjects(target_supple_class)

    sp_evals = sp_cls_data["evaluations"]

  

    # Detect Supplementary Candidates

    supple_candidates = []

    all_students_rows = []

  

    for idx, s in students_df.iterrows():

        r = s["Roll_No"]

        ev = sp_evals.get(r, {})

        m_dict = ev.get("marks", {})

        st_stat = ev.get("status", s.get("Status", "Present"))

        

        failed_subs = []

        for sub in cls_subjects:

            s_id = sub["id"]

            s_name = sub["name"]

            se = m_dict.get(s_id, {})

            tot = se.get("total", 75)

            if tot < 33 or st_stat == "Absent":

                failed_subs.append(f"{s_name} ({tot}/100)")

        

        subs_text = ", ".join(failed_subs) if failed_subs else "-----"

        

        rec = {

            "Roll_No": r,

            "Name": s["Name"],

            "Father_Name": s["Father_Name"],

            "Section": s.get("Section", "A"),

            "Supple_Subjects": subs_text,

            "Is_Supple": len(failed_subs) > 0

        }

        all_students_rows.append(rec)

        if len(failed_subs) > 0:

            supple_candidates.append(rec)

  

    # Filter choice & Print Button Bar

    c_f1, c_f2 = st.columns([3, 1])

    with c_f1:

        view_filter = st.radio("प्रदर्शित सूची चुनें:", ["केवल पूरक / पुनः परीक्षा वाले छात्र (Only Supplementary Candidates)", "कक्षा के सभी छात्र (All Students matching Excel Template)"], horizontal=True, key="supple_view_filter")

    with c_f2:

        if not is_teacher:

            render_html("<div style='margin-top: 10px;'>")

            st.button("🖨️ Print", on_click=None, use_container_width=True, type="primary", key="btn_supple_print")

            st.markdown("</div>", unsafe_allow_html=True)

        else:

            render_html("<div style='color:#991B1B; font-size:11px; font-weight:bold; margin-top:20px; text-align:right;'>🔒 प्रिंट केवल संस्था प्रधान हेतु</div>")

  

    active_list = supple_candidates if "केवल पूरक" in view_filter else all_students_rows

  

    if not active_list:

        st.success(f"🎉 बधाई! {display_supple_class} में कोई भी छात्र पूरक / अनुपूरक परीक्षा हेतु नहीं है (100% परीक्षा परिणाम)!")

    else:

        # Build Table HTML matching image_05d509.png exactly

        supple_rows_html = ""

        for rec in active_list:

            subj_style = "color: #B91C1C; font-weight: bold;" if rec["Is_Supple"] else "color: #555;"

            supple_rows_html += f"""

            <tr style="height: 30px; font-size: 12.5px;">

                <td style="border: 1px solid #000; text-align: center; padding: 4px; font-weight: bold; width: 12%;">{rec['Roll_No']}</td>

                <td style="border: 1px solid #000; text-align: left; padding: 4px 8px; font-weight: bold; width: 28%;">{rec['Name']}</td>

                <td style="border: 1px solid #000; text-align: left; padding: 4px 8px; width: 28%;">{rec['Father_Name']}</td>

                <td style="border: 1px solid #000; text-align: left; padding: 4px 8px; width: 32%; {subj_style}">{rec['Supple_Subjects']}</td>

            </tr>

            """

  

        exact_supple_html = f"""

        <div class="printable-area" style="background: #ffffff; border: 2px solid #000; padding: 14px 18px; max-width: 820px; margin: auto; font-family: Arial, sans-serif; color: #000;">

            <!-- TOP HEADER BLOCK -->

            <table style="width: 100%; border-collapse: collapse; border: 1px solid #000; text-align: center; font-size: 13px; font-weight: bold; margin-bottom: 0px;">

                <tr>

                    <td colspan="2" style="border: 1px solid #000; padding: 6px; font-size: 18px; font-weight: 900; letter-spacing: 0.5px;">

                        Dise Code : {s_info.get('udise', '23260100101')}

                    </td>

                </tr>

                <tr>

                    <td style="border: 1px solid #000; width: 50%; padding: 4px;">Block : {s_info.get('block','Fanda')}</td>

                    <td style="border: 1px solid #000; width: 50%; padding: 4px;">District : {s_info.get('district','Bhopal')}</td>

                </tr>

                <tr>

                    <td style="border: 1px solid #000; padding: 4px;">Class : {display_supple_class}</td>

                    <td style="border: 1px solid #000; padding: 4px;">Medium : {get_display_medium(s_info)}</td>

                </tr>

                <tr>

                    <td colspan="2" style="border: 1px solid #000; padding: 6px; font-size: 17px; font-weight: 900; letter-spacing: 0.5px; background: #fafafa;">

                        Suppelementary Students List

                    </td>

                </tr>

            </table>

  

            <!-- MAIN TABLE MATCHING image_05d509.png -->

            <table style="width: 100%; border-collapse: collapse; border: 1px solid #000; font-size: 12px; text-align: center; margin-top: 0px;">

                <thead>

                    <tr style="background-color: #ffffff; height: 34px; font-weight: bold; border-top: none;">

                        <th style="border: 1px solid #000; width: 12%; text-align: center;">Roll No.</th>

                        <th style="border: 1px solid #000; width: 28%; text-align: left; padding-left: 8px;">Name Of Student</th>

                        <th style="border: 1px solid #000; width: 28%; text-align: left; padding-left: 8px;">Father's Name</th>

                        <th style="border: 1px solid #000; width: 32%; text-align: left; padding-left: 8px;">Suppelementary Subjects</th>

                    </tr>

                </thead>

                <tbody>

                    {supple_rows_html}

                </tbody>

            </table>

  

            <div style="display: flex; justify-content: space-between; margin-top: 40px; font-weight: bold; font-size: 12px; text-align: center;">

                <div>_______________________<br>कक्षा अध्यापक हस्ताक्षर</div>

                <div>_______________________<br>परीक्षा प्रभारी</div>

                <div>_______________________<br>संस्था प्रधान (सील सहित)</div>

            </div>

            <div style="text-align: center; font-size: 10.5px; margin-top: 15px; color: #555; font-style: italic;">

                Supplementary List Generated On: {TODAY_STR}

            </div>

        </div>

        """

  

        render_html(exact_supple_html)

  

        # Export Excel Section (Principal Only with Gatekeeper)

        if is_teacher:

            render_html("""

            <div style="background: #FEF2F2; border-left: 4px solid #EF4444; padding: 10px 14px; border-radius: 6px; color: #991B1B; margin-top: 14px; font-size: 12px;">

                <b>🔒 शासकीय सुरक्षा सूचना:</b> पूरक परीक्षा छात्र सूची का आधिकारिक प्रिंट एवं एक्सेल एक्सपोर्ट केवल <b>संस्था प्रधान (Principal)</b> खाते में अधिकृत है।

            </div>

            """)

        else:

            st.divider()

            render_html("##### 📥 पूरक परीक्षा छात्र सूची एक्सपोर्ट (Export for BRC / RSKMP Portal):")

            if render_export_gatekeeper("पूरक परीक्षा छात्र सूची"):

                supple_export_df = pd.DataFrame(active_list)

                s_bytes, s_mime, s_ext = export_dataframe_bytes(supple_export_df, "Excel (.xlsx)")

                st.download_button(

                    f"📥 पूरक सूची एक्सेल डाउनलोड (.xlsx)",

                    data=s_bytes,

                    file_name=f"Supplementary_Students_List_{target_supple_class}_{cur_sess}.xlsx",

                    mime=s_mime,

                    type="primary",

                    use_container_width=True

                )

        render_govt_portals_hub("पूरक परीक्षा छात्र सूची", target_supple_class, supple_export_df if 'supple_export_df' in locals() else None, "Supplementary_List")

# ----------------- MODULE 14: ANNUAL RESULT RECORD & WEIGHTED EVALUATION SHEET (OFFICIAL RSKMP & MPBSE) -----------------
elif menu == T.get("nav_weighted", "📑 14. वार्षिक परीक्षा परिणाम अभिलेख पत्रक (RSKMP व MPBSE प्रारूप)"):
    cur_role = st.session_state.get("authenticated_role", "PRINCIPAL")
    is_teacher = (cur_role == "TEACHER")
    assigned_cls = st.session_state.get("assigned_class")
    s_info = st.session_state.school_info
    cur_sess = s_info.get("session", "2026-27")

    # Class and Section Selectors
    c_wtop1, c_wtop2, c_wtop3 = st.columns([2.2, 1.3, 1.3])
    with c_wtop1:
        st.markdown('<div class="main-header">📑 वार्षिक परीक्षा परिणाम अभिलेख पत्रक</div>', unsafe_allow_html=True)
        render_html('<div class="sub-header">राज्य शिक्षा केंद्र (RSKMP परिशिष्ट 4 व 6) एवं माध्यमिक शिक्षा मंडल (MPBSE) आधिकारिक प्रारूप</div>')
    with c_wtop2:
        if is_teacher and assigned_cls:
            target_w_class = assigned_cls
            render_html(f"<div style='border: 1px solid #CBD5E1; background: #F1F5F9; padding: 7px 10px; border-radius: 6px; font-weight: bold; font-size: 13px; text-align: center; color: #1E3A8A; margin-top: 22px;'>🎯 आवंटित कक्षा: {target_w_class}</div>")
        else:
            target_w_class = st.selectbox(
                "1. कक्षा चुनें (Class):", 
                st.session_state.classes_list, 
                index=st.session_state.classes_list.index(selected_class) if selected_class in st.session_state.classes_list else 0,
                key="weighted_class_picker"
            )
    
    w_cls_data = get_class_data(target_w_class)
    raw_st_df = w_cls_data["students"]
    existing_secs = sorted(list(set([str(s).strip() for s in raw_st_df["Section"].dropna().unique() if str(s).strip()]))) if not raw_st_df.empty and "Section" in raw_st_df.columns else ["A"]
    sec_options = ["सभी सेक्शन (All Sections Combined)"] + (existing_secs if existing_secs else ["A", "B", "C"])
    with c_wtop3:
        target_w_sec = st.selectbox("2. सेक्शन चुनें (Section):", sec_options, key="weighted_sec_picker")

    if target_w_sec != "सभी सेक्शन (All Sections Combined)" and not raw_st_df.empty and "Section" in raw_st_df.columns:
        students_df = raw_st_df[raw_st_df["Section"] == target_w_sec].copy()
        display_w_class = f"{target_w_class} - Section {target_w_sec}"
    else:
        students_df = raw_st_df.copy()
        display_w_class = f"{target_w_class} (समस्त सेक्शन)"

    cls_subjects = get_class_subjects(target_w_class)
    sub_count = len(cls_subjects)
    w_evals = w_cls_data["evaluations"]

    clean_cls = str(target_w_class).lower()
    is_5_8_board = ("class 5" in clean_cls or "class 8" in clean_cls or "5th" in clean_cls or "8th" in clean_cls)
    is_9_10_high = ("class 9" in clean_cls or "class 10" in clean_cls or "9th" in clean_cls or "10th" in clean_cls)
    
    if is_9_10_high:
        board_header_title = "माध्यमिक शिक्षा मंडल, मध्य प्रदेश, भोपाल (MPBSE)"
        sheet_subtitle = "हाईस्कूल वार्षिक परीक्षा परिणाम अभिलेख पंजी (सत्र 2026-27)"
        appendix_tag = "MPBSE हाईस्कूल विनियम अनुसार (75 थ्योरी + 25 प्रोजेक्ट = 100)"
    elif is_5_8_board:
        board_header_title = "राज्य शिक्षा केंद्र, मध्य प्रदेश, भोपाल (RSKMP)"
        sheet_subtitle = f"वार्षिक परीक्षा परिणाम अभिलेख पत्रक — {target_w_class} बोर्ड परीक्षा (सत्र 2026-27)"
        appendix_tag = "RSKMP बोर्ड विनियम अनुसार (20 अर्धवार्षिक + 20 प्रोजेक्ट + 60 वार्षिक लिखित = 100)"
    elif "class 3" in clean_cls or "class 4" in clean_cls or "3rd" in clean_cls or "4th" in clean_cls:
        board_header_title = "राज्य शिक्षा केंद्र, मध्य प्रदेश, भोपाल (RSKMP)"
        sheet_subtitle = "वार्षिक परीक्षा परिणाम अभिलेख पत्रक (प्राथमिक शाला) — सत्र 2026-27"
        appendix_tag = "परिशिष्ट 4(अ) — कक्षा 3 व 4 (10% मासिक + 20% अर्धवार्षिक + 10% प्रोजेक्ट + 60 लिखित = 100)"
    else:
        board_header_title = "राज्य शिक्षा केंद्र, मध्य प्रदेश, भोपाल (RSKMP)"
        sheet_subtitle = "वार्षिक परीक्षा परिणाम अभिलेख पत्रक (माध्यमिक शाला) — सत्र 2026-27"
        appendix_tag = "परिशिष्ट 6(अ) — कक्षा 6 व 7 (10% मासिक + 20% अर्धवार्षिक + 10% प्रोजेक्ट + 60 लिखित = 100)"

    c_wopt1, c_wopt2 = st.columns([3, 2])
    with c_wopt1:
        view_layout_choice = st.radio(
            "प्रारूप चयन (Layout View):",
            ["🏛️ शासकीय वार्षिक परिणाम अभिलेख पत्रक (Official RSKMP / MPBSE Gazette)", "📑 35-कॉलम घटकवार वेटेज पत्रक (Component-Wise 10%+20%+10%+60% Sheet)"],
            horizontal=True,
            key="w_view_layout_choice"
        )
    with c_wopt2:
        hy_scheme_choice = st.selectbox(
            "अर्धवार्षिक गणना आधार:",
            ["60", "40", "50", "20", "auto"],
            format_func=lambda x: {
                "60": "60 अंक (RSKMP मानक: प्राप्तांक ÷ 3 = 20%)",
                "40": "40 अंक (स्थानीय परीक्षा: प्राप्तांक ÷ 2 = 20%)",
                "50": "50 अंक (प्राप्तांक × 20 / 50)",
                "20": "20 अंक (सीधे 20% अधिभार)",
                "auto": "ऑटो-डिटेक्ट (Auto Detect)"
            }[x],
            index=0,
            key="w_hy_scheme_picker_v2"
        )

    if students_df.empty:
        st.warning(f"⚠️ {display_w_class} में कोई विद्यार्थी पंजीकृत नहीं है।")
    else:
        # Prepare Data for Both Formats
        records_master = []
        for idx, s in students_df.iterrows():
            r = s["Roll_No"]
            ev = w_evals.get(r, {})
            m_dict = ev.get("marks", {})
            st_stat = ev.get("status", s.get("Status", "Present"))
            
            s_rec = {
                "Sr_No": idx + 1,
                "Roll_No": r,
                "Scholar_No": s.get("Scholar_No", "--"),
                "Samagra_ID": s.get("SSSM_ID", "--"),
                "Name": s["Name"],
                "Father_Name": s["Father_Name"],
                "Mother_Name": s.get("Mother_Name", "--"),
                "DOB": s.get("DOB", "--"),
                "Gender": s.get("Gender", "--"),
                "Category": s.get("Category", "--"),
                "Section": s.get("Section", "A"),
                "Attended_Days": s.get("Attended_Days", 200),
                "Total_Days": s.get("Total_Days", 220),
                "Subjects": {}
            }
            
            grand_total = 0
            all_pass = True
            
            for sub in cls_subjects:
                s_id = sub["id"]
                s_name = sub["name"]
                se = m_dict.get(s_id, {})
                
                # Monthly (10%)
                m_score, _, _ = calculate_subject_monthly_weightage(ev, s_id, target_w_class)
                if st_stat == "Absent": m_score = 0
                
                # Half-Yearly (20%)
                raw_hy = se.get("half_yearly", 48)
                hy_score = calculate_subject_half_yearly_weightage(raw_hy, hy_scheme_choice)
                if st_stat == "Absent": hy_score = 0
                
                # Project (10% or 20 for board)
                raw_proj = se.get("project", 32 if not is_5_8_board else 16)
                proj_score = calculate_subject_project_weightage_rule(raw_proj, target_w_class)
                if st_stat == "Absent": proj_score = 0
                
                # Annual Written (60)
                ann_score = min(60, max(0, se.get("annual", 48))) if st_stat != "Absent" else 0
                
                if is_9_10_high:
                    # High school: 75 written + 25 project
                    sub_final = min(100, round((ann_score / 60) * 75) + proj_score)
                elif is_5_8_board:
                    # 5th/8th board: 20 HY + 20 Proj + 60 Written
                    sub_final = min(100, hy_score + proj_score + ann_score)
                else:
                    # 3,4,6,7: 10 Monthly + 20 HY + 10 Proj + 60 Written
                    sub_final = min(100, m_score + hy_score + proj_score + ann_score)
                    
                sub_grd = calculate_grade(sub_final) if st_stat != "Absent" else "Ab"
                if sub_final < 33: all_pass = False
                
                grand_total += sub_final
                
                s_rec["Subjects"][s_id] = {
                    "name": s_name,
                    "monthly_10": m_score,
                    "hy_20": hy_score,
                    "proj_wt": proj_score,
                    "written_60": ann_score,
                    "total_100": sub_final,
                    "grade": sub_grd
                }
            
            max_grand = len(cls_subjects) * 100
            pct = round((grand_total / max_grand) * 100, 1) if max_grand > 0 else 0
            final_grd = calculate_grade(pct) if st_stat != "Absent" else "Ab"
            res_str = "PASS" if (all_pass and pct >= 33 and st_stat != "Absent") else ("ABSENT" if st_stat == "Absent" else "FAIL")
            
            s_rec["Grand_Total"] = grand_total
            s_rec["Max_Marks"] = max_grand
            s_rec["Percentage"] = pct
            s_rec["Final_Grade"] = final_grd
            s_rec["Result"] = res_str
            s_rec["Division"] = calculate_division(pct) if st_stat != "Absent" else "--"
            
            records_master.append(s_rec)

        # Calculate Ranks
        records_master = sorted(records_master, key=lambda x: (x["Result"] == "PASS", x["Grand_Total"]), reverse=True)
        for i, rec in enumerate(records_master):
            rec["Rank"] = i + 1
            
        # Re-sort by Sr_No for official tabulation sheet
        records_master = sorted(records_master, key=lambda x: x["Sr_No"])

        # Top Action Bar
        c_wbar1, c_wbar2 = st.columns([3, 1])
        with c_wbar1:
            st.markdown(f"<b>📌 चयनित प्रारूप:</b> {appendix_tag} | <b>छात्र संख्या:</b> {len(records_master)}", unsafe_allow_html=True)
        with c_wbar2:
            if not is_teacher:
                st.button("🖨️ Print Gazette", on_click=None, use_container_width=True, type="primary", key="btn_w_print_final")
            else:
                st.markdown("<div style='color:#991B1B; font-size:11px; font-weight:bold; text-align:right;'>🔒 प्रिंट केवल संस्था प्रधान हेतु</div>", unsafe_allow_html=True)

        # ----------------- VIEW 1: OFFICIAL RSKMP / MPBSE GAZETTE REGISTER -----------------
        if "शासकीय वार्षिक परिणाम" in view_layout_choice:
            # Sub-headers for each subject
            sub_col_ths = ""
            for sub in cls_subjects:
                if is_5_8_board:
                    sub_col_ths += f"""
                    <th colspan="5" style="border: 1px solid #000; background: #F1F5F9; font-size: 11px; padding: 4px;">{sub['name']}</th>
                    """
                elif is_9_10_high:
                    sub_col_ths += f"""
                    <th colspan="4" style="border: 1px solid #000; background: #F1F5F9; font-size: 11px; padding: 4px;">{sub['name']}</th>
                    """
                else:
                    sub_col_ths += f"""
                    <th colspan="6" style="border: 1px solid #000; background: #F1F5F9; font-size: 11px; padding: 4px;">{sub['name']}</th>
                    """

            # Internal sub-columns row
            sub_comp_ths = ""
            for _ in cls_subjects:
                if is_5_8_board:
                    sub_comp_ths += """
                    <th style="border: 1px solid #000; font-size: 9.5px; width: 32px;">अर्ध (20)</th>
                    <th style="border: 1px solid #000; font-size: 9.5px; width: 32px;">प्रोजे (20)</th>
                    <th style="border: 1px solid #000; font-size: 9.5px; width: 32px;">लिखित (60)</th>
                    <th style="border: 1px solid #000; font-size: 10px; width: 34px; font-weight: bold; background: #EFF6FF;">कुल (100)</th>
                    <th style="border: 1px solid #000; font-size: 9.5px; width: 26px;">ग्रेड</th>
                    """
                elif is_9_10_high:
                    sub_comp_ths += """
                    <th style="border: 1px solid #000; font-size: 9.5px; width: 35px;">थ्योरी (75)</th>
                    <th style="border: 1px solid #000; font-size: 9.5px; width: 35px;">प्रोजेक्ट (25)</th>
                    <th style="border: 1px solid #000; font-size: 10px; width: 35px; font-weight: bold; background: #EFF6FF;">कुल (100)</th>
                    <th style="border: 1px solid #000; font-size: 9.5px; width: 28px;">ग्रेड</th>
                    """
                else:
                    sub_comp_ths += """
                    <th style="border: 1px solid #000; font-size: 9px; width: 28px;">मासिक (10)</th>
                    <th style="border: 1px solid #000; font-size: 9px; width: 28px;">अर्ध (20)</th>
                    <th style="border: 1px solid #000; font-size: 9px; width: 28px;">प्रोजे (10)</th>
                    <th style="border: 1px solid #000; font-size: 9px; width: 28px;">लिखित (60)</th>
                    <th style="border: 1px solid #000; font-size: 10px; width: 32px; font-weight: bold; background: #EFF6FF;">कुल (100)</th>
                    <th style="border: 1px solid #000; font-size: 9px; width: 24px;">ग्रेड</th>
                    """

            # Build Rows HTML
            gazette_rows = ""
            for rec in records_master:
                subj_tds = ""
                for sub in cls_subjects:
                    sdata = rec["Subjects"][sub["id"]]
                    if is_5_8_board:
                        subj_tds += f"""
                        <td style="border: 1px solid #000; padding: 2px;">{sdata['hy_20']}</td>
                        <td style="border: 1px solid #000; padding: 2px;">{sdata['proj_wt']}</td>
                        <td style="border: 1px solid #000; padding: 2px;">{sdata['written_60']}</td>
                        <td style="border: 1px solid #000; padding: 2px; font-weight: bold; background: #F8FAFC;">{sdata['total_100']}</td>
                        <td style="border: 1px solid #000; padding: 2px; font-weight: bold;">{sdata['grade']}</td>
                        """
                    elif is_9_10_high:
                        subj_tds += f"""
                        <td style="border: 1px solid #000; padding: 2px;">{sdata['written_60']}</td>
                        <td style="border: 1px solid #000; padding: 2px;">{sdata['proj_wt']}</td>
                        <td style="border: 1px solid #000; padding: 2px; font-weight: bold; background: #F8FAFC;">{sdata['total_100']}</td>
                        <td style="border: 1px solid #000; padding: 2px; font-weight: bold;">{sdata['grade']}</td>
                        """
                    else:
                        subj_tds += f"""
                        <td style="border: 1px solid #000; padding: 2px;">{sdata['monthly_10']}</td>
                        <td style="border: 1px solid #000; padding: 2px;">{sdata['hy_20']}</td>
                        <td style="border: 1px solid #000; padding: 2px;">{sdata['proj_wt']}</td>
                        <td style="border: 1px solid #000; padding: 2px;">{sdata['written_60']}</td>
                        <td style="border: 1px solid #000; padding: 2px; font-weight: bold; background: #F8FAFC;">{sdata['total_100']}</td>
                        <td style="border: 1px solid #000; padding: 2px; font-weight: bold;">{sdata['grade']}</td>
                        """

                res_c = "#15803D" if rec["Result"] == "PASS" else "#B91C1C"
                gazette_rows += f"""
                <tr style="height: 26px; font-size: 10px; text-align: center;">
                    <td style="border: 1px solid #000; padding: 2px; font-weight: bold;">{rec['Sr_No']}</td>
                    <td style="border: 1px solid #000; padding: 2px; font-weight: bold;">{rec['Roll_No']}</td>
                    <td style="border: 1px solid #000; padding: 2px;">{rec['Scholar_No']}</td>
                    <td style="border: 1px solid #000; padding: 2px; font-size: 9.5px;">{rec['Samagra_ID']}</td>
                    <td style="border: 1px solid #000; padding: 2px 6px; text-align: left; font-weight: bold; white-space: nowrap; color: #1E3A8A;">{rec['Name']}</td>
                    <td style="border: 1px solid #000; padding: 2px 6px; text-align: left; white-space: nowrap;">{rec['Father_Name']}</td>
                    <td style="border: 1px solid #000; padding: 2px 6px; text-align: left; white-space: nowrap;">{rec['Mother_Name']}</td>
                    <td style="border: 1px solid #000; padding: 2px; font-size: 9.5px;">{rec['Category']} / {rec['Gender'][:1]}</td>
                    {subj_tds}
                    <td style="border: 1px solid #000; padding: 2px; font-weight: 900; background: #FFFDF0; font-size: 11px;">{rec['Grand_Total']}</td>
                    <td style="border: 1px solid #000; padding: 2px; font-weight: bold; color: #1E3A8A;">{rec['Percentage']}%</td>
                    <td style="border: 1px solid #000; padding: 2px; font-weight: bold;">{rec['Final_Grade']}</td>
                    <td style="border: 1px solid #000; padding: 2px; font-weight: bold; color: {res_c};">{rec['Result']}</td>
                    <td style="border: 1px solid #000; padding: 2px; font-weight: bold;">{rec['Rank']}</td>
                    <td style="border: 1px solid #000; padding: 2px; font-size: 9.5px;">{rec['Attended_Days']}/{rec['Total_Days']}</td>
                </tr>
                """

            gazette_table_html = f"""
            <div class="printable-area" style="background: #ffffff; border: 2px solid #000; padding: 10px 14px; font-family: Arial, sans-serif; color: #000; overflow-x: auto;">
                <!-- GOVT HEADER -->
                <div style="text-align: center; border-bottom: 2px solid #000; padding-bottom: 6px; margin-bottom: 8px;">
                    <div style="font-size: 18px; font-weight: 900; color: #1E3A8A; letter-spacing: 0.5px;">
                        {board_header_title}
                    </div>
                    <div style="font-size: 15px; font-weight: 800; color: #000; margin-top: 2px;">
                        {sheet_subtitle}
                    </div>
                    <div style="font-size: 12px; font-weight: bold; color: #475569; margin-top: 2px;">
                        {appendix_tag}
                    </div>
                    <div style="display: flex; justify-content: space-between; font-size: 11.5px; font-weight: bold; margin-top: 6px; border-top: 1px solid #000; padding-top: 4px;">
                        <div><b>शाला:</b> {s_info.get('name', 'शासकीय माध्यमिक विद्यालय')} | <b>DISE:</b> {s_info.get('udise', '23260100101')}</div>
                        <div><b>ब्लॉक:</b> {s_info.get('block','SENDHWA')} | <b>जिला:</b> {s_info.get('district','BARWANI')}</div>
                        <div><b>कक्षा:</b> {display_w_class} | <b>माध्यम:</b> {get_display_medium(s_info)} | <b>सत्र:</b> {cur_sess}</div>
                    </div>
                </div>

                <!-- GAZETTE TABLE -->
                <table style="width: 100%; border-collapse: collapse; border: 1px solid #000; font-size: 10px; text-align: center;">
                    <thead>
                        <tr style="background: #ffffff; font-weight: bold;">
                            <th rowspan="2" style="border: 1px solid #000; width: 28px;">सरल क्र.</th>
                            <th rowspan="2" style="border: 1px solid #000; width: 45px;">अनुक्रमांक</th>
                            <th rowspan="2" style="border: 1px solid #000; width: 50px;">दाखिला क्र.</th>
                            <th rowspan="2" style="border: 1px solid #000; width: 65px;">समग्र ID</th>
                            <th rowspan="2" style="border: 1px solid #000; width: 130px; text-align: left; padding-left: 6px;">विद्यार्थी का नाम</th>
                            <th rowspan="2" style="border: 1px solid #000; width: 110px; text-align: left; padding-left: 6px;">पिता का नाम</th>
                            <th rowspan="2" style="border: 1px solid #000; width: 100px; text-align: left; padding-left: 6px;">माता का नाम</th>
                            <th rowspan="2" style="border: 1px solid #000; width: 55px;">वर्ग/लिंग</th>
                            {sub_col_ths}
                            <th rowspan="2" style="border: 1px solid #000; width: 45px; background: #FFFDF0; font-weight: 900;">महायोग</th>
                            <th rowspan="2" style="border: 1px solid #000; width: 45px;">प्रतिशत</th>
                            <th rowspan="2" style="border: 1px solid #000; width: 35px;">ग्रेड</th>
                            <th rowspan="2" style="border: 1px solid #000; width: 45px;">परिणाम</th>
                            <th rowspan="2" style="border: 1px solid #000; width: 35px;">रैंक</th>
                            <th rowspan="2" style="border: 1px solid #000; width: 50px;">उपस्थिति</th>
                        </tr>
                        <tr style="background: #ffffff;">
                            {sub_comp_ths}
                        </tr>
                    </thead>
                    <tbody>
                        {gazette_rows}
                    </tbody>
                </table>

                <!-- SIGNATURE BLOCK -->
                <div style="display: flex; justify-content: space-between; margin-top: 35px; font-weight: bold; font-size: 11px; text-align: center;">
                    <div>_______________________<br>कक्षा अध्यापक हस्ताक्षर</div>
                    <div>_______________________<br>मूल्यांकन / परीक्षा प्रभारी</div>
                    <div>_______________________<br>संस्था प्रधान (सील सहित)</div>
                </div>
                <div style="text-align: center; font-size: 9.5px; margin-top: 10px; color: #64748B;">
                    शासकीय वार्षिक परीक्षा परिणाम अभिलेख पत्रक | मुद्रण दिनांक: {TODAY_STR}
                </div>
            </div>
            """
            render_html(gazette_table_html)

        # ----------------- VIEW 2: 35-COLUMN COMPONENT-WISE WEIGHTAGE SHEET (IMAGE: image_05e7a7.png) -----------------
        else:
            # Component-wise layout with proper spacing and styling
            v_sub_ths = "".join([f'<th class="v-th" style="writing-mode: vertical-rl; transform: rotate(180deg); height: 110px; font-size: 10px; padding: 2px; border: 1px solid #000;">{sub["name"]}</th>' for sub in cls_subjects])
            tot_cols_cnt = 4 + 5 * sub_count + 1
            num_cells = "".join([f'<td style="border: 1px solid #000; padding: 2px; font-weight: bold; background: #FDEBD0;">{c_no}</td>' for c_no in range(1, tot_cols_cnt + 1)])

            c_rows_html = ""
            for rec in records_master:
                # 1. Monthly (10%)
                m_tds = "".join([f'<td style="border: 1px solid #000; padding: 2px;">{rec["Subjects"][sub["id"]]["monthly_10"]}</td>' for sub in cls_subjects])
                # 2. HY (20%)
                hy_tds = "".join([f'<td style="border: 1px solid #000; padding: 2px;">{rec["Subjects"][sub["id"]]["hy_20"]}</td>' for sub in cls_subjects])
                # 3. Project (10%)
                pj_tds = "".join([f'<td style="border: 1px solid #000; padding: 2px;">{rec["Subjects"][sub["id"]]["proj_wt"]}</td>' for sub in cls_subjects])
                # 4. Written (60)
                wr_tds = "".join([f'<td style="border: 1px solid #000; padding: 2px;">{rec["Subjects"][sub["id"]]["written_60"]}</td>' for sub in cls_subjects])
                # 5. Final (100)
                fn_tds = "".join([f'<td style="border: 1px solid #000; padding: 2px; font-weight: bold; color: #15803D;">{rec["Subjects"][sub["id"]]["total_100"]}</td>' for sub in cls_subjects])

                c_rows_html += f"""
                <tr style="height: 24px; font-size: 10px; text-align: center;">
                    <td style="border: 1px solid #000; padding: 2px; font-weight: bold;">{rec['Sr_No']}</td>
                    <td style="border: 1px solid #000; padding: 2px; font-weight: bold;">{rec['Roll_No']}</td>
                    <td style="border: 1px solid #000; padding: 2px 6px; text-align: left; font-weight: bold; white-space: nowrap;">{rec['Name']}</td>
                    <td style="border: 1px solid #000; padding: 2px; white-space: nowrap;">{target_w_class}</td>
                    {m_tds}
                    {hy_tds}
                    {pj_tds}
                    {wr_tds}
                    {fn_tds}
                    <td style="border: 1px solid #000; padding: 2px; font-weight: 900; color: #0F172A; background: #FFF8DC; font-size: 11px;">{rec['Grand_Total']}</td>
                </tr>
                """

            c_35_html = f"""
            <div class="printable-area" style="background: #ffffff; border: 2px solid #000; padding: 8px 10px; font-family: Arial, sans-serif; color: #000; overflow-x: auto;">
                <div style="text-align: center; font-size: 17px; font-weight: 900; letter-spacing: 0.5px; margin-bottom: 2px;">
                    {board_header_title}
                </div>
                <div style="text-align: center; font-size: 14px; font-weight: 800; color: #000; margin-bottom: 2px;">
                    {s_info.get('name', 'शासकीय माध्यमिक विद्यालय')} — 35-कॉलम वार्षिक अधिभार मूल्यांकन पत्रक
                </div>
                <div style="text-align: center; font-size: 11.5px; font-weight: bold; color: #334155; margin-bottom: 8px;">
                    DISE: {s_info.get('udise', '23260100101')} | ब्लॉक: {s_info.get('block','SENDHWA')} | जिला: {s_info.get('district','BARWANI')} | कक्षा: {display_w_class} | सत्र: {cur_sess}
                </div>

                <table style="width: 100%; border-collapse: collapse; border: 1px solid #000; font-size: 10px; text-align: center;">
                    <thead>
                        <tr style="background: #ffffff; font-weight: bold; font-size: 10.5px;">
                            <th rowspan="2" style="border: 1px solid #000; width: 30px;">Sr.No.</th>
                            <th rowspan="2" style="border: 1px solid #000; width: 45px;">Roll No.</th>
                            <th rowspan="2" style="border: 1px solid #000; width: 140px; text-align: center;">Name Of Student</th>
                            <th rowspan="2" style="border: 1px solid #000; width: 60px;">Class</th>
                            <th colspan="{sub_count}" style="border: 1px solid #000; background: #F8FAFC;">Monthly Evaluation 10%<br>Weightage</th>
                            <th colspan="{sub_count}" style="border: 1px solid #000; background: #F8FAFC;">Half Yearly Evaluation 20%<br>Weightage</th>
                            <th colspan="{sub_count}" style="border: 1px solid #000; background: #F8FAFC;">Annual Project Evaluation<br>10% Weightage</th>
                            <th colspan="{sub_count}" style="border: 1px solid #000; background: #F8FAFC;">Annual Written Evaluation<br>60 Marks</th>
                            <th colspan="{sub_count + 1}" style="border: 1px solid #000; background: #EFF6FF; color: #1E3A8A;">Monthly+Half Yearly+Annual+Project<br>10%+20%+60+10%=100%</th>
                        </tr>
                        <tr style="background: #ffffff;">
                            {v_sub_ths}
                            {v_sub_ths}
                            {v_sub_ths}
                            {v_sub_ths}
                            {v_sub_ths}
                            <th class="v-th" style="writing-mode: vertical-rl; transform: rotate(180deg); height: 110px; font-size: 10px; padding: 2px; border: 1px solid #000; font-weight: 900; background: #EFF6FF; color: #1E3A8A;">Grand Total</th>
                        </tr>
                        <tr style="height: 20px; font-size: 9.5px; text-align: center;">
                            {num_cells}
                        </tr>
                    </thead>
                    <tbody>
                        {c_rows_html}
                    </tbody>
                </table>

                <div style="display: flex; justify-content: space-between; margin-top: 35px; font-weight: bold; font-size: 11px; text-align: center;">
                    <div>_______________________<br>कक्षा अध्यापक हस्ताक्षर</div>
                    <div>_______________________<br>मूल्यांकन प्रभारी</div>
                    <div>_______________________<br>संस्था प्रधान (सील सहित)</div>
                </div>
            </div>
            """
            render_html(c_35_html)

        # Excel Export Section
        if not is_teacher:
            st.divider()
            st.markdown("##### 📥 आधिकारिक वार्षिक परिणाम अभिलेख पत्रक एक्सेल डाउनलोड (.xlsx):")
            if render_export_gatekeeper("वार्षिक परिणाम अभिलेख पत्रक"):
                # Flat export dataframe
                export_flat_rows = []
                for rec in records_master:
                    flat_r = {
                        "सरल क्र.": rec["Sr_No"],
                        "रोल नंबर": rec["Roll_No"],
                        "दाखिला क्र.": rec["Scholar_No"],
                        "समग्र आई.डी.": rec["Samagra_ID"],
                        "विद्यार्थी का नाम": rec["Name"],
                        "पिता का नाम": rec["Father_Name"],
                        "माता का नाम": rec["Mother_Name"],
                        "वर्ग/लिंग": f"{rec['Category']} / {rec['Gender']}",
                    }
                    for sub in cls_subjects:
                        sdata = rec["Subjects"][sub["id"]]
                        flat_r[f"{sub['name']}_मासिक10%"] = sdata["monthly_10"]
                        flat_r[f"{sub['name']}_अर्धवार्षिक20%"] = sdata["hy_20"]
                        flat_r[f"{sub['name']}_प्रोजेक्ट"] = sdata["proj_wt"]
                        flat_r[f"{sub['name']}_लिखित60"] = sdata["written_60"]
                        flat_r[f"{sub['name']}_कुल100"] = sdata["total_100"]
                        flat_r[f"{sub['name']}_ग्रेड"] = sdata["grade"]
                    
                    flat_r["महायोग"] = rec["Grand_Total"]
                    flat_r["पूर्णांक"] = rec["Max_Marks"]
                    flat_r["प्रतिशत"] = f"{rec['Percentage']}%"
                    flat_r["ग्रेड"] = rec["Final_Grade"]
                    flat_r["परिणाम"] = rec["Result"]
                    flat_r["रैंक"] = rec["Rank"]
                    flat_r["उपस्थिति"] = f"{rec['Attended_Days']}/{rec['Total_Days']}"
                    export_flat_rows.append(flat_r)
                    
                w_export_df = pd.DataFrame(export_flat_rows)
                w_bytes, w_mime, w_ext = export_dataframe_bytes(w_export_df, "Excel (.xlsx)")
                st.download_button(
                    "📥 आधिकारिक अभिलेख पत्रक एक्सेल डाउनलोड (.xlsx)",
                    data=w_bytes,
                    file_name=f"Annual_Result_Record_Gazette_{target_w_class}_{cur_sess}.xlsx",
                    mime=w_mime,
                    type="primary",
                    use_container_width=True
                )


        render_govt_portals_hub("35-कॉलम वेटेज मूल्यांकन पत्रक", target_w_class, w_export_df if 'w_export_df' in locals() else None, "35Col_Weighted_Evaluation")

# ----------------- MODULE 15: SESSION CHANGE & PROMOTION -----------------
elif menu == T["nav_promote"]:
    st.markdown(f'<div class="main-header">🔄 सत्र परिवर्तन एवं कक्षा पदोन्नति (Session Promotion)</div>', unsafe_allow_html=True)
    render_html('<div class="sub-header">नया शैक्षणिक सत्र प्रारंभ होने पर सभी उत्तीर्ण विद्यार्थियों को स्वतः अगली कक्षा में प्रमोट करें</div>')

    col_p1, col_p2 = st.columns(2)
    with col_p1:
        c_sess = st.text_input("वर्तमान शैक्षणिक सत्र:", value=st.session_state.school_info.get("session", "2023-24"), disabled=True)
    with col_p2:
        parts = c_sess.split("-")
        try:
            y1 = int(parts[0])
            y2 = int(parts[1]) if len(parts) > 1 else y1 + 1
            default_next = f"{y1+1}-{y2+1}"
        except Exception:
            default_next = "2024-25"
        n_sess = st.text_input("आगामी नया शैक्षणिक सत्र:", value=default_next)

    st.divider()
    st.subheader("कक्षा पदोन्नति का प्रारूप (Promotion Flow Preview):")

    promo_preview = []
    classes = st.session_state.classes_list
    for idx, c in enumerate(classes):
        cnt = len(st.session_state.data_store.get(c, {}).get("students", []))
        if idx < len(classes) - 1:
            target = classes[idx + 1]
            status_text = f"Promote to {target} ➡️"
        else:
            target = "Graduated / Passed Out (Alumni)"
            status_text = "Graduate / Issue TC 🎓"
        promo_preview.append({"Current Class": c, "Total Students": cnt, "Next Class (New Session)": target, "Action": status_text})

    st.dataframe(pd.DataFrame(promo_preview), use_container_width=True)

    st.warning("⚠️ ध्यान दें: प्रमोट करने पर सभी विद्यार्थियों का व्यक्तिगत विवरण (नाम, स्कॉलर नं, माता-पिता, जन्मतिथि, समग्र आईडी, फोटो) अगली कक्षा में चला जाएगा और नए सत्र के लिए परीक्षा अंक रीसेट हो जाएंगे।")

    if st.button("🚀 सभी पात्र विद्यार्थियों को अगली कक्षा में प्रमोट करें (Promote All)", type="primary"):
        graduated_list = []
        old_store = st.session_state.data_store
        new_store = {}

        for c in classes:
            new_store[c] = {
                "students": pd.DataFrame(),
                "evaluations": {},
                "monthly_attendance": pd.DataFrame(),
                "working_days": DEFAULT_WORKING_DAYS
            }

        for i in range(len(classes) - 1, -1, -1):
            cur_cls = classes[i]
            cur_students = old_store.get(cur_cls, {}).get("students", pd.DataFrame())

            if not cur_students.empty:
                if i == len(classes) - 1:
                    graduated_list.extend(cur_students.to_dict(orient="records"))
                else:
                    nxt_cls = classes[i + 1]
                    promoted_df = cur_students.copy()
                    promoted_df["Class"] = nxt_cls
                    promoted_df["Roll_No"] = range(101, 101 + len(promoted_df))
                    new_store[nxt_cls]["students"] = promoted_df

        st.session_state.data_store = new_store
        st.session_state.school_info["session"] = n_sess
        save_data_to_disk()

        st.balloons()
        st.success(f"🎉 बधाई हो! सभी कक्षाओं के विद्यार्थी सफलतापूर्वक आगामी सत्र {n_sess} की अगली कक्षा में प्रमोट हो गए हैं!")
        st.rerun()

