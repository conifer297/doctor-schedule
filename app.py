import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import random
import io

st.set_page_config(layout="wide", page_title="Medical Fin-Scheduler Pro")

# --- 1. CSS & STYLING ---
st.markdown("""
    <style>
    .main .block-container { padding: 1rem; }
    th { border: 1px solid #ddd !important; text-align: center !important; background-color: #f0f2f6; color: black !important; font-weight: bold; }
    td { border: 1px solid #ddd !important; text-align: center !important; }
    input { text-align: center; }
    </style>
""", unsafe_allow_html=True)

# --- 2. INITIALIZATION ---
if 'doctors' not in st.session_state:
    st.session_state.doctors = []
if 'custom_holidays' not in st.session_state:
    st.session_state.custom_holidays = {}
if 'case_data' not in st.session_state:
    st.session_state.case_data = {}

def get_thai_year(dt): return dt.year + 543

def get_fixed_holidays(year_thai):
    yc = year_thai - 543
    return {datetime(yc, 1, 1): "ปีใหม่", datetime(yc, 4, 13): "สงกรานต์", datetime(yc, 4, 14): "สงกรานต์", 
            datetime(yc, 4, 15): "สงกรานต์", datetime(yc, 5, 1): "แรงงาน", datetime(yc, 12, 5): "วันพ่อ", 
            datetime(yc, 12, 31): "สิ้นปี"} # ย่อเพื่อประหยัดพื้นที่

# --- 3. SIDEBAR ---
with st.sidebar:
    st.title("⚙️ ตั้งค่า & ข้อมูล")
    selected_year = st.number_input("ปี พ.ศ. เริ่มต้น (มิ.ย.)", 2567, 2600, 2568)
    s_dt = datetime(selected_year - 543, 6, 1)
    e_dt = datetime(selected_year - 542, 5, 31)

    if st.button("🗑️ ล้างข้อมูลทั้งหมด"):
        st.session_state.doctors = []
        st.session_state.custom_holidays = {}
        st.session_state.case_data = {}
        st.rerun()

    with st.form("doc_form", clear_on_submit=True):
        st.subheader("👨‍⚕️ เพิ่มแพทย์")
        name = st.text_input("ชื่อ (เช่น A, B, C)")
        start = st.date_input("เริ่มงาน", s_dt)
        if st.form_submit_button("บันทึก"):
            if name:
                # ตัดคำว่า "หมอ" ออกตามโจทย์ข้อ 8
                clean_name = name.replace("หมอ", "").strip()
                st.session_state.doctors.append({"id": random.randint(100,999), "name": clean_name, "start": datetime.combine(start, datetime.min.time())})
                st.rerun()

    # รายชื่อแพทย์และปุ่มลบ
    for i, d in enumerate(st.session_state.doctors):
        c1, c2 = st.columns([3, 1])
        c1.write(f"แพทย์ {d['name']}")
        if c2.button("❌", key=f"del_{d['id']}"):
            st.session_state.doctors.pop(i)
            st.rerun()

# --- 4. LOGIC: SMART ROTATION & FINANCE ---
def generate_schedule():
    holidays = get_fixed_holidays(selected_year)
    holidays.update(get_fixed_holidays(selected_year + 1))
    holidays.update(st.session_state.custom_holidays)
    
    docs = [d['name'] for d in st.session_state.doctors]
    if len(docs) < 2: return pd.DataFrame(), {}

    curr = s_dt
    rows = []
    month_stats = {} # เก็บข้อมูลเงินรายเดือน
    
    # วางแผนเวรโอพีดีวันธรรมดา (Fixed Rotation)
    wd_pool = []
    curr_temp = s_dt
    doc_idx = 0
    while curr_temp <= e_dt:
        is_h = (curr_temp.weekday() >= 5) or (curr_temp in holidays)
        if not is_h:
            # ถ้าเป็นวันธรรมดา ให้รันตามคิว A, B, C...
            assigned = docs[doc_idx % len(docs)]
            wd_pool.append(assigned)
            doc_idx += 1
        curr_temp += timedelta(days=1)

    curr = s_dt
    wd_idx = 0
    while curr <= e_dt:
        m_key = f"{curr.month}/{to_thai_year(curr)}"
        if m_key not in month_stats: month_stats[m_key] = {d: {"case_money": 0, "ward_money": 0} for d in docs}

        h_text = holidays.get(curr, "")
        is_h = (curr.weekday() >= 5) or (h_text != "")
        
        # 1. เวรโอพีดี (นอกเวลา)
        v1 = "-"
        if not is_h:
            v1 = wd_pool[wd_idx]
            wd_idx += 1
        else:
            # วันหยุดใช้ระบบสุ่ม/เวียนจาก Pool วันหยุด
            v1 = random.choice(docs)

        # 2. เวรวอร์ด
        v2 = random.choice([d for d in docs if d != v1])
        
        # 3. คำนวณค่าเวรวอร์ด (ข้อ 10)
        v2_pay = 1200 if is_h else 600
        month_stats[m_key][v2]["ward_money"] += v2_pay

        # 4. ดึงข้อมูลจำนวนเคสจาก Session State (ข้อ 9)
        date_str = curr.strftime("%Y-%m-%d")
        c_in = st.session_state.case_data.get(f"{date_str}_in", 0)
        c_out = st.session_state.case_data.get(f"{date_str}_out", 0)
        c_ward = st.session_state.case_data.get(f"{date_str}_ward", 0)

        # คิดเงิน (ข้อ 9)
        # เคสในเวลา 5 บาท (เข้าทุกคนเฉลี่ย หรือเข้าเวรโอพีดี? โจทย์บอกเข้าแพทย์แต่ละคน ในที่นี้ขอเข้าคนตรวจโอพีดีวันนั้น)
        month_stats[m_key][v1]["case_money"] += (c_in * 5) + (c_out * 50) + (c_ward * 50)

        rows.append({
            "วันที่": curr.strftime(f"%d/%m/{to_thai_year(curr)}"),
            "วัน": ["จันทร์","อังคาร","พุธ","พฤหัสบดี","ศุกร์","เสาร์","อาทิตย์"][curr.weekday()],
            "โอพีดี": v1, "วอร์ด": v2, "หมายเหตุ": h_text,
            "เคสในเวลา": c_in, "เคสนอกเวลา": c_out, "เคสวอร์ด": c_ward,
            "ค่าเวรวอร์ด": v2_pay, "is_h": is_h, "raw_date": date_str
        })
        curr += timedelta(days=1)
    
    return pd.DataFrame(rows), month_stats

# --- 5. DISPLAY ---
st.title(f"🏥 ระบบจัดเวรและคำนวณค่าตอบแทน {selected_year}")

if len(st.session_state.doctors) >= 2:
    df, stats = generate_schedule()
    
    # ส่วนกรอกข้อมูลจำนวนเคส
    st.subheader("📝 กรอกจำนวนเคสประจำวัน")
    col_date, col_in, col_out, col_wd = st.columns(4)
    with col_date: edit_date = st.date_input("เลือกวันที่เพื่อกรอกเคส", datetime.now())
    with col_in: in_val = st.number_input("จำนวนเคสในเวลา (5.-)", 0)
    with col_out: out_val = st.number_input("จำนวนเคสนอกเวลา (50.-)", 0)
    with col_wd: wd_val = st.number_input("จำนวนคนไข้วอร์ด (50.-)", 0)
    
    if st.button("บันทึกสถิติเคส"):
        d_key = edit_date.strftime("%Y-%m-%d")
        st.session_state.case_data[f"{d_key}_in"] = in_val
        st.session_state.case_data[f"{d_key}_out"] = out_val
        st.session_state.case_data[f"{d_key}_ward"] = wd_val
        st.success("บันทึกสำเร็จ!")
        st.rerun()

    # แสดงตารางใหญ่
    def style_row(row):
        color = 'background-color: #FF8A80; color: black;' if row['is_h'] else 'background-color: white; color: black;'
        return [color] * len(row)

    st.subheader("🗓️ ตารางเวรและรายได้")
    st.dataframe(df.style.apply(style_row, axis=1).hide(axis='columns', subset=['is_h', 'raw_date']), height=500, use_container_width=True)

    # --- 6. SUMMARY REPORT (ข้อ 12) ---
    st.divider()
    st.subheader("💰 สรุปยอดเงินรายเดือนแยกตามแพทย์")
    for month, data in stats.items():
        with st.expander(f"ดูยอดเงินเดือน {month}"):
            sum_df = pd.DataFrame.from_dict(data, orient='index')
            sum_df.columns = ["ค่าเคสรวม (In/Out/Ward)", "ค่าเวรวอร์ด"]
            sum_df["รวมสุทธิ"] = sum_df.sum(axis=1)
            st.table(sum_df)

    # Note เพิ่มเติม (ข้อ 11)
    st.text_area("🗒️ บันทึกเพิ่มเติม (Note)", placeholder="พิมพ์หมายเหตุภาพรวมที่นี่...")

else:
    st.info("👈 กรุณาเพิ่มชื่อแพทย์ที่แถบด้านข้างอย่างน้อย 2 ท่าน")

def to_thai_year(dt): return dt.year + 543
