import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import random
import io

st.set_page_config(layout="wide", page_title="Medical Shift Scheduler")

# --- การตั้งค่าสี ---
# สีสำหรับหัวตาราง
HEADER_COLORS = {
    "เวรนอกเวลา": "#FFD700",  # สีทอง/เหลือง (โอพีดี)
    "เวรวอร์ด": "#87CEFA",     # สีฟ้าอ่อน
    "เวรถปภ.": "#98FB98"      # สีเขียวอ่อน
}

# ฟังก์ชันสุ่มสีประจำตัวแพทย์ (สีอ่อนเพื่อให้เห็นตัวหนังสือชัด)
def get_pastel_color(name):
    random.seed(sum(ord(c) for c in name)) # เพื่อให้ชื่อเดิมได้สีเดิมเสมอ
    return f"hsl({random.randint(0, 360)}, 70%, 85%)"

# --- ข้อมูลเริ่มต้น ---
if 'doctors' not in st.session_state:
    st.session_state.doctors = [
        {"id": 1, "name": "หมอเอ", "start_date": datetime(2025, 6, 1)},
        {"id": 2, "name": "หมอบี", "start_date": datetime(2025, 6, 1)},
        {"id": 3, "name": "หมอซี", "start_date": datetime(2025, 6, 1)},
        {"id": 4, "name": "หมอดี", "start_date": datetime(2025, 6, 1)},
    ]

if 'holidays' not in st.session_state:
    # เก็บเป็น Dictionary {วันที่: "ชื่อวันหยุด"}
    st.session_state.holidays = {
        datetime(2025, 12, 5): "วันพ่อแห่งชาติ",
        datetime(2026, 1, 1): "วันขึ้นปีใหม่",
        datetime(2026, 4, 13): "วันสงกรานต์"
    }

st.title("ระบบจัดเวรแพทย์ (มิ.ย. - พ.ค.)")

# --- UI ส่วนจัดการ ---
with st.sidebar:
    st.header("🏥 จัดการรายชื่อแพทย์")
    new_doc_name = st.text_input("ชื่อแพทย์")
    new_doc_start = st.date_input("วันที่เริ่มงาน", datetime(2025, 6, 1))
    if st.button("เพิ่มแพทย์"):
        if new_doc_name:
            new_id = len(st.session_state.doctors) + 1
            st.session_state.doctors.append({
                "id": new_id, 
                "name": new_doc_name, 
                "start_date": datetime.combine(new_doc_start, datetime.min.time())
            })
            st.success(f"เพิ่ม {new_doc_name} แล้ว")

    st.header("📅 เพิ่มวันหยุดพิเศษ")
    h_date = st.date_input("วันที่หยุด")
    h_name = st.text_input("ชื่อวันหยุด (เช่น วันหยุดกองทัพ)")
    if st.button("บันทึกวันหยุด"):
        st.session_state.holidays[datetime.combine(h_date, datetime.min.time())] = h_name
        st.success("บันทึกสำเร็จ")

# --- ตรรกะการจัดเวร ---
def generate_schedule(start_date, end_date):
    current_date = start_date
    schedule = []
    workload = {doc['id']: {'weekday': 0, 'weekend': 0} for doc in st.session_state.doctors}
    doc_colors = {doc['name']: get_pastel_color(doc['name']) for doc in st.session_state.doctors}

    while current_date <= end_date:
        # ตรวจสอบประเภทวัน
        holiday_name = st.session_state.holidays.get(current_date, "")
        is_weekend = current_date.weekday() >= 5
        is_holiday = holiday_name != ""
        is_sec_day = current_date.weekday() in [4, 5, 6] or is_holiday # ศุกร์ เสาร์ อาทิตย์ หรือวันหยุด
        
        # กรองหมอที่เริ่มงานแล้ว
        available_docs = [doc for doc in st.session_state.doctors if doc['start_date'] <= current_date]
        random.shuffle(available_docs)
        
        assigned_today = []
        is_work_free_day = is_weekend or is_holiday

        # 1. เวรโอพีดี
        available_docs.sort(key=lambda x: workload[x['id']]['weekend' if is_work_free_day else 'weekday'])
        d_out = available_docs[0]
        assigned_today.append(d_out['id'])
        workload[d_out['id']]['weekend' if is_work_free_day else 'weekday'] += 1

        # 2. เวรวอร์ด
        rem = [d for d in available_docs if d['id'] not in assigned_today]
        d_ward = rem[0]
        assigned_today.append(d_ward['id'])
        workload[d_ward['id']]['weekend' if is_work_free_day else 'weekday'] += 1

        # 3. เวรถปภ.
        d_sec = "-"
        if is_sec_day:
            rem = [d for d in available_docs if d['id'] not in assigned_today]
            if rem:
                d_sec_obj = rem[0]
                d_sec = d_sec_obj['name']
                workload[d_sec_obj['id']]['weekend' if is_work_free_day else 'weekday'] += 1

        schedule.append({
            "วันที่": current_date.strftime("%Y-%m-%d"),
            "วัน": ["จันทร์","อังคาร","พุธ","พฤหัสบดี","ศุกร์","เสาร์","อาทิตย์"][current_date.weekday()],
            "เวรนอกเวลา": d_out['name'],
            "เวรวอร์ด": d_ward['name'],
            "เวรถปภ.": d_sec,
            "หมายเหตุ": holiday_name,
            "is_holiday": is_holiday or is_weekend
        })
        current_date += timedelta(days=1)
    
    return pd.DataFrame(schedule), doc_colors

# --- ส่วนการแสดงผลตารางสวยงาม ---
if st.button("🔄 ประมวลผลตารางเวร"):
    df, colors = generate_schedule(datetime(2025, 6, 1), datetime(2026, 5, 31))

    # ฟังก์ชันกำหนดสีพื้นหลัง
    def style_table(row):
        styles = [''] * len(row)
        # สีพื้นหลังวันหยุด (แดงอ่อน) ในช่องวันที่
        if row['is_holiday']:
            styles[0] = 'background-color: #FFEBEE' # แดงอ่อน
            styles[1] = 'background-color: #FFEBEE'

        # สีประจำตัวแพทย์
        for i, col in enumerate(['เวรนอกเวลา', 'เวรวอร์ด', 'เวรถปภ.']):
            name = row[col]
            if name in colors:
                styles[df.columns.get_loc(col)] = f'background-color: {colors[name]}'
        return styles

    # พ่น CSS สำหรับหัวตาราง
    st.markdown(f"""
        <style>
            th:nth-child(4) {{ background-color: {HEADER_COLORS['เวรนอกเวลา']} !important; color: black; }}
            th:nth-child(5) {{ background-color: {HEADER_COLORS['เวรวอร์ด']} !important; color: black; }}
            th:nth-child(6) {{ background-color: {HEADER_COLORS['เวรถปภ.']} !important; color: black; }}
        </style>
    """, unsafe_allow_name=True)

    # แสดงตาราง
    styled_df = df.drop(columns=['is_holiday']).style.apply(style_table, axis=1)
    st.dataframe(styled_df, height=600, use_container_width=True)

    # ปุ่มดาวน์โหลด
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.drop(columns=['is_holiday']).to_excel(writer, index=False)
    st.download_button("📥 ดาวน์โหลด Excel", output.getvalue(), "shift_schedule.xlsx")
