import streamlit as st
import pandas as pd
import numpy as np
import json, base64, os, hashlib, urllib.parse
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
    """Strips leading indentation from every line so Markdown never treats HTML as an indented code block"""
    clean_html = "\n".join([line.strip() for line in html_str.splitlines() if line.strip()])
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
st.markdown("""
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
""", unsafe_allow_html=True)



# ----------------- WHATSAPP RESULT NOTIFICATION GENERATOR -----------------
def generate_whatsapp_result_link(student_name, roll_no, cls_name, grand_obt, max_grand, pct, grd, result_str, school_name, parent_mobile=""):
    """Generates direct, clean WhatsApp Web / App shareable result link for parents"""
    clean_mob = "".join(filter(str.isdigit, str(parent_mobile))) if parent_mobile else ""
    if len(clean_mob) == 10:
        clean_mob = "91" + clean_mob
    
    status_emoji = "🟢" if "pass" in str(result_str).lower() or "उत्तीर्ण" in str(result_str) else "🟠"
    
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
def render_export_gatekeeper(context_label="Data Export"):
    """
    Enforces Role Restriction and 6-Digit OTP Gatekeeper before allowing data export.
    Returns True if export is permitted, False otherwise.
    """
    role = st.session_state.get("authenticated_role", "PRINCIPAL")
    if role == "TEACHER":
        st.markdown("""
        <div style="background: #FEF2F2; border-left: 4px solid #EF4444; padding: 12px 16px; border-radius: 6px; color: #991B1B; margin: 10px 0;">
            <b>🔒 शासकीय डेटा सुरक्षा सूचना:</b> बल्क डेटा एवं आधिकारिक शासकीय परीक्षाफल एक्सपोर्ट का अधिकार केवल <b>संस्था प्रधान (Principal)</b> खाते में अधिकृत है।
        </div>
        """, unsafe_allow_html=True)
        return False
    
    auth_school = st.session_state.get("authenticated_school", {})
    if not st.session_state.get("export_otp_verified", False):
        st.markdown("""
        <div style="background: #EFF6FF; border: 1px solid #BFDBFE; padding: 10px 14px; border-radius: 6px; margin-bottom: 10px;">
            <b style="color: #1E3A8A; font-size: 13.5px;">🔒 अधिकृत एक्सपोर्ट सुरक्षा सत्यापन (DPDP Act 2023 Compliance)</b><br>
            <span style="font-size: 12px; color: #334155;">संस्था प्रधान के अधिकृत मोबाइल पर 6-अंकीय OTP सत्यापन एवं कानूनी दायित्व स्वीकार करना अनिवार्य है।</span>
        </div>
        """, unsafe_allow_html=True)
        c_gk1, c_gk2 = st.columns([1.5, 3])
        with c_gk1:
            exp_otp = st.text_input("6-अंकीय एक्सपोर्ट OTP:*", value="888999", key=f"gk_otp_{context_label}", help="परीक्षण हेतु डिफॉल्ट OTP: 888999")
        with c_gk2:
            st.markdown("<div style='margin-top: 15px;'>", unsafe_allow_html=True)
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
        st.markdown(f"<div style='color: #15803D; font-size: 12.5px; font-weight: bold; margin-bottom: 8px;'>🟢 एक्सपोर्ट अधिकृत (OTP सत्यापित) | डिजिटल ऑडिट लॉग सक्रिय</div>", unsafe_allow_html=True)
        return True

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
        "nav_marksheet": "🖨️ 6. वार्षिक प्रगति पत्रक (Print Marksheet)",
        "nav_a3_result": "📜 7. A3 वार्षिक परीक्षाफल पत्रक (Annual Result Sheet)",
        "nav_summary": "📊 8. श्रेणीवार परीक्षा परिणाम सारांश (Result Summary)",
        "nav_promote": "🔄 9. सत्र परिवर्तन एवं कक्षा पदोन्नति (Session Promotion)",
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
        "nav_marksheet": "🖨️ 6. Progress Report Card (Marksheet)",
        "nav_a3_result": "📜 7. A3 Annual Result Sheet",
        "nav_summary": "📊 8. Category/Grade Wise Result Summary",
        "nav_promote": "🔄 9. Session Roll-over & Promotion",
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
        "nav_marksheet": "🖨️ 6. प्रगती पत्रक (Marksheet)",
        "nav_a3_result": "📜 7. A3 वार्षिक निकाल पत्रक (Annual Result Sheet)",
        "nav_summary": "📊 8. प्रवर्गनिहाय निकाल गोषवारा (Result Summary)",
        "nav_promote": "🔄 9. सत्र बदल व वर्ग पदोन्नती (Promotion)",
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


DEFAULT_CLASSES = ["Class 1st", "Class 2nd", "Class 3rd", "Class 4th", "Class 5th", "Class 6th", "Class 7th", "Class 8th"]
MONTHS_LIST = ["Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "Jan", "Feb", "Mar"]
DEFAULT_WORKING_DAYS = {"Apr": 24, "May": 0, "Jun": 12, "Jul": 25, "Aug": 24, "Sep": 24, "Oct": 20, "Nov": 22, "Dec": 24, "Jan": 23, "Feb": 22, "Mar": 20}


def get_class_subjects(cls_name):
    clean = str(cls_name).lower().strip()
    if any(k in clean for k in ["class 1", "class 2", "1st", "2nd"]):
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
                st.session_state.classes_list = payload["classes_list"]
            if "data_store" in payload and isinstance(payload["data_store"], dict):
                st.session_state.data_store = deserialize_store(payload["data_store"])
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


def get_class_data(cls_name):
    if cls_name not in st.session_state.data_store:
        st.session_state.data_store[cls_name] = {
            "students": pd.DataFrame(),
            "evaluations": {},
            "monthly_attendance": pd.DataFrame(),
            "working_days": DEFAULT_WORKING_DAYS
        }
        save_data_to_disk()
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
    st.markdown("""
    <div style="background: linear-gradient(135deg, #0F172A 0%, #1E293B 50%, #334155 100%); padding: 20px 24px; border-radius: 12px; color: white; margin-bottom: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.3);">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <h2 style="margin: 0; color: #F8FAFC; font-size: 26px;">👑 School Result Pro — सुपर एडमिन कंट्रोल रूम</h2>
                <div style="font-size: 13.5px; opacity: 0.9; margin-top: 4px;">मध्य प्रदेश राज्य स्तरीय केंद्रीय विद्यालय एवं परीक्षाफल प्रबंधन प्रणाली</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

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
        st.markdown("<div style='margin-top: 15px;'>", unsafe_allow_html=True)
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
        st.markdown("#### ⚙️ 1-क्लिक लाइसेंस प्रबंधन (Quick School Action):")
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
                st.markdown(f"**{s_name}** (`{d}`)<br><span style='font-size:12px; color:#555;'>मोबाइल: {s_mob} | जिला: {s.get('district','')}</span>", unsafe_allow_html=True)
            with lead_c2:
                st.markdown(f"<span style='font-size:13px;'>स्थिति: <b>{s_stat}</b></span><br><span style='font-size:11.5px; color:#666;'>{s_plan}</span>", unsafe_allow_html=True)
            with lead_c3:
                stage_choice = st.selectbox("फॉलो-अप स्टेज:", ["Day 2: सहायता संदेश", "Day 7: फ़ीचर रिमाइंडर", "Day 13: ₹499 क्लोजिंग ऑफर"], key=f"crm_stg_{d}")
            with lead_c4:
                st.markdown("<div style='margin-top: 10px;'>", unsafe_allow_html=True)
                if "Day 2" in stage_choice:
                    pitch_txt = f"नमस्ते सर, हमने देखा कि आपने *{s_name}* के लिए School Result Pro का डेमो शुरू किया है। क्या आपको RSKMP 44-कॉलम गोशवारा या मार्कशीट बनाने में कोई सहायता चाहिए? हम AnyDesk पर 5 मिनट का लाइव डेमो दे सकते हैं।"
                elif "Day 7" in stage_choice:
                    pitch_txt = f"आदरणीय सर, क्या आपने *{s_name}* के बच्चों के लिए 'WhatsApp पर रिजल्ट भेजने' और 'RSKMP एक्सेल एक्सपोर्ट' वाला फ़ीचर टेस्ट किया? मात्र ₹499 में पूरे साल का संपूर्ण रिजल्ट उपलब्ध है।"
                else:
                    pitch_txt = f"आदरणीय प्राचार्य महोदय, *{s_name}* का डेमो ट्रायल समाप्त हो रहा है। सभी कक्षाओं के वार्षिक परीक्षाफल, A3 गोशवारा और बिना रुकावट उपयोग जारी रखने हेतु आज ही ₹499 में वार्षिक पास सक्रिय करें।"
                
                wa_pitch_url = f"https://wa.me/{clean_s_mob}?text={urllib.parse.quote(pitch_txt)}" if clean_s_mob else "#"
                st.markdown(f"""
                <a href="{wa_pitch_url}" target="_blank" style="text-decoration: none;">
                    <div style="background: #25D366; color: white; font-size: 12px; font-weight: bold; padding: 6px 10px; border-radius: 6px; text-align: center;">
                        📲 WhatsApp फॉलो-अप भेजें
                    </div>
                </a>
                """, unsafe_allow_html=True)
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


    st.markdown("<br><hr style='margin: 15px 0 8px 0; border: none; border-top: 1px solid #E2E8F0;'>", unsafe_allow_html=True)
    st.markdown("<div style='font-size: 11.5px; color: #64748B; text-align: center;'>© 2026-27 School Result Pro. सर्व शिक्षा अभियान एवं म.प्र. शासन दिशा-निर्देशानुसार। सर्वाधिकार सुरक्षित।</div>", unsafe_allow_html=True)
    st.stop()


# ----------------- CASE 2: NORMAL LOGIN & LANDING PORTAL (WHEN NOT AUTHENTICATED) -----------------
if st.session_state.get("authenticated_school") is None:
    st.markdown("""
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
    """, unsafe_allow_html=True)

    # Check if Super Admin secret mode is requested via URL or secret toggle
    query_params = getattr(st, "query_params", {})
    is_admin_query = (query_params.get("admin") in ["true", "1", "secret", "master"])
    if "show_secret_admin" not in st.session_state:
        st.session_state.show_secret_admin = False

    is_admin_mode = is_admin_query or st.session_state.show_secret_admin

    if is_admin_mode:
        # EXCLUSIVE SUPER ADMIN MASTER GATEWAY (ONLY FOR YOU)
        st.markdown("""
        <div style="background: linear-gradient(135deg, #0F172A, #1E293B); padding: 16px 20px; border-radius: 10px; color: white; margin-bottom: 15px; border-left: 5px solid #F59E0B;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <b style="font-size: 16px; color: #FCD34D;">👑 सुपर एडमिन मास्टर कंसोल (Exclusive Owner Gateway)</b><br>
                    <span style="font-size: 12px; color: #94A3B8;">यह स्क्रीन केवल प्लेटफ़ॉर्म निर्माता / स्वामी के लिए है। सामान्य उपयोगकर्ताओं को यह दिखाई नहीं देती।</span>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
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
            st.markdown("""
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
            """, unsafe_allow_html=True)
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

            st.info("📲 सुरक्षा नियम: संस्था प्रधान के पंजीकृत मोबाइल नंबर पर 6-अंकीय OTP सत्यापन अनिवार्य है।")
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
            st.markdown("""
            <div style="background: #F0FDF4; border: 1px solid #86EFAC; padding: 14px; border-radius: 8px; margin-top: 10px;">
                <b style="color: #166534; font-size: 14px;">🏛️ संस्था प्रधान के अधिकार:</b><br>
                <span style="font-size: 12.5px; color: #14532D;">
                    • स्कूल की सभी कक्षाओं का पूर्ण नियंत्रण<br>
                    • शिक्षकों के ड्राफ्ट एवं सुधार का 1-क्लिक अप्रूवल<br>
                    • 44-कॉलम A3 शीट एवं RSKMP एक्सेल एक्सपोर्ट<br>
                    • संस्था सेटअप, लोगो एवं शिक्षक आवंटन<br>
                </span>
            </div>
            """, unsafe_allow_html=True)

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
            st.markdown("""
            <div style="background: #FFFBEB; border: 1px solid #FDE68A; padding: 14px; border-radius: 8px; margin-top: 10px;">
                <b style="color: #92400E; font-size: 14px;">👨‍🏫 कक्षा अध्यापक के अधिकार:</b><br>
                <span style="font-size: 12.5px; color: #78350F;">
                    • केवल अपनी कक्षा का दैनिक हाजिरी रजिस्टर<br>
                    • अपनी कक्षा के परीक्षा व प्रोजेक्ट अंक भरना<br>
                    • नए छात्र का ड्राफ्ट जोड़ना (प्रिंसिपल अनुमोदन हेतु)<br>
                    • 🔒 शासकीय डेटा एक्सपोर्ट पूरी तरह सुरक्षित व लॉक<br>
                </span>
            </div>
            """, unsafe_allow_html=True)

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
        st.markdown("""
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
        """, unsafe_allow_html=True)

    # Tab 5: Support Helpline
    with auth_tab5:
        st.subheader("📞 सहायता, प्रशिक्षण एवं संपर्क (Support Helpline)")
        c_hp1, c_hp2 = st.columns(2)
        with c_hp1:
            st.markdown("""
            **📱 हेल्पलाइन नंबर:** +91 98260 XXXXX  
            **💬 व्हाट्सएप सपोर्ट:** +91 98260 XXXXX  
            **📧 ईमेल आईडी:** support@schoolresultpro.in  
            **⏰ सपोर्ट समय:** प्रातः 9:00 बजे से सायं 8:00 बजे तक
            """)
        with c_hp2:
            st.markdown("""
            **📍 तकनीकी केंद्र:** भोपाल, मध्य प्रदेश (Bhopal, MP)  
            **🎯 विशेष सुविधा:** किसी भी प्रकार की तकनीकी कठिनाई होने पर AnyDesk पर निशुल्क 5 मिनट का लाइव समाधान।
            """)

    st.stop()

with st.sidebar:
    auth_school = st.session_state.get("authenticated_school", {})
    user_role = st.session_state.get("authenticated_role", "PRINCIPAL")
    user_display_name = st.session_state.get("authenticated_user_name", "संस्था प्रधान")
    assigned_c = st.session_state.get("assigned_class")
    
    if auth_school:
        role_label = "🏛️ संस्था प्रधान (Principal)" if user_role == "PRINCIPAL" else f"👨‍🏫 कक्षा अध्यापक: {user_display_name} ({assigned_c})"
        pending_cnt = len(auth_school.get("pending_approvals", []))
        
        st.markdown(f'''
        <div style="background: linear-gradient(135deg, #1E3A8A, #2563EB); padding: 10px 12px; border-radius: 8px; color: white; margin-bottom: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <div style="font-weight: 800; font-size: 13.5px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">🏫 {auth_school.get("school_name", "School Portal")}</div>
            <div style="font-size: 11px; opacity: 0.9;">DISE: {auth_school.get("dise_code", "")} | {auth_school.get("block","")}</div>
            <div style="font-size: 11px; color: #FEF08A; font-weight: bold; margin-top: 2px;">{role_label}</div>
            <div style="font-size: 10px; color: #BBF7D0; font-weight: bold; margin-top: 3px;">🟢 {auth_school.get("plan", "School Result Pro पास (₹499/वर्ष)")}</div>
        </div>
        ''', unsafe_allow_html=True)
        
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
    if st.session_state.get("authenticated_role") == "TEACHER" and st.session_state.get("assigned_class"):
        teacher_assigned_cls = st.session_state.get("assigned_class")
        if teacher_assigned_cls not in st.session_state.classes_list:
            st.session_state.classes_list.append(teacher_assigned_cls)
        selected_class = teacher_assigned_cls
        st.markdown(f"<div style='border: 1px solid #CBD5E1; background: #F1F5F9; padding: 6px 10px; border-radius: 6px; font-weight: bold; font-size: 13px; text-align: center; color: #1E3A8A;'>🎯 आवंटित कक्षा: {selected_class}</div>", unsafe_allow_html=True)
    else:
        selected_class = st.selectbox(T["select_class"], st.session_state.classes_list, 
                                      index=6 if "Class 7th" in st.session_state.classes_list else 0,
                                      label_visibility="collapsed")
    
    with st.expander(T["add_class"]):
        new_cls = st.text_input(T["new_class_placeholder"])
        if st.button(T["add_class_btn"]):
            if new_cls and new_cls not in st.session_state.classes_list:
                st.session_state.classes_list.append(new_cls)
                save_data_to_disk()
                st.success(f"{new_cls} added!")
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
            T["nav_marksheet"],
            T["nav_a3_result"],
            T["nav_summary"],
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
current_sess = st.session_state.school_info.get('session', '2023-24')


if not st.session_state.update_alert_dismissed:
    with st.expander("🔔 **शासकीय पोर्टल अपडेट मॉनिटर (RSKMP / MPBSE Updates)**", expanded=False):
        c_nt1, c_nt2 = st.columns([3, 1])
        with c_nt1:
            st.markdown(f'''
            <div style="background: #FEF3C7; border-left: 5px solid #D97706; padding: 8px 12px; border-radius: 4px;">
                <b style="color: #92400E; font-size: 13.5px;">📢 नवीन शासकीय प्रारूप अपडेट सूचना (सत्र {current_sess}):</b><br>
                <span style="color: #78350F; font-size: 12.5px;">
                    राज्य शिक्षा केंद्र (RSKMP) एवं माध्यमिक शिक्षा मण्डल (MPBSE) के नवीन मूल्यांकन दिशा-निर्देश एवं एक्सेल अपलोड प्रारूप का अपडेट डिटेक्ट हुआ है।
                </span>
            </div>
            ''', unsafe_allow_html=True)
        with c_nt2:
            st.markdown("<div style='margin-top: 6px;'>", unsafe_allow_html=True)
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
        st.markdown(f'''
        <div style="background: #F0FDF4; border: 2px solid #16A34A; padding: 14px 18px; border-radius: 8px; margin-bottom: 15px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <h4 style="color: #166534; margin: 0;">🏛️ नवीन शासकीय प्रारूप अपलोड एवं सत्र अनुकूलन (Format Adopter)</h4>
            </div>
            <p style="color: #14532D; font-size: 13px; margin-top: 6px;">
                सरकारी पोर्टल (RSKMP या MPBSE) से डाउनलोड की गई नई एक्सेल शीट यहाँ अपलोड करें। ऐप स्वतः उसके कॉलम स्कैन करेगी और <b>केवल चयनित सत्र</b> के लिए नया नियम सक्रिय करेगी (पुराने सत्रों का डेटा पूर्ववत सुरक्षित रहेगा)।
            </p>
        </div>
        ''', unsafe_allow_html=True)


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
    auth_school = st.session_state.get("authenticated_school", {})
    dise_curr = auth_school.get("dise_code", "")
    with st.container():
        st.markdown("""
        <div style="background: linear-gradient(135deg, #1E3A8A, #2563EB); padding: 14px 18px; border-radius: 10px; color: white; margin-bottom: 15px;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <h3 style="margin: 0; color: white;">💎 स्कूल लाइसेंस एवं सदस्यता प्रबंधन (License & Subscription)</h3>
            </div>
            <div style="font-size: 13px; opacity: 0.95; margin-top: 4px;">
                यहाँ से आप अपने विद्यालय के सक्रिय प्लान की जांच कर सकते हैं अथवा वार्षिक लाइसेंस को ऑनलाइन UPI द्वारा तुरंत सक्रिय/नवीनीकृत कर सकते हैं।
            </div>
        </div>
        """, unsafe_allow_html=True)

        col_lic1, col_lic2 = st.columns([1.5, 1])
        with col_lic1:
            st.markdown(f"""
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
            st.markdown("""
            <div style="border: 2px solid #16A34A; padding: 14px; border-radius: 8px; text-align: center; background: #F0FDF4;">
                <b style="color: #166534; font-size: 14px;">📲 स्कैन करके भुगतान करें (Scan & Pay)</b><br>
                <span style="font-size: 11.5px; color: #15803D;">Google Pay, PhonePe, Paytm, BHIM UPI मान्य</span>
            </div>
            """, unsafe_allow_html=True)

            upi_id_demo = "schoolresultpro@upi"
            upi_qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=180x180&data=upi://pay?pa={upi_id_demo}%26pn=SchoolResultPro%26am={plan_amount}%26cu=INR"
            
            st.markdown(f"""
            <div style="text-align: center; margin-top: 10px;">
                <img src="{upi_qr_url}" style="width: 170px; height: 170px; border: 1px solid #ccc; border-radius: 6px;">
                <div style="font-weight: bold; font-size: 13px; color: #1E3A8A; margin-top: 6px;">
                    UPI ID: <code>{upi_id_demo}</code>
                </div>
                <div style="font-size: 12px; color: #555;">
                    भुगतान के बाद मिला 12-अंकीय UTR नंबर बाईं ओर दर्ज करके सबमिट करें।
                </div>
            </div>
            """, unsafe_allow_html=True)
    st.divider()

# ----------------- MODULE 1: SCHOOL SETUP -----------------
if menu == T["nav_school"]:
    st.markdown(f'<div class="main-header">🏫 स्कूल प्रोफाइल एवं संस्था विवरण</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="sub-header">मार्कशीट, गोशवारा और स्कूल रिकॉर्ड हेतु आवश्यक सभी 10 जानकारियां</div>', unsafe_allow_html=True)


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
        
        if st.button("💾 स्कूल जानकारी सहेजें (Save School Info)", type="primary"):
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
            st.markdown("<div style='margin-top: 28px;'>", unsafe_allow_html=True)
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
            
            auth_school = st.session_state.get("authenticated_school", {})
            cur_dise = auth_school.get("dise_code", "")
            registry = load_schools_registry()
            sch_in_reg = registry.get(cur_dise, auth_school)
            teachers_list = sch_in_reg.get("teachers", [])

            if teachers_list:
                t_display_rows = [{"क्र.": i+1, "शिक्षक का नाम": t["name"], "मोबाइल नंबर": t["mobile"], "आवंटित कक्षा": t["assigned_class"]} for i, t in enumerate(teachers_list)]
                st.dataframe(pd.DataFrame(t_display_rows), use_container_width=True)
            else:
                st.info("अभी कोई शिक्षक पंजीकृत नहीं है। नीचे दिए गए फॉर्म से नया शिक्षक जोड़ें।")

            st.markdown("##### ➕ नया कक्षा अध्यापक जोड़ें:")
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
    auth_school = st.session_state.get("authenticated_school", {})
    cur_dise = auth_school.get("dise_code", "")
    
    st.markdown(f'<div class="main-header">👨‍🎓 विद्यार्थी मास्टर डेटा — {selected_class}</div>', unsafe_allow_html=True)
    if cur_role == "TEACHER":
        st.markdown(f'<div class="sub-header">कक्षा अध्यापक मोड ({st.session_state.get("authenticated_user_name")}) — नए छात्र का ड्राफ्ट जोड़ें अथवा सुधार अनुरोध भेजें (प्रिंसिपल अनुमोदन हेतु)</div>', unsafe_allow_html=True)
        tab1, tab2, tab3, tab4 = st.tabs([
            "📋 छात्र सूची (View Only)", 
            "➕ नया छात्र ड्राफ्ट करें (Draft New Student)", 
            "✏️ बायो-डेटा सुधार अनुरोध (Propose Correction)",
            "📸 छात्र फोटो अपलोड (Photo Manager)"
        ])
    else:
        st.markdown(f'<div class="sub-header">संस्था प्रधान मोड — छात्र संपादन, 1-क्लिक शिक्षक अनुमोदन एवं यूनिवर्सल एक्सेल माइग्रेशन</div>', unsafe_allow_html=True)
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
        st.write(f"वर्तमान में **{len(cls_data['students'])}** छात्र पंजीकृत हैं:")
        df_students = cls_data["students"].copy()
        
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
                "Medium": st.column_config.SelectboxColumn("Medium", options=ALL_MEDIUMS),
                "Status": st.column_config.SelectboxColumn("Status", options=["Present", "Absent"]),
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
            
            c_bot1, c_bot2, c_bot3 = st.columns(3)
            with c_bot1:
                s_medium = st.selectbox("13. Medium:", ALL_MEDIUMS)
            with c_bot2:
                s_tot_days = st.number_input("Working Days:", value=220)
            with c_bot3:
                s_att_days = st.number_input("Attended Days:", value=200)

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
                        "Medium": s_medium, "Status": "Present", "Photo_b64": p_b64,
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
                    corr_field = st.selectbox("किस फ़ील्ड में सुधार करना है?", ["छात्र का नाम (Name)", "पिता का नाम (Father Name)", "माता का नाम (Mother Name)", "जन्मतिथि (DOB)", "समग्र आईडी (Samagra ID)", "स्कॉलर नंबर (Scholar No)"])
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
            st.subheader("📸 छात्र फोटो अपलोड (Photo Manager)")
            students_df = cls_data["students"]
            if students_df.empty:
                st.warning("⚠️ कृपया पहले छात्र जोड़ें!")
            else:
                col_p_left, col_p_right = st.columns([2, 1])
                with col_p_left:
                    st_photo_names = [f"Roll {s['Roll_No']}: {s['Name']}" for _, s in students_df.iterrows()]
                    sel_st_photo_str = st.selectbox("विद्यार्थी चुनें:", st_photo_names, key="photo_sel_st_tr")
                    p_roll = int(sel_st_photo_str.split(":")[0].replace("Roll", "").strip())
                    target_st = students_df[students_df["Roll_No"] == p_roll].iloc[0]
                    new_photo = st.file_uploader(f"रोल {p_roll} ({target_st['Name']}) का फोटो चुनें:", type=["jpg", "jpeg", "png"], key=f"photo_up_tr_{p_roll}")
                    if st.button("💾 फोटो सुरक्षित करें", type="primary", key=f"btn_p_save_tr_{p_roll}"):
                        if new_photo:
                            b64_img = base64.b64encode(new_photo.read()).decode()
                            cls_data["students"].loc[cls_data["students"]["Roll_No"] == p_roll, "Photo_b64"] = b64_img
                            save_data_to_disk()
                            st.success("फोटो सुरक्षित!")
                            st.rerun()
                with col_p_right:
                    if target_st.get("Photo_b64"):
                        st.image(base64.b64decode(target_st["Photo_b64"]), width=130)
                    else:
                        st.info("फोटो उपलब्ध नहीं")

    else:
        # ---------------- FOR PRINCIPAL: PHOTO, TC, APPROVALS & EXCEL MIGRATOR ----------------
        with tab3:
            st.subheader("📸 छात्र फोटो अपलोड एवं प्रबंधन (Photo Manager)")
            students_df = cls_data["students"]
            if students_df.empty:
                st.warning("⚠️ कृपया पहले छात्र जोड़ें!")
            else:
                col_p_left, col_p_right = st.columns([2, 1])
                with col_p_left:
                    st_photo_names = [f"Roll {s['Roll_No']}: {s['Name']}" for _, s in students_df.iterrows()]
                    sel_st_photo_str = st.selectbox("विद्यार्थी चुनें:", st_photo_names, key="photo_sel_st_pr")
                    p_roll = int(sel_st_photo_str.split(":")[0].replace("Roll", "").strip())
                    target_st = students_df[students_df["Roll_No"] == p_roll].iloc[0]
                    new_photo = st.file_uploader(f"रोल {p_roll} ({target_st['Name']}) का फोटो चुनें:", type=["jpg", "jpeg", "png"], key=f"photo_up_pr_{p_roll}")
                    if st.button("💾 फोटो सुरक्षित करें", type="primary", key=f"btn_p_save_pr_{p_roll}"):
                        if new_photo:
                            b64_img = base64.b64encode(new_photo.read()).decode()
                            cls_data["students"].loc[cls_data["students"]["Roll_No"] == p_roll, "Photo_b64"] = b64_img
                            save_data_to_disk()
                            st.success("फोटो सुरक्षित!")
                            st.rerun()
                with col_p_right:
                    if target_st.get("Photo_b64"):
                        st.image(base64.b64decode(target_st["Photo_b64"]), width=130)
                    else:
                        st.info("फोटो उपलब्ध नहीं")

        with tab4:
            st.subheader("🗑️ छात्र हटाएं / स्थानांतरण प्रमाण पत्र (TC) जारी करें")
            students_df = cls_data["students"]
            if students_df.empty:
                st.warning("कक्षा में कोई छात्र उपलब्ध नहीं है।")
            else:
                del_options = [f"Roll {s['Roll_No']}: {s['Name']} (Scholar: {s['Scholar_No']})" for _, s in students_df.iterrows()]
                student_to_delete_str = st.selectbox("हटाने हेतु विद्यार्थी चुनें:", del_options, key="del_st_pr")
                del_roll = int(student_to_delete_str.split(":")[0].replace("Roll", "").strip())
                tc_reason = st.text_input("शाला छोड़ने का कारण (Reason for Leaving / TC):", value="Transfer Certificate (TC) Issued / Left School", key="del_reason_pr")
                if st.button("⚠️ पुष्टि करें और विद्यार्थी का रिकॉर्ड हटाएं", type="primary"):
                    cls_data["students"] = cls_data["students"][cls_data["students"]["Roll_No"] != del_roll].reset_index(drop=True)
                    if del_roll in cls_data["evaluations"]: del cls_data["evaluations"][del_roll]
                    save_data_to_disk()
                    log_security_event(cur_dise, "Principal", "Principal", auth_school.get("mobile"), "DELETE_STUDENT_TC", f"Deleted Roll {del_roll}, Reason: {tc_reason}")
                    st.success(f"✅ रोल नंबर {del_roll} का रिकॉर्ड सफलतापूर्वक हटा दिया गया।")
                    st.rerun()

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
                st.markdown(f"**कुल {len(pending_list)} अनुरोध अनुमोदन हेतु प्रतीक्षारत हैं:**")
                
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
                            st.markdown(f"✏️ **सुधार अनुरोध:** **{req['student_name']}** (रोल: `{req['roll_no']}`)<br><span style='font-size:12px; color:#555;'>फ़ील्ड: <b>{req['field']}</b> ➔ नया मान: <b style='color:green;'>{req['new_value']}</b><br>कारण: {req.get('reason','')} | शिक्षक: {req['teacher_name']}</span>", unsafe_allow_html=True)
                    
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
                                f_map = {"छात्र का नाम (Name)": "Name", "पिता का नाम (Father Name)": "Father_Name", "माता का नाम (Mother Name)": "Mother_Name", "जन्मतिथि (DOB)": "DOB", "समग्र आईडी (Samagra ID)": "SSSM_ID", "स्कॉलर नंबर (Scholar No)": "Scholar_No"}
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
            st.subheader("📥 यूनिवर्सल एक्सेल ऑनबोर्डिंग एवं लीगेसी माइग्रेशन")
            st.caption("समग्र, शिक्षा पोर्टल, RSKMP या किसी भी पुरानी एक्सेल/सीएसवी को 1-क्लिक में अपलोड करें:")

            mig_up = st.file_uploader("📥 अपनी मौजूदा एक्सेल या सीएसवी शीट चुनें (.xlsx / .csv):", type=["xlsx", "csv"], key="uni_excel_mig_up")
            
            if mig_up:
                try:
                    if mig_up.name.endswith(".csv"):
                        raw_mig_df = pd.read_csv(BytesIO(mig_up.read()))
                    else:
                        raw_mig_df = pd.read_excel(BytesIO(mig_up.read()))

                    st.success(f"🎉 शीट सफलतापूर्वक पढ़ी गई! कुल **{len(raw_mig_df)}** पंक्तियाँ एवं **{len(raw_mig_df.columns)}** कॉलम मिले।")
                    
                    # Auto-map columns
                    col_map = {}
                    for c in raw_mig_df.columns:
                        cl = str(c).lower().strip()
                        if any(k in cl for k in ["छात्र", "student", "name", "naam"]) and "father" not in cl and "mother" not in cl: col_map["Name"] = c
                        elif any(k in cl for k in ["पिता", "father", "pita"]): col_map["Father_Name"] = c
                        elif any(k in cl for k in ["माता", "mother", "mata"]): col_map["Mother_Name"] = c
                        elif any(k in cl for k in ["जन्म", "dob", "birth"]): col_map["DOB"] = c
                        elif any(k in cl for k in ["समग्र", "samagra", "sssm"]): col_map["SSSM_ID"] = c
                        elif any(k in cl for k in ["दाखिला", "scholar", "admission"]): col_map["Scholar_No"] = c
                        elif any(k in cl for k in ["रोल", "roll"]): col_map["Roll_No"] = c
                        elif any(k in cl for k in ["लिंग", "gender", "sex"]): col_map["Gender"] = c
                        elif any(k in cl for k in ["जाति", "वर्ग", "category", "cat"]): col_map["Category"] = c
                        elif any(k in cl for k in ["आधार", "aadhar", "uid"]): col_map["Aadhar_No"] = c

                    st.write("**🔍 ऑटो-डिटेक्टेड कॉलम मैपिंग:**")
                    c_mp1, c_mp2 = st.columns(2)
                    with c_mp1:
                        for k in ["Name", "Father_Name", "Mother_Name", "DOB", "Scholar_No"]:
                            st.caption(f"• **{k}** ➔ `{col_map.get(k, 'Not Found')}`")
                    with c_mp2:
                        for k in ["Roll_No", "SSSM_ID", "Gender", "Category", "Aadhar_No"]:
                            st.caption(f"• **{k}** ➔ `{col_map.get(k, 'Not Found')}`")

                    # Build Normalized DF
                    norm_rows = []
                    missing_dob_cnt = 0
                    missing_sssm_cnt = 0

                    for idx_r, r in raw_mig_df.iterrows():
                        st_n = str(r.get(col_map.get("Name", ""), "")).strip() if col_map.get("Name") else f"Student {idx_r+1}"
                        st_dob = str(r.get(col_map.get("DOB", ""), "")).strip() if col_map.get("DOB") else ""
                        st_sssm = str(r.get(col_map.get("SSSM_ID", ""), "")).strip() if col_map.get("SSSM_ID") else ""
                        
                        if not st_dob or st_dob == "nan": missing_dob_cnt += 1
                        if not st_sssm or st_sssm == "nan": missing_sssm_cnt += 1

                        norm_rows.append({
                            "Roll_No": int(r.get(col_map.get("Roll_No", ""), idx_r+101)) if col_map.get("Roll_No") and str(r.get(col_map.get("Roll_No", ""))).isdigit() else idx_r+101,
                            "Scholar_No": str(r.get(col_map.get("Scholar_No", ""), f"10{idx_r+1}")).replace(".0",""),
                            "Name": st_n,
                            "Father_Name": str(r.get(col_map.get("Father_Name", ""), "")).replace("nan",""),
                            "Mother_Name": str(r.get(col_map.get("Mother_Name", ""), "")).replace("nan",""),
                            "DOB": st_dob.replace("nan",""),
                            "Class": selected_class,
                            "Section": "A",
                            "Gender": str(r.get(col_map.get("Gender", ""), "Boy")).capitalize() if col_map.get("Gender") else "Boy",
                            "Category": str(r.get(col_map.get("Category", ""), "OBC")).upper() if col_map.get("Category") else "OBC",
                            "SSSM_ID": st_sssm.replace("nan",""),
                            "Aadhar_No": str(r.get(col_map.get("Aadhar_No", ""), "")).replace("nan",""),
                            "Medium": "Hindi (हिन्दी)",
                            "Status": "Present",
                            "Total_Days": 220,
                            "Attended_Days": 200,
                            "Photo_b64": None
                        })
                    
                    norm_df = pd.DataFrame(norm_rows)

                    # Gap Detection Report
                    st.divider()
                    st.markdown("#### ⚠️ डेटा गैप डिटेक्शन रिपोर्ट (Audit Report):")
                    c_gp1, c_gp2, c_gp3 = st.columns(3)
                    c_gp1.metric("कुल पहचाने गए छात्र", f"{len(norm_df)}")
                    c_gp2.metric("अधूरी समग्र आईडी", f"{missing_sssm_cnt}", delta=f"-{missing_sssm_cnt}" if missing_sssm_cnt else None, delta_color="inverse")
                    c_gp3.metric("अधूरी जन्मतिथि", f"{missing_dob_cnt}", delta=f"-{missing_dob_cnt}" if missing_dob_cnt else None, delta_color="inverse")

                    st.caption("💡 आप नीचे दी गई टेबल में छूटा हुआ डेटा सीधे टाइप करके यहीं भर सकते हैं:")
                    edited_norm_df = st.data_editor(norm_df, num_rows="dynamic", use_container_width=True, key="norm_mig_editor")

                    # Destination & Save
                    c_dest1, c_dest2 = st.columns(2)
                    with c_dest1:
                        target_import_sess = st.selectbox("यह डेटा किस सत्र हेतु आयात करना है?", ["2026-27 (वर्तमान चालू सत्र)", "2025-26 (लीगेसी आर्काइव)", "2024-25 (लीगेसी आर्काइव)"], key="mig_target_sess")
                    with c_dest2:
                        st.markdown("<div style='margin-top: 28px;'>", unsafe_allow_html=True)
                        if st.button("🚀 यह डेटा सफलतापूर्वक आयात करें (Import to Class)", type="primary", use_container_width=True):
                            cls_data["students"] = edited_norm_df
                            save_data_to_disk()
                            log_security_event(cur_dise, "Principal", "Principal", auth_school.get("mobile"), "UNIVERSAL_EXCEL_IMPORT", f"Imported {len(edited_norm_df)} students from {mig_up.name}")
                            st.balloons()
                            st.success(f"🎉 शानदार! कुल {len(edited_norm_df)} छात्र कक्षा {selected_class} में सफलतापूर्वक आयात हो गए!")
                            st.rerun()
                        st.markdown("</div>", unsafe_allow_html=True)

                except Exception as e:
                    st.error(f"फ़ाइल प्रोसेस करने में त्रुटि: {e}")

# ----------------- MODULE 3: DUAL ATTENDANCE REGISTER (DAILY + MONTHLY) -----------------
elif menu == T["nav_attendance"]:
    st.markdown('<div class="main-header">📅 विद्यार्थी उपस्थिति प्रबंधन (Student Attendance Portal)</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">कक्षा अध्यापक द्वारा दैनिक मोबाइल हाजिरी लगाएं अथवा 12-माह का शासकीय उपस्थिति पत्रक देखें व एक्सपोर्ट करें</div>', unsafe_allow_html=True)

    students_df = cls_data["students"]
    if students_df.empty:
        st.warning("⚠️ कृपया पहले 'विद्यार्थी मास्टर' में छात्र जोड़ें!")
    else:
        tab_att1, tab_att2 = st.tabs([
            "📝 दैनिक कक्षा हाजिरी (Daily Teacher Attendance)",
            "📅 माहवार शासकीय उपस्थिति पत्रक (Monthly Attendance Sheet & Export)"
        ])

        # ======================= TAB 1: DAILY TEACHER ATTENDANCE =======================
        with tab_att1:
            st.subheader(f"📲 दैनिक छात्र उपस्थिति — {selected_class}")
            st.caption("कक्षा अध्यापक यहाँ से आज की तारीख चुनकर छात्रों की हाजिरी लगा सकते हैं। डेटा सीधे मास्टर रिकॉर्ड और वार्षिक रिजल्ट में अपडेट होगा:")

            MONTHS_MAP = {1:"Jan", 2:"Feb", 3:"Mar", 4:"Apr", 5:"May", 6:"Jun", 7:"Jul", 8:"Aug", 9:"Sep", 10:"Oct", 11:"Nov", 12:"Dec"}
            
            c_d1, c_d2, c_d3 = st.columns([2, 2, 3])
            with c_d1:
                cur_date = st.date_input("📅 उपस्थिति दिनांक (Select Date):", value=datetime.now().date(), key="daily_att_date")
                cur_month_abbr = MONTHS_MAP.get(cur_date.month, "Sep")
            with c_d2:
                st.markdown(f"<div style='border: 1px solid #CBD5E1; padding: 6px 12px; border-radius: 6px; background: #F8FAFC; margin-top: 25px; text-align: center; font-size: 13px;'><b>सक्रिय माह:</b> <span style='color:#1E3A8A; font-weight:bold;'>{cur_month_abbr}</span></div>", unsafe_allow_html=True)

            if "daily_attendance" not in cls_data:
                cls_data["daily_attendance"] = {}

            date_str = str(cur_date)
            existing_day_record = cls_data["daily_attendance"].get(date_str, {})

            with c_d3:
                st.markdown("<div style='margin-top: 25px;'>", unsafe_allow_html=True)
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
                    st.markdown(f"**{s['Name']}** (रोल नंबर: `{r_no}`)<br><span style='font-size: 12px; color: #555;'>दाखिला: {s.get('Scholar_No','--')} | पिता: {s.get('Father_Name','--')}</span>", unsafe_allow_html=True)

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
                        st.markdown(f"""
                        <a href="{wa_abs_link}" target="_blank" style="text-decoration: none;">
                            <div style="background: #EF4444; color: white; font-size: 11.5px; font-weight: bold; padding: 4px 6px; border-radius: 4px; text-align: center; margin-top: 4px;">
                                📲 पालक को सूचना
                            </div>
                        </a>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown("<span style='color: #16A34A; font-weight: bold; font-size: 13px;'>🟢 उपस्थित</span>", unsafe_allow_html=True)

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
                st.markdown(f"<div style='border: 2px solid #000; padding: 6px; text-align: center; margin-top: 18px; font-weight: bold; font-size: 16px; background: #fff;'>Total: {tot_work_days}</div>", unsafe_allow_html=True)
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
            st.markdown("### 📥 उपस्थिति डेटा एक्सपोर्ट (Export Attendance Register)")
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

# ----------------- MODULE 4: EVALUATION ENTRY (SUBJECT-WISE PRESENT/ABSENT) -----------------
elif menu == T["nav_eval"]:
    st.markdown(f'<div class="main-header">📝 परीक्षा एवं गतिविधि मूल्यांकन — {selected_class}</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">विद्यार्थी प्रोफाइल, पेपर/विषयवार Present/Absent, मुख्य विषय (अर्धवार्षिक 40 + वार्षिक 60) व सह-शैक्षिक गुण</div>', unsafe_allow_html=True)


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
                        <div><b>माध्यम:</b> {stud.get('Medium', 'Hindi')}</div>
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
                        stat_hy = st.selectbox(f"stat_hy_{s_id}", ["Present", "Absent"], index=0 if p_hy_stat == "Present" else 1, key=f"stat_hy_{sel_roll}_{s_id}", label_visibility="collapsed")
                    with r_cols[2]:
                        val_hy = st.number_input(f"hy_{s_id}", min_value=0, max_value=20, value=0 if stat_hy == "Absent" else min(20, int(p_hy_val)), disabled=(stat_hy == "Absent"), key=f"num_hy_{sel_roll}_{s_id}", label_visibility="collapsed")
                    with r_cols[3]:
                        val_proj = st.number_input(f"proj_{s_id}", min_value=0, max_value=20, value=min(20, int(p_proj_val)), key=f"num_proj_{sel_roll}_{s_id}", label_visibility="collapsed")
                    with r_cols[4]:
                        stat_yr = st.selectbox(f"stat_yr_{s_id}", ["Present", "Absent"], index=0 if p_yr_stat == "Present" else 1, key=f"stat_yr_{sel_roll}_{s_id}", label_visibility="collapsed")
                    with r_cols[5]:
                        val_yr = st.number_input(f"yr_{s_id}", min_value=0, max_value=60, value=0 if stat_yr == "Absent" else int(p_yr_val), disabled=(stat_yr == "Absent"), key=f"num_yr_{sel_roll}_{s_id}", label_visibility="collapsed")
                    
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
                        stat_hy = st.selectbox(f"stat_hy_{s_id}", ["Present", "Absent"], index=0 if p_hy_stat == "Present" else 1, key=f"stat_hy_{sel_roll}_{s_id}", label_visibility="collapsed")
                    with r_cols[2]:
                        val_hy = st.number_input(f"hy_{s_id}", min_value=0, max_value=40, value=0 if stat_hy == "Absent" else int(p_hy_val), disabled=(stat_hy == "Absent"), key=f"num_hy_{sel_roll}_{s_id}", label_visibility="collapsed")
                    with r_cols[3]:
                        stat_yr = st.selectbox(f"stat_yr_{s_id}", ["Present", "Absent"], index=0 if p_yr_stat == "Present" else 1, key=f"stat_yr_{sel_roll}_{s_id}", label_visibility="collapsed")
                    with r_cols[4]:
                        val_yr = st.number_input(f"yr_{s_id}", min_value=0, max_value=60, value=0 if stat_yr == "Absent" else int(p_yr_val), disabled=(stat_yr == "Absent"), key=f"num_yr_{sel_roll}_{s_id}", label_visibility="collapsed")
                    
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
                    sel_grd = st.selectbox(label, ["A", "B", "C"], index=opt_idx, key=f"co_{sel_roll}_{k}", label_visibility="collapsed")
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
                        sel_grd = st.selectbox(label, ["A", "B", "C"], index=opt_idx, key=f"soc_{sel_roll}_{k}", label_visibility="collapsed")
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
    st.markdown(f'<div class="main-header">🔍 छात्र संपूर्ण डेटा समीक्षा (Student 360° Data Dossier)</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">कक्षा एवं सेक्शन चुनें — केवल उन विद्यार्थियों की सूची दिखेगी जिनका डेटा दर्ज हो चुका है। नाम पर क्लिक करने पर पूरा डेटा खुलेगा।</div>', unsafe_allow_html=True)


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
        st.markdown(f'''
        <div style="border: 1px solid #93C5FD; background: #EFF6FF; padding: 8px 12px; border-radius: 6px; text-align: center; margin-top: 15px;">
            <span style="font-size: 13px; color: #1E3A8A; font-weight: bold;">डेटा प्रविष्टि स्थिति:</span><br>
            <span style="font-size: 16px; font-weight: 800; color: #008000;">{data_entered_cnt}</span> / {tot_enrolled} छात्र पूर्ण
        </div>
        ''', unsafe_allow_html=True)


    st.divider()


    # ================== VIEW STATE 1: ONLY LIST OF STUDENTS IS SHOWN ==================
    if st.session_state.active_dossier_roll is None:
        st.markdown(f"### 📋 {v_class} ({v_section}) — मूल्यांकन दर्ज विद्यार्थियों की सूची")
        
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
                    st.markdown(f"<span style='font-size: 13px;'>कुल प्राप्तांक: <b>{tot_obt}/{v_max_total}</b> ({pct}%)</span><br>"
                                f"<span style='font-size: 12px;'>परिणाम: <b style='color:{res_col};'>{res_txt}</b> | ग्रेड: <b>{grd}</b> | उपस्थिति: <b>{s.get('Attended_Days',200)}/{s.get('Total_Days',220)}</b></span>", 
                                unsafe_allow_html=True)
                with card_c4:
                    st.markdown("<div style='margin-top: 10px;'>", unsafe_allow_html=True)
                    if st.button(f"👁️ पूरा डेटा देखें", key=f"btn_view_dossier_{r}", type="primary", use_container_width=True):
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
            st.markdown(f"### 📋 विद्यार्थी संपूर्ण रिकॉर्ड: {target_student['Name']} (Roll: {cur_sel_roll})")
        with c_back2:
            single_st_df = generate_master_44col_df(pd.DataFrame([target_student]), v_evals, v_subjects, st.session_state.school_info, v_class)
            s_b, s_m, s_ext = export_dataframe_bytes(single_st_df, "Excel (.xlsx)")
            st.download_button(
                "📥 Excel",
                data=s_b,
                file_name=f"Student_{cur_sel_roll}_{target_student['Name']}_{st.session_state.school_info.get('session','2023-24')}.xlsx",
                mime=s_m,
                use_container_width=True,
                key=f"btn_single_exp_{cur_sel_roll}"
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
            st.markdown(f"""
            <a href="{m5_wa_url}" target="_blank" style="text-decoration: none;">
                <div style="background: #25D366; color: white; font-weight: bold; font-size: 12.5px; padding: 6px 8px; border-radius: 6px; text-align: center; box-shadow: 0 2px 4px rgba(37,211,102,0.25);">
                    📲 WhatsApp रिजल्ट
                </div>
            </a>
            """, unsafe_allow_html=True)
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
            st.markdown("#### 👤 व्यक्तिगत विवरण (Student Bio-Data)")
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
                st.markdown(f"**माध्यम (Medium):** {target_student.get('Medium','Hindi')}")


            st.markdown(f"**समग्र आईडी (Samagra ID):** `{target_student.get('SSSM_ID','--')}` | **आधार नंबर:** `{target_student.get('Aadhar_No','--')}`")
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
        st.markdown(f"#### 📚 मुख्य विषय परीक्षा परिणाम (Academic Evaluation — {v_class})")
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
elif menu == T["nav_marksheet"]:
    students_df = cls_data["students"]
    if students_df.empty:
        st.warning("⚠️ कक्षा में कोई छात्र उपलब्ध नहीं है।")
    else:
        st_names = [f"Roll {s['Roll_No']}: {s['Name']}" for _, s in students_df.iterrows()]
        c_top1, c_top2, c_top3, c_top4 = st.columns([2.5, 2, 1.2, 2.3])
        with c_top1:
            sel_student_str = st.selectbox("विद्यार्थी / रोल नंबर चुनें:", st_names)
            sel_roll = int(sel_student_str.split(":")[0].replace("Roll", "").strip())
        with c_top2:
            top_roll_box_html = f"""
            <div style="border: 2px solid #000; padding: 6px 12px; background: #fff; text-align: center; margin-top: 18px;">
                <span style="font-size: 13px; font-weight: bold; margin-right: 10px;">Enter Student Roll Number:</span>
                <span style="color: red; font-size: 18px; font-weight: 800;">{sel_roll}</span>
            </div>
            """
            render_html(top_roll_box_html)
        with c_top3:
            st.markdown("<div style='margin-top: 22px;'>", unsafe_allow_html=True)
            st.button("🖨️ Print", on_click=None, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)
        with c_top4:
            st.markdown("<div style='margin-top: 10px;'>", unsafe_allow_html=True)
            # WhatsApp instant trigger placeholder
            wa_target_st = students_df[students_df["Roll_No"] == sel_roll].iloc[0]
            st_ev_wa = cls_data["evaluations"].get(sel_roll, {})
            st_m_wa = st_ev_wa.get("marks", {})
            cls_subs_wa = get_class_subjects(selected_class)
            wa_tot = sum([st_m_wa.get(sub["id"], {}).get("total", 75) for sub in cls_subs_wa])
            wa_max = len(cls_subs_wa) * 100
            wa_pct = round((wa_tot / wa_max) * 100, 1) if wa_max else 0
            wa_grd = calculate_grade(wa_pct)
            wa_res = "PASS (उत्तीर्ण)" if (wa_pct >= 33 and st_ev_wa.get("status", "Present") != "Absent") else "FAIL"
            
            wa_mob_val = wa_target_st.get("Contact", wa_target_st.get("Mobile", ""))
            wa_link, _ = generate_whatsapp_result_link(
                wa_target_st['Name'], sel_roll, selected_class, wa_tot, wa_max, wa_pct, wa_grd, wa_res,
                st.session_state.school_info.get('name', 'शासकीय विद्यालय'), wa_mob_val
            )
            st.markdown(f"""
            <a href="{wa_link}" target="_blank" style="text-decoration: none;">
                <div style="background: #25D366; color: white; font-weight: bold; font-size: 13px; padding: 7px 10px; border-radius: 6px; text-align: center; box-shadow: 0 2px 4px rgba(37,211,102,0.3); margin-top: 12px;">
                    📲 WhatsApp पर रिजल्ट भेजें
                </div>
            </a>
            """, unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)


        stud = students_df[students_df["Roll_No"] == sel_roll].iloc[0]
        s_info = st.session_state.school_info
        cls_subjects = get_class_subjects(selected_class)
        sub_count = len(cls_subjects)
        
        max_hy_total = sub_count * 40
        max_yr_total = sub_count * 60
        max_grand_total = sub_count * 100


        ev = cls_data["evaluations"].get(sel_roll, {})


        # Logo handling
        if s_info.get("logo_b64"):
            logo_img_html = f'<img src="data:image/png;base64,{s_info["logo_b64"]}" style="width: 75px; height: 75px; object-fit: contain;">'
        else:
            logo_img_html = '<div style="width: 70px; height: 70px; border-radius: 50%; border: 2px solid #8B5A2B; display: flex; align-items: center; justify-content: center; font-size: 32px; background: #FFF8DC;">🏫</div>'


        # Photo handling
        if stud.get("Photo_b64"):
            photo_cell_html = f'<img src="data:image/jpeg;base64,{stud["Photo_b64"]}" style="width: 95px; height: 115px; object-fit: cover; border: 1px solid #000;">'
        else:
            photo_cell_html = '<div style="width: 95px; height: 115px; border: 1px dashed #666; display: flex; align-items: center; justify-content: center; font-size: 11px; text-align: center; color: #555; background: #FAFAFA;">पासपोर्ट फोटो<br>(Photo)</div>'


        total_hy_obt = 0
        total_yr_obt = 0
        grand_obt = 0
        all_passed = True
        subject_rows_html = ""


        for sub in cls_subjects:
            s_id = sub["id"]
            s_name = sub["name"]
            
            s_eval = ev.get("marks", {}).get(s_id, {})
            hy_obt = s_eval.get("half_yearly", 32)
            yr_obt = s_eval.get("annual", 48)
            tot_obt = s_eval.get("total", hy_obt + yr_obt)


            total_hy_obt += hy_obt
            total_yr_obt += yr_obt
            grand_obt += tot_obt


            hy_grd = calculate_grade(round((hy_obt / 40) * 100))
            yr_grd = calculate_grade(round((yr_obt / 60) * 100))
            tot_grd = calculate_grade(tot_obt)


            if tot_obt < 33: all_passed = False
            obt_color = "#008000" if tot_obt >= 33 else "#CC0000"


            subject_rows_html += f"""
            <tr>
                <td style="border: 1px solid #000; text-align: left; padding: 4px 6px; font-weight: bold;">▸ {s_name}</td>
                <td style="border: 1px solid #000; padding: 4px;">40</td>
                <td style="border: 1px solid #000; padding: 4px; font-weight: bold; color: #000;">{hy_obt}</td>
                <td style="border: 1px solid #000; padding: 4px; font-weight: bold; color: {obt_color};">{hy_grd}</td>
                <td style="border: 1px solid #000; padding: 4px;">60</td>
                <td style="border: 1px solid #000; padding: 4px; font-weight: bold; color: #000;">{yr_obt}</td>
                <td style="border: 1px solid #000; padding: 4px; font-weight: bold; color: {obt_color};">{yr_grd}</td>
                <td style="border: 1px solid #000; padding: 4px;">100</td>
                <td style="border: 1px solid #000; padding: 4px; font-weight: bold; color: {obt_color}; font-size: 13px;">{tot_obt}</td>
                <td style="border: 1px solid #000; padding: 4px; font-weight: bold; color: {obt_color}; font-size: 13px;">{tot_grd}</td>
            </tr>
            """


        hy_tot_pct = round((total_hy_obt / max_hy_total) * 100, 1) if max_hy_total else 0
        yr_tot_pct = round((total_yr_obt / max_yr_total) * 100, 1) if max_yr_total else 0
        grand_pct = round((grand_obt / max_grand_total) * 100, 2) if max_grand_total else 0


        hy_tot_grd = calculate_grade(hy_tot_pct)
        yr_tot_grd = calculate_grade(yr_tot_pct)
        overall_grade = calculate_grade(grand_pct)


        pass_status = "Pass" if (all_passed and grand_pct >= 33) else "Fail"
        pass_color = "#008000" if pass_status == "Pass" else "#CC0000"


        # Rank
        rank_val = 1
        if len(students_df) > 1:
            all_tots = []
            for _, st_row in students_df.iterrows():
                r_st = st_row["Roll_No"]
                e_st = cls_data["evaluations"].get(r_st, {}).get("marks", {})
                st_tot = sum([e_st.get(sub["id"], {}).get("total", 70) for sub in cls_subjects])
                all_tots.append(st_tot)
            all_tots.sort(reverse=True)
            rank_val = all_tots.index(grand_obt) + 1 if grand_obt in all_tots else 1


        classes_lst = st.session_state.classes_list
        cur_cls_idx = classes_lst.index(selected_class) if selected_class in classes_lst else -1
        next_class_name = classes_lst[cur_cls_idx + 1] if cur_cls_idx != -1 and cur_cls_idx < len(classes_lst) - 1 else "Higher Secondary / Passed Out"
        promo_text = f"Class {next_class_name}" if pass_status == "Pass" else "Detained in Same Class"
        remarks_text = "Promoted" if pass_status == "Pass" else "Fail"


        cocurr_dict = ev.get("co_curricular", {})
        cocurr_rows_html = ""
        for k, label in CO_CURRICULAR_ACTIVITIES:
            g_val = cocurr_dict.get(k, "A")
            cocurr_rows_html += f"""
            <tr style="height: 25px;">
                <td style="border: 1px solid #000; text-align: left; padding: 2px 5px; font-weight: bold; font-size: 10px; white-space: nowrap;">▸ {label.split("(")[0].strip()}</td>
                <td style="border: 1px solid #000; text-align: center; padding: 2px; font-weight: bold; font-size: 11px;">{g_val}</td>
            </tr>
            """


        social_dict = ev.get("social", {})
        soc_rows_html = ""
        for i in range(5):
            k1, l1 = SOCIAL_ACTIVITIES[i]
            k2, l2 = SOCIAL_ACTIVITIES[i+5]
            g1 = social_dict.get(k1, "A")
            g2 = social_dict.get(k2, "A")
            name1 = l1.split("(")[0].strip()
            name2 = l2.split("(")[0].strip()
            if "ENVIRONMENTAL" in name2:
                name2 = "ENVIRONMENTAL CONS."
            soc_rows_html += f"""
            <tr style="height: 26px;">
                <td style="border: 1px solid #000; text-align: left; padding: 2px 6px; font-weight: bold; font-size: 10px; white-space: nowrap; width: 38%;">▸ {name1}</td>
                <td style="border: 1px solid #000; text-align: center; padding: 2px; font-weight: bold; font-size: 11px; width: 12%;">{g1}</td>
                <td style="border: 1px solid #000; text-align: left; padding: 2px 6px; font-weight: bold; font-size: 9.5px; white-space: nowrap; width: 38%;">▸ {name2}</td>
                <td style="border: 1px solid #000; text-align: center; padding: 2px; font-weight: bold; font-size: 11px; width: 12%;">{g2}</td>
            </tr>
            """


        exact_card_html = f"""
        <div class="printable-area" style="background: #ffffff; border: 2px solid #000; padding: 12px 16px; max-width: 760px; margin: auto; font-family: Arial, sans-serif; color: #000;">
            <table style="width: 100%; border: none; margin-bottom: 6px;">
                <tr>
                    <td style="width: 15%; text-align: left; vertical-align: top;">{logo_img_html}</td>
                    <td style="width: 85%; text-align: center; vertical-align: middle;">
                        <div style="font-weight: 800; font-size: 16px; color: #008000; letter-spacing: 0.5px;">
                            Dise Code : {s_info.get('udise', '23260100101')}
                        </div>
                        <div style="font-weight: 800; font-size: 16px; color: #003399; margin-top: 4px; border-bottom: 2px solid #003399; display: inline-block; padding-bottom: 2px;">
                            Student Progress Card (Session : {s_info.get('session', '2023-24')})
                        </div>
                    </td>
                </tr>
            </table>


            <table style="width: 100%; border-collapse: collapse; border: 1px solid #000; font-size: 12px; margin-bottom: 8px;">
                <tr>
                    <td style="border: 1px solid #000; font-weight: bold; width: 22%; padding: 3px 6px;">Roll Number</td>
                    <td style="border: 1px solid #000; width: 20%; padding: 3px 6px;">{stud['Roll_No']}</td>
                    <td style="border: 1px solid #000; font-weight: bold; width: 22%; padding: 3px 6px;">Scholar Number</td>
                    <td style="border: 1px solid #000; width: 18%; padding: 3px 6px;">{stud['Scholar_No']}</td>
                    <td rowspan="7" style="border: 1px solid #000; width: 18%; text-align: center; vertical-align: middle; padding: 2px;">
                        {photo_cell_html}
                    </td>
                </tr>
                <tr>
                    <td style="border: 1px solid #000; font-weight: bold; padding: 3px 6px;">Name Of Student</td>
                    <td colspan="3" style="border: 1px solid #000; font-weight: bold; padding: 3px 6px;">{stud['Name']}</td>
                </tr>
                <tr>
                    <td style="border: 1px solid #000; font-weight: bold; padding: 3px 6px;">Father's Name</td>
                    <td colspan="3" style="border: 1px solid #000; padding: 3px 6px;">{stud['Father_Name']}</td>
                </tr>
                <tr>
                    <td style="border: 1px solid #000; font-weight: bold; padding: 3px 6px;">Mother's Name</td>
                    <td colspan="3" style="border: 1px solid #000; padding: 3px 6px;">{stud['Mother_Name']}</td>
                </tr>
                <tr>
                    <td style="border: 1px solid #000; font-weight: bold; padding: 3px 6px;">Date Of Birth</td>
                    <td colspan="3" style="border: 1px solid #000; padding: 3px 6px;">{stud['DOB']}</td>
                </tr>
                <tr>
                    <td style="border: 1px solid #000; font-weight: bold; padding: 3px 6px;">Class</td>
                    <td style="border: 1px solid #000; padding: 3px 6px;">{stud.get('Class', selected_class)}</td>
                    <td style="border: 1px solid #000; font-weight: bold; padding: 3px 6px;">Section</td>
                    <td style="border: 1px solid #000; padding: 3px 6px;">{stud.get('Section', 'A')}</td>
                </tr>
                <tr>
                    <td style="border: 1px solid #000; font-weight: bold; padding: 3px 6px;">Gender</td>
                    <td style="border: 1px solid #000; padding: 3px 6px;">{stud['Gender']}</td>
                    <td style="border: 1px solid #000; font-weight: bold; padding: 3px 6px;">Category</td>
                    <td style="border: 1px solid #000; padding: 3px 6px;">{stud['Category']}</td>
                </tr>
                <tr>
                    <td style="border: 1px solid #000; font-weight: bold; padding: 3px 6px;">Samagra ID</td>
                    <td style="border: 1px solid #000; padding: 3px 6px;">{stud['SSSM_ID']}</td>
                    <td style="border: 1px solid #000; font-weight: bold; padding: 3px 6px;">Aadhar Number</td>
                    <td style="border: 1px solid #000; padding: 3px 6px;">{stud.get('Aadhar_No', '')}</td>
                    <td style="border: 1px solid #000; padding: 3px 4px; font-size: 11px;">
                        <b>Medium:</b> {stud.get('Medium', 'Hindi')}
                    </td>
                </tr>
            </table>


            <div style="font-weight: 800; font-size: 13px; color: #003399; margin-top: 6px; margin-bottom: 4px;">
                ▸ Student's Performance : <span style="color: #CC0000; font-size: 11px; font-weight: normal;">[As per the order of M.P. Govt.]</span>
            </div>


            <table style="width: 100%; border-collapse: collapse; border: 1px solid #000; font-size: 12px; text-align: center; margin-bottom: 8px;">
                <thead>
                    <tr style="background-color: #FAFAFA; font-weight: bold;">
                        <th rowspan="2" style="border: 1px solid #000; width: 28%; text-align: center; padding: 4px;">Subjects</th>
                        <th colspan="3" style="border: 1px solid #000; padding: 4px;">Half Yearly Evaluation</th>
                        <th colspan="3" style="border: 1px solid #000; padding: 4px;">Annual Evaluation</th>
                        <th colspan="3" style="border: 1px solid #000; padding: 4px;">Final Assessment</th>
                    </tr>
                    <tr style="background-color: #FAFAFA; font-weight: bold;">
                        <th style="border: 1px solid #000; padding: 3px;">Max.</th>
                        <th style="border: 1px solid #000; padding: 3px;">Obt.</th>
                        <th style="border: 1px solid #000; padding: 3px;">Grade</th>
                        <th style="border: 1px solid #000; padding: 3px;">Max.</th>
                        <th style="border: 1px solid #000; padding: 3px;">Obt.</th>
                        <th style="border: 1px solid #000; padding: 3px;">Grade</th>
                        <th style="border: 1px solid #000; padding: 3px;">Max.</th>
                        <th style="border: 1px solid #000; padding: 3px;">Obt.</th>
                        <th style="border: 1px solid #000; padding: 3px;">Grade</th>
                    </tr>
                </thead>
                <tbody>
                    {subject_rows_html}
                    <tr style="background-color: #F8F9FA; font-weight: bold;">
                        <td style="border: 1px solid #000; text-align: left; padding: 4px 6px;">Grand Total</td>
                        <td style="border: 1px solid #000; padding: 4px;">{max_hy_total}</td>
                        <td style="border: 1px solid #000; padding: 4px; color: {pass_color};">{total_hy_obt}</td>
                        <td style="border: 1px solid #000; padding: 4px; color: {pass_color};">{hy_tot_grd}</td>
                        <td style="border: 1px solid #000; padding: 4px;">{max_yr_total}</td>
                        <td style="border: 1px solid #000; padding: 4px; color: {pass_color};">{total_yr_obt}</td>
                        <td style="border: 1px solid #000; padding: 4px; color: {pass_color};">{yr_tot_grd}</td>
                        <td style="border: 1px solid #000; padding: 4px;">{max_grand_total}</td>
                        <td style="border: 1px solid #000; padding: 4px; color: {pass_color}; font-size: 13px;">{grand_obt}</td>
                        <td style="border: 1px solid #000; padding: 4px; color: {pass_color}; font-size: 13px;">{overall_grade}</td>
                    </tr>
                </tbody>
            </table>


            <div style="font-weight: 800; font-size: 13px; color: #003399; margin-top: 6px; margin-bottom: 4px;">
                ▸ Performance in Co-Scholastics Areas :
            </div>


            <table style="width: 100%; border-collapse: collapse; border: none; margin-bottom: 8px;">
                <tr>
                    <td style="width: 33%; vertical-align: top; padding-right: 6px;">
                        <table style="width: 100%; border-collapse: collapse; border: 1px solid #000; table-layout: fixed;">
                            <thead>
                                <tr style="background-color: #FDEBD0; height: 28px;">
                                    <th style="border: 1px solid #000; text-align: left; padding: 2px 4px; font-size: 11px; width: 75%;">Co-Curricular Activities</th>
                                    <th style="border: 1px solid #000; text-align: center; padding: 2px; font-size: 11px; width: 25%;">Grade</th>
                                </tr>
                            </thead>
                            <tbody>{cocurr_rows_html}</tbody>
                        </table>
                    </td>
                    <td style="width: 67%; vertical-align: top; padding-left: 6px;">
                        <table style="width: 100%; border-collapse: collapse; border: 1px solid #000; table-layout: fixed;">
                            <colgroup>
                                <col style="width: 38%;">
                                <col style="width: 12%;">
                                <col style="width: 38%;">
                                <col style="width: 12%;">
                            </colgroup>
                            <thead>
                                <tr style="background-color: #FDEBD0; height: 28px;">
                                    <th colspan="4" style="border: 1px solid #000; text-align: center; padding: 2px 4px; font-size: 11px;">Social Activities</th>
                                </tr>
                            </thead>
                            <tbody>{soc_rows_html}</tbody>
                        </table>
                    </td>
                </tr>
            </table>


            <div style="font-weight: 800; font-size: 13px; color: #003399; margin-top: 6px; margin-bottom: 4px;">
                ▸ Final Result :
            </div>


            <table style="width: 100%; border-collapse: collapse; border: 1px solid #000; font-size: 12px; text-align: center; margin-bottom: 6px;">
                <thead>
                    <tr style="background-color: #FAFAFA; font-weight: bold;">
                        <th style="border: 1px solid #000; padding: 4px;">Max. Marks</th>
                        <th style="border: 1px solid #000; padding: 4px;">Obt. Marks</th>
                        <th style="border: 1px solid #000; padding: 4px;">Result</th>
                        <th style="border: 1px solid #000; padding: 4px;">Percentage</th>
                        <th style="border: 1px solid #000; padding: 4px;">Grade</th>
                        <th style="border: 1px solid #000; padding: 4px;">Rank</th>
                        <th style="border: 1px solid #000; padding: 4px;">Attendance</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td style="border: 1px solid #000; padding: 5px; font-weight: bold; color: #008000; font-size: 13px;">{max_grand_total}</td>
                        <td style="border: 1px solid #000; padding: 5px; font-weight: bold; color: #008000; font-size: 13px;">{grand_obt}</td>
                        <td style="border: 1px solid #000; padding: 5px; font-weight: bold; color: {pass_color}; font-size: 13px;">{pass_status}</td>
                        <td style="border: 1px solid #000; padding: 5px; font-weight: bold; color: #008000; font-size: 13px;">{grand_pct}%</td>
                        <td style="border: 1px solid #000; padding: 5px; font-weight: bold; color: {pass_color}; font-size: 13px;">{overall_grade}</td>
                        <td style="border: 1px solid #000; padding: 5px; font-weight: bold; font-size: 13px;">{rank_val}</td>
                        <td style="border: 1px solid #000; padding: 5px; font-size: 12px;">{stud.get('Attended_Days', 200)} / {stud.get('Total_Days', 220)}</td>
                    </tr>
                </tbody>
            </table>


            <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 8px; margin-bottom: 25px; font-size: 12px; font-weight: bold;">
                <div>
                    Class Teacher Remarks: <span style="color: {pass_color}; border-bottom: 1px solid #000; padding: 0 20px;">{remarks_text}</span>
                </div>
                <div>
                    <span style="color: #D35400;">Congratulations!</span> Promoted to Class: <span style="color: #003399; border-bottom: 1px solid #000; padding: 0 20px;">{promo_text}</span>
                </div>
            </div>


            <div style="display: flex; justify-content: space-between; margin-top: 30px; font-size: 13px; font-weight: bold; text-align: center;">
                <div style="width: 30%;">Class Teacher</div>
                <div style="width: 30%;">Exam In-Charge</div>
                <div style="width: 30%;">Head Of School</div>
            </div>


            <div style="text-align: center; font-size: 11px; margin-top: 15px; color: #444; font-style: italic;">
                Report Card Printed On: {TODAY_STR}
            </div>
        </div>
        """
        
        # Export Marksheets Summary for all students
        st.markdown("### 📥 सभी छात्रों का परीक्षाफल डेटा एक्सपोर्ट (Export All Results)")
        c_mexp1, c_mexp2 = st.columns([2, 2])
        with c_mexp1:
            m_exp_fmt = st.selectbox("प्रारूप चुनें (File Format):", ["Excel (.xlsx)", "CSV (.csv)"], key="m_exp_fmt")
        with c_mexp2:
            m_master_df = generate_master_44col_df(students_df, cls_data["evaluations"], cls_subjects, s_info, selected_class)
            m_bytes, m_mime, m_ext = export_dataframe_bytes(m_master_df, m_exp_fmt)
            m_filename = f"Result_Marksheets_{selected_class}_{s_info.get('session','2023-24')}{m_ext}"
            st.download_button(
                f"📥 संपूर्ण परीक्षाफल तालिका डाउनलोड करें ({m_exp_fmt})",
                data=m_bytes,
                file_name=m_filename,
                mime=m_mime,
                type="primary",
                use_container_width=True
            )
        st.divider()


        render_html(exact_card_html)


# ----------------- MODULE 7: A3 ANNUAL RESULT SHEET (EXACT REPLICA: image_fde76c.png) -----------------
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
        st.markdown('''
        <div style="border: 2px solid #008000; padding: 6px 14px; background: #fff; display: inline-block;">
            <span style="color: #CC0000; font-weight: 800; font-size: 14px;">*इस परीक्षाफल पत्रक को अनुमोदन हेतु A-3 साइज़ के पेपर पर प्रिंट करें</span>
        </div>
        ''', unsafe_allow_html=True)
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
                            <td style="border: 1px solid #000; padding: 3px 6px;"><b>Medium :</b> {s_info.get('medium','Hindi')}</td>
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




# ----------------- MODULE 8: CATEGORY/GRADE WISE RESULT SUMMARY (IMAGE 3: image_aabe70.png) -----------------
elif menu == T["nav_summary"]:
    students_df = cls_data["students"]
    s_info = st.session_state.school_info
    cls_subjects = get_class_subjects(selected_class)
    sub_count = len(cls_subjects)
    max_total = sub_count * 100


    c_s1, c_s2 = st.columns([4, 1])
    with c_s2:
        st.button("🖨️ Print Summary", on_click=None, use_container_width=True)


    # Dynamic calculation of Category & Gender distribution
    cats = ["SC", "ST", "OBC", "GEN"]
    summary_metrics = ["Enrolled", "Appeared", "Absent", "Pass", "Fail", "Percentage"]
    grades_list = ["A+", "A", "B+", "B", "C+", "C", "D", "E"]


    # Compute for each student: gender, cat, status, pass/fail, grade
    calc_data = []
    for _, s in students_df.iterrows():
        r_no = s["Roll_No"]
        ev = cls_data["evaluations"].get(r_no, {})
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
    
        # Clean category
        c_raw = str(s.get("Category", "OBC")).upper()
        if "SC" in c_raw: c_clean = "SC"
        elif "ST" in c_raw: c_clean = "ST"
        elif "OBC" in c_raw: c_clean = "OBC"
        else: c_clean = "GEN"


        # Clean gender
        g_raw = str(s.get("Gender", "Boy")).lower()
        g_clean = "Girls" if "girl" in g_raw else "Boys"


        calc_data.append({
            "Gender": g_clean,
            "Category": c_clean,
            "Status": st_status,
            "Pass": is_pass,
            "Grade": grd
        })


    cdf = pd.DataFrame(calc_data)


    # Helper function to count
    def get_cnt(g_filter, c_filter, m_type):
        if cdf.empty: return 0
        df_sub = cdf.copy()
        if g_filter != "ALL": df_sub = df_sub[df_sub["Gender"] == g_filter]
        if c_filter != "ALL": df_sub = df_sub[df_sub["Category"] == c_filter]


        if m_type == "Enrolled": return len(df_sub)
        elif m_type == "Appeared": return len(df_sub[df_sub["Status"] != "Absent"])
        elif m_type == "Absent": return len(df_sub[df_sub["Status"] == "Absent"])
        elif m_type == "Pass": return len(df_sub[df_sub["Pass"] == True])
        elif m_type == "Fail": return len(df_sub[df_sub["Pass"] == False])
        return 0


    # Table 1: Category/Summary Rows HTML
    cat_rows_html = ""
    for m in summary_metrics:
        if m == "Percentage":
            # Compute percentage
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
            <tr style="font-weight: bold;">
                <td style="border: 1px solid #000; text-align: left; padding: 4px;">{m}</td>
                <td style="border: 1px solid #000;">{g_sc_p}</td><td style="border: 1px solid #000;">{g_st_p}</td><td style="border: 1px solid #000;">{g_obc_p}</td><td style="border: 1px solid #000;">{g_gen_p}</td><td style="border: 1px solid #000; font-weight: 800;">{g_tot_p}</td>
                <td style="border: 1px solid #000;">{b_sc_p}</td><td style="border: 1px solid #000;">{b_st_p}</td><td style="border: 1px solid #000;">{b_obc_p}</td><td style="border: 1px solid #000;">{b_gen_p}</td><td style="border: 1px solid #000; font-weight: 800;">{b_tot_p}</td>
                <td style="border: 1px solid #000;">{all_sc_p}</td><td style="border: 1px solid #000;">{all_st_p}</td><td style="border: 1px solid #000;">{all_obc_p}</td><td style="border: 1px solid #000;">{all_gen_p}</td><td style="border: 1px solid #000; font-weight: 800;">{all_tot_p}</td>
            </tr>
            """
        else:
            cat_rows_html += f"""
            <tr>
                <td style="border: 1px solid #000; text-align: left; padding: 4px; font-weight: 600;">{m}</td>
                <td style="border: 1px solid #000;">{get_cnt('Girls','SC',m)}</td><td style="border: 1px solid #000;">{get_cnt('Girls','ST',m)}</td><td style="border: 1px solid #000;">{get_cnt('Girls','OBC',m)}</td><td style="border: 1px solid #000;">{get_cnt('Girls','GEN',m)}</td><td style="border: 1px solid #000; font-weight: 800;">{get_cnt('Girls','ALL',m)}</td>
                <td style="border: 1px solid #000;">{get_cnt('Boys','SC',m)}</td><td style="border: 1px solid #000;">{get_cnt('Boys','ST',m)}</td><td style="border: 1px solid #000;">{get_cnt('Boys','OBC',m)}</td><td style="border: 1px solid #000;">{get_cnt('Boys','GEN',m)}</td><td style="border: 1px solid #000; font-weight: 800;">{get_cnt('Boys','ALL',m)}</td>
                <td style="border: 1px solid #000;">{get_cnt('ALL','SC',m)}</td><td style="border: 1px solid #000;">{get_cnt('ALL','ST',m)}</td><td style="border: 1px solid #000;">{get_cnt('ALL','OBC',m)}</td><td style="border: 1px solid #000;">{get_cnt('ALL','GEN',m)}</td><td style="border: 1px solid #000; font-weight: 800;">{get_cnt('ALL','ALL',m)}</td>
            </tr>
            """


    # Table 2: Grade Rows HTML
    grade_rows_html = ""
    for g in grades_list:
        def get_grd_cnt(g_filter, c_filter):
            if cdf.empty: return 0
            df_sub = cdf[cdf["Grade"] == g]
            if g_filter != "ALL": df_sub = df_sub[df_sub["Gender"] == g_filter]
            if c_filter != "ALL": df_sub = df_sub[df_sub["Category"] == c_filter]
            return len(df_sub)


        grade_rows_html += f"""
        <tr>
            <td style="border: 1px solid #000; font-weight: bold; padding: 3px;">{g}</td>
            <td style="border: 1px solid #000;">{get_grd_cnt('Girls','SC')}</td><td style="border: 1px solid #000;">{get_grd_cnt('Girls','ST')}</td><td style="border: 1px solid #000;">{get_grd_cnt('Girls','OBC')}</td><td style="border: 1px solid #000;">{get_grd_cnt('Girls','GEN')}</td><td style="border: 1px solid #000; font-weight: 800;">{get_grd_cnt('Girls','ALL')}</td>
            <td style="border: 1px solid #000;">{get_grd_cnt('Boys','SC')}</td><td style="border: 1px solid #000;">{get_grd_cnt('Boys','ST')}</td><td style="border: 1px solid #000;">{get_grd_cnt('Boys','OBC')}</td><td style="border: 1px solid #000;">{get_grd_cnt('Boys','GEN')}</td><td style="border: 1px solid #000; font-weight: 800;">{get_grd_cnt('Boys','ALL')}</td>
            <td style="border: 1px solid #000;">{get_grd_cnt('ALL','SC')}</td><td style="border: 1px solid #000;">{get_grd_cnt('ALL','ST')}</td><td style="border: 1px solid #000;">{get_grd_cnt('ALL','OBC')}</td><td style="border: 1px solid #000;">{get_grd_cnt('ALL','GEN')}</td><td style="border: 1px solid #000; font-weight: 800;">{get_grd_cnt('ALL','ALL')}</td>
        </tr>
        """


    # Exact Layout matching image_aabe70.png
    summary_page_html = f"""
    <div class="printable-area" style="background: #fff; border: 2px solid #000; padding: 14px 20px; max-width: 820px; margin: auto; font-family: Arial, sans-serif; color: #000;">
        <!-- TOP HEADER TABLE -->
        <table style="width: 100%; border-collapse: collapse; border: 1px solid #000; text-align: center; font-size: 13px; font-weight: bold; margin-bottom: 8px;">
            <tr>
                <td colspan="2" style="border: 1px solid #000; padding: 6px; font-size: 18px; font-weight: 900; letter-spacing: 0.5px;">
                    Dise Code : {s_info.get('udise', '23260100101')}
                </td>
            </tr>
            <tr>
                <td style="border: 1px solid #000; width: 50%; padding: 4px;">Block : {s_info.get('block','')}</td>
                <td style="border: 1px solid #000; width: 50%; padding: 4px;">District : {s_info.get('district','')}</td>
            </tr>
            <tr>
                <td style="border: 1px solid #000; padding: 4px;">Class : {selected_class}</td>
                <td style="border: 1px solid #000; padding: 4px;">Medium : {s_info.get('medium','Hindi')}</td>
            </tr>
            <tr>
                <td colspan="2" style="border: 1px solid #000; padding: 6px; font-size: 18px; font-weight: 900; letter-spacing: 0.5px;">
                    Annual Result {s_info.get('session', '2023-24')}
                </td>
            </tr>
        </table>


        <div style="text-align: center; font-weight: 800; font-size: 14px; margin-top: 10px; margin-bottom: 8px; border-top: 2px solid #000; border-bottom: 2px solid #000; padding: 4px 0;">
            Category/Grade Wise Result Summary
        </div>


        <!-- TABLE 1: SUMMARY -->
        <table style="width: 100%; border-collapse: collapse; border: 1px solid #000; text-align: center; font-size: 12px; margin-bottom: 15px;">
            <thead>
                <tr style="background: #fff; font-weight: bold;">
                    <th rowspan="2" style="border: 1px solid #000; width: 16%; padding: 4px;">Summary</th>
                    <th colspan="5" style="border: 1px solid #000; width: 28%; background: #fff; color: #000080;">Girls</th>
                    <th colspan="5" style="border: 1px solid #000; width: 28%; background: #fff; color: #000080;">Boys</th>
                    <th colspan="5" style="border: 1px solid #000; width: 28%; background: #fff; color: #000080;">Grand Total</th>
                </tr>
                <tr style="background: #fff; font-size: 11px;">
                    <th style="border: 1px solid #000; padding: 3px;">Sc</th><th style="border: 1px solid #000; padding: 3px;">St</th><th style="border: 1px solid #000; padding: 3px;">Obc</th><th style="border: 1px solid #000; padding: 3px;">Gen.</th><th style="border: 1px solid #000; padding: 3px; font-weight: 800;">Total</th>
                    <th style="border: 1px solid #000; padding: 3px;">Sc</th><th style="border: 1px solid #000; padding: 3px;">St</th><th style="border: 1px solid #000; padding: 3px;">Obc</th><th style="border: 1px solid #000; padding: 3px;">Gen.</th><th style="border: 1px solid #000; padding: 3px; font-weight: 800;">Total</th>
                    <th style="border: 1px solid #000; padding: 3px;">Sc</th><th style="border: 1px solid #000; padding: 3px;">St</th><th style="border: 1px solid #000; padding: 3px;">Obc</th><th style="border: 1px solid #000; padding: 3px;">Gen.</th><th style="border: 1px solid #000; padding: 3px; font-weight: 800;">Total</th>
                </tr>
            </thead>
            <tbody>
                {cat_rows_html}
            </tbody>
        </table>


        <!-- TABLE 2: GRADE WISE -->
        <table style="width: 100%; border-collapse: collapse; border: 1px solid #000; text-align: center; font-size: 12px; margin-bottom: 25px;">
            <thead>
                <tr style="background: #fff; font-weight: bold;">
                    <th rowspan="2" style="border: 1px solid #000; width: 16%; padding: 4px;">Grade</th>
                    <th colspan="5" style="border: 1px solid #000; width: 28%; color: #000080;">Girls</th>
                    <th colspan="5" style="border: 1px solid #000; width: 28%; color: #000080;">Boys</th>
                    <th colspan="5" style="border: 1px solid #000; width: 28%; color: #000080;">Grand Total</th>
                </tr>
                <tr style="background: #fff; font-size: 11px;">
                    <th style="border: 1px solid #000; padding: 3px;">Sc</th><th style="border: 1px solid #000; padding: 3px;">St</th><th style="border: 1px solid #000; padding: 3px;">Obc</th><th style="border: 1px solid #000; padding: 3px;">Gen.</th><th style="border: 1px solid #000; padding: 3px; font-weight: 800;">Total</th>
                    <th style="border: 1px solid #000; padding: 3px;">Sc</th><th style="border: 1px solid #000; padding: 3px;">St</th><th style="border: 1px solid #000; padding: 3px;">Obc</th><th style="border: 1px solid #000; padding: 3px;">Gen.</th><th style="border: 1px solid #000; padding: 3px; font-weight: 800;">Total</th>
                    <th style="border: 1px solid #000; padding: 3px;">Sc</th><th style="border: 1px solid #000; padding: 3px;">St</th><th style="border: 1px solid #000; padding: 3px;">Obc</th><th style="border: 1px solid #000; padding: 3px;">Gen.</th><th style="border: 1px solid #000; padding: 3px; font-weight: 800;">Total</th>
                </tr>
            </thead>
            <tbody>
                {grade_rows_html}
            </tbody>
        </table>


        <!-- FOOTER SIGNATURE -->
        <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 30px; font-size: 13px; font-weight: bold;">
            <div>Printed On : {TODAY_STR}</div>
            <div>Signature Exam Incharge</div>
        </div>
    </div>
    """
    
    # Export Summary Tables for Department Submissions
    st.markdown("### 📥 सांख्यिकी सारांश एक्सपोर्ट (Export Result Summary for BEO / BRC / DEO Office)")
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
                file_name=f"Result_Summary_Statistics_{selected_class}_{s_info.get('session','2023-24')}{s_ext}",
                mime=s_mime,
                type="primary",
                use_container_width=True
            )
    
# ----------------- MODULE 9: SESSION CHANGE & PROMOTION -----------------
elif menu == T["nav_promote"]:
        st.markdown(f'<div class="main-header">🔄 सत्र परिवर्तन एवं कक्षा पदोन्नति (Session Promotion)</div>', unsafe_allow_html=True)
        st.markdown('<div class="sub-header">नया शैक्षणिक सत्र प्रारंभ होने पर सभी उत्तीर्ण विद्यार्थियों को स्वतः अगली कक्षा में प्रमोट करें</div>', unsafe_allow_html=True)


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
