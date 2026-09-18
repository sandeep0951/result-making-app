import streamlit as st
import pandas as pd
import numpy as np
import json, base64, os, hashlib, urllib.parse, re
from io import BytesIO
from datetime import datetime, date

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
            h = se.get("half_yearly", 16 if has_proj_comp else 32)
            p = se.get("project", 16) if has_proj_comp else 0
            a = se.get("annual", 48)
            t = se.get("total", (h + p + a) if has_proj_comp else (h + a))
            tot_m += t
            if has_proj_comp:
                if h < 7 or p < 7 or a < 20 or t < 33:
                    all_pass = False
            else:
                if h < 13 or a < 20 or t < 33:
                    all_pass = False
            
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
        
        co = ev.get("co_curricular", {})
        for k, _ in CO_CURRICULAR_ACTIVITIES:
            row[k] = co.get(k, "A")
            
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
    """Generates the exact 44-column master tabulation sheet"""
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
        for i, sub in enumerate(cls_subjects):
            s_eval = m_dict.get(sub["id"], {})
            row[f"{12+i}_HY_{sub['name']}"] = s_eval.get("half_yearly", 32)
        for i, sub in enumerate(cls_subjects):
            s_eval = m_dict.get(sub["id"], {})
            row[f"{16+i}_Annual_{sub['name']}"] = s_eval.get("annual", 48)
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
        
        co = ev.get("co_curricular", {})
        row["30_LITERARY_SKILLS"] = co.get("LITERARY_SKILLS", "A")
        row["31_SCIENTIFIC_SKILLS"] = co.get("SCIENTIFIC_SKILLS", "A")
        row["32_CULTURAL_SKILLS"] = co.get("CULTURAL_SKILLS", "A")
        row["33_CREATIVITY"] = co.get("CREATIVITY", "A")
        row["34_SPORTS"] = co.get("SPORTS", "A")
        
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

# ----------------- CUSTOM CSS FOR BEAUTIFUL UI, DEVANAGARI FONTS & PRINTING (A4 & A3) -----------------
render_html("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+Devanagari:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
<style>
    /* Universal Devanagari Hindi font enforcement preventing Tofu squares */
    html, body, [class*="css"], div, span, label, input, button, select, textarea, table, th, td, h1, h2, h3, h4, h5, h6 {
        font-family: 'Noto Sans Devanagari', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif !important;
    }
    .main-header {
        font-size: 25px;
        font-weight: 800;
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
        color: #000;
        width: 100%;
        overflow-x: auto;
        -webkit-overflow-scrolling: touch;
    }
    .a3-table th {
        background-color: #f8fafc;
        font-weight: bold;
    }
    @media print {
        body * {
            visibility: hidden !important;
        }
        .printable-area, .printable-area * {
            visibility: visible !important;
        }
        .printable-area {
            position: absolute !important;
            left: 0 !important;
            top: 0 !important;
            width: 100% !important;
            margin: 0 !important;
            padding: 0 !important;
            border: none !important;
        }
        .no-print, header, footer, [data-testid="stHeader"], [data-testid="stSidebar"] {
            display: none !important;
        }
        @page {
            size: auto;
            margin: 6mm;
        }
    }
</style>
""")

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

def render_govt_portals_hub(tab_title, target_class, export_df=None, default_file_name="Portal_Upload"):
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

    c_p1, c_p2, c_p3, c_p4 = st.columns(4)
    with c_p1:
        st.markdown('<a href="https://www.rskmp.in" target="_blank" style="text-decoration: none;"><div style="background: #1E3A8A; color: white; padding: 8px 10px; border-radius: 6px; text-align: center; font-size: 12px; font-weight: bold;">🏛️ RSKMP पोर्टल (rskmp.in)</div></a>', unsafe_allow_html=True)
    with c_p2:
        st.markdown('<a href="https://mpbse.mponline.gov.in" target="_blank" style="text-decoration: none;"><div style="background: #D97706; color: white; padding: 8px 10px; border-radius: 6px; text-align: center; font-size: 12px; font-weight: bold;">🏢 MPBSE पोर्टल (MP Online)</div></a>', unsafe_allow_html=True)
    with c_p3:
        st.markdown('<a href="https://shikshaportal.mp.gov.in" target="_blank" style="text-decoration: none;"><div style="background: #0D9488; color: white; padding: 8px 10px; border-radius: 6px; text-align: center; font-size: 12px; font-weight: bold;">📚 समग्र शिक्षा पोर्टल (MP)</div></a>', unsafe_allow_html=True)
    with c_p4:
        st.markdown('<a href="https://www.vimarsh.mp.gov.in" target="_blank" style="text-decoration: none;"><div style="background: #4F46E5; color: white; padding: 8px 10px; border-radius: 6px; text-align: center; font-size: 12px; font-weight: bold;">🎯 विमर्श पोर्टल (DPI MP)</div></a>', unsafe_allow_html=True)

    c_hub_left, c_hub_right = st.columns([1.5, 1.5])
    with c_hub_left:
        with st.expander("🚀 डायरेक्ट पोर्टल पर डेटा अपलोड / प्रेषण (बिना OTP के)", expanded=True):
            st.markdown(f"**कक्षा:** `{target_class}` | **माड्यूल:** `{tab_title}`")
            target_portal_url = "https://www.rskmp.in" if not is_9_10 else "https://mpbse.mponline.gov.in"
            target_portal_name = "RSKMP (rskmp.in)" if not is_9_10 else "MPBSE MP Online"
            st.markdown(f'<a href="{target_portal_url}" target="_blank" style="text-decoration: none;"><div style="background: #15803D; color: white; padding: 10px 14px; border-radius: 6px; text-align: center; font-weight: bold; font-size: 13px; margin: 6px 0;">🌐 सीधे {target_portal_name} खोलें एवं डेटा प्रेषित करें ↗</div></a>', unsafe_allow_html=True)
            st.caption("ℹ️ इस विकल्प के लिए OTP की आवश्यकता नहीं है। शिक्षक या संस्था प्रधान सीधे पोर्टल लॉगिन कर डेटा अपलोड कर सकते हैं।")
            if export_df is not None and not export_df.empty:
                show_payload = st.checkbox("📋 1-क्लिक डेटा पेलोड देखें / कॉपी करें (Portal Fast Upload)", value=False, key=f"chk_payload_{tab_title}_{target_class}")
                if show_payload:
                    csv_preview = export_df.to_csv(index=False)
                    st.text_area("पोर्टल हेतु तैयार डेटा (CSV / Copy-Paste Text):", value=csv_preview, height=120, key=f"ta_payload_{tab_title}_{target_class}")

    with c_hub_right:
        with st.expander("📥 कंप्यूटर में बल्क अपलोड फ़ाइल डाउनलोड (केवल Principal हेतु - OTP सुरक्षित)", expanded=True):
            if is_teacher:
                st.markdown('<div style="background: #FEF2F2; border-left: 4px solid #EF4444; padding: 10px 14px; border-radius: 6px; color: #991B1B; font-size: 12px; margin: 6px 0;"><b>🔒 शासकीय डेटा सुरक्षा सूचना:</b> फ़ाइल डाउनलोड केवल <b>संस्था प्रधान (Principal)</b> खाते में अधिकृत है।</div>', unsafe_allow_html=True)
            else:
                st.markdown("<span style='font-size: 12px; color: #334155;'>पोर्टल पर ऑफलाइन बल्क अपलोड हेतु Excel/CSV फ़ाइल अपने कंप्यूटर में डाउनलोड करें:</span>", unsafe_allow_html=True)
                if export_df is not None and not export_df.empty:
                    if render_export_gatekeeper(f"{tab_title} फ़ाइल डाउनलोड"):
                        c_dw1, c_dw2 = st.columns(2)
                        with c_dw1:
                            x_bytes, x_mime, x_ext = export_dataframe_bytes(export_df, "Excel (.xlsx)")
                            st.download_button("📥 एक्सेल फ़ाइल (.xlsx)", data=x_bytes, file_name=f"{default_file_name}_{target_class}_{cur_sess}.xlsx", mime=x_mime, type="primary", use_container_width=True, key=f"btn_dw_xlsx_{tab_title}_{target_class}")
                        with c_dw2:
                            c_bytes, c_mime, c_ext = export_dataframe_bytes(export_df, "CSV (.csv)")
                            st.download_button("📥 CSV फ़ाइल (.csv)", data=c_bytes, file_name=f"{default_file_name}_{target_class}_{cur_sess}.csv", mime=c_mime, use_container_width=True, key=f"btn_dw_csv_{tab_title}_{target_class}")
                else:
                    st.caption("⚠️ इस कक्षा में अभी कोई डेटा उपलब्ध नहीं है।")

def render_export_gatekeeper(context_label="Data Export"):
    role = st.session_state.get("authenticated_role", "PRINCIPAL")
    if role == "TEACHER":
        render_html('<div style="background: #FEF2F2; border-left: 4px solid #EF4444; padding: 12px 16px; border-radius: 6px; color: #991B1B; margin: 10px 0;"><b>🔒 शासकीय डेटा सुरक्षा सूचना:</b> बल्क डेटा एवं आधिकारिक शासकीय परीक्षाफल एक्सपोर्ट का अधिकार केवल <b>संस्था प्रधान (Principal)</b> खाते में अधिकृत है।</div>')
        return False
    auth_school = st.session_state.get("authenticated_school") or {}
    if not st.session_state.get("export_otp_verified", False):
        render_html('<div style="background: #EFF6FF; border: 1px solid #BFDBFE; padding: 10px 14px; border-radius: 6px; margin-bottom: 10px;"><b style="color: #1E3A8A; font-size: 13.5px;">🔒 अधिकृत एक्सपोर्ट सुरक्षा सत्यापन (DPDP Act 2023 Compliance)</b><br><span style="font-size: 12px; color: #334155;">संस्था प्रधान के अधिकृत मोबाइल पर 6-अंकीय OTP सत्यापन एवं कानूनी दायित्व स्वीकार करना अनिवार्य है।</span></div>')
        c_gk1, c_gk2 = st.columns([1.5, 3])
        with c_gk1:
            exp_otp = st.text_input("6-अंकीय एक्सपोर्ट OTP:*", value="888999", key=f"gk_otp_{context_label}", help="परीक्षण हेतु डिफॉल्ट OTP: 888999")
        with c_gk2:
            render_html("<div style='margin-top: 15px;'>")
            exp_consent = st.checkbox("✅ मैं प्रमाणित करता हूँ कि यह डेटा विद्यालय के अधिकृत उपयोग हेतु डाउनलोड किया जा रहा है।", value=True, key=f"gk_chk_{context_label}")
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
        render_html("<div style='color: #15803D; font-size: 12.5px; font-weight: bold; margin-bottom: 8px;'>🟢 एक्सपोर्ट अधिकृत (OTP सत्यापित) | डिजिटल ऑडिट लॉग सक्रिय</div>")
        return True

# ----------------- MONTHLY EVALUATION SCHEDULE & WEIGHTAGE ENGINE -----------------
def smart_match_subject_col(col_name, sub_name, sub_id):
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
    try:
        fname = uploaded_file.name.lower()
        if fname.endswith(".csv"):
            return pd.read_csv(uploaded_file)
        else:
            return pd.read_excel(uploaded_file)
    except Exception:
        return None

def get_class_monthly_test_months(cls_name):
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
        return [
            {"id": "aug", "name": "माह 1: अगस्त (August) - 10 अंक"},
            {"id": "sep", "name": "माह 2: सितम्बर (September) - 10 अंक"},
            {"id": "dec", "name": "माह 3: दिसम्बर (December) - 10 अंक"},
            {"id": "jan", "name": "माह 4: जनवरी (January) - 10 अंक"}
        ]

def calculate_subject_project_weightage_rule(raw_proj, cls_name="Class 7th"):
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
        if raw_proj <= 10:
            return int(raw_proj)
        elif raw_proj <= 20:
            return min(10, max(0, round((raw_proj / 20) * 10)))
        elif raw_proj <= 40:
            return min(10, max(0, round((raw_proj / 40) * 10)))
        else:
            return min(10, max(0, round((raw_proj / 100) * 10)))

def calculate_subject_quarterly_weightage(raw_q, max_q=75):
    """Calculates MPBSE 5% statutory weightage for Class 9th & 10th (max 5 marks).
    Formula: round((raw_marks / max_marks) * 5), bounded between 0 and 5.
    """
    try:
        raw_val = float(raw_q)
    except (ValueError, TypeError):
        return 0
    if raw_val <= 0:
        return 0
    max_val = max(1.0, float(max_q))
    w = round((raw_val / max_val) * 5.0)
    return int(min(5, max(0, w)))

def calculate_subject_half_yearly_weightage(raw_hy, hy_max_scheme="auto"):
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
        if raw_hy <= 20:
            return int(raw_hy)
        elif raw_hy <= 40:
            return min(20, max(0, round((raw_hy / 40) * 20)))
        elif raw_hy <= 60:
            return min(20, max(0, round((raw_hy / 60) * 20)))
        else:
            return min(20, max(0, round((raw_hy / 100) * 20)))

def calculate_subject_monthly_weightage(student_ev, sub_id, cls_name):
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
    metadata = {}
    limit_rows = min(15, len(raw_df))
    for r_idx in range(limit_rows):
        row_cells = [str(v).strip() for v in raw_df.iloc[r_idx].dropna().tolist() if str(v).strip() and str(v).strip() != "nan"]
        for c_idx, cell in enumerate(row_cells):
            cl = cell.lower()
            if any(k in cl for k in ["school name", "name of school", "विद्यालय का नाम", "स्कूल का नाम"]):
                val = re.sub(r"^(?:school\s*name|name\s*of\s*school|विद्यालय\s*का\s*नाम|स्कूल\s*का\s*नाम)\s*[:\-]?\s*", "", cell, flags=re.I).strip()
                if val and len(val) > 3 and not any(k in val.lower() for k in ["class", "dise", "session", "block", "district", "medium"]):
                    metadata["name"] = val
                elif c_idx + 1 < len(row_cells):
                    next_val = row_cells[c_idx + 1].strip()
                    if len(next_val) > 3 and not any(k in next_val.lower() for k in ["class", "dise", "session", "block", "district", "medium"]):
                        metadata["name"] = next_val

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
                    metadata["medium"] = "Urdu (اردो)"
                elif med_to_check:
                    metadata["medium"] = med_to_check

            if any(k in cl for k in ["session", "सत्र", "annual result sheet"]):
                m = re.search(r"(\d{4}[-_/]\d{2,4})", cell)
                if m:
                    metadata["session"] = m.group(1).strip()
                elif c_idx + 1 < len(row_cells):
                    m = re.search(r"(\d{4}[-_/]\d{2,4})", row_cells[c_idx + 1])
                    if m:
                        metadata["session"] = m.group(1).strip()

            if any(k in cl for k in ["block", "ब्लॉक", "संकुल"]):
                val = re.sub(r"^(?:block|ब्लॉक|संकुल)\s*[:\-]?\s*", "", cell, flags=re.I).strip()
                if val and not any(k in val.lower() for k in ["district", "medium", "session", "class"]):
                    metadata["block"] = val
                elif c_idx + 1 < len(row_cells):
                    metadata["block"] = row_cells[c_idx + 1].strip()

            if any(k in cl for k in ["district", "जिला"]):
                val = re.sub(r"^(?:district|जिला)\s*[:\-]?\s*", "", cell, flags=re.I).strip()
                if val and not any(k in val.lower() for k in ["block", "medium", "session", "class"]):
                    metadata["district"] = val
                elif c_idx + 1 < len(row_cells):
                    metadata["district"] = row_cells[c_idx + 1].strip()

            if any(k in cl for k in ["dise", "udise", "डाइस"]):
                m = re.search(r"(\d{11})", cell)
                if m:
                    metadata["udise"] = m.group(1).strip()
                elif c_idx + 1 < len(row_cells):
                    m = re.search(r"(\d{11})", row_cells[c_idx + 1])
                    if m:
                        metadata["udise"] = m.group(1).strip()

            if any(k in cl for k in ["class", "कक्षा"]):
                val = re.sub(r"^(?:class|कक्षा)\s*[:\-]?\s*", "", cell, flags=re.I).strip()
                target_str = val if val else (row_cells[c_idx + 1].strip() if c_idx + 1 < len(row_cells) else "")
                num_m = re.search(r"(\d+)", target_str)
                if num_m:
                    n = num_m.group(1)
                    metadata["class"] = f"Class {n}th" if n in ["4","5","6","7","8","9","10"] else (f"Class {n}st" if n=="1" else (f"Class {n}nd" if n=="2" else f"Class {n}rd"))

    return metadata

def get_display_medium(s_info, stud=None):
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
    col_mapping = {}
    cols = [str(c).strip() for c in columns if str(c).strip() and not str(c).startswith("Unnamed:")]
    
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

    for c in cols:
        if c == col_mapping.get("Father_Name") or c == col_mapping.get("Mother_Name"):
            continue
        cl = c.lower()
        if any(k in cl for k in ["studant", "student", "stuent", "studen", "stdnt", "name", "naam", "nam", "विद्यार्थी", "छात्र", "परीक्षार्थी", "नाम", "बालक", "बालिका", "candidate", "s_name", "st_name"]) and not any(ex in cl for ex in ["father", "mother", "pita", "mata", "school", "vidyalaya"]):
            col_mapping["Name"] = c
            break

    for c in cols:
        cl = c.lower()
        if any(k in cl for k in ["scholar", "dakhila", "दाखिला", "admission", "sch_no", "adm_no", "scholar_no", "adm"]):
            col_mapping["Scholar_No"] = c
            break

    for c in cols:
        if c == col_mapping.get("Scholar_No"):
            continue
        cl = c.lower()
        if any(k in cl for k in ["roll", "r_no", "rno", "अनुक्रमांक", "रोल", "rollno", "roll_no"]) or cl.strip() == "r no" or cl.strip().startswith("r no ") or cl.strip().endswith(" r no"):
            col_mapping["Roll_No"] = c
            break

    for c in cols:
        if c in [col_mapping.get("Scholar_No"), col_mapping.get("Roll_No")]:
            continue
        cl = c.lower()
        if any(k in cl for k in ["sr.no", "sr_no", "sr no", "s.no", "sno", "क्रमांक", "क्र."]):
            col_mapping["Sr_No"] = c
            break

    for c in cols:
        cl = c.lower()
        if any(k in cl for k in ["dob", "birth", "d.o.b", "d_o_b", "जन्म", "जन्मतिथि", "जन्म दिनांक", "date of birth"]):
            col_mapping["DOB"] = c
            break

    for c in cols:
        cl = c.lower()
        if any(k in cl for k in ["samagra", "sssm", "smgr", "samgra", "समग्र", "समग्र आईडी", "sssmid", "sssm_id"]):
            col_mapping["SSSM_ID"] = c
            break

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

    for c in cols:
        cl = c.lower()
        if any(k in cl for k in ["gender", "sex", "लिंग", "boy/girl", "boy_girl", "जेंडर"]):
            col_mapping["Gender"] = c
            break

    for c in cols:
        cl = c.lower()
        if any(k in cl for k in ["category", "caste", "caste_category", "वर्ग", "जाति", "श्रेणी", "cat"]):
            col_mapping["Category"] = c
            break

    for c in cols:
        cl = c.lower()
        if any(k in cl for k in ["aadhar", "uid", "आधार", "aadhaar", "uidai", "aadhar_no"]):
            col_mapping["Aadhar_No"] = c
            break

    for c in cols:
        cl = c.lower()
        if any(k in cl for k in ["pan", "pancard", "pan_no", "panno", "पैन", "pan number", "pan_number"]):
            col_mapping["PAN_No"] = c
            break

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
        "nav_student": "👨🎓 2. विद्यार्थी मास्टर (Student Master)",
        "nav_attendance": "📅 3. माहवार उपस्थिति पत्रक (Monthly Attendance)",
        "nav_eval": "📝 4. परीक्षा एवं गतिविधि मूल्यांकन (Evaluation Entry)",
        "nav_viewer": "🔍 5. छात्र संपूर्ण डेटा समीक्षा (Student Data Viewer)",
        "nav_monthly_test": "📝 6. मासिक मूल्यांकन रजिस्टर (Monthly Test — 10 अंक)",
        "nav_quarterly": "📑 7. त्रैमासिक परीक्षा मूल्यांकन (Quarterly Exam — MPBSE 5% अधिभार)",
        "nav_half_yearly": "📑 8. अर्धवार्षिक परीक्षा मूल्यांकन (Half-Yearly Exam — 20%/5% अधिभार)",
        "nav_project": "🎨 9. वार्षिक प्रोजेक्ट कार्य मूल्यांकन (Project Work — 10%/15/20 अंक)",
        "nav_marksheet": "🖨️ 10. शासकीय वार्षिक प्रगति पत्रक एवं RSKMP/MPBSE पोर्टल केंद्र",
        "nav_a3_result": "📜 11. A3 वार्षिक परीक्षाफल पत्रक (Annual Result Sheet)",
        "nav_summary": "📊 12. श्रेणीवार परीक्षा परिणाम सारांश (Result Summary)",
        "nav_merit": "🏆 13. वार्षिक परीक्षा प्रावीण्य सूची (Merit List)",
        "nav_supple": "📋 14. पूरक परीक्षा छात्र सूची (Supplementary List)",
        "nav_weighted": "📑 15. वार्षिक परीक्षा परिणाम अभिलेख पत्रक (RSKMP व MPBSE प्रारूप)",
        "nav_promote": "🔄 16. सत्र परिवर्तन एवं कक्षा पदोन्नति (Session Promotion)",
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
        "nav_student": "👨🎓 2. Student Master",
        "nav_attendance": "📅 3. Monthly Attendance Sheet",
        "nav_eval": "📝 4. Marks & Activity Evaluation",
        "nav_viewer": "🔍 5. Student Complete Data Viewer",
        "nav_monthly_test": "📝 6. Monthly Test Evaluation (10 Marks)",
        "nav_quarterly": "📑 7. Quarterly Examination (Quarterly Exam — MPBSE 5% Weightage)",
        "nav_half_yearly": "📑 8. Half-Yearly Examination (Half-Yearly Exam — 20%/5% Weightage)",
        "nav_project": "🎨 9. Annual Project Work Evaluation",
        "nav_marksheet": "🖨️ 10. Govt Holistic Progress Card & RSKMP/MPBSE Portal Center",
        "nav_a3_result": "📜 11. A3 Annual Result Sheet",
        "nav_summary": "📊 12. Category/Grade Wise Result Summary",
        "nav_merit": "🏆 13. Annual Result Merit List",
        "nav_supple": "📋 14. Supplementary Students List",
        "nav_weighted": "📑 15. Annual Result Record Sheet (RSKMP & MPBSE Format)",
        "nav_promote": "🔄 16. Session Roll-over & Promotion",
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
        "nav_student": "👨🎓 2. विद्यार्थी मास्टर (Student Master)",
        "nav_attendance": "📅 3. मासिक उपस्थिती पत्रक (Monthly Attendance)",
        "nav_eval": "📝 4. परीक्षा व मूल्यमापन (Evaluation Entry)",
        "nav_viewer": "🔍 5. विद्यार्थी संपूर्ण माहिती दर्शक (Student Data Viewer)",
        "nav_monthly_test": "📝 6. मासिक मूल्यमापन नोंदवही (Monthly Test — 10 गुण)",
        "nav_quarterly": "📑 7. त्रैमासिक परीक्षा मूल्यमापन (Quarterly Exam — 5% भारांश)",
        "nav_half_yearly": "📑 8. सत्रांत / सहामाही परीक्षा मूल्यमापन (20%/5% भारांश)",
        "nav_project": "🎨 9. वार्षिक प्रकल्प कार्य मूल्यमापन (Project Work)",
        "nav_marksheet": "🖨️ 10. शासकीय प्रगती पत्रक व RSKMP/MPBSE पोर्टल केंद्र",
        "nav_a3_result": "📜 11. A3 वार्षिक निकाल पत्रक (Annual Result Sheet)",
        "nav_summary": "📊 12. प्रवर्गनिहाय निकाल गोषवारा (Result Summary)",
        "nav_merit": "🏆 13. वार्षिक परीक्षा गुणवत्ता यादी (Merit List)",
        "nav_supple": "📋 14. पुरवणी परीक्षा विद्यार्थी यादी (Supplementary List)",
        "nav_weighted": "📑 15. वार्षिक निकाल अभिलेख पत्रक (RSKMP व MPBSE प्रारूप)",
        "nav_promote": "🔄 16. सत्र बदल व वर्ग पदोन्नती (Promotion)",
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

def get_ordinal_suffix(n):
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
    if not name:
        return ""
    clean = str(name).strip()
    clean_lower = clean.lower()
    clean_lower = re.sub(r"\b(calss|clas|clss|clz)\b", "class", clean_lower)
    if "nurs" in clean_lower:
        return "Class Nursery"
    if any(k in clean_lower for k in ["lkg", "kg1", "kg 1", "kg-1", "junior kg", "kg-i"]):
        return "Class LKG"
    if any(k in clean_lower for k in ["ukg", "kg2", "kg 2", "kg-2", "senior kg", "kg-ii"]):
        return "Class UKG"
    if "balvatika" in clean_lower or "बालवाटिका" in clean_lower:
        return "Class Balvatika"
    num_match = re.search(r"(\d+)", clean_lower)
    if num_match:
        n = int(num_match.group(1))
        correct_ordinal = get_ordinal_suffix(n)
        return f"Class {correct_ordinal}"
    clean_title = " ".join([w.capitalize() for w in clean.split()])
    if not clean_title.lower().startswith("class"):
        clean_title = f"Class {clean_title}"
    return clean_title

def clean_and_sort_classes(classes_list):
    normalized = []
    seen = set()
    for c in classes_list:
        norm = normalize_class_name(c)
        if norm and norm not in seen:
            seen.add(norm)
            normalized.append(norm)
    def sort_key(c):
        cl = c.lower()
        if "nursery" in cl: return -4
        if "lkg" in cl or "kg1" in cl: return -3
        if "ukg" in cl or "kg2" in cl: return -2
        if "balvatika" in cl: return -1
        num_m = re.search(r"(\d+)", cl)
        if num_m: return int(num_m.group(1))
        return 999
    return sorted(normalized, key=sort_key)

def migrate_data_store_keys(data_store):
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
    # RSKMP/MPBSE Compliance Fix: Check Class 9th & 10th prior to Class 1st & 2nd to prevent substring collision
    elif any(k in clean for k in ["class 9", "class 10", "9th", "10th", "कक्षा 9", "कक्षा 10"]):
        return [
            {"id": "hindi", "name": "Hindi (प्रथम भाषा)", "code": "01"},
            {"id": "english", "name": "English (द्वितीय भाषा)", "code": "02"},
            {"id": "sanskrit", "name": "Sanskrit (तृतीय भाषा)", "code": "03"},
            {"id": "maths", "name": "Mathematics (गणित)", "code": "04"},
            {"id": "science", "name": "Science (विज्ञान)", "code": "05"},
            {"id": "social_science", "name": "Social Science (सामाजिक विज्ञान)", "code": "06"}
        ]
    elif any(k in clean for k in ["class 1st", "class 2nd", "class 1", "class 2", "1st", "2nd"]) and not any(k in clean for k in ["10", "11", "12"]):
        return [
            {"id": "hindi", "name": "Hindi (हिन्दी)", "code": "01"},
            {"id": "english", "name": "English (अंग्रेजी)", "code": "02"},
            {"id": "maths", "name": "Mathematics (गणित)", "code": "03"}
        ]
    elif any(k in clean for k in ["class 3", "class 4", "class 5", "3rd", "4th", "5th"]):
        return [
            {"id": "hindi", "name": "Hindi (हिन्दी)", "code": "01"},
            {"id": "english", "name": "English (अंग्रेजी)", "code": "02"},
            {"id": "maths", "name": "Mathematics (गणित)", "code": "03"},
            {"id": "evs", "name": "EVS / पर्यावरण", "code": "04"}
        ]
    else:
        return [
            {"id": "hindi", "name": "Hindi (हिन्दी)", "code": "01"},
            {"id": "english", "name": "English (अंग्रेजी)", "code": "02"},
            {"id": "sanskrit", "name": "Sanskrit / तृतीय भाषा", "code": "03"},
            {"id": "maths", "name": "Mathematics (गणित)", "code": "04"},
            {"id": "science", "name": "Science (विज्ञान)", "code": "05"},
            {"id": "social_science", "name": "Social Science (सामाजिक विज्ञान)", "code": "06"}
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
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return df
    if "PAN_No" not in df.columns:
        df["PAN_No"] = ""
    if "APAAR_ID" not in df.columns:
        df["APAAR_ID"] = ""
    for c in list(df.columns):
        c_clean = str(c).strip().lower().replace(" ", "").replace("_", "").replace("-", "")
        if any(k in c_clean for k in ["apaar", "apar", "edulocker"]) and c != "APAAR_ID":
            mask = (df["APAAR_ID"].isna() | (df["APAAR_ID"].astype(str).str.strip().isin(["", "nan", "None"])))
            df.loc[mask, "APAAR_ID"] = df.loc[mask, c].fillna("").astype(str)
            df.drop(columns=[c], inplace=True)
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

# =========================================================================================
# 🚀 COMMERCIAL MULTI-TENANT SAAS AUTHENTICATION & SUPER ADMIN PORTAL (MODULE A - UNTOUCHED)
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

    with adm_tab3:
        st.subheader("🎯 ट्रायल लीड्स एवं 1-क्लिक व्हाट्सएप फॉलो-अप")
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
                render_html(f'<a href="{wa_pitch_url}" target="_blank" style="text-decoration: none;"><div style="background: #25D366; color: white; font-size: 12px; font-weight: bold; padding: 6px 10px; border-radius: 6px; text-align: center;">📱 WhatsApp फॉलो-अप भेजें</div></a>')
                st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("<hr style='margin:6px 0; border:none; border-top:1px solid #E2E8F0;'>", unsafe_allow_html=True)

    with adm_tab4:
        st.subheader("🔍 सपोर्ट एक्सेस मोड (Diagnose School Data)")
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

    with adm_tab5:
        st.subheader("🛡️ केंद्रीय सुरक्षा एवं एक्सेस ऑडिट लॉग्स")
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

    query_params = getattr(st, "query_params", {})
    is_admin_query = (query_params.get("admin") in ["true", "1", "secret", "master"])
    if "show_secret_admin" not in st.session_state:
        st.session_state.show_secret_admin = False

    is_admin_mode = is_admin_query or st.session_state.show_secret_admin

    if is_admin_mode:
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

    auth_tab1, auth_tab2, auth_tab3, auth_tab4, auth_tab5 = st.tabs([
        "🏛️ संस्था प्रधान लॉगिन (Principal Login with OTP)",
        "👨🏫 कक्षा अध्यापक लॉगिन (Teacher Login with OTP)",
        "📝 नया स्कूल पंजीकरण (15 दिन निःशुल्क ट्रायल)",
        "💎 ₹499 ऑल-इन-वन वार्षिक पास",
        "📞 सहायता एवं संपर्क"
    ])

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

    with auth_tab2:
        c_tl1, c_tl2 = st.columns([1.5, 1])
        with c_tl1:
            st.subheader("👨🏫 कक्षा अध्यापक (Teacher) लॉगिन")
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
                <b style="color: #92400E; font-size: 14px;">👨🏫 कक्षा अध्यापक के अधिकार:</b><br>
                <span style="font-size: 12.5px; color: #78350F;">
                    • केवल अपनी कक्षा का दैनिक हाजिरी रजिस्टर<br>
                    • अपनी कक्षा के परीक्षा व प्रोजेक्ट अंक भरना<br>
                    • नए छात्र का ड्राफ्ट जोड़ना (प्रिंसिपल अनुमोदन हेतु)<br>
                    • 🔒 शासकीय डेटा एक्सपोर्ट पूरी तरह सुरक्षित व लॉक<br>
                </span>
            </div>
            """)

    with auth_tab3:
        st.subheader("📝 नवीन संस्था निःशुल्क पंजीकरण (15-Day Free Trial)")
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

# ----------------- SIDEBAR CONTROLS & NAVIGATION -----------------
with st.sidebar:
    auth_school = st.session_state.get("authenticated_school") or {}
    user_role = st.session_state.get("authenticated_role", "PRINCIPAL")
    user_display_name = st.session_state.get("authenticated_user_name", "संस्था प्रधान")
    assigned_c = st.session_state.get("assigned_class")
    
    if auth_school:
        role_label = "🏛️ संस्था प्रधान (Principal)" if user_role == "PRINCIPAL" else f"👨🏫 कक्षा अध्यापक: {user_display_name} ({assigned_c})"
        pending_cnt = len(auth_school.get("pending_approvals", []))
        
        render_html(f"""
        <div style="background: linear-gradient(135deg, #1E3A8A, #2563EB); padding: 10px 12px; border-radius: 8px; color: white; margin-bottom: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <div style="font-weight: 800; font-size: 13.5px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">🏫 {auth_school.get("school_name", "School Portal")}</div>
            <div style="font-size: 11px; opacity: 0.9;">DISE: {auth_school.get("dise_code", "")} | {auth_school.get("block","")}</div>
            <div style="font-size: 11px; color: #FEF08A; font-weight: bold; margin-top: 2px;">{role_label}</div>
            <div style="font-size: 10px; color: #BBF7D0; font-weight: bold; margin-top: 3px;">🟢 {auth_school.get("plan", "School Result Pro पास (₹499/वर्ष)")}</div>
        </div>
        """)
        
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
        if st.button("🔄 सभी 15 कक्षाएं जोड़ें (Nursery से 12th तक)", key="btn_restore_all_classes_sb", use_container_width=True, type="primary"):
            st.session_state.classes_list = clean_and_sort_classes(list(dict.fromkeys(st.session_state.classes_list + DEFAULT_CLASSES)))
            save_data_to_disk()
            st.success("✅ सभी कक्षाएं (Nursery से 12th) लोड हो गईं!")
            st.rerun()

        if st.button("🧹 सभी स्पेलिंग ठीक करें (Auto-Fix All)", key="btn_auto_clean_classes_sb", use_container_width=True):
            st.session_state.classes_list = clean_and_sort_classes(st.session_state.classes_list)
            st.session_state.data_store = migrate_data_store_keys(st.session_state.data_store)
            save_data_to_disk()
            st.success("✅ सभी कक्षाएं शुद्ध प्रारूप में व्यवस्थित हो गईं!")
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
            T["nav_quarterly"],
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
            render_html(f"""
            <div style="background: #FEF3C7; border-left: 5px solid #D97706; padding: 8px 12px; border-radius: 4px;">
                <b style="color: #92400E; font-size: 13.5px;">📢 नवीन शासकीय प्रारूप अपडेट सूचना (सत्र {current_sess}):</b><br>
                <span style="color: #78350F; font-size: 12.5px;">
                    राज्य शिक्षा केंद्र (RSKMP) एवं माध्यमिक शिक्षा मण्डल (MPBSE) के नवीन मूल्यांकन दिशा-निर्देश एवं एक्सेल अपलोड प्रारूप का अपडेट डिटेक्ट हुआ है।
                </span>
            </div>
            """)
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

if st.session_state.get("show_format_adopter_dialog"):
    with st.container():
        render_html("""
        <div style="background: #F0FDF4; border: 2px solid #16A34A; padding: 14px 18px; border-radius: 8px; margin-bottom: 15px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <h4 style="color: #166534; margin: 0;">🏛️ नवीन शासकीय प्रारूप अपलोड एवं सत्र अनुकूलन (Format Adopter)</h4>
            </div>
            <p style="color: #14532D; font-size: 13px; margin-top: 6px;">
                सरकारी पोर्टल (RSKMP या MPBSE) से डाउनलोड की गई नई एक्सेल शीट यहाँ अपलोड करें।
            </p>
        </div>
        """)
        c_link1, c_link2, c_link3 = st.columns(3)
        c_link1.markdown("🔗 **[RSKMP पोर्टल लॉगिन (rskmp.in)](https://www.rskmp.in)**")
        c_link2.markdown("🔗 **[MPBSE बोर्ड पोर्टल (mpbse.nic.in)](http://mpbse.nic.in)**")
        c_link3.markdown("🔗 **[एमपी ऑनलाइन स्कूल मॉड्यूल](https://mponline.gov.in)**")

        c_up_file, c_up_sess = st.columns([3, 2])
        with c_up_file:
            uploaded_template = st.file_uploader("📥 डाउनलोड की गई सरकारी एक्सेल फ़ाइल चुनें (.xlsx / .csv):", type=["xlsx", "csv"], key="govt_template_uploader")
        with c_up_sess:
            target_sess = st.selectbox("यह नया प्रारूप किस सत्र हेतु लागू करना है?", [current_sess, "2024-25", "2025-26", "2026-27", "2027-28"], key="target_adoption_sess")
            sess_isolate_check = st.checkbox("✅ पुष्टि करें कि पूर्ववर्ती सत्रों का रिकॉर्ड मूल नियम पर ही सुरक्षित रहेगा", value=True, key="sess_isolate_confirm")

        if uploaded_template:
            scan_res = scan_govt_excel_template(uploaded_template.read(), uploaded_template.name)
            if scan_res["success"]:
                st.success(f"🎉 सरकारी टेम्पलेट सफलतापूर्वक पहचाना गया! कुल {scan_res['total_columns']} कॉलम मिले।")
                c_act_save, c_act_close = st.columns([2, 1])
                with c_act_save:
                    if st.button(f"💾 सत्र {target_sess} हेतु नया प्रारूप सक्रिय करें", type="primary", use_container_width=True):
                        if target_sess not in st.session_state.session_exam_rules:
                            st.session_state.session_exam_rules[target_sess] = {}
                        st.session_state.session_exam_rules[target_sess] = {
                            "adopted_from_file": uploaded_template.name,
                            "mode": "board_5_8" if scan_res.get("has_project") else "standard_rsk",
                            "columns": scan_res["columns"]
                        }
                        save_data_to_disk()
                        st.balloons()
                        st.success(f"✅ नवीन प्रारूप सफलतापूर्वक केवल सत्र {target_sess} हेतु सक्रिय कर दिया गया!")
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
                            st.success(f"🎉 बधाई! {auth_school.get('school_name')} का वार्षिक प्रो लाइसेंस सक्रिय हो गया!")
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
            upi_qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=180x180&data=upi://pay?pa={upi_id_demo}%26pn=SchoolResultPro%26am={plan_amount}%26cu=INR"
            render_html(f"""
            <div style="text-align: center; margin-top: 10px;">
                <img src="{upi_qr_url}" style="width: 170px; height: 170px; border: 1px solid #ccc; border-radius: 6px;">
                <div style="font-weight: bold; font-size: 13px; color: #1E3A8A; margin-top: 6px;">
                    UPI ID: <code>{upi_id_demo}</code>
                </div>
            </div>
            """)
    st.divider()

s_info = st.session_state.school_info

# ----------------- REUSABLE BULK & SINGLE PHOTO MANAGER -----------------
def render_photo_manager(cls_data, selected_class, is_teacher=False, key_prefix="pr"):
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
                    if new_photo.size > 2 * 1024 * 1024:
                        st.error("⚠️ फोटो फ़ाइल 2MB से कम होनी चाहिए!")
                    else:
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

        uploaded_images = {}
        if bulk_files:
            for bf in bulk_files:
                if bf.size <= 5 * 1024 * 1024:
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
                    st.warning("⚠️ कोई भी फोटो रोल नंबर से मैच नहीं हो सकी।")

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
            # Basic validation
            if len(str(s_udise).strip()) != 11:
                st.warning("⚠️ U-DISE कोड सामान्यतः 11 अंकों का होता है।")
            st.session_state.school_info.update({
                "session": s_sess, "name": s_name, "udise": s_udise, "medium": s_med,
                "class_level": s_cls, "address": s_addr, "block": s_block, "district": s_dist,
                "contact": s_contact, "email": s_email
            })
            save_data_to_disk()
            st.success("✅ स्कूल की सभी 10 जानकारियां सुरक्षित कर ली गईं!")

    with col2:
        st.subheader("🖼️ स्कूल लोगो (School Logo)")
        logo_file = st.file_uploader("लोगो अपलोड करें (PNG/JPG, अधिकतम 5MB)", type=["png", "jpg", "jpeg"], key="school_logo")
        if logo_file:
            if logo_file.size > 5 * 1024 * 1024:
                st.error("⚠️ लोगो फ़ाइल का आकार 5MB से कम होना चाहिए!")
            else:
                bytes_data = logo_file.read()
                st.session_state.school_info["logo_b64"] = base64.b64encode(bytes_data).decode()
                save_data_to_disk()
                st.image(bytes_data, width=110, caption="School Logo")
        elif st.session_state.school_info.get("logo_b64"):
            st.image(base64.b64decode(st.session_state.school_info["logo_b64"]), width=110, caption="Current Logo")
            
        st.divider()
        st.subheader("✍️ डिजिटल सील / हस्ताक्षर")
        sign_file = st.file_uploader("प्रधानाध्यापक सील / हस्ताक्षर (अधिकतम 3MB)", type=["png", "jpg", "jpeg"], key="school_sign")
        if sign_file:
            if sign_file.size > 3 * 1024 * 1024:
                st.error("⚠️ हस्ताक्षर फ़ाइल 3MB से कम होनी चाहिए!")
            else:
                st.session_state.school_info["sign_b64"] = base64.b64encode(sign_file.read()).decode()
                save_data_to_disk()
                st.success("हस्ताक्षर सुरक्षित!")

        st.divider()
        st.subheader("⚙️ परीक्षा घटक व पूर्णांक प्रबंधन (Exam Components & Marks Master)")
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
        with st.expander("👨🏫 कक्षा अध्यापक प्रबंधन एवं कक्षा आवंटन (Manage Teachers)", expanded=False):
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

    render_html(f'<div class="main-header">👨🎓 विद्यार्थी मास्टर डेटा — {selected_class}</div>')
    if cur_role == "TEACHER":
        render_html(f'<div class="sub-header">कक्षा अध्यापक मोड ({st.session_state.get("authenticated_user_name")}) — नए छात्र का ड्राफ्ट जोड़ें अथवा सुधार अनुरोध भेजें</div>')
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
                if st.button("🔤 A-Z अनुसार रोल नं. पुनः आवंटित करें", help="छात्रों को अंग्रेजी वर्णमाला अनुसार रोल नंबर 1, 2, 3... पुनः आवंटित करें"):
                    st_az_df = sort_students_dataframe(cls_data["students"], "Name").copy()
                    st_az_df["Roll_No"] = range(1, len(st_az_df) + 1)
                    cls_data["students"] = st_az_df
                    save_data_to_disk()
                    st.success("✅ सभी छात्रों को वर्णमाला अनुसार रोल नंबर आवंटित कर दिए गए!")
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

        sort_choice_key = "Roll_No"
        if "वर्णमाला" in st_view_sort: sort_choice_key = "Name"
        elif "दाखिला" in st_view_sort: sort_choice_key = "Scholar_No"

        df_students = sort_students_dataframe(cls_data["students"].copy(), sort_choice_key)
        df_students = reorder_student_columns(df_students)

        if is_teacher:
            st.info("🔒 कक्षा अध्यापक मोड: बायो-डेटा केवल पठनीय है। नए छात्र या सुधार हेतु अगले टैब्स का उपयोग करें।")

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

    # ---------------- TAB 2: ADD STUDENT / DRAFT STUDENT (WITH DOB & REGEX VALIDATION) ----------------
    with tab2:
        if is_teacher:
            st.subheader("➕ नए छात्र का ड्राफ्ट जोड़ें (Submit for Principal Approval):")
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
                # FIX: Set realistic default date for school students instead of current date
                s_dob = st.date_input(
                    "6. Date Of Birth (जन्मतिथि):",
                    value=date(2013, 5, 1),
                    min_value=date(2000, 1, 1),
                    max_value=datetime.now().date(),
                    help="विद्यार्थी की वास्तविक जन्मतिथि चुनें"
                )
            with c3:
                s_class = st.text_input("7. Class:", value=selected_class, disabled=is_teacher)
                s_sec = st.selectbox("8. Section:", ["A", "B", "C", "D", "E"])
                s_gender = st.selectbox("9. Gender:", ["Boy", "Girl", "Other"])
            with c4:
                s_cat = st.selectbox("10. Category:", ["General", "OBC", "SC", "ST"])
                s_sssm = st.text_input("11. Samagra ID (9-अंक):", placeholder="उदा. 123456789")
                s_aadhar = st.text_input("12. Aadhar Number (12-अंक):", placeholder="उदा. 123456789012")
            
            c_mid1, c_mid2, c_mid3 = st.columns(3)
            with c_mid1:
                s_pan = st.text_input("13. PAN Number (पैन नंबर):", placeholder="उदा. ABCDE1234F")
            with c_mid2:
                s_apaar = st.text_input("14. APAAR ID (अपार आईडी):", placeholder="12-अंकीय अपार आईडी")
            with c_mid3:
                s_medium = st.selectbox("15. Medium (माध्यम):", ALL_MEDIUMS)
            
            c_bot1, c_bot2, c_bot3 = st.columns(3)
            with c_bot1:
                s_tot_days = st.number_input("16. Working Days:", value=220)
            with c_bot2:
                s_att_days = st.number_input("17. Attended Days:", value=200)
            with c_bot3:
                s_status = st.selectbox("18. Exam Status:", ["Present", "Absent"])

            photo_file = st.file_uploader("विद्यार्थी का फोटो (Photo Upload - अधिकतम 2MB):", type=["jpg", "jpeg", "png"], key="reg_photo_uni")
            btn_label = "📤 अनुमोदन हेतु संस्था प्रधान को भेजें (Submit for Approval)" if is_teacher else "➕ विद्यार्थी जोड़ें (Submit)"
            submit_student = st.form_submit_button(btn_label, type="primary")

            if submit_student:
                clean_sssm = str(s_sssm).strip()
                clean_aadhar = "".join(filter(str.isdigit, str(s_aadhar)))
                
                if not s_name:
                    st.error("कृपया छात्र का नाम दर्ज करें!")
                elif clean_sssm and len(clean_sssm) != 9:
                    st.warning("⚠️ समग्र आईडी (Samagra ID) 9 अंकों की होनी चाहिए!")
                elif clean_aadhar and len(clean_aadhar) != 12:
                    st.warning("⚠️ आधार नंबर (Aadhar Number) 12 अंकों का होना चाहिए!")
                else:
                    p_b64 = None
                    if photo_file:
                        if photo_file.size <= 2 * 1024 * 1024:
                            p_b64 = base64.b64encode(photo_file.read()).decode()
                    new_row = {
                        "Roll_No": int(s_roll), "Scholar_No": s_schol, "Name": s_name,
                        "Father_Name": s_father, "Mother_Name": s_mother, "DOB": str(s_dob),
                        "Class": selected_class, "Section": s_sec, "Gender": s_gender,
                        "Category": s_cat, "SSSM_ID": clean_sssm, "Aadhar_No": clean_aadhar,
                        "PAN_No": s_pan.strip(),
                        "APAAR_ID": s_apaar.strip(),
                        "Medium": s_medium, "Status": s_status, "Photo_b64": p_b64,
                        "Total_Days": int(s_tot_days), "Attended_Days": int(s_att_days)
                    }
                    if is_teacher:
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
        with tab4:
            render_photo_manager(cls_data, selected_class, is_teacher=True, key_prefix="tr")
    else:
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
                del_from_all = st.checkbox("⚠️ यदि यह रोल नंबर अन्य कक्षाओं में भी मौजूद है, तो सभी कक्षाओं से हटाएं", value=True, key="del_all_cls_chk")
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
                        log_security_event(cur_dise, "Principal", "Principal", auth_school.get("mobile"), "DELETE_STUDENT_TC", f"Deleted Roll {clean_del} from ALL classes ({removed_cnt} removed)")
                        st.success(f"✅ रोल नंबर {clean_del} का रिकॉर्ड सभी कक्षाओं से हटा दिया गया!")
                        st.rerun()
                    else:
                        m = cls_data["students"]["Roll_No"].astype(str).str.strip().str.replace(".0", "", regex=False) != clean_del
                        cls_data["students"] = cls_data["students"][m].reset_index(drop=True)
                        for k in [clean_del, int(clean_del) if clean_del.isdigit() else clean_del, f"{clean_del}.0"]:
                            if k in cls_data["evaluations"]:
                                del cls_data["evaluations"][k]
                        save_data_to_disk()
                        st.success(f"✅ रोल नंबर {clean_del} का रिकॉर्ड हटा दिया गया।")
                        st.rerun()
        with tab5:
            st.subheader("🔔 शिक्षक अनुमोदन डेस्क (Teacher Approvals Queue)")
            registry = load_schools_registry()
            sch_reg = registry.get(cur_dise, auth_school)
            pending_list = sch_reg.get("pending_approvals", [])

            if not pending_list:
                st.success("✅ कोई भी शिक्षक अनुमोदन लंबित नहीं है! सभी रिकॉर्ड्स अद्यतन हैं।")
            else:
                render_html(f"**कुल {len(pending_list)} अनुरोध अनुमोदन हेतु प्रतीक्षारत हैं:**")
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
                    st.balloons()
                    st.success("🎉 सभी शिक्षक अनुरोध सफलतापूर्वक अनुमोदित कर दिए गए!")
                    st.rerun()
                st.divider()

                for idx, req in enumerate(pending_list):
                    r_c1, r_c2, r_c3 = st.columns([4, 2, 2])
                    with r_c1:
                        if req["type"] == "new_student":
                            st_d = req["data"]
                            st.markdown(f"➕ **नया छात्र:** **{st_d['Name']}** (रोल: `{st_d['Roll_No']}`, दाखिला: `{st_d['Scholar_No']}`)<br><span style='font-size:12px; color:#555;'>कक्षा: <b>{req['class']}</b> | शिक्षक: {req['teacher_name']} | समय: {req['requested_at']}</span>", unsafe_allow_html=True)
                        else:
                            render_html(f"✏️ **सुधार अनुरोध:** **{req['student_name']}** (रोल: `{req['roll_no']}`)<br><span style='font-size:12px; color:#555;'>फ़ील्ड: <b>{req['field']}</b> ➔ नया मान: <b style='color:green;'>{req['new_value']}</b></span>")
                    with r_c2:
                        if st.button("✅ स्वीकार करें", key=f"btn_appr_{req['id']}", type="primary", use_container_width=True):
                            if req["type"] == "new_student":
                                st_cls = req["class"]
                                t_cls_data = get_class_data(st_cls)
                                t_cls_data["students"] = pd.concat([t_cls_data["students"], pd.DataFrame([req["data"]])], ignore_index=True)
                            else:
                                st_cls = req["class"]
                                t_cls_data = get_class_data(st_cls)
                                f_map = {
                                    "छात्र का नाम (Name)": "Name", "पिता का नाम (Father Name)": "Father_Name", 
                                    "माता का नाम (Mother Name)": "Mother_Name", "जन्मतिथि (DOB)": "DOB", 
                                    "समग्र आईडी (Samagra ID)": "SSSM_ID", "आधार नंबर (Aadhar No)": "Aadhar_No",
                                    "अपार आईडी (APAAR ID)": "APAAR_ID", "माध्यम (Medium)": "Medium",
                                    "स्कॉलर नंबर (Scholar No)": "Scholar_No"
                                }
                                internal_f = f_map.get(req["field"], "Name")
                                t_cls_data["students"].loc[t_cls_data["students"]["Roll_No"] == req["roll_no"], internal_f] = req["new_value"]
                            sch_reg["pending_approvals"].pop(idx)
                            registry[cur_dise] = sch_reg
                            save_schools_registry(registry)
                            st.session_state.authenticated_school = sch_reg
                            save_data_to_disk()
                            st.success("अनुरोध स्वीकार कर लिया गया!")
                            st.rerun()
                    with r_c3:
                        if st.button("❌ अस्वीकार", key=f"btn_rej_{req['id']}", use_container_width=True):
                            sch_reg["pending_approvals"].pop(idx)
                            registry[cur_dise] = sch_reg
                            save_schools_registry(registry)
                            st.session_state.authenticated_school = sch_reg
                            st.warning("अनुरोध अस्वीकार कर दिया गया।")
                            st.rerun()
                    st.markdown("<hr style='margin:6px 0;'>", unsafe_allow_html=True)
        with tab6:
            st.subheader("📥 यूनिवर्सल एक्सेल ऑनबोर्डिंग एवं मल्टी-शीट क्लास माइग्रेटर")
            mig_up = st.file_uploader("📥 अपनी एक्सेल या सीएसवी फ़ाइल चुनें (.xlsx / .csv):", type=["xlsx", "csv"], key="uni_excel_mig_up")
            if mig_up:
                try:
                    file_bytes = mig_up.read()
                    sheet_data_dict = {}
                    extracted_excel_meta = {}
                    from collections import Counter
                    all_meta_names, all_meta_mediums, all_meta_sessions = [], [], []
                    all_meta_blocks, all_meta_districts, all_meta_udises = [], [], []

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
                                weight = 3 if any(k in sh_name.lower() for k in ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]) else 1
                                if "name" in sh_meta and sh_meta["name"]: all_meta_names.extend([sh_meta["name"]] * weight)
                                if "medium" in sh_meta and sh_meta["medium"]: all_meta_mediums.extend([sh_meta["medium"]] * weight)
                                if "session" in sh_meta and sh_meta["session"]: all_meta_sessions.extend([sh_meta["session"]] * weight)
                                if "block" in sh_meta and sh_meta["block"]: all_meta_blocks.extend([sh_meta["block"]] * weight)
                                if "district" in sh_meta and sh_meta["district"]: all_meta_districts.extend([sh_meta["district"]] * weight)
                                if "udise" in sh_meta and sh_meta["udise"]: all_meta_udises.extend([sh_meta["udise"]] * weight)
                                clean_df = parse_clean_excel_sheet(raw_sh_df)
                                if not clean_df.empty: sheet_data_dict[sh_name] = clean_df

                    if all_meta_names: extracted_excel_meta["name"] = Counter(all_meta_names).most_common(1)[0][0]
                    if all_meta_mediums: extracted_excel_meta["medium"] = Counter(all_meta_mediums).most_common(1)[0][0]
                    if all_meta_sessions: extracted_excel_meta["session"] = Counter(all_meta_sessions).most_common(1)[0][0]
                    if all_meta_blocks: extracted_excel_meta["block"] = Counter(all_meta_blocks).most_common(1)[0][0]
                    if all_meta_districts: extracted_excel_meta["district"] = Counter(all_meta_districts).most_common(1)[0][0]
                    if all_meta_udises: extracted_excel_meta["udise"] = Counter(all_meta_udises).most_common(1)[0][0]

                    with st.expander("🏫 एक्सेल हेडर से पहचानी गई संस्था जानकारी:", expanded=True):
                        c_meta_r1, c_meta_r2 = st.columns(2)
                        with c_meta_r1:
                            conf_name = st.text_input("🏫 स्कूल का नाम:*", value=extracted_excel_meta.get("name", st.session_state.school_info.get("name", "PALI GYAN MANDIR HIGH SCHOOL")), key="mig_conf_name_input")
                            cur_med_val = extracted_excel_meta.get("medium", st.session_state.school_info.get("medium", "Hindi (हिन्दी)"))
                            m_idx = ALL_MEDIUMS.index(cur_med_val) if cur_med_val in ALL_MEDIUMS else 0
                            conf_med = st.selectbox("🌐 माध्यम:*", ALL_MEDIUMS, index=m_idx, key="mig_conf_med_picker")
                            conf_sess = st.text_input("📅 सत्र:*", value=extracted_excel_meta.get("session", st.session_state.school_info.get("session", "2025-26")), key="mig_conf_sess_input")
                        with c_meta_r2:
                            conf_block = st.text_input("📍 ब्लॉक:*", value=extracted_excel_meta.get("block", st.session_state.school_info.get("block", "SENDHWA")), key="mig_conf_block_input")
                            conf_dist = st.text_input("🏙️ जिला:*", value=extracted_excel_meta.get("district", st.session_state.school_info.get("district", "BARWANI")), key="mig_conf_dist_input")
                            conf_udise = st.text_input("🔢 डाइस कोड:*", value=extracted_excel_meta.get("udise", st.session_state.school_info.get("udise", "23260100101")), key="mig_conf_udise_input")

                    st.session_state.school_info["name"] = conf_name
                    st.session_state.school_info["medium"] = conf_med
                    st.session_state.school_info["session"] = conf_sess
                    st.session_state.school_info["block"] = conf_block
                    st.session_state.school_info["district"] = conf_dist
                    st.session_state.school_info["udise"] = conf_udise

                    st.success(f"🎉 फ़ाइल पढ़ी गई: कुल {len(sheet_data_dict)} शीट्स पाई गईं।")
                except Exception as e:
                    st.error(f"❌ एक्सेल फ़ाइल आयात करने में त्रुटि: {e}")

# ----------------- MODULE 3: DUAL ATTENDANCE REGISTER -----------------
elif menu == T["nav_attendance"]:
    st.markdown('<div class="main-header">📅 विद्यार्थी उपस्थिति प्रबंधन (Student Attendance Portal)</div>', unsafe_allow_html=True)
    render_html('<div class="sub-header">दैनिक मोबाइल हाजिरी अथवा 12-माह का शासकीय उपस्थिति पत्रक</div>')
    students_df = cls_data["students"]
    if students_df.empty:
        st.warning("⚠️ कृपया पहले 'विद्यार्थी मास्टर' में छात्र जोड़ें!")
    else:
        tab_att1, tab_att2 = st.tabs([
            "📝 दैनिक कक्षा हाजिरी (Daily Teacher Attendance)",
            "📅 माहवार शासकीय उपस्थिति पत्रक (Monthly Attendance Sheet & Export)"
        ])
        with tab_att1:
            st.subheader(f"📱 दैनिक छात्र उपस्थिति — {selected_class}")
            MONTHS_MAP = {1:"Jan", 2:"Feb", 3:"Mar", 4:"Apr", 5:"May", 6:"Jun", 7:"Jul", 8:"Aug", 9:"Sep", 10:"Oct", 11:"Nov", 12:"Dec"}
            c_d1, c_d2, c_d3 = st.columns([2, 2, 3])
            with c_d1:
                cur_date = st.date_input("📅 उपस्थिति दिनांक:", value=datetime.now().date(), key="daily_att_date")
                cur_month_abbr = MONTHS_MAP.get(cur_date.month, "Sep")
            with c_d2:
                render_html(f"<div style='border: 1px solid #CBD5E1; padding: 6px 12px; border-radius: 6px; background: #F8FAFC; margin-top: 25px; text-align: center; font-size: 13px;'><b>सक्रिय माह:</b> <span style='color:#1E3A8A; font-weight:bold;'>{cur_month_abbr}</span></div>")
            
            if "daily_attendance" not in cls_data: cls_data["daily_attendance"] = {}
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
            daily_marked_status = {}
            for idx, s in students_df.iterrows():
                r_no = s["Roll_No"]
                default_stat = existing_day_record.get(str(r_no), "Present")
                ss_key = f"d_att_{r_no}_{date_str}"
                chosen_stat = st.session_state.get(ss_key, default_stat)
                daily_marked_status[r_no] = chosen_stat

                row_c1, row_c2, row_c3 = st.columns([1, 4, 3])
                with row_c1:
                    st.write(f"**Roll {r_no}**")
                with row_c2:
                    st.write(f"**{s['Name']}** (Scholar: {s.get('Scholar_No','--')})")
                with row_c3:
                    stat_choice = st.radio(f"status_{r_no}", ["Present (उपस्थित)", "Absent (अनुपस्थित)"], index=0 if chosen_stat == "Present" else 1, key=ss_key, horizontal=True, label_visibility="collapsed")
                    daily_marked_status[r_no] = "Present" if "Present" in stat_choice else "Absent"

            if st.button("💾 आज की हाजिरी सुरक्षित करें", type="primary", use_container_width=True):
                cls_data["daily_attendance"][date_str] = {str(k): v for k, v in daily_marked_status.items()}
                save_data_to_disk()
                st.success("✅ दैनिक उपस्थिति सुरक्षित!")

        with tab_att2:
            st.subheader("🏫 स्कूल कुल कार्य दिवस:")
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
                render_html(f"<div style='border: 2px solid #000; padding: 6px; text-align: center; margin-top: 18px; font-weight: bold; font-size: 16px;'>Total: {tot_work_days}</div>")
            cls_data["working_days"] = updated_work

            att_df = cls_data.get("monthly_attendance", pd.DataFrame())
            if att_df.empty or len(att_df) != len(students_df):
                rows = []
                for _, s in students_df.iterrows():
                    r = {"Roll_No": s["Roll_No"], "Name": s["Name"]}
                    for m in MONTHS_LIST: r[m] = 20 if updated_work[m] > 0 else 0
                    rows.append(r)
                att_df = pd.DataFrame(rows)
            att_df["Total"] = att_df[MONTHS_LIST].sum(axis=1)

            edited_att = st.data_editor(
                att_df,
                use_container_width=True,
                column_config={
                    "Roll_No": st.column_config.NumberColumn("Roll No.", disabled=True),
                    "Name": st.column_config.TextColumn("Name Of Student", disabled=True),
                    **{m: st.column_config.NumberColumn(m, min_value=0, max_value=31) for m in MONTHS_LIST},
                    "Total": st.column_config.NumberColumn("Total", disabled=True)
                },
                key=f"editor_att_{selected_class}"
            )
            if st.button("💾 माहवार उपस्थिति सहेजें", type="primary"):
                edited_att["Total"] = edited_att[MONTHS_LIST].sum(axis=1)
                cls_data["monthly_attendance"] = edited_att
                for idx, r in edited_att.iterrows():
                    cls_data["students"].loc[cls_data["students"]["Roll_No"] == r["Roll_No"], "Attended_Days"] = int(r["Total"])
                    cls_data["students"].loc[cls_data["students"]["Roll_No"] == r["Roll_No"], "Total_Days"] = int(tot_work_days)
                save_data_to_disk()
                st.success("✅ माहवार उपस्थिति सुरक्षित!")

# ----------------- MODULE 4: EVALUATION ENTRY (SUBJECT-WISE PRESENT/ABSENT) -----------------
elif menu == T["nav_eval"]:
    s_info = st.session_state.school_info
    st.markdown(f'<div class="main-header">📝 परीक्षा एवं गतिविधि मूल्यांकन — {selected_class}</div>', unsafe_allow_html=True)
    render_html('<div class="sub-header">विद्यार्थी प्रोफाइल, पेपर/विषयवार Present/Absent, मुख्य विषय (अर्धवार्षिक 40 + वार्षिक 60) व सह-शैक्षिक गुण</div>')

    students_df = cls_data["students"]
    if students_df.empty:
        st.warning("⚠️ कृपया पहले 'विद्यार्थी मास्टर' में छात्र जोड़ें!")
    else:
        st_names = [f"Roll {s['Roll_No']}: {s['Name']} (Scholar: {s['Scholar_No']})" for _, s in students_df.iterrows()]
        selected_student_str = st.selectbox("विद्यार्थी चुनें (Select Student):", st_names)
        sel_roll = int(selected_student_str.split(":")[0].replace("Roll", "").strip())
        stud = students_df[students_df["Roll_No"] == sel_roll].iloc[0]
        cls_subjects = get_class_subjects(selected_class)
        
        if sel_roll not in cls_data["evaluations"]:
            cls_data["evaluations"][sel_roll] = {
                "status": stud.get("Status", "Present"),
                "marks": {sub["id"]: {"status_hy": "Present", "half_yearly": 32, "status_yr": "Present", "annual": 48, "project": 16, "total": 80, "grade": "A"} for sub in cls_subjects},
                "co_curricular": {k: "A" for k, _ in CO_CURRICULAR_ACTIVITIES},
                "social": {k: "A" for k, _ in SOCIAL_ACTIVITIES}
            }
        eval_data = cls_data["evaluations"][sel_roll]

        col_st1, col_st2 = st.columns([1, 3])
        with col_st1:
            st_overall_status = st.selectbox("📌 छात्र की परीक्षा स्थिति:", ["Present", "Absent"], 
                                             index=0 if eval_data.get("status", "Present") == "Present" else 1)
            eval_data["status"] = st_overall_status

        cur_exam_rule = get_session_exam_rule(st.session_state.school_info.get("session", "2023-24"), selected_class)
        has_proj_m4 = any(c["id"] == "project" for c in cur_exam_rule["components"])

        with st.expander(f"📚 1. मुख्य विषय अंक प्रविष्टि ({cur_exam_rule['name']})", expanded=True):
            updated_marks = {}
            for sub in cls_subjects:
                s_id = sub["id"]
                s_name = sub["name"]
                prev_sub = eval_data.get("marks", {}).get(s_id, {})
                p_hy_val = prev_sub.get("half_yearly", 16 if has_proj_m4 else 32)
                p_proj_val = prev_sub.get("project", 18)
                p_yr_val = prev_sub.get("annual", 48)

                if has_proj_m4:
                    r_cols = st.columns([3, 2, 2, 2, 2, 2])
                    with r_cols[0]: st.write(f"📖 **{s_name}**")
                    with r_cols[1]: val_hy = st.number_input(f"अर्धवार्षिक (20)", min_value=0, max_value=20, value=min(20, max(0, int(p_hy_val))), key=f"num_hy_{selected_class}_{sel_roll}_{s_id}")
                    with r_cols[2]: val_proj = st.number_input(f"प्रोजेक्ट (20)", min_value=0, max_value=20, value=min(20, max(0, int(p_proj_val))), key=f"num_proj_{selected_class}_{sel_roll}_{s_id}")
                    with r_cols[3]: val_yr = st.number_input(f"वार्षिक (60)", min_value=0, max_value=60, value=min(60, max(0, int(p_yr_val))), key=f"num_yr_{selected_class}_{sel_roll}_{s_id}")
                    m_tot = val_hy + val_proj + val_yr if st_overall_status != "Absent" else 0
                    m_grd = calculate_grade(m_tot) if st_overall_status != "Absent" else "Ab"
                    with r_cols[4]: st.markdown(f"**कुल:** `{m_tot}/100`")
                    with r_cols[5]: st.markdown(f"**ग्रेड:** `{m_grd}`")
                    updated_marks[s_id] = {"half_yearly": val_hy, "project": val_proj, "annual": val_yr, "total": m_tot, "grade": m_grd}
                else:
                    r_cols = st.columns([3, 2, 2, 2, 2])
                    with r_cols[0]: st.write(f"📖 **{s_name}**")
                    with r_cols[1]: val_hy = st.number_input(f"अर्धवार्षिक (40)", min_value=0, max_value=40, value=min(40, max(0, int(p_hy_val))), key=f"num_hy_{selected_class}_{sel_roll}_{s_id}")
                    with r_cols[2]: val_yr = st.number_input(f"वार्षिक (60)", min_value=0, max_value=60, value=min(60, max(0, int(p_yr_val))), key=f"num_yr_{selected_class}_{sel_roll}_{s_id}")
                    m_tot = val_hy + val_yr if st_overall_status != "Absent" else 0
                    m_grd = calculate_grade(m_tot) if st_overall_status != "Absent" else "Ab"
                    with r_cols[3]: st.markdown(f"**कुल:** `{m_tot}/100`")
                    with r_cols[4]: st.markdown(f"**ग्रेड:** `{m_grd}`")
                    updated_marks[s_id] = {"half_yearly": val_hy, "annual": val_yr, "total": m_tot, "grade": m_grd}

        with st.expander("🎨 2. सह-शैक्षिक गतिविधियां मूल्यांकन (5 क्षेत्र)", expanded=False):
            c_grid = st.columns(len(CO_CURRICULAR_ACTIVITIES))
            updated_co = {}
            for idx, (k, label) in enumerate(CO_CURRICULAR_ACTIVITIES):
                with c_grid[idx]:
                    cur_val = eval_data.get("co_curricular", {}).get(k, "A")
                    opt_idx = ["A", "B", "C"].index(cur_val) if cur_val in ["A", "B", "C"] else 0
                    sel_grd = st.selectbox(label, ["A", "B", "C"], index=opt_idx, key=f"co_{selected_class}_{sel_roll}_{k}")
                    updated_co[k] = sel_grd

        with st.expander("🤝 3. व्यक्तिगत एवं सामाजिक गुण मूल्यांकन (10 गुण)", expanded=False):
            s_col_a, s_col_b = st.columns(2)
            updated_soc = {}
            for idx, (k, label) in enumerate(SOCIAL_ACTIVITIES):
                target_col = s_col_a if idx < 5 else s_col_b
                with target_col:
                    cur_val = eval_data.get("social", {}).get(k, "A")
                    opt_idx = ["A", "B", "C"].index(cur_val) if cur_val in ["A", "B", "C"] else 0
                    sel_grd = st.selectbox(label, ["A", "B", "C"], index=opt_idx, key=f"soc_{selected_class}_{sel_roll}_{k}")
                    updated_soc[k] = sel_grd

        if st.button(f"💾 रोल नंबर {sel_roll} ({stud['Name']}) का संपूर्ण मूल्यांकन सुरक्षित करें", type="primary", use_container_width=True):
            cls_data["evaluations"][sel_roll] = {
                "status": st_overall_status,
                "marks": updated_marks,
                "co_curricular": updated_co,
                "social": updated_soc
            }
            save_data_to_disk()
            st.success(f"✅ रोल नंबर {sel_roll} का मूल्यांकन सुरक्षित व सिंक कर दिया गया!")
            st.rerun()

# ----------------- MODULE 5: STUDENT COMPLETE DATA DOSSIER & VIEWER -----------------
elif menu == T["nav_viewer"]:
    s_info = st.session_state.school_info
    render_html('<div class="main-header">🔍 छात्र संपूर्ण डेटा समीक्षा (Student 360° Data Dossier)</div>')
    render_html('<div class="sub-header">विद्यार्थी का संपूर्ण विवरण, अंक, ग्रेड एवं परिणाम की विस्तृत समीक्षा</div>')

    if "active_dossier_roll" not in st.session_state:
        st.session_state.active_dossier_roll = None

    c_v_top1, c_v_top2, c_v_top3 = st.columns([2, 2, 2])
    with c_v_top1:
        v_class = st.selectbox("1. कक्षा चुनें:", st.session_state.classes_list, 
                               index=st.session_state.classes_list.index(selected_class) if selected_class in st.session_state.classes_list else 0,
                               key="viewer_class_sel")

    v_cls_data = get_class_data(v_class)
    v_students_df = v_cls_data["students"]
    v_evals = v_cls_data["evaluations"]
    v_subjects = get_class_subjects(v_class)
    v_sub_count = len(v_subjects)
    v_max_total = v_sub_count * 100

    existing_secs = sorted(list(set([str(s).strip() for s in v_students_df["Section"].dropna().unique() if str(s).strip()]))) if not v_students_df.empty and "Section" in v_students_df.columns else ["A"]
    all_sec_options = ["सभी सेक्शन"] + (existing_secs if existing_secs else ["A", "B", "C"])
    with c_v_top2:
        v_section = st.selectbox("2. सेक्शन चुनें:", all_sec_options, key="viewer_sec_sel")

    if v_section != "सभी सेक्शन" and not v_students_df.empty:
        filtered_df = v_students_df[v_students_df["Section"] == v_section].copy()
    else:
        filtered_df = v_students_df.copy()

    # FIX: Robustly detect entered students and compute marks dynamically (eliminating 0/600 sync lag)
    data_entered_students = []
    if not filtered_df.empty:
        for _, s in filtered_df.iterrows():
            r = s["Roll_No"]
            if r in v_evals and "marks" in v_evals[r]:
                data_entered_students.append(s)

    with c_v_top3:
        render_html(f'''
        <div style="border: 1px solid #93C5FD; background: #EFF6FF; padding: 8px 12px; border-radius: 6px; text-align: center; margin-top: 15px;">
            <span style="font-size: 13px; color: #1E3A8A; font-weight: bold;">डेटा प्रविष्टि स्थिति:</span><br>
            <span style="font-size: 16px; font-weight: 800; color: #008000;">{len(data_entered_students)}</span> / {len(filtered_df)} छात्र पूर्ण
        </div>
        ''')
    st.divider()

    if st.session_state.active_dossier_roll is None:
        st.subheader(f"📋 {v_class} — पंजीकृत विद्यार्थियों की सूची")
        if not data_entered_students:
            st.info(f"ℹ️ {v_class} में अभी किसी विद्यार्थी के अंक दर्ज नहीं हैं।")
        else:
            for idx, s in enumerate(data_entered_students):
                r = s["Roll_No"]
                ev = v_evals.get(r, {})
                m_dict = ev.get("marks", {})
                
                # FIX: Compute dynamic total even if pre-computed total key was not refreshed
                tot_obt = 0
                all_p = True
                for sub in v_subjects:
                    se = m_dict.get(sub["id"], {})
                    t_sub = se.get("total")
                    if t_sub is None:
                        t_sub = se.get("half_yearly", 0) + se.get("annual", 0) + se.get("project", 0)
                    tot_obt += int(t_sub)
                    if int(t_sub) < 33: all_p = False

                pct = round((tot_obt / v_max_total) * 100, 1) if v_max_total else 0
                grd = calculate_grade(pct) if ev.get("status", "Present") != "Absent" else "Ab"
                is_p = (all_p and pct >= 33 and ev.get("status", "Present") != "Absent")
                res_col = "#008000" if is_p else "#CC0000"

                card_c1, card_c2, card_c3 = st.columns([4, 3, 2])
                with card_c1:
                    st.markdown(f"**{s['Name']}** (रोल नंबर: `{r}`) | पिता: {s.get('Father_Name','--')}")
                with card_c2:
                    st.markdown(f"प्राप्तांक: **{tot_obt}/{v_max_total}** ({pct}%) | परिणाम: <b style='color:{res_col}'>{'PASS' if is_p else 'FAIL'}</b> | ग्रेड: **{grd}**", unsafe_allow_html=True)
                with card_c3:
                    if st.button("👁️ पूरा डेटा देखें", key=f"btn_dossier_{v_class}_{r}", use_container_width=True):
                        st.session_state.active_dossier_roll = r
                        st.rerun()
                st.markdown("<hr style='margin:4px 0;'>", unsafe_allow_html=True)
    else:
        cur_sel_roll = st.session_state.active_dossier_roll
        target_student = v_students_df[v_students_df["Roll_No"] == cur_sel_roll].iloc[0]
        t_ev = v_evals.get(cur_sel_roll, {})
        t_marks = t_ev.get("marks", {})

        c_bk1, c_bk2 = st.columns([4, 1])
        with c_bk1:
            st.subheader(f"👤 {target_student['Name']} (Roll {cur_sel_roll}) का संपूर्ण रिकॉर्ड")
        with c_bk2:
            if st.button("⬅️ सूची पर वापस", use_container_width=True):
                st.session_state.active_dossier_roll = None
                st.rerun()

        exam_table_rows = []
        tot_all = 0
        all_p = True
        for sub in v_subjects:
            se = t_marks.get(sub["id"], {})
            hy = se.get("half_yearly", 0)
            yr = se.get("annual", 0)
            t_sub = se.get("total", hy + yr)
            g_sub = se.get("grade", calculate_grade(t_sub))
            tot_all += int(t_sub)
            if int(t_sub) < 33: all_p = False
            exam_table_rows.append({
                "विषय": sub["name"],
                "अर्धवार्षिक": hy,
                "वार्षिक लिखित": yr,
                "कुल प्राप्तांक [100]": t_sub,
                "ग्रेड": g_sub
            })
        st.dataframe(pd.DataFrame(exam_table_rows), use_container_width=True)

        tot_pct = round((tot_all / v_max_total) * 100, 1) if v_max_total else 0
        m_c1, m_c2, m_c3, m_c4 = st.columns(4)
        m_c1.metric("कुल प्राप्तांक", f"{tot_all} / {v_max_total}")
        m_c2.metric("प्रतिशत", f"{tot_pct}%")
        m_c3.metric("ग्रेड", calculate_grade(tot_pct))
        m_c4.metric("परिणाम", "PASS" if (all_p and tot_pct >= 33) else "FAIL")

# ----------------- MODULE 6: MONTHLY EVALUATION REGISTER -----------------
elif menu == T.get("nav_monthly_test", "📝 6. मासिक मूल्यांकन रजिस्टर (Monthly Test — 10 अंक)"):
    cur_role = st.session_state.get("authenticated_role", "PRINCIPAL")
    is_teacher = (cur_role == "TEACHER")
    assigned_cls = st.session_state.get("assigned_class")
    target_mt_class = assigned_cls if (is_teacher and assigned_cls) else selected_class

    st.markdown('<div class="main-header">📝 मासिक मूल्यांकन रजिस्टर (10 अंक)</div>', unsafe_allow_html=True)
    # FIX: Clean formula representation without raw LaTeX rendering error
    st.info("💡 **मासिक टेस्ट निर्देश:** प्रत्येक विषय के अधिकतम **10 अंक** हैं। यहाँ भरे गए अंक 4 माह के योग के आधार पर 4 से विभाजित (कुल योग ÷ 4) होकर 35-कॉलम वाली शीट के **Monthly 10% Weightage** में जुड़ते हैं।")

    mt_cls_data = get_class_data(target_mt_class)
    students_df = mt_cls_data["students"]
    cls_subjects = get_class_subjects(target_mt_class)
    available_months = get_class_monthly_test_months(target_mt_class)
    selected_month_id = st.selectbox("मूल्यांकन माह चुनें:", [m["id"] for m in available_months], format_func=lambda x: dict((m["id"], m["name"]) for m in available_months)[x])

    if students_df.empty:
        st.warning(f"⚠️ {target_mt_class} में कोई छात्र पंजीकृत नहीं है।")
    else:
        mt_rows = []
        mt_evals = mt_cls_data["evaluations"]
        for _, s in students_df.iterrows():
            r = s["Roll_No"]
            ev = mt_evals.get(r, {})
            cur_month_marks = ev.get("monthly_tests", {}).get(selected_month_id, {})
            row = {"Roll_No": r, "Name": s["Name"]}
            for sub in cls_subjects:
                row[sub["name"]] = int(cur_month_marks.get(sub["id"], 8))
            mt_rows.append(row)

        edited_mt_df = st.data_editor(pd.DataFrame(mt_rows), use_container_width=True, key=f"mt_ed_{target_mt_class}_{selected_month_id}")
        if st.button("💾 मासिक अंक सुरक्षित करें", type="primary"):
            for _, erow in edited_mt_df.iterrows():
                r = erow["Roll_No"]
                if r not in mt_evals: mt_evals[r] = {"marks": {}, "monthly_tests": {}}
                if "monthly_tests" not in mt_evals[r]: mt_evals[r]["monthly_tests"] = {}
                if selected_month_id not in mt_evals[r]["monthly_tests"]: mt_evals[r]["monthly_tests"][selected_month_id] = {}
                for sub in cls_subjects:
                    mt_evals[r]["monthly_tests"][selected_month_id][sub["id"]] = int(erow[sub["name"]])
            save_data_to_disk()
            st.success("✅ मासिक अंक सुरक्षित एवं अधिभार अपडेट!")
            st.rerun()

# ----------------- MODULE 7: QUARTERLY EXAMINATION (MPBSE 5% WEIGHTAGE) -----------------
elif menu == T.get("nav_quarterly", "📑 7. त्रैमासिक परीक्षा मूल्यांकन (Quarterly Exam — MPBSE 5% अधिभार)"):
    clean_qcls = str(selected_class).lower().strip()
    is_9_or_10 = any(k in clean_qcls for k in ["class 9", "class 10", "9th", "10th", "कक्षा 9", "कक्षा 10"])

    st.markdown('<div class="main-header">📑 त्रैमासिक परीक्षा मूल्यांकन पंजी (Quarterly Exam)</div>', unsafe_allow_html=True)
    
    if is_9_or_10:
        st.info("💡 **MPBSE हाईस्कूल (कक्षा 9वीं व 10वीं) शासकीय नियम:** 75 अंक सैद्धांतिक बोर्ड परीक्षा + 25 अंक आंतरिक मूल्यांकन। आंतरिक मूल्यांकन के 25 अंकों में **त्रैमासिक परीक्षा के प्राप्तांक का 5% अधिभार (अधिकतम 05 अंक)**, **अर्धवार्षिक परीक्षा का 5% अधिभार (अधिकतम 05 अंक)**, एवं **प्रायोजना कार्य / प्रैक्टिकल के 15 अंक** सम्मिलित होते हैं (5 + 5 + 15 = 25 अंक)।")
    else:
        st.info("💡 **त्रैमासिक परीक्षा मूल्यांकन:** यहाँ विद्यार्थियों के त्रैमासिक परीक्षा के विषयवार प्राप्तांक दर्ज किए जाते हैं तथा निर्धारित अधिभार की स्वतः गणना होती है।")

    q_cls_data = get_class_data(selected_class)
    students_df = q_cls_data["students"]
    cls_subjects = get_class_subjects(selected_class)
    q_evals = q_cls_data["evaluations"]

    if students_df.empty:
        st.warning("⚠️ कक्षा में कोई विद्यार्थी पंजीकृत नहीं है।")
    else:
        col_q1, col_q2 = st.columns([2, 2])
        with col_q1:
            q_max_marks = st.selectbox(
                "त्रैमासिक परीक्षा पूर्णांक (Max Marks per Subject):",
                [75, 100, 50],
                index=0 if is_9_or_10 else 1,
                help="MPBSE बोर्ड परीक्षा प्रारूप हेतु सामान्यतः 75 अंक का प्रश्नपत्र होता है।"
            )
        with col_q2:
            st.markdown(f"**निर्धारित आंतरिक अधिभार:** `5% (अधिकतम 05 अंक प्रति विषय)`")

        q_rows = []
        for _, s in students_df.iterrows():
            r = s["Roll_No"]
            ev = q_evals.get(r, {})
            m_dict = ev.get("marks", {})
            row = {"Roll_No": r, "Name": s["Name"]}
            for sub in cls_subjects:
                raw_q = m_dict.get(sub["id"], {}).get("quarterly", int(q_max_marks * 0.70))
                w_5 = calculate_subject_quarterly_weightage(raw_q, q_max_marks)
                row[sub["name"]] = int(raw_q)
                row[f"{sub['name']}_5%"] = w_5
            q_rows.append(row)

        edited_q = st.data_editor(pd.DataFrame(q_rows), use_container_width=True, key=f"q_ed_{selected_class}")
        
        c_qs1, c_qs2 = st.columns([3, 1])
        with c_qs1:
            if st.button("💾 त्रैमासिक अंक सुरक्षित करें", type="primary"):
                for _, erow in edited_q.iterrows():
                    r = erow["Roll_No"]
                    if r not in q_evals: q_evals[r] = {"marks": {}}
                    if "marks" not in q_evals[r]: q_evals[r]["marks"] = {}
                    for sub in cls_subjects:
                        if sub["id"] not in q_evals[r]["marks"]: q_evals[r]["marks"][sub["id"]] = {}
                        raw_val = int(erow[sub["name"]])
                        q_evals[r]["marks"][sub["id"]]["quarterly"] = raw_val
                        q_evals[r]["marks"][sub["id"]]["quarterly_5%"] = calculate_subject_quarterly_weightage(raw_val, q_max_marks)
                save_data_to_disk()
                st.success("✅ त्रैमासिक प्राप्तांक एवं 5% अधिभार सुरक्षित कर दिए गए!")
                st.rerun()

        # MPBSE 25-Marks Internal Assessment Consolidated Summary for High School (Class 9 & 10)
        if is_9_or_10:
            st.divider()
            st.subheader("🎯 MPBSE 25-अंक आंतरिक मूल्यांकन कंसोलिडेटेड सारांश (Class 10th Internal Assessment)")
            st.caption("यह तालिका त्रैमासिक (5) + अर्धवार्षिक (5) + प्रोजेक्ट (15) = कुल 25 अंक बोर्ड पोर्टल अपलोड हेतु स्वतः समेकित करती है।")
            ia_rows = []
            for _, s in students_df.iterrows():
                r = s["Roll_No"]
                ev = q_evals.get(r, {})
                m_dict = ev.get("marks", {})
                ia_row = {"Roll_No": r, "Scholar_No": s.get("Scholar_No", "--"), "Name": s["Name"]}
                tot_ia = 0
                for sub in cls_subjects:
                    s_id = sub["id"]
                    sub_m = m_dict.get(s_id, {})
                    q_w = sub_m.get("quarterly_5%", calculate_subject_quarterly_weightage(sub_m.get("quarterly", int(q_max_marks*0.7)), q_max_marks))
                    hy_raw = sub_m.get("half_yearly", int(q_max_marks*0.7))
                    hy_w = calculate_subject_quarterly_weightage(hy_raw, q_max_marks)
                    proj_raw = sub_m.get("project", 12)
                    proj_15 = min(15, max(0, int(proj_raw)))
                    sub_ia_total = q_w + hy_w + proj_15
                    tot_ia += sub_ia_total
                    ia_row[f"{sub['name']} [25]"] = f"{sub_ia_total} (Q:{q_w} H:{hy_w} P:{proj_15})"
                ia_row["कुल आंतरिक अंक [150]"] = tot_ia
                ia_row["औसत IA %"] = round((tot_ia / (len(cls_subjects)*25)) * 100, 1) if cls_subjects else 0
                ia_rows.append(ia_row)
            
            ia_df = pd.DataFrame(ia_rows)
            st.dataframe(ia_df, use_container_width=True)
            
            csv_ia = ia_df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
            st.download_button(
                "📥 MPBSE आंतरिक मूल्यांकन (25 अंक) CSV डाउनलोड करें",
                data=csv_ia,
                file_name=f"MPBSE_{selected_class}_Internal_Assessment_25M_{st.session_state.school_info.get('session','2026-27')}.csv",
                mime="text/csv"
            )

# ----------------- MODULE 8: HALF-YEARLY EXAMINATION -----------------
elif menu == T.get("nav_half_yearly", "📑 8. अर्धवार्षिक परीक्षा मूल्यांकन (Half-Yearly Exam — 20%/5% अधिभार)"):
    st.markdown('<div class="main-header">📑 अर्धवार्षिक परीक्षा मूल्यांकन पंजी (20% अधिभार)</div>', unsafe_allow_html=True)
    # FIX: Clean plain text representation
    clean_hcls = str(selected_class).lower().strip()
    is_9_10_hy = any(k in clean_hcls for k in ["class 9", "class 10", "9th", "10th", "कक्षा 9", "कक्षा 10"])

    if is_9_10_hy:
        st.info("💡 **शासकीय नियम (MPBSE हाईस्कूल):** कक्षा 9वीं व 10वीं हेतु अर्धवार्षिक परीक्षा 75 अंक की होती है तथा आंतरिक मूल्यांकन हेतु 5% अधिभार (अधिकतम 05 अंक) की गणना की जाती है।")
    else:
        st.info("💡 **शासकीय नियम (RSKMP):** अर्धवार्षिक परीक्षा 60 अंक की होती है। 20% अधिभार हेतु (प्राप्तांक ÷ 3 = 20%) की गणना की जाती है।")

    hy_cls_data = get_class_data(selected_class)
    students_df = hy_cls_data["students"]
    cls_subjects = get_class_subjects(selected_class)
    hy_evals = hy_cls_data["evaluations"]

    if students_df.empty:
        st.warning("कक्षा में कोई विद्यार्थी नहीं है।")
    else:
        hy_rows = []
        for _, s in students_df.iterrows():
            r = s["Roll_No"]
            ev = hy_evals.get(r, {})
            m_dict = ev.get("marks", {})
            row = {"Roll_No": r, "Name": s["Name"]}
            for sub in cls_subjects:
                raw_m = m_dict.get(sub["id"], {}).get("half_yearly", 52 if is_9_10_hy else 48)
                row[sub["name"]] = int(raw_m)
                if is_9_10_hy:
                    row[f"{sub['name']}_5%"] = calculate_subject_quarterly_weightage(raw_m, 75)
                else:
                    row[f"{sub['name']}_20%"] = calculate_subject_half_yearly_weightage(raw_m, "60")
            hy_rows.append(row)

        edited_hy = st.data_editor(pd.DataFrame(hy_rows), use_container_width=True, key=f"hy_ed_{selected_class}")
        if st.button("💾 अर्धवार्षिक अंक सुरक्षित करें", type="primary"):
            for _, erow in edited_hy.iterrows():
                r = erow["Roll_No"]
                if r not in hy_evals: hy_evals[r] = {"marks": {}}
                if "marks" not in hy_evals[r]: hy_evals[r]["marks"] = {}
                for sub in cls_subjects:
                    if sub["id"] not in hy_evals[r]["marks"]: hy_evals[r]["marks"][sub["id"]] = {}
                    hy_evals[r]["marks"][sub["id"]]["half_yearly"] = int(erow[sub["name"]])
            save_data_to_disk()
            st.success("✅ अर्धवार्षिक प्राप्तांक व 20% अधिभार सुरक्षित!")
            st.rerun()

# ----------------- MODULE 9: ANNUAL PROJECT WORK EVALUATION -----------------
elif menu == T.get("nav_project", "🎨 9. वार्षिक प्रोजेक्ट कार्य मूल्यांकन (Project Work — 10%/15/20 अंक)"):
    st.markdown('<div class="main-header">🎨 वार्षिक प्रोजेक्ट कार्य मूल्यांकन पंजी</div>', unsafe_allow_html=True)
    # FIX: Clean plain text representation
    st.info("💡 **प्रोजेक्ट कार्य मूल्यांकन:** 5वीं व 8वीं बोर्ड हेतु 20 अंक तथा स्थानीय कक्षाओं हेतु 40 अंक (प्राप्तांक ÷ 4 = 10% अधिभार)।")
    pj_cls_data = get_class_data(selected_class)
    students_df = pj_cls_data["students"]
    cls_subjects = get_class_subjects(selected_class)
    pj_evals = pj_cls_data["evaluations"]

    if students_df.empty:
        st.warning("कक्षा में कोई विद्यार्थी नहीं है।")
    else:
        pj_rows = []
        for _, s in students_df.iterrows():
            r = s["Roll_No"]
            ev = pj_evals.get(r, {})
            m_dict = ev.get("marks", {})
            row = {"Roll_No": r, "Name": s["Name"]}
            for sub in cls_subjects:
                raw_pj = m_dict.get(sub["id"], {}).get("project", 32)
                row[sub["name"]] = int(raw_pj)
                row[f"{sub['name']}_अधिभार"] = calculate_subject_project_weightage_rule(raw_pj, selected_class)
            pj_rows.append(row)

        edited_pj = st.data_editor(pd.DataFrame(pj_rows), use_container_width=True, key=f"pj_ed_{selected_class}")
        if st.button("💾 प्रोजेक्ट अंक सुरक्षित करें", type="primary"):
            for _, erow in edited_pj.iterrows():
                r = erow["Roll_No"]
                if r not in pj_evals: pj_evals[r] = {"marks": {}}
                if "marks" not in pj_evals[r]: pj_evals[r]["marks"] = {}
                for sub in cls_subjects:
                    if sub["id"] not in pj_evals[r]["marks"]: pj_evals[r]["marks"][sub["id"]] = {}
                    pj_evals[r]["marks"][sub["id"]]["project"] = int(erow[sub["name"]])
            save_data_to_disk()
            st.success("✅ प्रोजेक्ट अंक सुरक्षित एवं अधिभार अपडेट!")
            st.rerun()

# ----------------- MODULE 10: PRINT MARKSHEET (SHASHKIY PRAGATI PATRAK) -----------------
elif menu == T.get("nav_marksheet", "🖨️ 10. शासकीय वार्षिक प्रगति पत्रक एवं RSKMP/MPBSE पोर्टल केंद्र"):
    s_info = st.session_state.school_info
    cur_sess = s_info.get("session", "2026-27")
    ms_cls_data = get_class_data(selected_class)
    students_df = ms_cls_data["students"]
    cls_subjects = get_class_subjects(selected_class)

    st.markdown('<div class="main-header">🖨️ शासकीय समग्र प्रगति पत्रक एवं पोर्टल केंद्र</div>', unsafe_allow_html=True)
    if students_df.empty:
        st.warning("कक्षा में विद्यार्थी पंजीकृत नहीं हैं।")
    else:
        st_names = [f"Roll {s['Roll_No']}: {s['Name']}" for _, s in students_df.iterrows()]
        sel_st_str = st.selectbox("विद्यार्थी चुनें:", st_names)
        sel_r = int(sel_st_str.split(":")[0].replace("Roll", "").strip())
        stud = students_df[students_df["Roll_No"] == sel_r].iloc[0]
        ev = ms_cls_data["evaluations"].get(sel_r, {})
        m_dict = ev.get("marks", {})

        c_btn1, c_btn2 = st.columns([3, 1])
        with c_btn2:
            st.button("🖨️ Print Marksheet", type="primary", use_container_width=True)

        cur_exam_rule = get_session_exam_rule(cur_sess, selected_class)
        has_proj_comp = any(c["id"] == "project" for c in cur_exam_rule["components"])

        rows_h = ""
        tot_marks = 0
        if has_proj_comp:
            for idx, sub in enumerate(cls_subjects):
                se = m_dict.get(sub["id"], {})
                hy = se.get("half_yearly", 16)
                proj = se.get("project", 16)
                yr = se.get("annual", 48)
                t = se.get("total", hy + proj + yr)
                g = se.get("grade", calculate_grade(t))
                tot_marks += t
                rows_h += f"<tr style='height:28px; text-align:center;'><td style='border:1px solid #000;'>{idx+1}</td><td style='border:1px solid #000; text-align:left; padding-left:8px;'><b>{sub['name']}</b></td><td style='border:1px solid #000;'>{hy}</td><td style='border:1px solid #000;'>{proj}</td><td style='border:1px solid #000;'>{yr}</td><td style='border:1px solid #000; font-weight:bold; color:#1E3A8A;'>{t}</td><td style='border:1px solid #000; font-weight:bold;'>{g}</td></tr>"

            table_header_html = """
                <tr style="background:#F1F5F9; height:30px; font-weight:bold; text-align:center;">
                    <th style="border:1px solid #000; width:6%;">क्र.</th>
                    <th style="border:1px solid #000; text-align:left; padding-left:8px;">विषय (Subject)</th>
                    <th style="border:1px solid #000; width:15%;">अर्धवार्षिक [20]</th>
                    <th style="border:1px solid #000; width:15%;">प्रोजेक्ट कार्य [20]</th>
                    <th style="border:1px solid #000; width:18%;">वार्षिक लिखित [60]</th>
                    <th style="border:1px solid #000; width:16%;">कुल [100]</th>
                    <th style="border:1px solid #000; width:10%;">ग्रेड</th>
                </tr>
            """
            grand_total_row = f"""
                <tr style="background:#FFFDF0; height:32px; font-weight:bold; text-align:center; font-size:13px;">
                    <td colspan="5" style="border:1px solid #000; text-align:right; padding-right:12px;">महायोग (Grand Total):</td>
                    <td style="border:1px solid #000; color:#1E3A8A;">{tot_marks} / {len(cls_subjects) * 100}</td>
                    <td style="border:1px solid #000; color:green;">{calculate_grade(round((tot_marks / (len(cls_subjects)*100))*100, 1) if cls_subjects else 0)}</td>
                </tr>
            """
        else:
            for idx, sub in enumerate(cls_subjects):
                se = m_dict.get(sub["id"], {})
                hy = se.get("half_yearly", 32)
                yr = se.get("annual", 48)
                t = se.get("total", hy + yr)
                g = se.get("grade", calculate_grade(t))
                tot_marks += t
                rows_h += f"<tr style='height:28px; text-align:center;'><td style='border:1px solid #000;'>{idx+1}</td><td style='border:1px solid #000; text-align:left; padding-left:8px;'><b>{sub['name']}</b></td><td style='border:1px solid #000;'>{hy}</td><td style='border:1px solid #000;'>{yr}</td><td style='border:1px solid #000; font-weight:bold; color:#1E3A8A;'>{t}</td><td style='border:1px solid #000; font-weight:bold;'>{g}</td></tr>"

            table_header_html = """
                <tr style="background:#F1F5F9; height:30px; font-weight:bold; text-align:center;">
                    <th style="border:1px solid #000; width:8%;">क्र.</th>
                    <th style="border:1px solid #000; text-align:left; padding-left:8px;">विषय (Subject)</th>
                    <th style="border:1px solid #000; width:18%;">अर्धवार्षिक [40]</th>
                    <th style="border:1px solid #000; width:18%;">वार्षिक परीक्षा [60]</th>
                    <th style="border:1px solid #000; width:18%;">कुल [100]</th>
                    <th style="border:1px solid #000; width:12%;">ग्रेड</th>
                </tr>
            """
            grand_total_row = f"""
                <tr style="background:#FFFDF0; height:32px; font-weight:bold; text-align:center; font-size:13px;">
                    <td colspan="4" style="border:1px solid #000; text-align:right; padding-right:12px;">महायोग (Grand Total):</td>
                    <td style="border:1px solid #000; color:#1E3A8A;">{tot_marks} / {len(cls_subjects) * 100}</td>
                    <td style="border:1px solid #000; color:green;">{calculate_grade(round((tot_marks / (len(cls_subjects)*100))*100, 1) if cls_subjects else 0)}</td>
                </tr>
            """

        max_m = len(cls_subjects) * 100
        pct = round((tot_marks / max_m) * 100, 1) if max_m else 0

        marksheet_html = f"""
        <div class="printable-area" style="background:#ffffff; border:3px double #1E3A8A; padding:20px; max-width:850px; margin:auto; color:#000;">
            <div style="text-align:center; margin-bottom:15px;">
                <div style="font-size:14px; font-weight:bold; color:#1E3A8A;">मध्य प्रदेश शासन • स्कूल शिक्षा विभाग</div>
                <div style="font-size:22px; font-weight:900; color:#0F172A; text-transform:uppercase;">समग्र प्रगति पत्रक (Holistic Progress Card)</div>
                <div style="font-size:16px; font-weight:bold; color:#1E3A8A;">{s_info.get('name','')}</div>
                <div style="font-size:12px; color:#555;">DISE: {s_info.get('udise','')} | ब्लॉक: {s_info.get('block','')} | जिला: {s_info.get('district','')} | सत्र: {cur_sess}</div>
            </div>
            <table style="width:100%; border-collapse:collapse; border:1px solid #000; font-size:12px; margin-bottom:12px; background:#f8fafc;">
                <tr>
                    <td style="border:1px solid #000; padding:6px;"><b>विद्यार्थी का नाम:</b> {stud['Name']}</td>
                    <td style="border:1px solid #000; padding:6px;"><b>अनुक्रमांक (Roll No):</b> <b style="color:#B91C1C; font-size:14px;">{stud['Roll_No']}</b></td>
                </tr>
                <tr>
                    <td style="border:1px solid #000; padding:6px;"><b>पिता का नाम:</b> {stud['Father_Name']}</td>
                    <td style="border:1px solid #000; padding:6px;"><b>दाखिला क्र. (Scholar):</b> {stud.get('Scholar_No','--')}</td>
                </tr>
                <tr>
                    <td style="border:1px solid #000; padding:6px;"><b>माता का नाम:</b> {stud['Mother_Name']}</td>
                    <td style="border:1px solid #000; padding:6px;"><b>समग्र आईडी:</b> {stud.get('SSSM_ID','--')}</td>
                </tr>
                <tr>
                    <td style="border:1px solid #000; padding:6px;"><b>कक्षा व वर्ग:</b> {selected_class} - {stud.get('Section','A')}</td>
                    <td style="border:1px solid #000; padding:6px;"><b>जन्मतिथि:</b> {stud.get('DOB','--')}</td>
                </tr>
            </table>
            <table style="width:100%; border-collapse:collapse; border:1px solid #000; font-size:12px; margin-bottom:12px;">
                {table_header_html}
                {rows_h}
                {grand_total_row}
            </table>
            <div style="display:flex; justify-content:space-between; margin-top:40px; text-align:center; font-size:12px; font-weight:bold;">
                <div>_________________________<br>कक्षा अध्यापक हस्ताक्षर</div>
                <div>_________________________<br>परीक्षा प्रभारी</div>
                <div>_________________________<br>संस्था प्रधान (मुद्रा सहित)</div>
            </div>
        </div>
        """
        render_html(marksheet_html)

# ----------------- MODULE 11: A3 ANNUAL RESULT SHEET -----------------
elif menu == T["nav_a3_result"]:
    students_df = cls_data["students"]
    s_info = st.session_state.school_info
    cls_subjects = get_class_subjects(selected_class)
    sub_count = len(cls_subjects)
    max_total = sub_count * 100

    cur_exam_rule = get_session_exam_rule(s_info.get("session", "2026-27"), selected_class)
    has_proj_comp = any(c["id"] == "project" for c in cur_exam_rule["components"])

    c_a3_top1, c_a3_top2 = st.columns([3, 1])
    with c_a3_top1:
        render_html('<div style="border: 2px solid #008000; padding: 6px 14px; background: #fff; display: inline-block;"><span style="color: #CC0000; font-weight: 800; font-size: 14px;">*इस परीक्षाफल पत्रक को अनुमोदन हेतु A-3 साइज़ के पेपर पर प्रिंट करें</span></div>')
    with c_a3_top2:
        st.button("🖨️ Print A3 Sheet", use_container_width=True, type="primary")

    student_rows_a3 = ""
    for idx, s in students_df.iterrows():
        r_no = s["Roll_No"]
        ev = cls_data["evaluations"].get(r_no, {})
        tot_obt = 0
        all_p = True
        hy_c, pr_c, yr_c, fn_c = "", "", "", ""
        for sub in cls_subjects:
            se = ev.get("marks", {}).get(sub["id"], {})
            h = se.get("half_yearly", 16 if has_proj_comp else 32)
            p = se.get("project", 16 if has_proj_comp else 0)
            y = se.get("annual", 48)
            t = se.get("total", (h + p + y) if has_proj_comp else (h + y))
            tot_obt += t
            
            # RSKMP / MPBSE Statutory Passing Rule:
            if has_proj_comp:
                if h < 7 or p < 7 or y < 20 or t < 33:
                    all_p = False
            else:
                if h < 13 or y < 20 or t < 33:
                    all_p = False

            hy_c += f'<td style="border:1px solid #000; padding:2px;">{h}</td>'
            if has_proj_comp:
                pr_c += f'<td style="border:1px solid #000; padding:2px;">{p}</td>'
            yr_c += f'<td style="border:1px solid #000; padding:2px;">{y}</td>'
            fn_c += f'<td style="border:1px solid #000; padding:2px; font-weight:bold; color:green;">{t}</td>'

        pct = round((tot_obt / max_total) * 100, 1) if max_total else 0
        grd = calculate_grade(pct)
        is_p = (all_p and pct >= 33)
        res_col = "green" if is_p else "red"

        student_rows_a3 += f"""
        <tr style="height:26px; font-size:11px; text-align:center;">
            <td style="border:1px solid #000;">{idx+1}</td>
            <td style="border:1px solid #000; font-weight:bold;">{r_no}</td>
            <td style="border:1px solid #000;">{s['Scholar_No']}</td>
            <td style="border:1px solid #000; text-align:left; padding:2px 5px; font-weight:bold; white-space:nowrap;">{s['Name']}</td>
            <td style="border:1px solid #000; text-align:left; padding:2px 5px; white-space:nowrap;">{s['Mother_Name']}</td>
            <td style="border:1px solid #000; text-align:left; padding:2px 5px; white-space:nowrap;">{s['Father_Name']}</td>
            <td style="border:1px solid #000; white-space:nowrap;">{s['DOB']}</td>
            <td style="border:1px solid #000;">{s['Gender']}</td>
            <td style="border:1px solid #000;">{s['Category']}</td>
            <td style="border:1px solid #000;">{s['SSSM_ID']}</td>
            <td style="border:1px solid #000;">{s.get('Aadhar_No','')}</td>
            {hy_c}{pr_c}{yr_c}{fn_c}
            <td style="border:1px solid #000; font-weight:bold; color:green;">{tot_obt}</td>
            <td style="border:1px solid #000; font-weight:bold; color:{res_col};">{'Pass' if is_p else 'Fail'}</td>
            <td style="border:1px solid #000; font-weight:bold; color:green;">{pct}%</td>
            <td style="border:1px solid #000; font-weight:bold;">{grd}</td>
            <td style="border:1px solid #000;">{idx+1}</td>
            <td style="border:1px solid #000;">{s.get('Attended_Days',200)}/{s.get('Total_Days',220)}</td>
        </tr>
        """

    sub_ths_hy = "".join([f'<th class="v-th-tall">{sub["name"]}</th>' for sub in cls_subjects])
    sub_ths_pr = "".join([f'<th class="v-th-tall">{sub["name"]}</th>' for sub in cls_subjects]) if has_proj_comp else ""
    sub_ths_yr = "".join([f'<th class="v-th-tall">{sub["name"]}</th>' for sub in cls_subjects])
    sub_ths_fn = "".join([f'<th class="v-th-tall">{sub["name"]}</th>' for sub in cls_subjects])

    if has_proj_comp:
        a3_component_headers = f"""
                    <th colspan="{sub_count}" style="border:1px solid #000;">Half Yearly [20]</th>
                    <th colspan="{sub_count}" style="border:1px solid #000;">Project Work [20]</th>
                    <th colspan="{sub_count}" style="border:1px solid #000;">Annual Written [60]</th>
                    <th colspan="{sub_count}" style="border:1px solid #000;">Final Assessment [100]</th>
        """
    else:
        a3_component_headers = f"""
                    <th colspan="{sub_count}" style="border:1px solid #000;">Half Yearly [40]</th>
                    <th colspan="{sub_count}" style="border:1px solid #000;">Annual Written [60]</th>
                    <th colspan="{sub_count}" style="border:1px solid #000;">Final Assessment [100]</th>
        """

    a3_html = f"""
    <div class="printable-area a3-box">
        <div style="font-size:22px; font-weight:900; margin-bottom:8px;">ANNUAL RESULT SHEET {s_info.get('session','2026-27')}</div>
        <table class="a3-table" style="width:100%; border-collapse:collapse; border:1px solid #000;">
            <thead>
                <tr style="background:#f8fafc; font-weight:bold;">
                    <th rowspan="2" class="v-th-tall">Sr.No.</th>
                    <th rowspan="2" class="v-th-tall">Roll No.</th>
                    <th rowspan="2" class="v-th-tall">Scholar No.</th>
                    <th rowspan="2" style="border:1px solid #000; min-width:140px;">Name Of Student</th>
                    <th rowspan="2" style="border:1px solid #000; min-width:110px;">Mother's Name</th>
                    <th rowspan="2" style="border:1px solid #000; min-width:110px;">Father's Name</th>
                    <th rowspan="2" style="border:1px solid #000; min-width:85px;">DOB</th>
                    <th rowspan="2" class="v-th-tall">Gender</th>
                    <th rowspan="2" class="v-th-tall">Category</th>
                    <th rowspan="2" class="v-th-tall">Samagra ID</th>
                    <th rowspan="2" style="border:1px solid #000; min-width:85px;">Aadhar No.</th>
                    {a3_component_headers}
                    <th rowspan="2" class="v-th-tall">Total Obtained</th>
                    <th rowspan="2" class="v-th-tall">Result</th>
                    <th rowspan="2" class="v-th-tall">Percentage</th>
                    <th rowspan="2" class="v-th-tall">Grade</th>
                    <th rowspan="2" class="v-th-tall">Rank</th>
                    <th rowspan="2" class="v-th-tall">Attendance</th>
                </tr>
                <tr>
                    {sub_ths_hy}{sub_ths_pr}{sub_ths_yr}{sub_ths_fn}
                </tr>
            </thead>
            <tbody>
                {student_rows_a3}
            </tbody>
        </table>
    </div>
    """
    render_html(a3_html)

# ----------------- MODULE 12: SUMMARY -----------------
elif menu == T["nav_summary"]:
    st.markdown('<div class="main-header">📊 श्रेणीवार एवं ग्रेडवार परीक्षा परिणाम सारांश</div>', unsafe_allow_html=True)
    st.info("कक्षा का संपूर्ण श्रेणीवार (SC/ST/OBC/GEN) एवं ग्रेडवार सारांश।")
    summary_df = generate_master_44col_df(cls_data["students"], cls_data["evaluations"], get_class_subjects(selected_class), st.session_state.school_info, selected_class)
    st.dataframe(summary_df, use_container_width=True)

# ----------------- MODULE 13: MERIT LIST -----------------
elif menu == T.get("nav_merit", "🏆 13. वार्षिक परीक्षा प्रावीण्य सूची (Merit List)"): 
    st.markdown('<div class="main-header">🏆 वार्षिक परीक्षा प्रावीण्य सूची (Merit List)</div>', unsafe_allow_html=True)
    m_df = cls_data["students"].copy()
    if not m_df.empty:
        records = []
        cls_subs = get_class_subjects(selected_class)
        for _, s in m_df.iterrows():
            ev = cls_data["evaluations"].get(s["Roll_No"], {})
            tot = sum([ev.get("marks", {}).get(sub["id"], {}).get("total", 0) for sub in cls_subs])
            pct = round((tot / (len(cls_subs)*100)) * 100, 1)
            records.append({"Roll_No": s["Roll_No"], "Name": s["Name"], "Father_Name": s["Father_Name"], "Total": tot, "Percentage": pct, "Grade": calculate_grade(pct)})
        res_df = pd.DataFrame(records).sort_values(by="Total", reverse=True)
        res_df["Rank"] = range(1, len(res_df) + 1)
        st.dataframe(res_df[["Rank", "Roll_No", "Name", "Father_Name", "Total", "Percentage", "Grade"]], use_container_width=True)

# ----------------- MODULE 14: SUPPLEMENTARY LIST -----------------
elif menu == T.get("nav_supple", "📋 14. पूरक परीक्षा छात्र सूची (Supplementary List)"): 
    st.markdown('<div class="main-header">📋 पूरक / अनुपूरक परीक्षा छात्र सूची (RSKMP एवं MPBSE नियमानुसार)</div>', unsafe_allow_html=True)
    cls_subs = get_class_subjects(selected_class)
    rule_cfg = get_session_exam_rule(st.session_state.school_info.get("session", "2026-27"), selected_class)
    has_proj = any(c["id"] == "project" for c in rule_cfg["components"])
    
    st.info(f"📌 **लागू शासकीय नियम:** {rule_cfg['name']} | **उत्तीर्णांक मानदंड:** वार्षिक लिखित न्यूनतम 20/60 (33.33%), {'प्रोजेक्ट न्यूनतम 7/20 (33.33%)' if has_proj else 'अर्धवार्षिक न्यूनतम 13/40 (33.33%)'} एवं कुल न्यूनतम 33/100")
    
    supple_data = []
    for _, s in cls_data["students"].iterrows():
        r_no = s["Roll_No"]
        ev = cls_data["evaluations"].get(r_no, {})
        failed_subs = []
        for sub in cls_subs:
            se = ev.get("marks", {}).get(sub["id"], {})
            h = se.get("half_yearly", 16 if has_proj else 32)
            p = se.get("project", 16 if has_proj else 0)
            y = se.get("annual", 48)
            t = se.get("total", (h + p + y) if has_proj else (h + y))
            
            reasons = []
            if has_proj:
                if y < 20: reasons.append(f"वार्षिक लिखित {y}/60 (< 20)")
                if p < 7: reasons.append(f"प्रोजेक्ट {p}/20 (< 7)")
                if h < 7: reasons.append(f"अर्धवार्षिक {h}/20 (< 7)")
                if t < 33: reasons.append(f"कुल प्राप्तांक {t}/100 (< 33)")
            else:
                if y < 20: reasons.append(f"वार्षिक परीक्षा {y}/60 (< 20)")
                if h < 13: reasons.append(f"अर्धवार्षिक {h}/40 (< 13)")
                if t < 33: reasons.append(f"कुल प्राप्तांक {t}/100 (< 33)")
                
            if reasons:
                failed_subs.append(f"{sub['name']} ({', '.join(reasons)})")
        
        if failed_subs:
            fail_count = len(failed_subs)
            supple_status = "पूरक परीक्षा (Supplementary)" if fail_count <= 2 else "अनुत्तीर्ण (Needs Retest / Fail)"
            supple_data.append({
                "Roll_No": r_no,
                "Scholar_No": s.get("Scholar_No", "--"),
                "Name": s["Name"],
                "Father_Name": s["Father_Name"],
                "Failed_Subjects_Count": fail_count,
                "Failed_Subjects_Details": " | ".join(failed_subs),
                "Result_Status": supple_status
            })
            
    if supple_data:
        supple_df = pd.DataFrame(supple_data)
        st.dataframe(supple_df, use_container_width=True)
        st.warning(f"⚠️ कुल **{len(supple_data)}** विद्यार्थी पूरक/पुनः परीक्षा पात्रता में पाए गए हैं।")
    else:
        st.success("🎉 बधाई! कोई भी छात्र पूरक परीक्षा हेतु नहीं है (समस्त छात्र शासकीय न्यूनतम अर्हता अनुसार उत्तीर्ण)!")

# ----------------- MODULE 15: WEIGHTED EVALUATION SHEET -----------------
elif menu == T.get("nav_weighted", "📑 15. वार्षिक परीक्षा परिणाम अभिलेख पत्रक (RSKMP व MPBSE प्रारूप)"): 
    st.markdown('<div class="main-header">📑 वार्षिक परीक्षा परिणाम अभिलेख पत्रक (35-कॉलम वेटेज शीट)</div>', unsafe_allow_html=True)
    w_df = generate_master_44col_df(cls_data["students"], cls_data["evaluations"], get_class_subjects(selected_class), st.session_state.school_info, selected_class)
    st.dataframe(w_df, use_container_width=True)

# ----------------- MODULE 16: SESSION CHANGE & PROMOTION -----------------
elif menu == T["nav_promote"]:
    st.markdown('<div class="main-header">🔄 सत्र परिवर्तन एवं कक्षा पदोन्नति (Session Promotion)</div>', unsafe_allow_html=True)
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        c_sess = st.text_input("वर्तमान सत्र:", value=st.session_state.school_info.get("session", "2023-24"), disabled=True)
    with col_p2:
        parts = c_sess.split("-")
        try:
            y1 = int(parts[0])
            y2 = int(parts[1]) if len(parts) > 1 else y1 + 1
            default_next = f"{y1+1}-{y2+1}"
        except Exception:
            default_next = "2024-25"
        n_sess = st.text_input("आगामी सत्र:", value=default_next)

    if st.button("🚀 सभी पात्र विद्यार्थियों को अगली कक्षा में प्रमोट करें (Promote All)", type="primary"):
        classes = st.session_state.classes_list
        old_store = st.session_state.data_store
        new_store = {}
        for c in classes:
            new_store[c] = {"students": pd.DataFrame(), "evaluations": {}, "monthly_attendance": pd.DataFrame(), "working_days": DEFAULT_WORKING_DAYS}

        for i in range(len(classes) - 1, -1, -1):
            cur_cls = classes[i]
            cur_students = old_store.get(cur_cls, {}).get("students", pd.DataFrame())
            if not cur_students.empty:
                if i < len(classes) - 1:
                    nxt_cls = classes[i + 1]
                    promoted_df = cur_students.copy()
                    promoted_df["Class"] = nxt_cls
                    promoted_df["Roll_No"] = range(101, 101 + len(promoted_df))
                    new_store[nxt_cls]["students"] = promoted_df

        st.session_state.data_store = new_store
        st.session_state.school_info["session"] = n_sess
        save_data_to_disk()
        st.balloons()
        st.success(f"🎉 सभी कक्षाओं के विद्यार्थी आगामी सत्र {n_sess} में प्रमोट हो गए हैं!")
        st.rerun()

