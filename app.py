import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import random
import collections

st.set_page_config(layout="wide", page_title="Doctor Fair-Scheduler Pro")

# --- CSS STYLING ---
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

# --- HELPER FUNCTIONS ---
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

# --- SESSION STATE ---
if 'doctors' not in st.session_state: st.session_state.doctors = []
if 'custom_holidays' not in st.session_state: st.session_state.custom_holidays = {}

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ ตั้งค่าระบบ")
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
        n_name = st.text_input("ชื่อ")
        n_start = st.date_input("เริ่มงาน", s_dt)
        if st.form_submit_button("เพิ่มแพทย์"):
            if n_name:
                st.session_state.doctors.append({"id": random.randint(100,999), "name": n_name.replace("หมอ", "").strip(), "start": datetime.combine(n_start, datetime.min.time())})
                st.rerun()

    for i, d in enumerate(st.session_state.doctors):
        c1, c2 = st.columns([4,1])
        c1.write(f"แพทย์ {d['name']}")
        if c2.button("🗑️", key=f"d_{d['id']}"):
            st.session_state.doctors.pop(i); st.rerun()

    st.divider()
    st.header("📅 วันหยุดเพิ่มเติม")
    with st.form("h_form", clear_on_submit=True):
        h_date = st.date_input("วันที่")
        h_name = st.text_input("ชื่อวันหยุด")
        if st.form_submit_button("บันทึก"):
            if h_name:
                st.session_state.custom_holidays[datetime.combine(h_date, datetime.min.time())] = h_name
                st.rerun()

# --- FAIR ALGORITHM ---
def generate_fair_schedule():
    all_h = get_fixed_holidays(selected_year)
    all_h.update(get_fixed_holidays(selected_year+1))
    all_h.update(st.session_state.custom_holidays)
    
    docs = [d['name'] for d in st.session_state.doctors]
    if not docs: return pd.DataFrame(), {}, {}
    
    # ภาระงาน: {ชื่อ: คะแนนรวม} (วันหยุด=2, วันธรรมดา=1)
    load = {n: 0 for n in docs}
    # สถิติละเอียด
    stats = {n: {"OPD_WD":0, "OPD_WE":0, "WARD_WD":0, "WARD_WE":0, "SEC_WD":0, "SEC_WE":0} for n in docs}
    # เก็บวันทำงานเพื่อหาช่วงหยุด
    work_days = {n: [] for n in docs}

    curr = s_dt
    data = []
    last_month = -1

    while curr <= e_dt:
        if curr.month != last_month:
            m_name = ["", "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน", "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"][curr.month]
            data.append({"วันที่": f"--- {m_name} {get_thai_year(curr)} ---", "is_header": True})
            last_month = curr.month

        h_text = all_h.get(curr, "")
        is_we = (curr.weekday() >= 5) or (h_text != "")
        score = 2 if is_we else 1
        suffix = "WE" if is_we else "WD"

        # เลือกแพทย์ที่ภาระงานน้อยที่สุด 3 อันดับแรก
        available = sorted(docs, key=lambda x: load[x])
        
        v1 = available[0]
        v2 = available[1]
        v3 = available[2] if len(docs) > 2 else "-"

        # อัปเดตโหลดและสถิติ
        load[v1] += score
        stats[v1][f"OPD_{suffix}"] += 1
        work_days[v1].append(curr)

        load[v2] += score
        stats[v2][f"WARD_{suffix}"] += 1
        work_days[v2].append(curr)

        if v3 != "-":
            if is_we or curr.weekday() == 4: # วันหยุดหรือวันศุกร์
                load[v3] += score
                stats[v3][f"SEC_{suffix}"] += 1
                work_days[v3].append(curr)
            else:
                v3 = "-"

        data.append({
            "วันที่": format_thai_date(curr),
            "วัน": ["จันทร์","อังคาร","พุธ","พฤหัสบดี","ศุกร์","เสาร์","อาทิตย์"][curr.weekday()],
            "เวรโอพีดี": v1, "เวรวอร์ด": v2, "เวรถปภ.": v3, "หมายเหตุ": h_text,
            "is_h": is_we, "is_header": False
        })
        curr += timedelta(days=1)

    # คำนวณช่วงวันหยุดยาว (Consecutive Off Days)
    off_stats = {}
    for n in docs:
        working = set(work_days[n])
        off_streaks = []
        streak = 0
        c = s_dt
        while c <= e_dt:
            if c not in working:
                streak += 1
            else:
                if streak >= 2: off_streaks.append(streak)
                streak = 0
            c += timedelta(days=1)
        if streak >= 2: off_streaks.append(streak)
        off_stats[n] = dict(collections.Counter(off_streaks))

    return pd.DataFrame(data), stats, off_stats

# --- DISPLAY ---
st.title(f"📋 ตารางเวรแพทย์ พ.ศ. {selected_year}")

if len(st.session_state.doctors) >= 2:
    df, stats, off_stats = generate_fair_schedule()
    
    def style_table(row):
        if row.get('is_header'): 
            return ['background-color: #B2EBF2; color: black; font-weight: bold; border: 1px solid black;'] * len(row)
        bg = '#FFCDD2' if row.get('is_h') else 'white'
        return [f'background-color: {bg}; border: 1px solid black; color: black;'] * len(row)

    st.dataframe(df.style.apply(style_table, axis=1).hide(axis='columns', subset=['is_h', 'is_header']), height=600, use_container_width=True)

    # --- ตารางสรุป 1: สถิติเวรละเอียด ---
    st.divider()
    st.subheader("📊 ตารางสรุปภาระงานรายบุคคล (แยกประเภทเวร)")
    summary_rows = []
    for n, s in stats.items():
        summary_rows.append({
            "ชื่อแพทย์": n,
            "OPD (ธรรมดา)": s['OPD_WD'], "OPD (หยุด)": s['OPD_WE'],
            "วอร์ด (ธรรมดา)": s['WARD_WD'], "วอร์ด (หยุด)": s['WARD_WE'],
            "ถปภ. (ธรรมดา)": s['SEC_WD'], "ถปภ. (หยุด)": s['SEC_WE'],
            "คะแนนรวม (2*หยุด + 1*ธรรมดา)": (s['OPD_WD']+s['WARD_WD']+s['SEC_WD']) + (s['OPD_WE']+s['WARD_WE']+s['SEC_WE'])*2
        })
    st.table(pd.DataFrame(summary_rows))

    # --- ตารางสรุป 2: วันหยุดยาว ---
    st.subheader("🏖️ ตารางสรุปวันหยุดยาวต่อเนื่อง (ครั้ง)")
    off_rows = []
    for n, o in off_stats.items():
        row = {"ชื่อแพทย์": n}
        for i in range(2, 7): # สรุปหยุด 2 - 6 วัน
            row[f"หยุดต่อเนื่อง {i} วัน"] = o.get(i, 0)
        row["หยุด > 6 วัน"] = sum(v for k, v in o.items() if k > 6)
        off_rows.append(row)
    st.table(pd.DataFrame(off_rows))
else:
    st.info("👈 กรุณาเพิ่มรายชื่อแพทย์ที่แถบด้านข้าง")
