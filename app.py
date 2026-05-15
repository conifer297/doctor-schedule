import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import random
import io

st.set_page_config(layout="wide", page_title="Medical Shift Scheduler")

# --- ข้อมูลแพทย์เริ่มต้น ---
if 'doctors' not in st.session_state:
    st.session_state.doctors = [
        {"id": 1, "name": "หมอเอ", "start_date": datetime(2025, 6, 1)},
        {"id": 2, "name": "หมอบี", "start_date": datetime(2025, 6, 1)},
        {"id": 3, "name": "หมอซี", "start_date": datetime(2025, 6, 1)},
        {"id": 4, "name": "หมอดี", "start_date": datetime(2025, 6, 1)},
    ]

if 'holidays' not in st.session_state:
    st.session_state.holidays = [datetime(2025, 12, 5), datetime(2026, 1, 1)]

st.title("ระบบจัดเวรแพทย์ประจำปี (มิ.ย. - พ.ค.)")

# --- เมนูข้างหน้าจอ ---
st.sidebar.header("จัดการรายชื่อแพทย์")
new_doc_name = st.sidebar.text_input("ชื่อแพทย์ใหม่")
new_doc_start = st.sidebar.date_input("วันที่เริ่มงาน", datetime(2025, 9, 1))
if st.sidebar.button("เพิ่มแพทย์"):
    new_id = len(st.session_state.doctors) + 1
    st.session_state.doctors.append({"id": new_id, "name": new_doc_name, "start_date": datetime.combine(new_doc_start, datetime.min.time())})
    st.success(f"เพิ่ม {new_doc_name} สำเร็จ")

st.sidebar.header("จัดการวันหยุดพิเศษ")
new_holiday = st.sidebar.date_input("เพิ่มวันหยุด")
if st.sidebar.button("เพิ่มวันหยุด"):
    st.session_state.holidays.append(datetime.combine(new_holiday, datetime.min.time()))

# --- ตรรกะการจัดเวร ---
def generate_schedule(start_date, end_date):
    current_date = start_date
    schedule = []
    workload = {doc['id']: {'weekday': 0, 'weekend': 0} for doc in st.session_state.doctors}

    while current_date <= end_date:
        is_weekend = current_date.weekday() >= 5 or current_date in st.session_state.holidays
        is_security_day = current_date.weekday() in [4, 5, 6] or current_date in st.session_state.holidays
        available_docs = [doc for doc in st.session_state.doctors if doc['start_date'] <= current_date]
        random.shuffle(available_docs)
        assigned_today = []
        
        # 1. เวรนอกเวลา
        available_docs.sort(key=lambda x: workload[x['id']]['weekend' if is_weekend else 'weekday'])
        doc_out = available_docs[0]
        assigned_today.append(doc_out['id'])
        workload[doc_out['id']]['weekend' if is_weekend else 'weekday'] += 1
        
        # 2. เวรวอร์ด
        remaining_docs = [d for d in available_docs if d['id'] not in assigned_today]
        doc_ward = remaining_docs[0]
        assigned_today.append(doc_ward['id'])
        workload[doc_ward['id']]['weekend' if is_weekend else 'weekday'] += 1
        
        # 3. เวรถปภ.
        doc_sec = "N/A"
        if is_security_day:
            remaining_docs = [d for d in available_docs if d['id'] not in assigned_today]
            if remaining_docs:
                doc_sec_obj = remaining_docs[0]
                doc_sec = doc_sec_obj['name']
                workload[doc_sec_obj['id']]['weekend' if is_weekend else 'weekday'] += 1

        schedule.append({
            "วันที่": current_date.strftime("%Y-%m-%d"),
            "ประเภทวัน": "วันหยุด/ศุกร์-อาทิตย์" if is_weekend else "วันธรรมดา",
            "เวรนอกเวลา": doc_out['name'],
            "เวรวอร์ด": doc_ward['name'],
            "เวรถปภ.": doc_sec
        })
        current_date += timedelta(days=1)
    return pd.DataFrame(schedule), workload

# --- การแสดงผล ---
if st.button("เริ่มจัดเวรทั้งปี"):
    df_result, final_workload = generate_schedule(datetime(2025, 6, 1), datetime(2026, 5, 31))
    st.subheader("ตารางเวรที่จัดได้")
    st.dataframe(df_result)
    
    # ปุ่มดาวน์โหลด Excel สำหรับ iPad
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_result.to_excel(writer, index=False)
    st.download_button(label="📥 ดาวน์โหลดไฟล์ Excel", data=output.getvalue(), file_name="schedule.xlsx")
