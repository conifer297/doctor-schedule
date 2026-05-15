import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import random
import io

st.set_page_config(layout="wide", page_title="Medical Fin-Scheduler Pro")

# --- 1. Helper Functions (ย้ายขึ้นมาบนสุดป้องกัน NameError) ---
def get_thai_year(dt): 
    return dt.year + 543

def get_fixed_holidays(year_thai):
    yc = year_thai - 543
    return {
        datetime(yc, 1, 1): "วันขึ้นปีใหม่",
        datetime(yc, 4, 13): "วันสงกรานต์",
        datetime(yc, 4, 14): "วันสงกรานต์",
        datetime(yc, 4, 15): "วันสงกรานต์",
        datetime(yc, 5, 1): "วันแรงงาน",
        datetime(yc, 5, 4): "วันฉัตรมงคล",
        datetime(yc, 6, 3): "วันเฉลิมฯ พระราชินี",
        datetime(yc, 7, 28): "วันเฉลิมฯ ร.10",
        datetime(yc, 8, 12): "วันแม่แห่งชาติ",
        datetime(yc, 10, 13): "วันสวรรคต ร.9",
        datetime(yc, 10, 23): "วันปิยมหาราช",
        datetime(yc, 12, 5): "วันพ่อแห่งชาติ",
        datetime(yc, 12, 10): "วันรัฐธรรมนูญ",
        datetime(yc, 12, 31): "วันสิ้นปี"
    }

# --- 2. CSS Styling ---
st.markdown("""
    <style>
    .main .block-container { padding: 1.5rem; }
    th { border: 1px solid #ddd !important; text-align: center !important; background-color: #f0f2f6; color: black !important; }
    td { border: 1px solid #ddd !important; text-align: center !important; vertical-align: middle !important; }
    .stDataFrame { border: 1px solid #ddd; }
    </style>
""", unsafe_allow_html=True)

# --- 3. Session State Initialization ---
if 'doctors' not in st.session_state:
    st.session_state.doctors = []
if 'custom_holidays' not in st.session_state:
    st.session_state.custom_holidays = {}
if 'case_data' not in st.session_state:
    st.session_state.case_data = {}

# --- 4. Sidebar Management ---
with st.sidebar:
    st.title("⚙️ ตั้งค่าระบบ")
    selected_year = st.number_input("ปี พ.ศ. เริ่มต้น (มิ.ย.)", 2560, 2600, 2568)
    s_dt = datetime(selected_year - 543, 6, 1)
    e_dt = datetime(selected_year - 542, 5, 31)

    if st.button("🗑️ ล้างข้อมูลทั้งหมด", use_container_width=True):
        st.session_state.doctors = []
        st.session_state.custom_holidays = {}
        st.session_state.case_data = {}
        st.rerun()

    st.divider()
    # ส่วนจัดการรายชื่อแพทย์
    st.header("👨‍⚕️ จัดการแพทย์")
    with st.form("doc_form", clear_on_submit=True):
        n_name = st.text_input("ชื่อแพทย์ (เช่น A, B)")
        n_start = st.date_input("วันที่เริ่มงาน", s_dt)
        if st.form_submit_button("➕ เพิ่มแพทย์"):
            if n_name:
                clean_name = n_name.replace("หมอ", "").strip()
                st.session_state.doctors.append({
                    "id": random.randint(1000, 9999), 
                    "name": clean_name, 
                    "start": datetime.combine(n_start, datetime.min.time())
                })
                st.rerun()

    if st.session_state.doctors:
        for i, d in enumerate(st.session_state.doctors):
            c1, c2 = st.columns([4, 1])
            c1.caption(f"{d['name']} (เริ่ม {d['start'].strftime('%d/%m/%Y')})")
            if c2.button("🗑️", key=f"del_doc_{d['id']}"):
                st.session_state.doctors.pop(i)
                st.rerun()

    st.divider()
    # ส่วนจัดการวันหยุด (Sidebar วันหยุดกลับมาแล้ว)
    st.header("📅 วันหยุดพิเศษ")
    with st.form("h_form", clear_on_submit=True):
        h_date = st.date_input("เลือกวันที่")
        h_name = st.text_input("ชื่อวันหยุด")
        if st.form_submit_button("💾 บันทึกวันหยุด"):
            if h_name:
                st.session_state.custom_holidays[datetime.combine(h_date, datetime.min.time())] = h_name
                st.rerun()

    if st.session_state.custom_holidays:
        for d, name in sorted(st.session_state.custom_holidays.items()):
            c1, c2 = st.columns([4, 1])
            c1.caption(f"{d.strftime('%d/%m/%Y')} {name}")
            if c2.button("🗑️", key=f"del_h_{d.timestamp()}"):
                del st.session_state.custom_holidays[d]
                st.rerun()

# --- 5. Algorithm: Rotation & Finance ---
def generate_schedule():
    holidays = get_fixed_holidays(selected_year)
    holidays.update(get_fixed_holidays(selected_year + 1))
    holidays.update(st.session_state.custom_holidays)
    
    docs = [d['name'] for d in st.session_state.doctors]
    if len(docs) < 2: return pd.DataFrame(), {}

    curr = s_dt
    rows = []
    month_stats = {}
    
    # วางแผน Fixed Rotation สำหรับวันธรรมดา
    wd_pool = []
    temp_curr = s_dt
    doc_idx = 0
    while temp_curr <= e_dt:
        is_h = (temp_curr.weekday() >= 5) or (temp_curr in holidays)
        if not is_h:
            wd_pool.append(docs[doc_idx % len(docs)])
            doc_idx += 1
        temp_curr += timedelta(days=1)

    wd_idx = 0
    last_month = -1
    while curr <= e_dt:
        # เช็คเปลี่ยนเดือนเพื่อเพิ่ม Header
        if curr.month != last_month:
            m_name = ["", "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน", "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"][curr.month]
            rows.append({"วันที่": f"--- {m_name} {get_thai_year(curr)} ---", "is_header": True})
            last_month = curr.month

        m_key = f"{m_name} {get_thai_year(curr)}"
        if m_key not in month_stats:
            month_stats[m_key] = {d: {"case_money": 0, "ward_money": 0} for d in docs}

        h_text = holidays.get(curr, "")
        is_h = (curr.weekday() >= 5) or (h_text != "")
        
        # จัดเวร
        v1 = wd_pool[wd_idx] if not is_h else random.choice(docs)
        if not is_h: wd_idx += 1
        v2 = random.choice([d for d in docs if d != v1])
        
        # คำนวณเงิน
        v2_pay = 1200 if is_h else 600
        month_stats[m_key][v2]["ward_money"] += v2_pay
        
        d_key = curr.strftime("%Y-%m-%d")
        c_in = st.session_state.case_data.get(f"{d_key}_in", 0)
        c_out = st.session_state.case_data.get(f"{d_key}_out", 0)
        c_wd = st.session_state.case_data.get(f"{d_key}_wd", 0)
        
        month_stats[m_key][v1]["case_money"] += (c_in * 5) + (c_out * 50) + (c_wd * 50)

        rows.append({
            "วันที่": curr.strftime(f"%d/%m/{get_thai_year(curr)}"),
            "วัน": ["จันทร์","อังคาร","พุธ","พฤหัสบดี","ศุกร์","เสาร์","อาทิตย์"][curr.weekday()],
            "โอพีดี": v1, "วอร์ด": v2, "หมายเหตุ": h_text,
            "เคสในเวลา": c_in, "เคสนอกเวลา": c_out, "เคสวอร์ด": c_wd,
            "ค่าเวรวอร์ด": v2_pay, "is_h": is_h, "is_header": False
        })
        curr += timedelta(days=1)
    
    return pd.DataFrame(rows), month_stats

# --- 6. Main UI ---
st.title(f"🏥 ตารางเวรและบัญชีค่าตอบแทน พ.ศ. {selected_year}")

if len(st.session_state.doctors) >= 2:
    df, stats = generate_schedule()
    
    # ส่วนกรอกข้อมูลเคส (UI สำหรับ iPad)
    with st.expander("📝 คลิกเพื่อกรอกจำนวนเคสประจำวัน"):
        c1, c2, c3, c4 = st.columns(4)
        e_date = c1.date_input("เลือกวันที่", datetime.now())
        e_in = c2.number_input("เคสในเวลา (5.-)", 0)
        e_out = c3.number_input("เคสนอกเวลา (50.-)", 0)
        e_wd = c4.number_input("เคสวอร์ด (50.-)", 0)
        if st.button("💾 บันทึกสถิติเคส", use_container_width=True):
            dk = e_date.strftime("%Y-%m-%d")
            st.session_state.case_data[f"{dk}_in"] = e_in
            st.session_state.case_data[f"{dk}_out"] = e_out
            st.session_state.case_data[f"{dk}_wd"] = e_wd
            st.success(f"บันทึกข้อมูลวันที่ {e_date.strftime('%d/%m/%Y')} สำเร็จ!")
            st.rerun()

    # การแสดงผลตาราง
    def style_table(row):
        if row.get('is_header', False): return ['background-color: #B2EBF2; font-weight: bold; color: black;'] * len(row)
        color = 'background-color: #FFCDD2;' if row.get('is_h', False) else 'background-color: white;'
        return [f'{color} color: black; font-weight: bold;'] * len(row)

    st.dataframe(
        df.style.apply(style_table, axis=1).hide(axis='columns', subset=['is_h', 'is_header']),
        height=600, use_container_width=True
    )

    # สรุปรายเดือน
    st.divider()
    st.subheader("💰 สรุปยอดเงินรายเดือน")
    for m, data in stats.items():
        with st.expander(f"📊 ยอดเงิน {m}"):
            res = pd.DataFrame.from_dict(data, orient='index')
            res.columns = ["ค่าเคส (5/50/50)", "ค่าเวรวอร์ด"]
            res["รวมสุทธิ"] = res.sum(axis=1)
            st.table(res)

    st.text_area("🗒️ บันทึกเพิ่มเติม (Note)", height=100)
else:
    st.info("👈 กรุณาเพิ่มรายชื่อแพทย์ที่ Sidebar เพื่อเริ่มจัดเวร")
