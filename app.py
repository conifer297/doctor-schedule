import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import random
import io

# ต้องเพิ่ม xlsxwriter ใน requirements.txt ด้วยนะครับ
st.set_page_config(layout="wide", page_title="Medical Shift Scheduler")

# --- CONFIG & COLORS ---
HEADER_COLORS = {"OPD": "#FFD700", "WARD": "#87CEFA", "SEC": "#98FB98", "HOLIDAY": "#FFEBEE"}

def get_pastel_color(name):
    random.seed(sum(ord(c) for c in name))
    return f"hsl({random.randint(0, 360)}, 80%, 90%)"

if 'doctors' not in st.session_state:
    st.session_state.doctors = [
        {"id": 1, "name": "หมอเอ", "start_date": datetime(2025, 6, 1)},
        {"id": 2, "name": "หมอบี", "start_date": datetime(2025, 6, 1)},
        {"id": 3, "name": "หมอซี", "start_date": datetime(2025, 6, 1)},
        {"id": 4, "name": "หมอดี", "start_date": datetime(2025, 6, 1)},
    ]

if 'holidays' not in st.session_state:
    st.session_state.holidays = {datetime(2025, 12, 5): "วันพ่อแห่งชาติ", datetime(2026, 1, 1): "วันขึ้นปีใหม่"}

st.title("🏥 ระบบจัดเวรแพทย์ (Export Excel/PDF)")

# --- SIDEBAR ---
with st.sidebar:
    st.header("👨‍⚕️ จัดการแพทย์")
    n_name = st.text_input("ชื่อแพทย์")
    n_start = st.date_input("วันเริ่มงาน", datetime(2025, 6, 1))
    if st.button("เพิ่มแพทย์"):
        st.session_state.doctors.append({"id": len(st.session_state.doctors)+1, "name": n_name, "start_date": datetime.combine(n_start, datetime.min.time())})
        st.rerun()

# --- LOGIC ---
def generate():
    df_list = []
    curr = datetime(2025, 6, 1)
    end = datetime(2026, 5, 31)
    workload = {d['id']: {'wd': 0, 'we': 0} for d in st.session_state.doctors}
    
    while curr <= end:
        h_name = st.session_state.holidays.get(curr, "")
        is_we = curr.weekday() >= 5
        is_h = h_name != ""
        is_free = is_we or is_h
        
        docs = [d for d in st.session_state.doctors if d['start_date'] <= curr]
        random.shuffle(docs)
        
        # จัดเวร
        docs.sort(key=lambda x: workload[x['id']]['we' if is_free else 'wd'])
        v1 = docs[0]
        workload[v1['id']]['we' if is_free else 'wd'] += 1
        
        v2 = [d for d in docs if d['id'] != v1['id']][0]
        workload[v2['id']]['we' if is_free else 'wd'] += 1
        
        v3_name = "-"
        if curr.weekday() in [4,5,6] or is_h:
            v3 = [d for d in docs if d['id'] not in [v1['id'], v2['id']]][0]
            v3_name = v3['name']
            workload[v3['id']]['we' if is_free else 'wd'] += 1
            
        df_list.append({"วันที่": curr.strftime("%d/%m/%Y"), "วัน": ["จ","อ","พ","พฤ","ศ","ส","อา"][curr.weekday()], "เวรนอกเวลา": v1['name'], "เวรวอร์ด": v2['name'], "เวรถปภ.": v3_name, "หมายเหตุ": h_name, "is_h": is_free})
        curr += timedelta(days=1)
    return pd.DataFrame(df_list)

if st.button("🚀 ประมวลผลและเตรียมไฟล์"):
    df = generate()
    colors = {d['name']: get_pastel_color(d['name']) for d in st.session_state.doctors}

    # 1. แสดงบนเว็บ
    def s_table(row):
        styles = ['background-color: #FFEBEE' if row['is_h'] else ''] * len(row)
        for i, col in enumerate(["เวรนอกเวลา", "เวรวอร์ด", "เวรถปภ."]):
            if row[col] in colors: styles[df.columns.get_loc(col)] = f"background-color: {colors[row[col]]}"
        return styles

    st.subheader("ตารางเวร")
    st.dataframe(df.drop(columns=['is_h']).style.apply(s_table, axis=1), height=500, use_container_width=True)

    # 2. ปุ่ม Export Excel (แบบมีสี)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.drop(columns=['is_h']).to_excel(writer, index=False, sheet_name='Sheet1')
        workbook = writer.book
        worksheet = writer.sheets['Sheet1']
        # ใส่สีหัวตารางใน Excel
        f1 = workbook.add_format({'bg_color': HEADER_COLORS['OPD'], 'border': 1})
        f2 = workbook.add_format({'bg_color': HEADER_COLORS['WARD'], 'border': 1})
        f3 = workbook.add_format({'bg_color': HEADER_COLORS['SEC'], 'border': 1})
        worksheet.write('C1', 'เวรนอกเวลา', f1)
        worksheet.write('D1', 'เวรวอร์ด', f2)
        worksheet.write('E1', 'เวรถปภ.', f3)

    st.download_button("🟢 ดาวน์โหลด Excel (มีสีหัวตาราง)", output.getvalue(), "schedule.xlsx")

    # 3. คำแนะนำสำหรับ PDF บน iPad
    st.info("💡 **วิธีบันทึกเป็น PDF ใน iPad:** ให้คุณกดปุ่มแชร์ของ Safari (รูปสี่เหลี่ยมลูกศรชี้ขึ้น) > เลือก 'พิมพ์' (Print) > แล้วใช้สองนิ้วกางออกที่รูปตัวอย่างเพื่อบันทึกเป็น PDF ครับ")
