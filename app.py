import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import random

# ตั้งค่าหน้าจอและนำเข้าฟอนต์ TH Sarabun (สารบรรณ)
st.set_page_config(layout="wide", page_title="Doctor Schedule Pro")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;700&display=swap');
    
    html, body, [class*="css"], .stMarkdown, p, div, span, label {
        font-family: 'Sarabun', sans-serif !important;
    }
    
    .main .block-container { padding: 1rem; }
    th { border: 1px solid #000 !important; text-align: center !important; background-color: #f0f2f6; color: black !important; font-weight: bold; }
    td { border: 1px solid #000 !important; text-align: center !important; }
    
    /* ปรับขนาดฟอนต์ให้ใหญ่ขึ้นเพื่อให้อ่านง่ายแบบ Sarabun */
    .stDataFrame { font-size: 1.1rem; }
    </style>
""", unsafe_allow_html=True)

# --- 1. Helper Functions ---
def get_thai_year(dt): return dt.year + 543

def format_thai_date(dt): return dt.strftime(f"%d/%m/{get_thai_year(dt)}")

def get_fixed_holidays(year_thai):
    yc = year_thai - 543
    return {
        datetime(yc, 1, 1): "วันขึ้นปีใหม่", datetime(yc, 4, 6): "วันจักรี",
        datetime(yc, 4, 13): "วันสงกรานต์", datetime(yc, 4, 14): "วันสงกรานต์",
        datetime(yc, 4, 15): "วันสงกรานต์", datetime(yc, 5, 1): "วันแรงงาน",
        datetime(yc, 5, 4): "วันฉัตรมงคล", datetime(yc, 6, 3): "วันเฉลิมฯ พระราชินี",
        datetime(yc, 7, 28): "วันเฉลิมฯ ร.10", datetime(yc, 8, 12): "วันแม่แห่งชาติ",
        datetime(yc, 10, 13): "วันสวรรคต ร.9", datetime(yc, 10, 23): "วันปิยมหาราช",
        datetime(yc, 12, 5): "วันพ่อแห่งชาติ", datetime(yc, 12, 10): "วันรัฐธรรมนูญ",
        datetime(yc, 12, 31): "วันสิ้นปี"
    }

# --- 2. Session State ---
if 'doctors' not in st.session_state: st.session_state.doctors = []
if 'custom_holidays' not in st.session_state: st.session_state.custom_holidays = {}

# --- 3. Sidebar ---
with st.sidebar:
    st.header("⚙️ ตั้งค่าพื้นฐาน")
    selected_year = st.number_input("จัดเวรของปี พ.ศ. (เริ่ม มิ.ย.)", 2560, 2600, 2568)
    s_dt = datetime(selected_year - 543, 6, 1)
    e_dt = datetime(selected_year - 542, 5, 31)

    if st.button("🗑️ ล้างข้อมูลใหม่ทั้งหมด", use_container_width=True):
        st.session_state.doctors = []
        st.session_state.custom_holidays = {}
        st.rerun()

    st.divider()
    st.header("👨‍⚕️ รายชื่อแพทย์")
    with st.form("doc_form", clear_on_submit=True):
        n_name = st.text_input("ชื่อ (เช่น A, B)")
        n_start = st.date_input("เริ่มงาน (พ.ศ.)", s_dt)
        if st.form_submit_button("เพิ่มแพทย์"):
            if n_name:
                clean = n_name.replace("หมอ", "").strip()
                st.session_state.doctors.append({"id": random.randint(100,999), "name": clean, "start": datetime.combine(n_start, datetime.min.time())})
                st.rerun()

    for i, d in enumerate(st.session_state.doctors):
        c1, c2 = st.columns([4,1])
        c1.write(f"แพทย์ {d['name']}")
        if c2.button("🗑️", key=f"d_{d['id']}"):
            st.session_state.doctors.pop(i); st.rerun()

    st.divider()
    st.header("📅 วันหยุดพิเศษ")
    with st.form("h_form", clear_on_submit=True):
        h_date = st.date_input("เลือกวันที่ (พ.ศ.)")
        h_name = st.text_input("ชื่อวันหยุด")
        if st.form_submit_button("บันทึกวันหยุด"):
            if h_name:
                st.session_state.custom_holidays[datetime.combine(h_date, datetime.min.time())] = h_name
                st.rerun()

    # รายการวันหยุดที่ลงไว้แล้ว (กลับมาแล้ว)
    if st.session_state.custom_holidays:
        st.subheader("รายการที่บันทึก:")
        for d, name in sorted(st.session_state.custom_holidays.items()):
            c1, c2 = st.columns([4,1])
            c1.caption(f"{format_thai_date(d)} - {name}")
            if c2.button("🗑️", key=f"h_{d.timestamp()}"):
                del st.session_state.custom_holidays[d]; st.rerun()

# --- 4. Logic: Rotation ---
def generate():
    all_h = get_fixed_holidays(selected_year)
    all_h.update(get_fixed_holidays(selected_year+1))
    all_h.update(st.session_state.custom_holidays)
    
    docs = [d['name'] for d in st.session_state.doctors]
    if not docs: return pd.DataFrame(), {}
    
    curr = s_dt
    data = []
    stats = {n: {"wd": 0, "we": 0} for n in docs}
    
    # ลอจิก Fixed Rotation สำหรับวันธรรมดา (ตามข้อ 7)
    wd_order = []
    temp = s_dt
    idx = 0
    while temp <= e_dt:
        is_h = (temp.weekday() >= 5) or (temp in all_h)
        if not is_h:
            wd_order.append(docs[idx % len(docs)])
            idx += 1
        temp += timedelta(days=1)

    curr = s_dt
    wd_idx = 0
    last_month = -1
    while curr <= e_dt:
        if curr.month != last_month:
            m_name = ["", "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน", "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"][curr.month]
            data.append({"วันที่": f"--- {m_name} {get_thai_year(curr)} ---", "is_header": True})
            last_month = curr.month

        h_text = all_h.get(curr, "")
        is_h = (curr.weekday() >= 5) or (h_text != "")
        
        v1 = wd_order[wd_idx] if not is_h else random.choice(docs)
        if not is_h: wd_idx += 1
        
        v2 = random.choice([d for d in docs if d != v1])
        v3 = "-"
        if is_h or curr.weekday() == 4: # วันหยุดหรือวันศุกร์
            v3 = random.choice([d for d in docs if d not in [v1, v2]])
        
        # เก็บสถิติ
        day_type = "we" if is_h else "wd"
        stats[v1][day_type] += 1
        stats[v2][day_type] += 1
        if v3 != "-": stats[v3][day_type] += 1

        data.append({
            "วันที่": format_thai_date(curr),
            "วัน": ["จันทร์","อังคาร","พุธ","พฤหัสบดี","ศุกร์","เสาร์","อาทิตย์"][curr.weekday()],
            "เวรโอพีดี": v1, "เวรวอร์ด": v2, "เวรถปภ.": v3, "หมายเหตุ": h_text,
            "is_h": is_h, "is_header": False
        })
        curr += timedelta(days=1)
    return pd.DataFrame(data), stats

# --- 5. Display ---
st.title(f"📋 ตารางเวรแพทย์ พ.ศ. {selected_year}")

if len(st.session_state.doctors) >= 2:
    df, stats = generate()
    
    def style_table(row):
        if row.get('is_header'): return ['background-color: #B2EBF2; font-weight: bold; border: 1px solid black;'] * len(row)
        bg = '#FFCDD2' if row.get('is_h') else 'white'
        return [f'background-color: {bg}; border: 1px solid black; color: black;'] * len(row)

    st.dataframe(
        df.style.apply(style_table, axis=1).hide(axis='columns', subset=['is_h', 'is_header']),
        height=700, use_container_width=True
    )

    # --- สรุปจำนวนเวร (กลับมาแล้ว) ---
    st.divider()
    st.subheader("📊 สรุปจำนวนเวรแยกประเภท")
    summary_data = []
    for name, s in stats.items():
        summary_data.append({
            "ชื่อแพทย์": name,
            "วันธรรมดา (ครั้ง)": s['wd'],
            "วันหยุด/นักขัตฤกษ์ (ครั้ง)": s['we'],
            "รวมทั้งหมด": s['wd'] + s['we']
        })
    st.table(pd.DataFrame(summary_data))
else:
    st.info("👈 กรุณาเพิ่มรายชื่อแพทย์ที่แถบด้านข้างอย่างน้อย 2 ท่าน")
