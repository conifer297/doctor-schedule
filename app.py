import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import random
import collections

st.set_page_config(layout="wide", page_title="Doctor Dynamic-Scheduler Pro")

# --- CSS & Fonts ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;700&display=swap');
    html, body, [class*="css"], .stMarkdown, p, div, span, label { font-family: 'Sarabun', sans-serif !important; }
    .main .block-container { padding: 1rem; }
    th { border: 1px solid #000 !important; text-align: center !important; background-color: #f0f2f6; color: black !important; font-weight: bold; }
    td { border: 1px solid #000 !important; text-align: center !important; }
    .stDataFrame { font-size: 1.1rem; }
    </style>
""", unsafe_allow_html=True)

def get_thai_year(dt): return dt.year + 543
def format_thai_date(dt): return dt.strftime(f"%d/%m/{get_thai_year(dt)}")

def get_fixed_holidays(year_thai):
    yc = year_thai - 543
    return {
        datetime(yc, 1, 1): "วันขึ้นปีใหม่", datetime(yc, 4, 13): "วันสงกรานต์",
        datetime(yc, 4, 14): "วันสงกรานต์", datetime(yc, 4, 15): "วันสงกรานต์",
        datetime(yc, 5, 1): "วันแรงงาน", datetime(yc, 6, 3): "วันเฉลิมฯ พระราชินี",
        datetime(yc, 7, 28): "วันเฉลิมฯ ร.10", datetime(yc, 8, 12): "วันแม่แห่งชาติ",
        datetime(yc, 10, 13): "วันสวรรคต ร.9", datetime(yc, 12, 5): "วันพ่อแห่งชาติ",
        datetime(yc, 12, 31): "วันสิ้นปี"
    }

if 'doctors' not in st.session_state: st.session_state.doctors = []
if 'custom_holidays' not in st.session_state: st.session_state.custom_holidays = {}

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ ตั้งค่าระบบ")
    selected_year = st.number_input("ปี พ.ศ. เริ่มต้น (มิ.ย.)", 2560, 2600, 2568)
    s_dt = datetime(selected_year - 543, 6, 1)
    e_dt = datetime(selected_year - 542, 5, 31)

    st.divider()
    st.header("👨‍⚕️ จัดการแพทย์")
    with st.form("doc_form", clear_on_submit=True):
        n_name = st.text_input("ชื่อแพทย์")
        n_start = st.date_input("วันที่เริ่มงานจริง (พ.ศ.)", s_dt)
        if st.form_submit_button("เพิ่มแพทย์"):
            if n_name:
                st.session_state.doctors.append({
                    "id": random.randint(100,999), 
                    "name": n_name.replace("หมอ", "").strip(), 
                    "start": datetime.combine(n_start, datetime.min.time())
                })
                st.rerun()

    for i, d in enumerate(st.session_state.doctors):
        c1, c2 = st.columns([4,1])
        # วงฟ้า: ระบุวันเริ่มงานชัดเจน
        c1.write(f"แพทย์ {d['name']} \n(เริ่ม {format_thai_date(d['start'])})")
        if c2.button("🗑️", key=f"d_{d['id']}"):
            st.session_state.doctors.pop(i); st.rerun()

    st.divider()
    st.header("📅 วันหยุด")
    with st.form("h_form", clear_on_submit=True):
        h_date = st.date_input("วันที่")
        h_name = st.text_input("ชื่อวันหยุด")
        if st.form_submit_button("บันทึก"):
            if h_name:
                st.session_state.custom_holidays[datetime.combine(h_date, datetime.min.time())] = h_name
                st.rerun()

# --- DYNAMIC ALGORITHM ---
def generate_dynamic_schedule():
    all_h = get_fixed_holidays(selected_year)
    all_h.update(get_fixed_holidays(selected_year+1))
    all_h.update(st.session_state.custom_holidays)
    
    if not st.session_state.doctors: return pd.DataFrame(), [], []

    # หาว่าแพทย์คนสุดท้ายเริ่มงานเมื่อไหร่
    latest_start = max([d['start'] for d in st.session_state.doctors])
    
    data = []
    # แยกเก็บสถิติ 2 ช่วง
    stats_before = {d['name']: collections.defaultdict(int) for d in st.session_state.doctors}
    stats_after = {d['name']: collections.defaultdict(int) for d in st.session_state.doctors}
    
    curr = s_dt
    last_month = -1
    
    # ตัวแปรควบคุมการรันเวรแบบ Fixed
    # เราจะเก็บ index ของแพทย์แต่ละกลุ่มความพร้อม
    pool_state = {} 

    while curr <= e_dt:
        if curr.month != last_month:
            m_name = ["", "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน", "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"][curr.month]
            data.append({"วันที่": f"--- {m_name} {get_thai_year(curr)} ---", "is_header": True})
            last_month = curr.month

        # 1. ตรวจสอบแพทย์ที่เริ่มงานแล้ว ณ วันนี้
        available_docs = sorted([d['name'] for d in st.session_state.doctors if d['start'] <= curr])
        
        if not available_docs: # กรณีไม่มีแพทย์คนไหนเริ่มงานเลย
            curr += timedelta(days=1)
            continue

        # 2. จัดลำดับเวรแบบ Fixed โดยจะ Reset เมื่อจำนวนคนเปลี่ยน
        n_avail = len(available_docs)
        if n_avail not in pool_state: pool_state[n_avail] = 0
        
        h_text = all_h.get(curr, "")
        is_we = (curr.weekday() >= 5) or (h_text != "")
        suffix = "WE" if is_we else "WD"

        # เลือกเวรหลัก (OPD) ตามคิว Fixed
        v1 = available_docs[pool_state[n_avail] % n_avail]
        if not is_we: pool_state[n_avail] += 1 # นับคิวเฉพาะวันธรรมดา
        
        # เลือกเวรรองและถปภ (สุ่มจากคนที่เหลือ)
        v2_pool = [d for d in available_docs if d != v1]
        v2 = random.choice(v2_pool) if v2_pool else v1
        
        v3 = "-"
        if is_we or curr.weekday() == 4:
            v3_pool = [d for d in available_docs if d not in [v1, v2]]
            if v3_pool: v3 = random.choice(v3_pool)

        # 3. บันทึกสถิติแยกช่วง (ก่อน/หลัง แพทย์คนสุดท้ายมา)
        target_stats = stats_after if curr >= latest_start else stats_before
        target_stats[v1][f"OPD_{suffix}"] += 1
        target_stats[v2][f"WARD_{suffix}"] += 1
        if v3 != "-": target_stats[v3][f"SEC_{suffix}"] += 1

        data.append({
            "วันที่": format_thai_date(curr), "วัน": ["จันทร์","อังคาร","พุธ","พฤหัสบดี","ศุกร์","เสาร์","อาทิตย์"][curr.weekday()],
            "เวรโอพีดี": v1, "เวรวอร์ด": v2, "เวรถปภ.": v3, "หมายเหตุ": h_text,
            "is_h": is_we, "is_header": False
        })
        curr += timedelta(days=1)

    return pd.DataFrame(data), stats_before, stats_after, latest_start

# --- UI ---
st.title(f"🏥 ตารางเวรแพทย์ (ระบบ Dynamic เริ่มงาน)")

if len(st.session_state.doctors) >= 1:
    df, s_before, s_after, l_start = generate_dynamic_schedule()
    
    def style_table(row):
        if row.get('is_header'): return ['background-color: #B2EBF2; color: black; font-weight: bold; border: 1px solid black;'] * len(row)
        return [f"background-color: {'#FFCDD2' if row.get('is_h') else 'white'}; color: black; border: 1px solid black;"] * len(row)

    st.dataframe(df.style.apply(style_table, axis=1).hide(axis='columns', subset=['is_h', 'is_header']), height=600, use_container_width=True)

    # --- ตารางสรุปใหม่ ---
    st.divider()
    st.header("📊 สรุปจำนวนเวรแยกช่วงเวลา")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader(f"1. ช่วงแรก (ก่อน {format_thai_date(l_start)})")
        df_b = pd.DataFrame.from_dict(s_before, orient='index').fillna(0).astype(int)
        if not df_b.empty: st.table(df_b)
        else: st.write("ไม่มีข้อมูลช่วงนี้")

    with col2:
        st.subheader(f"2. ช่วงสมบูรณ์ (ตั้งแต่ {format_thai_date(l_start)})")
        df_a = pd.DataFrame.from_dict(s_after, orient='index').fillna(0).astype(int)
        if not df_a.empty: st.table(df_a)
        else: st.write("ยังไม่ถึงกำหนดเริ่มงาน")
else:
    st.info("👈 เพิ่มชื่อแพทย์และวันที่เริ่มงานที่แถบด้านข้าง")
