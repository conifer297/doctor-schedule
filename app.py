import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import random
import collections

# ตั้งค่าหน้าจอและฟอนต์
st.set_page_config(layout="wide", page_title="Doctor Fair-Balance Scheduler")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;700&display=swap');
    html, body, [class*="css"], .stMarkdown, p, div, span, label { font-family: 'Sarabun', sans-serif !important; }
    th { border: 1px solid #000 !important; text-align: center !important; background-color: #f0f2f6; color: black !important; }
    td { border: 1px solid #000 !important; text-align: center !important; }
    </style>
""", unsafe_allow_html=True)

# --- Helpers ---
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

# --- Session State ---
if 'doctors' not in st.session_state: st.session_state.doctors = []
if 'all_active_holidays' not in st.session_state: st.session_state.all_active_holidays = {}
if 'init_year' not in st.session_state: st.session_state.init_year = None

# --- Sidebar ---
with st.sidebar:
    st.header("⚙️ ตั้งค่าระบบ")
    selected_year = st.number_input("ปี พ.ศ. เริ่มต้น (มิ.ย.)", 2560, 2600, 2568)
    s_dt = datetime(selected_year - 543, 6, 1)
    e_dt = datetime(selected_year - 542, 5, 31)

    if st.session_state.init_year != selected_year:
        hols = get_fixed_holidays(selected_year)
        hols.update(get_fixed_holidays(selected_year + 1))
        st.session_state.all_active_holidays = {d: n for d, n in hols.items() if s_dt <= d <= e_dt}
        st.session_state.init_year = selected_year

    if st.button("🗑️ ล้างข้อมูลทั้งหมด"):
        st.session_state.doctors = []
        st.session_state.all_active_holidays = {}
        st.rerun()

    st.divider()
    st.header("👨‍⚕️ จัดการแพทย์")
    with st.form("doc_form", clear_on_submit=True):
        n_name = st.text_input("ชื่อแพทย์")
        n_start = st.date_input("เริ่มงานจริง (พ.ศ.)", s_dt)
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
        c1.write(f"หมอ {d['name']} ({format_thai_date(d['start'])})")
        if c2.button("🗑️", key=f"d_{d['id']}"):
            st.session_state.doctors.pop(i); st.rerun()

    st.divider()
    st.header("📅 วันหยุด")
    with st.form("h_form", clear_on_submit=True):
        h_date = st.date_input("วันที่", s_dt)
        h_name = st.text_input("ชื่อวัน")
        if st.form_submit_button("เพิ่มวันหยุด"):
            if h_name:
                st.session_state.all_active_holidays[datetime.combine(h_date, datetime.min.time())] = h_name
                st.rerun()

    if st.session_state.all_active_holidays:
        for d, name in sorted(st.session_state.all_active_holidays.items()):
            c1, c2 = st.columns([3,1])
            c1.caption(f"{format_thai_date(d)} {name}")
            if c2.button("🗑️", key=f"h_{d.timestamp()}"):
                del st.session_state.all_active_holidays[d]; st.rerun()

# --- Core Algorithm: Balance and Freeze ---
def generate_schedule():
    all_h = st.session_state.all_active_holidays
    docs = st.session_state.doctors
    if not docs: return pd.DataFrame(), {}, {}, None
    
    # หาวันที่แพทย์คนล่าสุดเข้ามา
    latest_start_date = max([d['start'] for d in docs])
    
    data = []
    stats_before = {d['name']: collections.defaultdict(int) for d in docs}
    stats_after = {d['name']: collections.defaultdict(int) for d in docs}
    load_score = {d['name']: 0 for d in docs} # วันธรรมดา 1, วันหยุด 2
    work_days = {d['name']: [] for d in docs}

    curr = s_dt
    last_month = -1
    
    while curr <= e_dt:
        # แสดงหัวเดือน
        if curr.month != last_month:
            m_name = ["", "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน", "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"][curr.month]
            data.append({"วันที่": f"--- {m_name} {get_thai_year(curr)} ---", "is_header": True})
            last_month = curr.month

        # กรองแพทย์ที่ "เริ่มงานแล้ว" ณ วันที่คำนวณ
        available_docs = [d['name'] for d in docs if d['start'] <= curr]
        if not available_docs:
            curr += timedelta(days=1)
            continue

        h_text = all_h.get(curr, "")
        is_we = (curr.weekday() >= 5) or (h_text != "")
        score = 2 if is_we else 1
        suffix = "WE" if is_we else "WD"

        # --- อัลกอริทึมเลือกแพทย์ ---
        # เลือกคนที่ภาระงานสะสม (Load Score) น้อยที่สุดก่อน เพื่อชดใช้เวร
        # หากคะแนนเท่ากัน ให้สุ่ม
        sorted_by_load = sorted(available_docs, key=lambda x: (load_score[x], random.random()))
        
        v1 = sorted_by_load[0]
        v2 = sorted_by_load[1] if len(available_docs) > 1 else v1
        
        v3 = "-"
        if is_we or curr.weekday() == 4:
            v3_pool = [d for d in available_docs if d not in [v1, v2]]
            if v3_pool: v3 = random.choice(v3_pool)

        # บันทึกสถิติ
        target_stats = stats_after if curr >= latest_start_date else stats_before
        target_stats[v1][f"OPD_{suffix}"] += 1
        target_stats[v2][f"WARD_{suffix}"] += 1
        load_score[v1] += score
        load_score[v2] += score
        work_days[v1].append(curr)
        work_days[v2].append(curr)
        
        if v3 != "-":
            target_stats[v3][f"SEC_{suffix}"] += 1
            load_score[v3] += score
            work_days[v3].append(curr)

        data.append({
            "วันที่": format_thai_date(curr), "วัน": ["จันทร์","อังคาร","พุธ","พฤหัสบดี","ศุกร์","เสาร์","อาทิตย์"][curr.weekday()],
            "เวรโอพีดี": v1, "เวรวอร์ด": v2, "เวรถปภ.": v3, "หมายเหตุ": h_text,
            "is_h": is_we, "is_header": False
        })
        curr += timedelta(days=1)

    # คำนวณวันหยุดยาว
    off_stats = {}
    for d in docs:
        n = d['name']
        working = set(work_days[n])
        off_streaks, streak = [], 0
        c = s_dt
        while c <= e_dt:
            if c not in working: streak += 1
            else:
                if streak >= 2: off_streaks.append(streak)
                streak = 0
            c += timedelta(days=1)
        if streak >= 2: off_streaks.append(streak)
        off_stats[n] = dict(collections.Counter(off_streaks))

    return pd.DataFrame(data), stats_before, stats_after, latest_start_date, off_stats

# --- Display ---
st.title(f"🏥 ระบบจัดเวรชดเชยและล็อคประวัติ พ.ศ. {selected_year}")

if st.session_state.doctors:
    df, s_before, s_after, l_start, off_stats = generate_schedule()

    # ตารางหลัก
    def style_row(row):
        if row.get('is_header'): return ['background-color: #B2EBF2; color: black; font-weight: bold; border: 1px solid black;'] * len(row)
        bg = '#FFCDD2' if row.get('is_h') else 'white'
        return [f'background-color: {bg}; border: 1px solid black; color: black; font-weight: bold;'] * len(row)

    st.dataframe(df.style.apply(style_row, axis=1).hide(axis='columns', subset=['is_h', 'is_header']), height=600, use_container_width=True)

    # ตารางสรุป 1: ก่อนแพทย์คนล่าสุดมา
    st.divider()
    st.header(f"📊 1. สรุปภาระงานก่อน {format_thai_date(l_start)}")
    st.caption("ตารางนี้คือ 'ประวัติศาสตร์' ที่ล็อคไว้เพื่อใช้คำนวณการชดใช้เวร")
    df_b = pd.DataFrame.from_dict(s_before, orient='index').fillna(0).astype(int)
    if not df_b.empty:
        st.table(df_b.rename(columns={'OPD_WD':'โอพีดี(ธรรมดา)','OPD_WE':'โอพีดี(หยุด)','WARD_WD':'วอร์ด(ธรรมดา)','WARD_WE':'วอร์ด(หยุด)','SEC_WD':'ถปภ.(ธรรมดา)','SEC_WE':'ถปภ.(หยุด)'}))

    # ตารางสรุป 2: หลังแพทย์คนล่าสุดมา
    st.header(f"📊 2. สรุปภาระงานช่วงชดใช้และปรับสมดุล (ตั้งแต่ {format_thai_date(l_start)})")
    st.caption("แพทย์ที่มีเวรน้อยจากช่วงแรก จะถูกดึงมาขึ้นเวรถี่ขึ้นในช่วงนี้จนกว่าคะแนนจะสมดุล")
    df_a = pd.DataFrame.from_dict(s_after, orient='index').fillna(0).astype(int)
    if not df_a.empty:
        st.table(df_a.rename(columns={'OPD_WD':'โอพีดี(ธรรมดา)','OPD_WE':'โอพีดี(หยุด)','WARD_WD':'วอร์ด(ธรรมดา)','WARD_WE':'วอร์ด(หยุด)','SEC_WD':'ถปภ.(ธรรมดา)','SEC_WE':'ถปภ.(หยุด)'}))

    # ตารางวันหยุดยาว
    st.header("🏖️ สรุปวันหยุดยาวต่อเนื่อง (รวมทั้งปี)")
    off_rows = []
    for n, o in off_stats.items():
        row = {"ชื่อแพทย์": n}
        for i in range(2, 6): row[f"หยุด {i} วัน"] = o.get(i, 0)
        row["หยุด > 5 วัน"] = sum(v for k, v in o.items() if k > 5)
        off_rows.append(row)
    st.table(pd.DataFrame(off_rows))
else:
    st.info("👈 เพิ่มชื่อแพทย์และวันที่เริ่มงานจริงที่แถบด้านข้าง (เช่น หมอ A-D เริ่ม 1 มิ.ย., หมอ E เริ่ม 1 ก.ย.)")
