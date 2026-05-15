import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import random
import io

st.set_page_config(layout="wide", page_title="Medical Scheduler Pro")

# --- CUSTOM CSS FOR IPAD FULLSCREEN & CENTERING ---
st.markdown("""
    <style>
    .main .block-container { padding: 1rem 1rem; max-width: 100%; }
    [data-testid="stElementToolbar"] { display: none; }
    .stDataFrame div[data-testid="stTable"] div { text-align: center !important; }
    th { text-align: center !important; color: black !important; font-weight: bold !important; }
    </style>
""", unsafe_allow_html=True)

# --- COLORS SETTINGS ---
HEADER_COLORS = {"OPD": "#FFD700", "WARD": "#87CEFA", "SEC": "#98FB98", "HOLIDAY_CELL": "#FF9999"}

def get_distinct_color(idx):
    # ชุดสีพาสเทลที่แยกเฉดชัดเจน (แดง, เขียว, ฟ้า, ส้ม, ม่วง, ชมพู, เหลือง)
    palette = ["#FFB3BA", "#BAFFC9", "#BAE1FF", "#FFFFBA", "#FFDFBA", "#E0BBE4", "#D4F0F0", "#FEC8D8", "#C5E1A5", "#90CAF9"]
    return palette[idx % len(palette)]

# --- SESSION STATE ---
if 'doctors' not in st.session_state:
    st.session_state.doctors = [
        {"id": 1, "name": "หมอเอ", "start_date": datetime(2025, 6, 1)},
        {"id": 2, "name": "หมอบี", "start_date": datetime(2025, 6, 1)},
        {"id": 3, "name": "หมอซี", "start_date": datetime(2025, 6, 1)},
        {"id": 4, "name": "หมอดี", "start_date": datetime(2025, 6, 1)},
    ]

# วันหยุดราชการไทยเบื้องต้น
if 'holidays' not in st.session_state:
    st.session_state.holidays = {
        datetime(2025, 6, 3): "วันเฉลิมฯ พระราชินี", datetime(2025, 7, 10): "วันอาสาฬหบูชา",
        datetime(2025, 7, 11): "วันเข้าพรรษา", datetime(2025, 7, 28): "วันเฉลิมฯ ร.10",
        datetime(2025, 8, 12): "วันแม่แห่งชาติ", datetime(2025, 10, 13): "วันสวรรคต ร.9",
        datetime(2025, 10, 23): "วันปิยมหาราช", datetime(2025, 12, 5): "วันพ่อแห่งชาติ",
        datetime(2025, 12, 10): "วันรัฐธรรมนูญ", datetime(2025, 12, 31): "วันสิ้นปี",
        datetime(2026, 1, 1): "วันขึ้นปีใหม่", datetime(2026, 3, 3): "วันมาฆบูชา",
        datetime(2026, 4, 6): "วันจักรี", datetime(2026, 4, 13): "วันสงกรานต์",
        datetime(2026, 4, 14): "วันสงกรานต์", datetime(2026, 4, 15): "วันสงกรานต์",
        datetime(2026, 5, 1): "วันแรงงาน", datetime(2026, 5, 4): "วันฉัตรมงคล",
        datetime(2026, 5, 31): "วันวิสาขบูชา"
    }

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ ปี พ.ศ. ที่จัดเวร")
    selected_year = st.number_input("เริ่มต้น มิ.ย. ปี พ.ศ.", 2567, 2600, 2568)
    s_dt = datetime(selected_year - 543, 6, 1)
    e_dt = datetime(selected_year - 542, 5, 31)

    st.divider()
    st.header("👨‍⚕️ แพทย์ & วันหยุด")
    with st.expander("➕ เพิ่มแพทย์/วันหยุด"):
        with st.form("add_form", clear_on_submit=True):
            type = st.radio("ประเภท", ["แพทย์", "วันหยุด"])
            name = st.text_input("ชื่อ")
            date = st.date_input("วันที่")
            if st.form_submit_button("บันทึก"):
                if name:
                    if type == "แพทย์":
                        st.session_state.doctors.append({"id": random.randint(100,999), "name": name, "start_date": datetime.combine(date, datetime.min.time())})
                    else:
                        st.session_state.holidays[datetime.combine(date, datetime.min.time())] = name
                    st.rerun()

    st.subheader("📋 ลิสต์วันหยุดปัจจุบัน")
    for d, n in sorted(st.session_state.holidays.items()):
        if s_dt <= d <= e_dt:
            c1, c2 = st.columns([4, 1])
            c1.caption(f"{d.strftime('%d/%m/%Y')} {n}")
            if c2.button("🗑️", key=f"h_{d.timestamp()}"):
                del st.session_state.holidays[d]
                st.rerun()

# --- ALGORITHM & LOGIC ---
def generate_all():
    curr = s_dt
    data = []
    # เก็บสถิติ: {doc_name: {เวรประเภท: {วันธรรมดา/วันหยุด: count}}}
    stats = {d['name']: {"เวรนอกเวลา": [0, 0], "เวรวอร์ด": [0, 0], "เวรถปภ.": [0, 0]} for d in st.session_state.doctors}
    
    while curr <= e_dt:
        h_text = st.session_state.holidays.get(curr, "")
        is_free = (curr.weekday() >= 5) or (h_text != "")
        type_idx = 1 if is_free else 0 # 0=Weekday, 1=Holiday
        
        available = [d for d in st.session_state.doctors if d['start_date'] <= curr]
        if len(available) < 2: curr += timedelta(days=1); continue
        
        random.shuffle(available)
        # จัดเวร
        available.sort(key=lambda x: sum(stats[x['name']][k][type_idx] for k in stats[x['name']]))
        
        v1 = available[0]['name']
        stats[v1]["เวรนอกเวลา"][type_idx] += 1
        
        v2 = available[1]['name']
        stats[v2]["เวรวอร์ด"][type_idx] += 1
        
        v3 = "-"
        if curr.weekday() in [4,5,6] or h_text != "":
            v3 = available[2]['name'] if len(available) > 2 else available[0]['name']
            stats[v3]["เวรถปภ."][type_idx] += 1

        data.append({
            "วันที่": curr.strftime("%d/%m/%Y"),
            "วัน": ["จันทร์","อังคาร","พุธ","พฤหัสบดี","ศุกร์","เสาร์","อาทิตย์"][curr.weekday()],
            "เวรนอกเวลา": v1, "เวรวอร์ด": v2, "เวรถปภ.": v3,
            "หมายเหตุ": h_text, "is_h": is_free
        })
        curr += timedelta(days=1)
    return pd.DataFrame(data), stats

# --- DISPLAY ---
st.title(f"🏥 ตารางเวรแพทย์ปีงบประมาณ {selected_year}")

if len(st.session_state.doctors) >= 2:
    df, stats = generate_all()
    # สร้าง Color Map ให้แพทย์
    doc_colors = {d['name']: get_distinct_color(i) for i, d in enumerate(st.session_state.doctors)}

    def style_main(row):
        # พื้นฐานตัวหนังสือสีดำ กึ่งกลาง
        base = 'color: black; font-weight: bold; text-align: center;'
        styles = [base] * len(row)
        # สีช่องวันที่/วัน
        if row.iloc[-1]: # is_h
            styles[0] = styles[1] = f'background-color: {HEADER_COLORS["HOLIDAY_CELL"]}; {base}'
        else:
            styles[0] = styles[1] = f'background-color: white; {base}'
        
        # สีแพทย์
        for i, col_idx in enumerate([2, 3, 4]):
            name = row.iloc[col_idx]
            if name in doc_colors:
                styles[col_idx] = f'background-color: {doc_colors[name]}; {base}'
        return styles

    # พ่น Header CSS
    st.markdown(f"<style>th:nth-child(4){{background:{HEADER_COLORS['OPD']}!important}} th:nth-child(5){{background:{HEADER_COLORS['WARD']}!important}} th:nth-child(6){{background:{HEADER_COLORS['SEC']}!important}}</style>", unsafe_allow_html=True)
    
    st.dataframe(df.style.apply(style_main, axis=1).hide(axis='columns', subset=['is_h']), height=600, use_container_width=True)

    # --- SUMMARY TABLE ---
    st.divider()
    st.subheader("📊 สรุปจำนวนเวรรายบุคคล (ครั้ง)")
    summary_list = []
    for d_name, shifts in stats.items():
        summary_list.append({
            "ชื่อแพทย์": d_name,
            "นอกเวลา(ธรรมดา)": shifts["เวรนอกเวลา"][0], "นอกเวลา(หยุด)": shifts["เวรนอกเวลา"][1],
            "วอร์ด(ธรรมดา)": shifts["เวรวอร์ด"][0], "วอร์ด(หยุด)": shifts["เวรวอร์ด"][1],
            "ถปภ.(ธรรมดา)": shifts["เวรถปภ."][0], "ถปภ.(หยุด)": shifts["เวรถปภ."][1],
            "รวมทั้งหมด": sum(shifts[k][0] + shifts[k][1] for k in shifts)
        })
    st.table(pd.DataFrame(summary_list))

    # DOWNLOAD
    csv = df.drop(columns=['is_h']).to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 ดาวน์โหลดตาราง (CSV)", csv, "schedule.csv", "text/csv", use_container_width=True)
else:
    st.warning("เพิ่มแพทย์อย่างน้อย 2 คน")
