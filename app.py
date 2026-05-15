import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import random
import io

st.set_page_config(layout="wide", page_title="Medical Shift Scheduler")

# --- COLORS ---
HEADER_COLORS = {"OPD": "#FFD700", "WARD": "#87CEFA", "SEC": "#98FB98", "HOLIDAY": "#FFEBEE"}

def get_pastel_color(name):
    random.seed(sum(ord(c) for c in name))
    return f"hsl({random.randint(0, 360)}, 85%, 90%)"

# --- SESSION STATE INITIALIZATION ---
if 'doctors' not in st.session_state:
    st.session_state.doctors = [
        {"id": 1, "name": "หมอเอ", "start_date": datetime(2025, 6, 1)},
        {"id": 2, "name": "หมอบี", "start_date": datetime(2025, 6, 1)},
        {"id": 3, "name": "หมอซี", "start_date": datetime(2025, 6, 1)},
        {"id": 4, "name": "หมอดี", "start_date": datetime(2025, 6, 1)},
    ]

if 'holidays' not in st.session_state:
    st.session_state.holidays = {
        datetime(2025, 12, 5): "วันพ่อแห่งชาติ",
        datetime(2026, 1, 1): "วันขึ้นปีใหม่"
    }

# --- SIDEBAR: FORMS FOR IPAD STABILITY ---
with st.sidebar:
    st.header("👨‍⚕️ จัดการรายชื่อแพทย์")
    # ใช้ Form เพื่อป้องกัน Error ตอนพิมพ์บน iPad
    with st.form("doctor_form", clear_on_submit=True):
        n_name = st.text_input("ชื่อแพทย์")
        n_start = st.date_input("วันที่เริ่มงาน", datetime(2025, 6, 1))
        submit_doc = st.form_submit_button("➕ เพิ่มแพทย์")
        
        if submit_doc:
            if n_name:
                new_doc = {
                    "id": len(st.session_state.doctors) + 1,
                    "name": n_name,
                    "start_date": datetime.combine(n_start, datetime.min.time())
                }
                st.session_state.doctors.append(new_doc)
                st.success(f"เพิ่ม {n_name} แล้ว")
                st.rerun()
            else:
                st.error("กรุณาใส่ชื่อ")

    st.divider()
    st.header("📅 จัดการวันหยุด")
    with st.form("holiday_form", clear_on_submit=True):
        h_date = st.date_input("เลือกวันที่หยุด")
        h_name = st.text_input("ชื่อวันหยุด")
        submit_h = st.form_submit_button("💾 บันทึกวันหยุด")
        
        if submit_h:
            if h_name:
                st.session_state.holidays[datetime.combine(h_date, datetime.min.time())] = h_name
                st.success("บันทึกแล้ว")
                st.rerun()

    # แสดงรายการวันหยุด
    if st.session_state.holidays:
        st.write("**วันหยุดที่บันทึก:**")
        for d, name in sorted(st.session_state.holidays.items()):
            c1, c2 = st.columns([4, 1])
            c1.caption(f"{d.strftime('%d/%m/%Y')} {name}")
            if c2.button("🗑️", key=f"del_{d.timestamp()}"):
                del st.session_state.holidays[d]
                st.rerun()

# --- ALGORITHM ---
def generate():
    if not st.session_state.doctors:
        return pd.DataFrame()
        
    start_dt, end_dt = datetime(2025, 6, 1), datetime(2026, 5, 31)
    curr = start_dt
    data = []
    workload = {d['id']: {'wd': 0, 'we': 0} for d in st.session_state.doctors}
    
    while curr <= end_dt:
        h_text = st.session_state.holidays.get(curr, "")
        is_free = (curr.weekday() >= 5) or (h_text != "")
        
        # เลือกเฉพาะแพทย์ที่เริ่มงานแล้ว
        available = [d for d in st.session_state.doctors if d['start_date'] <= curr]
        
        if len(available) < 2: # ป้องกัน Error กรณีแพทย์ไม่พอ
            curr += timedelta(days=1)
            continue
            
        random.shuffle(available)
        assigned = []
        
        # จัดเวร 1 และ 2
        for _ in range(2):
            available.sort(key=lambda x: workload[x['id']]['we' if is_free else 'wd'])
            sel = [d for d in available if d['id'] not in assigned][0]
            assigned.append(sel['id'])
            workload[sel['id']]['we' if is_free else 'wd'] += 1
        
        # เวร 3 (ถปภ)
        v3_name = "-"
        if (curr.weekday() in [4,5,6] or h_text != ""):
            rem = [d for d in available if d['id'] not in assigned]
            if rem:
                v3 = rem[0]
                v3_name = v3['name']
                workload[v3['id']]['we' if is_free else 'wd'] += 1

        data.append({
            "วันที่": curr.strftime("%d/%m/%Y"),
            "วัน": ["จันทร์","อังคาร","พุธ","พฤหัสบดี","ศุกร์","เสาร์","อาทิตย์"][curr.weekday()],
            "เวรนอกเวลา": next(d['name'] for d in st.session_state.doctors if d['id'] == assigned[0]),
            "เวรวอร์ด": next(d['name'] for d in st.session_state.doctors if d['id'] == assigned[1]),
            "เวรถปภ.": v3_name,
            "หมายเหตุ": h_text,
            "is_h": is_free
        })
        curr += timedelta(days=1)
    return pd.DataFrame(data)

# --- MAIN DISPLAY ---
st.title("🏥 ตารางเวรแพทย์ประจำปี (มิ.ย. - พ.ค.)")
st.info(f"ขณะนี้มีแพทย์ในระบบ {len(st.session_state.doctors)} คน")

if len(st.session_state.doctors) >= 2:
    df = generate()
    if not df.empty:
        doc_colors = {d['name']: get_pastel_color(d['name']) for d in st.session_state.doctors}

        def style_df(row):
            styles = [''] * len(row)
            if row['is_h']:
                styles[0] = styles[1] = f'background-color: {HEADER_COLORS["HOLIDAY"]}'
            for i, col in enumerate(["เวรนอกเวลา", "เวรวอร์ด", "เวรถปภ."]):
                name = row[col]
                if name in doc_colors:
                    styles[df.columns.get_loc(col)] = f'background-color: {doc_colors[name]}'
            return styles

        st.markdown(f"<style>th:nth-child(4){{background:{HEADER_COLORS['OPD']}!important;color:black}} th:nth-child(5){{background:{HEADER_COLORS['WARD']}!important;color:black}} th:nth-child(6){{background:{HEADER_COLORS['SEC']}!important;color:black}}</style>", unsafe_allow_html=True)
        
        st.dataframe(df.drop(columns=['is_h']).style.apply(style_df, axis=1), height=500, use_container_width=True)

        # DOWNLOAD
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.drop(columns=['is_h']).to_excel(writer, index=False)
        st.download_button("📥 ดาวน์โหลด Excel", output.getvalue(), "schedule.xlsx", use_container_width=True)
else:
    st.warning("กรุณาเพิ่มแพทย์อย่างน้อย 2 คนเพื่อเริ่มจัดเวร")
