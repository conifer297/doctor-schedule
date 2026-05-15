import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import random
import collections

# ตั้งค่าหน้าจอและฟอนต์ TH Sarabun
st.set_page_config(layout="wide", page_title="Medical Fair-Scheduler Pro")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;700&display=swap');
    html, body, [class*="css"], .stMarkdown, p, div, span, label { font-family: 'Sarabun', sans-serif !important; }
    .main .block-container { padding: 1.5rem; }
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

# --- INITIALIZATION ---
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
        n_name = st.text_input("ชื่อแพทย์ (เช่น A, B)")
        n_start = st.date_input("วันที่เริ่มงานจริง", s_dt)
        if st.form_submit_button("➕ เพิ่มแพทย์"):
            if n_name:
                st.session_state.doctors.append({
                    "id": random.randint(100,999), 
                    "name": n_name.replace("หมอ", "").strip(), 
                    "start": datetime.combine(n_start, datetime.min.time())
                })
                st.rerun()

    for i, d in enumerate(st.session_state.doctors):
        c1, c2 = st.columns([4,1])
        c1.write(f"แพทย์ {d['name']} (เริ่ม {format_thai_date(d['start'])})")
        if c2.button("🗑️", key=f"d_{d['id']}"):
            st.session_state.doctors.pop(i); st.rerun()

    st.divider()
    st.header("📅 วันหยุดเพิ่มเติม")
    with st.form("h_form", clear_on_submit=True):
        h_date = st.date_input("วันที่หยุด", s_dt)
        h_name = st.text_input("ชื่อวันหยุด")
        if st.form_submit_button("💾 บันทึก"):
            if h_name:
                st.session_state.custom_holidays[datetime.combine(h_date, datetime.min.time())] = h_name
                st.rerun()

    # --- ปุ่มลบวันหยุดเพิ่มเติม (เอากลับคืนมาให้แล้วครับ) ---
    if st.session_state.custom_holidays:
        st.subheader("🗑️ ลบวันหยุดที่เพิ่มเอง")
        for d, name in sorted(st.session_state.custom_holidays.items()):
            c1, c2 = st.columns([4,1])
            c1.caption(f"{format_thai_date(d)} - {name}")
            if c2.button("🗑️", key=f"h_{d.timestamp()}"):
                del st.session_state.custom_holidays[d]
                st.rerun()

    st.divider()
    st.subheader("📋 รายการวันหยุดทั้งหมดในระบบ")
    all_h_list = get_fixed_holidays(selected_year)
    all_h_list.update(get_fixed_holidays(selected_year+1))
    all_h_list.update(st.session_state.custom_holidays)
    for d_h, name_h in sorted(all_h_list.items()):
        if s_dt <= d_h <= e_dt:
            st.caption(f"{format_thai_date(d_h)} - {name_h}")

# --- FAIR ALGORITHM (DYNAMIC STAFFING) ---
def generate_schedule():
    all_h = all_h_list
    docs = st.session_state.doctors
    if not docs: return pd.DataFrame(), {}, {}
    
    doc_names = [d['name'] for d in docs]
    stats = {n: {"OPD_WD":0, "OPD_WE":0, "WARD_WD":0, "WARD_WE":0, "SEC_WD":0, "SEC_WE":0} for n in doc_names}
    work_days = {n: [] for n in doc_names}
    
    data = []
    curr = s_dt
    last_month = -1
    pool_state = {}

    while curr <= e_dt:
        if curr.month != last_month:
            m_name = ["", "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน", "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"][curr.month]
            data.append({"วันที่": f"--- {m_name} {get_thai_year(curr)} ---", "is_header": True})
            last_month = curr.month

        available_docs = sorted([d['name'] for d in docs if d['start'] <= curr])
        if not available_docs:
            curr += timedelta(days=1)
            continue

        n_avail = len(available_docs)
        if n_avail not in pool_state: pool_state[n_avail] = 0
        
        h_text = all_h.get(curr, "")
        is_we = (curr.weekday() >= 5) or (h_text != "")
        suffix = "WE" if is_we else "WD"

        v1 = available_docs[pool_state[n_avail] % n_avail]
        if not is_we: pool_state[n_avail] += 1
        
        v2_pool = [d for d in available_docs if d != v1]
        v2 = random.choice(v2_pool) if v2_pool else v1
        
        v3 = "-"
        if is_we or curr.weekday() == 4:
            v3_pool = [d for d in available_docs if d not in [v1, v2]]
            if v3_pool: v3 = random.choice(v3_pool)

        stats[v1][f"OPD_{suffix}"] += 1
        work_days[v1].append(curr)
        stats[v2][f"WARD_{suffix}"] += 1
        work_days[v2].append(curr)
        if v3 != "-":
            stats[v3][f"SEC_{suffix}"] += 1
            work_days[v3].append(curr)

        data.append({
            "วันที่": format_thai_date(curr), "วัน": ["จันทร์","อังคาร","พุธ","พฤหัสบดี","ศุกร์","เสาร์","อาทิตย์"][curr.weekday()],
            "เวรโอพีดี": v1, "เวรวอร์ด": v2, "เวรถปภ.": v3, "หมายเหตุ": h_text,
            "is_h": is_we, "is_header": False
        })
        curr += timedelta(days=1)

    off_stats = {}
    for n in doc_names:
        working = set(work_days[n])
        off_streaks = []
        streak = 0
        c = s_dt
        while c <= e_dt:
            if c not in working: streak += 1
            else:
                if streak >= 2: off_streaks.append(streak)
                streak = 0
            c += timedelta(days=1)
        if streak >= 2: off_streaks.append(streak)
        off_stats[n] = dict(collections.Counter(off_streaks))

    return pd.DataFrame(data), stats, off_stats

# --- DISPLAY ---
st.title(f"🏥 ระบบจัดเวรแพทย์อัจฉริยะ พ.ศ. {selected_year}")

if st.session_state.doctors:
    df, stats_full, off_stats = generate_schedule()
    
    def style_table(row):
        if row.get('is_header'): return ['background-color: #B2EBF2; color: black; font-weight: bold; border: 1px solid black;'] * len(row)
        bg = '#FFCDD2' if row.get('is_h') else 'white'
        return [f'background-color: {bg}; border: 1px solid black; color: black; font-weight: bold;'] * len(row)

    st.dataframe(df.style.apply(style_table, axis=1).hide(axis='columns', subset=['is_h', 'is_header']), height=600, use_container_width=True)

    # --- ตารางสรุปละเอียด ---
    st.divider()
    st.header("📊 ตารางสรุปภาระงานละเอียด (แยกประเภทเวร)")
    summary_df = pd.DataFrame.from_dict(stats_full, orient='index').reset_index().rename(columns={'index': 'ชื่อแพทย์'})
    cols = ['ชื่อแพทย์', 'OPD_WD', 'OPD_WE', 'WARD_WD', 'WARD_WE', 'SEC_WD', 'SEC_WE']
    st.table(summary_df[cols].rename(columns={
        'OPD_WD': 'โอพีดี(ธรรมดา)', 'OPD_WE': 'โอพีดี(หยุด)',
        'WARD_WD': 'วอร์ด(ธรรมดา)', 'WARD_WE': 'วอร์ด(หยุด)',
        'SEC_WD': 'ถปภ.(ธรรมดา)', 'SEC_WE': 'ถปภ.(หยุด)'
    }))

    # --- ตารางวิเคราะห์วันหยุดยาว ---
    st.subheader("🏖️ ตารางสรุปวันหยุดยาวต่อเนื่อง (จำนวนครั้ง)")
    off_rows = []
    for n, o in off_stats.items():
        row = {"ชื่อแพทย์": n}
        for i in range(2, 6): row[f"หยุด {i} วัน"] = o.get(i, 0)
        row["หยุด > 5 วัน"] = sum(v for k, v in o.items() if k > 5)
        off_rows.append(row)
    st.table(pd.DataFrame(off_rows))
else:
    st.info("👈 กรุณาเพิ่มรายชื่อแพทย์ที่ Sidebar")
