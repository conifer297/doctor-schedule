import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import random
import io

st.set_page_config(layout="wide", page_title="Universal Medical Scheduler")

# --- COLORS ---
HEADER_COLORS = {"OPD": "#FFD700", "WARD": "#87CEFA", "SEC": "#98FB98", "HOLIDAY": "#FFEBEE"}

def get_pastel_color(name):
    random.seed(sum(ord(c) for c in name))
    return f"hsl({random.randint(0, 360)}, 85%, 90%)"

# --- SESSION STATE ---
if 'doctors' not in st.session_state:
    st.session_state.doctors = []

if 'holidays' not in st.session_state:
    st.session_state.holidays = {}

# --- SIDEBAR: SETUP ---
with st.sidebar:
    st.header("⚙️ ตั้งค่าช่วงเวลา")
    # ให้ผู้ใช้เลือกปีเริ่มต้นเองได้ (ใช้ได้ถึงอนาคต)
    selected_year = st.number_input("จัดเวรเริ่มปี พ.ศ. (มิ.ย.)", min_value=2567, max_value=2600, value=2568)
    start_date = datetime(selected_year - 543, 6, 1)
    end_date = datetime(selected_year - 542, 5, 31)
    st.caption(f"ช่วงเวลา: {start_date.strftime('%d/%m/%Y')} ถึง {end_date.strftime('%d/%m/%Y')}")

    st.divider()
    st.header("👨‍⚕️ จัดการรายชื่อแพทย์")
    with st.form("doc_form", clear_on_submit=True):
        n_name = st.text_input("ชื่อแพทย์")
        n_start = st.date_input("เริ่มทำงานวันที่", start_date)
        if st.form_submit_button("➕ เพิ่มแพทย์"):
            if n_name:
                st.session_state.doctors.append({
                    "id": random.randint(1000, 9999),
                    "name": n_name,
                    "start_date": datetime.combine(n_start, datetime.min.time())
                })
                st.rerun()

    if st.session_state.doctors:
        for i, doc in enumerate(st.session_state.doctors):
            c1, c2 = st.columns([4, 1])
            c1.caption(f"{doc['name']} (เริ่ม {doc['start_date'].strftime('%d/%m/%y')})")
            if c2.button("🗑️", key=f"del_doc_{doc['id']}"):
                st.session_state.doctors.pop(i)
                st.rerun()

    st.divider()
    st.header("📅 วันหยุดพิเศษ")
    with st.form("h_form", clear_on_submit=True):
        h_date = st.date_input("วันที่")
        h_name = st.text_input("ชื่อวันหยุด")
        if st.form_submit_button("💾 บันทึก"):
            if h_name:
                st.session_state.holidays[datetime.combine(h_date, datetime.min.time())] = h_name
                st.rerun()

    if st.session_state.holidays:
        for d, name in sorted(st.session_state.holidays.items()):
            # แสดงเฉพาะวันหยุดที่อยู่ในช่วงปีที่เลือก
            if start_date <= d <= end_date:
                c1, c2 = st.columns([4, 1])
                c1.caption(f"{d.strftime('%d/%m/%y')} {name}")
                if c2.button("🗑️", key=f"del_h_{d.timestamp()}"):
                    del st.session_state.holidays[d]
                    st.rerun()

# --- LOGIC ---
def generate(s_dt, e_dt):
    if not st.session_state.doctors: return pd.DataFrame()
    curr = s_dt
    data = []
    workload = {d['id']: {'wd': 0, 'we': 0} for d in st.session_state.doctors}
    
    while curr <= e_dt:
        h_text = st.session_state.holidays.get(curr, "")
        is_free = (curr.weekday() >= 5) or (h_text != "")
        available = [d for d in st.session_state.doctors if d['start_date'] <= curr]
        
        if len(available) < 2:
            curr += timedelta(days=1); continue
            
        random.shuffle(available)
        assigned = []
        # เกลี่ยภาระงาน
        for _ in range(2):
            available.sort(key=lambda x: workload[x['id']]['we' if is_free else 'wd'])
            sel = [d for d in available if d['id'] not in assigned][0]
            assigned.append(sel['id'])
            workload[sel['id']]['we' if is_free else 'wd'] += 1
        
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

# --- DISPLAY ---
st.title(f"🏥 ระบบจัดเวรแพทย์ปีงบประมาณ {selected_year}")

if len(st.session_state.doctors) >= 2:
    df = generate(start_date, end_date)
    if not df.empty:
        doc_colors = {d['name']: get_pastel_color(d['name']) for d in st.session_state.doctors}

        def style_df(row):
            styles = ['color: black; font-weight: bold;'] * len(row)
            if row.iloc[-1]: # highlight holiday
                styles[0] = styles[1] = f'background-color: {HEADER_COLORS["HOLIDAY"]};'
            for i, col_idx in enumerate([2, 3, 4]):
                name = row.iloc[col_idx]
                if name in doc_colors:
                    styles[col_idx] = f'background-color: {doc_colors[name]}; color: black;'
            return styles

        st.markdown(f"<style>th{{color:black!important;font-weight:bold!important}} th:nth-child(4){{background:{HEADER_COLORS['OPD']}!important}} th:nth-child(5){{background:{HEADER_COLORS['WARD']}!important}} th:nth-child(6){{background:{HEADER_COLORS['SEC']}!important}}</style>", unsafe_allow_html=True)
        
        st.dataframe(df.style.apply(style_df, axis=1).hide(axis='columns', subset=['is_h']), height=600, use_container_width=True)

        # DOWNLOAD
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.drop(columns=['is_h']).to_excel(writer, index=False)
        st.download_button("📥 ดาวน์โหลด Excel ตารางปีนี้", output.getvalue(), f"schedule_{selected_year}.xlsx", use_container_width=True)
else:
    st.warning("👈 กรุณาตั้งค่า 'ปี' และ 'รายชื่อแพทย์' ที่แถบด้านข้าง")
