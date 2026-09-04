import streamlit as st
import pandas as pd
import numpy as np
import json, base64, os
from io import BytesIO
from datetime import datetime

st.set_page_config(
    page_title="School Result Pro - बहुभाषी संपूर्ण परीक्षा प्रबंधन प्रणाली",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

DATA_FILE = "school_data_store.json"
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
        "nav_marksheet": "🖨️ 5. वार्षिक प्रगति पत्रक (Print Marksheet)",
        "nav_a3_result": "📜 6. A3 वार्षिक परीक्षाफल पत्रक (Annual Result Sheet)",
        "nav_summary": "📊 7. श्रेणीवार परीक्षा परिणाम सारांश (Result Summary)",
        "nav_promote": "🔄 8. सत्र परिवर्तन एवं कक्षा पदोन्नति (Session Promotion)",
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
        "nav_marksheet": "🖨️ 5. Progress Report Card (Marksheet)",
        "nav_a3_result": "📜 6. A3 Annual Result Sheet",
        "nav_summary": "📊 7. Category/Grade Wise Result Summary",
        "nav_promote": "🔄 8. Session Roll-over & Promotion",
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
        "nav_marksheet": "🖨️ 5. प्रगती पत्रक (Marksheet)",
        "nav_a3_result": "📜 6. A3 वार्षिक निकाल पत्रक (Annual Result Sheet)",
        "nav_summary": "📊 7. प्रवर्गनिहाय निकाल गोषवारा (Result Summary)",
        "nav_promote": "🔄 8. सत्र बदल व वर्ग पदोन्नती (Promotion)",
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
    try:
        payload = {
            "school_info": st.session_state.school_info,
            "classes_list": st.session_state.classes_list,
            "data_store": serialize_store(st.session_state.data_store)
        }
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        st.error(f"डेटा सुरक्षित करने में त्रुटि: {e}")
        return False

def load_data_from_disk():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
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
if "ui_lang" not in st.session_state:
    st.session_state.ui_lang = "हिन्दी (Hindi)"

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
with st.sidebar:
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

# ----------------- MODULE 2: STUDENT MASTER -----------------
elif menu == T["nav_student"]:
    st.markdown(f'<div class="main-header">👨‍🎓 विद्यार्थी मास्टर डेटा — {selected_class}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="sub-header">छात्रों का व्यक्तिगत विवरण दर्ज करें, संपादन करें या शाला छोड़ने पर टीसी जारी करें</div>', unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["📋 छात्र सूची एवं संपादन (Data Grid)", "➕ नया छात्र जोड़ें (Add Student)", "🗑️ छात्र हटाएं / टीसी (TC) जारी करें"])

    with tab1:
        st.write(f"वर्तमान में **{len(cls_data['students'])}** छात्र पंजीकृत हैं:")
        df_students = cls_data["students"].copy()
        
        edited_df = st.data_editor(
            df_students,
            num_rows="dynamic",
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
            key=f"editor_students_{selected_class}"
        )
        if st.button("💾 अपडेट सहेजें (Save Table)", type="primary"):
            cls_data["students"] = edited_df
            save_data_to_disk()
            st.success("✅ छात्र सूची सुरक्षित कर ली गई!")

    with tab2:
        st.subheader("विद्यार्थी की नई प्रविष्टि (Register New Student):")
        with st.form("add_student_form"):
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
                s_class = st.text_input("7. Class:", value=selected_class)
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

            photo_file = st.file_uploader("Photo (Optional):", type=["jpg", "jpeg", "png"])
            submit_student = st.form_submit_button("➕ विद्यार्थी जोड़ें (Submit)", type="primary")

            if submit_student:
                if not s_name:
                    st.error("कृपया छात्र का नाम दर्ज करें!")
                else:
                    p_b64 = None
                    if photo_file:
                        p_b64 = base64.b64encode(photo_file.read()).decode()
                    new_row = {
                        "Roll_No": s_roll, "Scholar_No": s_schol, "Name": s_name,
                        "Father_Name": s_father, "Mother_Name": s_mother, "DOB": str(s_dob),
                        "Class": s_class, "Section": s_sec, "Gender": s_gender,
                        "Category": s_cat, "SSSM_ID": s_sssm, "Aadhar_No": s_aadhar,
                        "Medium": s_medium, "Status": "Present", "Photo_b64": p_b64,
                        "Total_Days": s_tot_days, "Attended_Days": s_att_days
                    }
                    cls_data["students"] = pd.concat([cls_data["students"], pd.DataFrame([new_row])], ignore_index=True)
                    save_data_to_disk()
                    st.success(f"✅ छात्र '{s_name}' सफलतापूर्वक जोड़ा गया!")
                    st.rerun()

    with tab3:
        st.subheader("🗑️ छात्र हटाएं / स्थानांतरण प्रमाण पत्र (TC) जारी करें")
        st.info("यदि कोई विद्यार्थी शाला छोड़ता है या टीसी (TC) लेता है तो उसका रोल नंबर चुनकर रिकॉर्ड हटाएं:")
        
        students_df = cls_data["students"]
        if students_df.empty:
            st.warning("कक्षा में कोई छात्र उपलब्ध नहीं है।")
        else:
            del_options = [f"Roll {s['Roll_No']}: {s['Name']} (Scholar: {s['Scholar_No']})" for _, s in students_df.iterrows()]
            student_to_delete_str = st.selectbox("हटाने हेतु विद्यार्थी चुनें:", del_options)
            del_roll = int(student_to_delete_str.split(":")[0].replace("Roll", "").strip())
            tc_reason = st.text_input("शाला छोड़ने का कारण (Reason for Leaving / TC):", value="Transfer Certificate (TC) Issued / Left School")
            
            if st.button("⚠️ पुष्टि करें और विद्यार्थी का रिकॉर्ड हटाएं (Delete Record)", type="primary"):
                cls_data["students"] = cls_data["students"][cls_data["students"]["Roll_No"] != del_roll].reset_index(drop=True)
                if del_roll in cls_data["evaluations"]:
                    del cls_data["evaluations"][del_roll]
                save_data_to_disk()
                st.success(f"✅ रोल नंबर {del_roll} का रिकॉर्ड सफलतापूर्वक हटा दिया गया। कारण: {tc_reason}")
                st.rerun()

# ----------------- MODULE 3: MONTHLY ATTENDANCE SHEET (IMAGE 1: image_aab3c5.png) -----------------
elif menu == T["nav_attendance"]:
    st.markdown('<div class="main-header">📅 माहवार विद्यार्थी उपस्थिति पत्रक (Monthly Attendance Sheet)</div>', unsafe_allow_html=True)
    st.markdown('<div style="color: #008000; font-weight: bold; text-align: center; font-size: 15px; margin-bottom: 12px;">स्कूल कार्य दिवस की एंट्री माह के ठीक ऊपर वाले सेल में करें एवं विद्यार्थी की माहवार उपस्थिति की एंट्री उसके सामने वाले सेल में करें</div>', unsafe_allow_html=True)

    students_df = cls_data["students"]
    if students_df.empty:
        st.warning("⚠️ कृपया पहले 'विद्यार्थी मास्टर' में छात्र जोड़ें!")
    else:
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

        st.markdown(f"""
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
        """, unsafe_allow_html=True)

        # Overall Status
        col_st1, col_st2 = st.columns([1, 3])
        with col_st1:
            st_overall_status = st.selectbox("📌 छात्र की परीक्षा स्थिति:", ["Present", "Absent"], 
                                             index=0 if eval_data.get("status", "Present") == "Present" else 1)
            eval_data["status"] = st_overall_status

        # 1. Main Subjects (With Subject-Wise Present/Absent!)
        with st.expander(f"📚 1. मुख्य विषय अंक प्रविष्टि (विषयवार Present/Absent सहित)", expanded=True):
            st.info(f"💡 {selected_class} के विषय: अर्धवार्षिक (पूर्णांक 40, उत्तीर्णांक 13) | वार्षिक (पूर्णांक 60, उत्तीर्णांक 20) | कुल 100")
            
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
                p_hy_val = prev_sub.get("half_yearly", 32)
                p_yr_stat = prev_sub.get("status_yr", "Present")
                p_yr_val = prev_sub.get("annual", 48)

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
                    "status_yr": stat_yr, "annual": val_yr,
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

# ----------------- MODULE 5: PRINT MARKSHEET (EXACT REPLICA) -----------------
elif menu == T["nav_marksheet"]:
    students_df = cls_data["students"]
    if students_df.empty:
        st.warning("⚠️ कक्षा में कोई छात्र उपलब्ध नहीं है।")
    else:
        st_names = [f"Roll {s['Roll_No']}: {s['Name']}" for _, s in students_df.iterrows()]
        c_top1, c_top2, c_top3 = st.columns([3, 2, 2])
        with c_top1:
            sel_student_str = st.selectbox("विद्यार्थी / रोल नंबर चुनें:", st_names)
            sel_roll = int(sel_student_str.split(":")[0].replace("Roll", "").strip())
        with c_top2:
            st.markdown(f"""
            <div style="border: 2px solid #000; padding: 6px 12px; background: #fff; text-align: center; margin-top: 18px;">
                <span style="font-size: 13px; font-weight: bold; margin-right: 10px;">Enter Student Roll Number:</span>
                <span style="color: red; font-size: 18px; font-weight: 800;">{sel_roll}</span>
            </div>
            """, unsafe_allow_html=True)
        with c_top3:
            st.markdown("<div style='margin-top: 22px;'>", unsafe_allow_html=True)
            st.button("🖨️ Print", on_click=None, use_container_width=True)
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
            <tr>
                <td style="border: 1px solid #000; text-align: left; padding: 3px 5px; font-weight: bold; font-size: 11px;">▸ {label.split("(")[0].strip()}</td>
                <td style="border: 1px solid #000; text-align: center; padding: 3px 5px; font-weight: bold; font-size: 11px;">{g_val}</td>
            </tr>
            """

        social_dict = ev.get("social", {})
        soc_rows_html = ""
        for i in range(5):
            k1, l1 = SOCIAL_ACTIVITIES[i]
            k2, l2 = SOCIAL_ACTIVITIES[i+5]
            g1 = social_dict.get(k1, "A")
            g2 = social_dict.get(k2, "A")
            soc_rows_html += f"""
            <tr>
                <td style="border: 1px solid #000; text-align: left; padding: 3px 5px; font-weight: bold; font-size: 11px;">▸ {l1.split("(")[0].strip()}</td>
                <td style="border: 1px solid #000; text-align: center; padding: 3px 5px; font-weight: bold; font-size: 11px;">{g1}</td>
                <td style="border: 1px solid #000; text-align: left; padding: 3px 5px; font-weight: bold; font-size: 11px;">▸ {l2.split("(")[0].strip()}</td>
                <td style="border: 1px solid #000; text-align: center; padding: 3px 5px; font-weight: bold; font-size: 11px;">{g2}</td>
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
                    <td style="width: 38%; vertical-align: top; padding-right: 6px;">
                        <table style="width: 100%; border-collapse: collapse; border: 1px solid #000;">
                            <thead>
                                <tr style="background-color: #FDEBD0;">
                                    <th style="border: 1px solid #000; text-align: left; padding: 4px 6px; font-size: 11px;">Co-Curricular Activities</th>
                                    <th style="border: 1px solid #000; width: 25%; font-size: 11px; padding: 4px;">Grade</th>
                                </tr>
                            </thead>
                            <tbody>{cocurr_rows_html}</tbody>
                        </table>
                    </td>
                    <td style="width: 62%; vertical-align: top; padding-left: 6px;">
                        <table style="width: 100%; border-collapse: collapse; border: 1px solid #000;">
                            <thead>
                                <tr style="background-color: #FDEBD0;">
                                    <th colspan="4" style="border: 1px solid #000; text-align: center; padding: 4px 6px; font-size: 11px;">Social Activities</th>
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
        st.markdown(exact_card_html, unsafe_allow_html=True)

# ----------------- MODULE 6: A3 ANNUAL RESULT SHEET (IMAGE 2: image_aab7a9.png) -----------------
elif menu == T["nav_a3_result"]:
    students_df = cls_data["students"]
    s_info = st.session_state.school_info
    cls_subjects = get_class_subjects(selected_class)
    sub_count = len(cls_subjects)
    max_total = sub_count * 100

    c_a3_1, c_a3_2 = st.columns([3, 1])
    with c_a3_1:
        st.markdown('<div style="color: red; font-weight: bold; font-size: 15px;">*इस परीक्षाफल पत्रक को अनुमोदन हेतु A-3 साइज़ के पेपर पर प्रिंट करें</div>', unsafe_allow_html=True)
    with c_a3_2:
        st.button("🖨️ Print A3 Sheet", on_click=None, use_container_width=True)

    # Compute summaries for top boxes
    enrolled_cnt = len(students_df)
    appeared_cnt = 0
    absent_cnt = 0
    pass_cnt = 0
    fail_cnt = 0
    grade_counts = {"A+": 0, "A": 0, "B+": 0, "B": 0, "C+": 0, "C": 0, "D": 0, "E": 0}

    # Student rows for A3 Table
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

            hy_cells += f"<td>{hy_val}</td>"
            yr_cells += f"<td>{yr_val}</td>"
            fn_cells += f"<td><b>{sub_tot}</b></td>"

        pct = round((tot_obt / max_total) * 100, 1) if max_total else 0
        grd = calculate_grade(pct)
        is_pass = (all_passed and pct >= 33 and st_status != "Absent")
        res_str = "Pass" if is_pass else "Fail"
        if is_pass: pass_cnt += 1
        else: fail_cnt += 1

        if grd in grade_counts: grade_counts[grd] += 1

        # Co-Curricular
        co_dict = ev.get("co_curricular", {})
        co_tds = "".join([f"<td>{co_dict.get(k, 'A')}</td>" for k, _ in CO_CURRICULAR_ACTIVITIES])

        # Social
        soc_dict = ev.get("social", {})
        soc_tds = "".join([f"<td>{soc_dict.get(k, 'A')}</td>" for k, _ in SOCIAL_ACTIVITIES])

        student_rows_a3 += f"""
        <tr>
            <td>{idx+1}</td>
            <td>{r_no}</td>
            <td>{s['Scholar_No']}</td>
            <td style="text-align: left; font-weight: bold; white-space: nowrap;">{s['Name']}</td>
            <td style="text-align: left;">{s['Mother_Name']}</td>
            <td style="text-align: left;">{s['Father_Name']}</td>
            <td>{s['DOB']}</td>
            <td>{s['Gender']}</td>
            <td>{s['Category']}</td>
            <td>{s['SSSM_ID']}</td>
            <td>{s.get('Aadhar_No','')}</td>
            {hy_cells}
            {yr_cells}
            {fn_cells}
            <td style="font-weight: bold; color: #008000;">{tot_obt}</td>
            <td style="font-weight: bold; color: {'#008000' if res_str=='Pass' else '#CC0000'};">{res_str}</td>
            <td>{pct}%</td>
            <td style="font-weight: bold;">{grd}</td>
            <td>{idx+1}</td>
            <td>{s.get('Attended_Days', 200)}/{s.get('Total_Days', 220)}</td>
            {co_tds}
            {soc_tds}
        </tr>
        """

    # Exact Header HTML matching image_aab7a9.png
    a3_html = f"""
    <div class="printable-area" style="background: #fff; border: 2px solid #000; padding: 10px; font-family: Arial, sans-serif; width: 100%;">
        <div style="font-size: 22px; font-weight: 900; text-align: left; margin-bottom: 6px; letter-spacing: 0.5px;">
            ANNUAL RESULT SHEET {s_info.get('session', '2023-24')}
        </div>

        <table style="width: 100%; border-collapse: collapse; margin-bottom: 8px;">
            <tr>
                <td style="width: 50%; vertical-align: top;">
                    <table style="width: 100%; border-collapse: collapse; border: 1px solid #000; font-size: 11px;">
                        <tr><td colspan="4" style="border: 1px solid #000; padding: 3px 6px;"><b>Name Of School:</b> {s_info.get('name','')}</td></tr>
                        <tr>
                            <td style="border: 1px solid #000; padding: 3px 6px;"><b>Dise Code:</b> {s_info.get('udise','')}</td>
                            <td style="border: 1px solid #000; padding: 3px 6px;"><b>Class:</b> {selected_class}</td>
                            <td style="border: 1px solid #000; padding: 3px 6px;"><b>Medium:</b> {s_info.get('medium','Hindi')}</td>
                            <td style="border: 1px solid #000; padding: 3px 6px;"><b>Block:</b> {s_info.get('block','')} | <b>Dist:</b> {s_info.get('district','')}</td>
                        </tr>
                    </table>
                </td>
                <td style="width: 25%; vertical-align: top; padding: 0 4px;">
                    <table style="width: 100%; border-collapse: collapse; border: 1px solid #000; font-size: 11px; text-align: center;">
                        <tr style="background: #f8fafc;"><th colspan="5" style="border: 1px solid #000; padding: 2px;">Students Wise Summary</th></tr>
                        <tr style="font-weight: bold; background: #fff;">
                            <td style="border: 1px solid #000; padding: 2px;">Enrolled</td>
                            <td style="border: 1px solid #000; padding: 2px;">Appeared</td>
                            <td style="border: 1px solid #000; padding: 2px;">Absent</td>
                            <td style="border: 1px solid #000; padding: 2px;">Pass</td>
                            <td style="border: 1px solid #000; padding: 2px;">Fail</td>
                        </tr>
                        <tr style="font-weight: bold; font-size: 12px;">
                            <td style="border: 1px solid #000; padding: 2px;">{enrolled_cnt}</td>
                            <td style="border: 1px solid #000; padding: 2px;">{appeared_cnt}</td>
                            <td style="border: 1px solid #000; padding: 2px;">{absent_cnt}</td>
                            <td style="border: 1px solid #000; padding: 2px; color: green;">{pass_cnt}</td>
                            <td style="border: 1px solid #000; padding: 2px; color: red;">{fail_cnt}</td>
                        </tr>
                    </table>
                </td>
                <td style="width: 25%; vertical-align: top;">
                    <table style="width: 100%; border-collapse: collapse; border: 1px solid #000; font-size: 11px; text-align: center;">
                        <tr style="background: #f8fafc;"><th colspan="8" style="border: 1px solid #000; padding: 2px;">Grade Wise Result Summary</th></tr>
                        <tr style="font-weight: bold;">
                            <td style="border: 1px solid #000; padding: 2px;">A+</td><td style="border: 1px solid #000; padding: 2px;">A</td>
                            <td style="border: 1px solid #000; padding: 2px;">B+</td><td style="border: 1px solid #000; padding: 2px;">B</td>
                            <td style="border: 1px solid #000; padding: 2px;">C+</td><td style="border: 1px solid #000; padding: 2px;">C</td>
                            <td style="border: 1px solid #000; padding: 2px;">D</td><td style="border: 1px solid #000; padding: 2px;">E</td>
                        </tr>
                        <tr style="font-weight: bold; font-size: 12px;">
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

        <!-- A3 MASTER TABULATION TABLE -->
        <table class="a3-table">
            <thead>
                <tr>
                    <th rowspan="2">Sr.No.</th>
                    <th rowspan="2">Roll No.</th>
                    <th rowspan="2">Scholar No.</th>
                    <th rowspan="2">Name Of Student</th>
                    <th rowspan="2">Mother's Name</th>
                    <th rowspan="2">Father's Name</th>
                    <th rowspan="2">Date Of Birth</th>
                    <th rowspan="2">Gender</th>
                    <th rowspan="2">Category</th>
                    <th rowspan="2">Samagra ID</th>
                    <th rowspan="2">Aadhar No.</th>
                    <th colspan="{sub_count}">Half Yearly Evaluation (Max 40)</th>
                    <th colspan="{sub_count}">Annual Evaluation (Max 60)</th>
                    <th colspan="{sub_count}">Final Assessment (Max 100)</th>
                    <th colspan="6">Final Result</th>
                    <th colspan="5">Co-Curricular Activities</th>
                    <th colspan="10">SOCIAL ACTIVITIES</th>
                </tr>
                <tr>
                    {"".join([f"<th>{s['name'].split()[0]}</th>" for s in cls_subjects])}
                    {"".join([f"<th>{s['name'].split()[0]}</th>" for s in cls_subjects])}
                    {"".join([f"<th>{s['name'].split()[0]}</th>" for s in cls_subjects])}
                    <th>Total ({max_total})</th>
                    <th>Result</th>
                    <th>Percentage</th>
                    <th>Grade</th>
                    <th>Rank</th>
                    <th>Attendance</th>
                    <th>LITERARY</th><th>SCIENTIFIC</th><th>CULTURAL</th><th>CREATIVITY</th><th>SPORTS</th>
                    <th>REGULARITY</th><th>PUNCTUALITY</th><th>CLEANLINESS</th><th>DISCIPLINE</th><th>CO-OPERATION</th>
                    <th>ENV.</th><th>LEADERSHIP</th><th>TRUTHFULNESS</th><th>HONESTY</th><th>EXPRESIVE</th>
                </tr>
            </thead>
            <tbody>
                {student_rows_a3}
            </tbody>
        </table>
    </div>
    """
    st.markdown(a3_html, unsafe_allow_html=True)

# ----------------- MODULE 7: CATEGORY/GRADE WISE RESULT SUMMARY (IMAGE 3: image_aabe70.png) -----------------
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
    st.markdown(summary_page_html, unsafe_allow_html=True)

# ----------------- MODULE 8: SESSION CHANGE & PROMOTION -----------------
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

