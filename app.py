import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import random
import collections

# ตั้งค่าหน้าจอและสไตล์
st.set_page_config(layout="wide", page_title="Doctor Stable-Schedule Pro")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;700&display=swap');
    html, body, [class*="css"], .stMarkdown, p, div, span, label { font-family: 'Sarabun', sans-serif !important; }
    th { border: 1px solid #000 !important; text-align: center !important; background-color: #f0f2f6; color: black !important; font-weight: bold; }
    td { border: 1px solid #000 !important; text-align: center !important; }
    .stDataFrame { font-size: 1.1rem; }
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

# --- Sidebar ตั้งค่าและจัดการข้อมูล ---
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

    if st.button("🗑️ ล้างข้อมูลทั้งหมด", use_container_width=True):
        st.session_state.doctors = []
        st.session_state.all_active_holidays = {}
        st.session_state.init_year = None
        st.rerun()

    st.divider()
    st.header("👨‍⚕️ จัดการแพทย์")
    with st.form("doc_form", clear_on_submit=True):
        n_name = st.text_input("ชื่อแพทย์")
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
    st.header("📅 จัดการวันหยุด")
    with st.form("h_form", clear_on_submit=True):
        h_date = st.date_input("วันที่", s_dt)
        h_name = st.text_input("ชื่อวันหยุด")
        if st.form_submit_button("💾 เพิ่มวันหยุด"):
            if h_name:
                st.session_state.all_active_holidays[datetime.combine(h_date, datetime.min.time())] = h_name
                st.rerun()

    if st.session_state.all_active_holidays:
        st.subheader("🗑️ รายการวันหยุด (กดลบได้)")
        for d, name in sorted(st.session_state.all_active_holidays.items()):
            c1, c2 = st.columns([4,1])
            c1.caption(f"{format_thai_date(d)} - {name}")
            if c2.button("🗑️", key=f"h_{d.timestamp()}"):
                del st.session_state.all_active_holidays[d]; st.rerun()

# --- Core Algorithm: Stable Simulation & Holiday Analysis ---
def generate_schedule():
    all_h = st.session_state.all_active_holidays
    docs = st.session_state.doctors
    if not docs: return pd.DataFrame(), {}, {}, None, {}
    
    latest_start_date = max([d['start'] for d in docs])
    doc_names = [d['name'] for d in docs]
    
    # โครงสร้างเก็บสถิติภาระงานแยกประเภท
    def create_stat_template():
        return {"โอพีดี(ธรรมดา)":0, "โอพีดี(หยุด)":0, "วอร์ด(ธรรมดา)":0, "วอร์ด(หยุด)":0, "ถปภ.(ธรรมดา)":0, "ถปภ.(หยุด)":0}
        
    stats_before = {n: create_stat_template() for n in doc_names}
    stats_after = {n: create_stat_template() for n in doc_names}
    load_score = {n: 0 for n in doc_names}
    
    data = []
    curr = s_dt
    last_month = -1
    
    # 1. ทำการจัดเวรหลัก
    while curr <= e_dt:
        if curr.month != last_month:
            m_name = ["", "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน", "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"][curr.month]
            data.append({"วันที่": f"--- {m_name} {get_thai_year(curr)} ---", "is_header": True})
            last_month = curr.month

        # ล็อคความจำด้วย Seed วันที่ เพื่อรักษาผลลัพธ์ดั้งเดิมในอดีตไม่ให้ขยับ
        random.seed(int(curr.timestamp()))

        available_docs = sorted([d['name'] for d in docs if d['start'] <= curr])
        if not available_docs:
            curr += timedelta(days=1)
            continue

        h_text = all_h.get(curr, "")
        is_we = (curr.weekday() >= 5) or (h_text != "")
        score = 2 if is_we else 1
        day_type = "หยุด" if is_we else "ธรรมดา"

        # ชดใช้เวรโดยเลือกคนที่มีคะแนนภาระงานสะสมต่ำสุด ณ วันนั้นๆ
        sorted_by_load = sorted(available_docs, key=lambda x: (load_score[x], random.random()))
        
        v1 = sorted_by_load[0]
        v2 = sorted_by_load[1] if len(available_docs) > 1 else v1
        
        v3 = "-"
        if is_we or curr.weekday() == 4:
            v3_pool = [d for d in available_docs if d not in [v1, v2]]
            if v3_pool: v3 = random.choice(v3_pool)

        # บันทึกข้อมูลลงตารางสรุปตามช่วงเวลาแพทย์คนล่าสุดมาแทรก
        target_stats = stats_after if curr >= latest_start_date else stats_before
        target_stats[v1][f"โอพีดี({day_type})"] += 1
        target_stats[v2][f"วอร์ด({day_type})"] += 1
        load_score[v1] += score
        load_score[v2] += score
        if v3 != "-":
            target_stats[v3][f"ถปภ.({day_type})"] += 1
            load_score[v3] += score

        data.append({
            "วันที่": format_thai_date(curr), "วัน": ["จันทร์","อังคาร","พุธ","พฤหัสบดี","ศุกร์","เสาร์","อาทิตย์"][curr.weekday()],
            "เวรโอพีดี": v1, "เวรวอร์ด": v2, "เวรถปภ.": v3, "หมายเหตุ": h_text,
            "is_h": is_we, "is_header": False, "raw_date": curr
        })
        curr += timedelta(days=1)

    # 2. ค้นหาและวิเคราะห์ "ช่วงเทศกาลวันหยุดยาวราชการ" (Long Weekend)
    holiday_blocks = []
    current_block = []
    curr = s_dt
    while curr <= e_dt:
        is_h = (curr.weekday() >= 5) or (curr in all_h)
        if is_h:
            current_block.append(curr)
        else:
            if len(current_block) >= 2: # ถือเป็นวันหยุดยาวถ้าราชการติดต่อกันตั้งแต่ 2 วันขึ้นไป
                holiday_blocks.append(current_block)
            current_block = []
        curr += timedelta(days=1)
    if len(current_block) >= 2:
        holiday_blocks.append(current_block)

    # นับว่าแต่ละคนถูกสุ่มให้เข้าเวรในช่วงวันหยุดยาวเหล่านั้นกี่ครั้ง
    # โครงสร้าง: {ชื่อแพทย์: {ความยาวรอบวันหยุดยาว: จำนวนวันที่ต้องมาทำงาน}}
    hol_stats = {n: {2:0, 3:0, 4:0, "5วันขึ้นไป":0} for n in doc_names}
    
    # แปลงข้อมูลตารางหลักเพื่อสแกนเวรรายวัน
    df_clean = pd.DataFrame([r for r in data if not r.get("is_header")])
    
    if not df_clean.empty:
        for block in holiday_blocks:
            length = len(block)
            # แยกประเภทหัวข้อกลุ่มวันหยุดยาว
            if length == 2: cat = 2
            elif length == 3: cat = 3
            elif length == 4: cat = 4
            else: cat = "5วันขึ้นไป"
            
            # ตรวจสอบรายวันในบล็อกหยุดยาวนั้นๆ
            for day in block:
                day_rows = df_clean[df_clean["raw_date"] == day]
                if not day_rows.empty:
                    row = day_rows.iloc[0]
                    # เช็คแพทย์ทุกคนที่โดนเรียกปฏิบัติงานในวันนั้น
                    assigned = [row["เวรโอพีดี"], row["เวรวอร์ด"], row["เวรถปภ."]]
                    for n in doc_names:
                        if n in assigned:
                            hol_stats[n][cat] += 1

    return pd.DataFrame(data), stats_before, stats_after, latest_start_date, hol_stats

# --- ส่วนควบคุมการแสดงผลหน้าจอ (UI) ---
st.title(f"🏥 ระบบจัดเวรแพทย์ พ.ศ. {selected_year}")

if st.session_state.doctors:
    df, s_before, s_after, l_start, hol_stats = generate_schedule()

    def style_row(row):
        if row.get('is_header'): return ['background-color: #B2EBF2; color: black; font-weight: bold; border: 1px solid black;'] * len(row)
        return [f"background-color: {'#FFCDD2' if row.get('is_h') else 'white'}; color: black; border: 1px solid black; font-weight: bold;"] * len(row)

    # ตารางหลักประธานเวร
    st.dataframe(df.style.apply(style_row, axis=1).hide(axis='columns', subset=['is_h', 'is_header', 'raw_date']), height=500, use_container_width=True)

    # ฟังก์ชันช่วยจัดรูปแบบโครงสร้างพร้อมช่องผลรวมสุทธิ (สีน้ำเงิน)
    def build_summary_table(stats_dict):
        res_df = pd.DataFrame.from_dict(stats_dict, orient='index').fillna(0).astype(int)
        if res_df.empty: return res_df
        
        # คำนวณยอดรวมสรุปแต่ละหมวดหมู่ตามเจตนาผู้ใช้งาน
        res_df["รวมเวรธรรมดา"] = res_df["โอพีดี(ธรรมดา)"] + res_df["วอร์ด(ธรรมดา)"] + res_df["ถปภ.(ธรรมดา)"]
        res_df["รวมเวรวันหยุด"] = res_df["โอพีดี(หยุด)"] + res_df["วอร์ด(หยุด)"] + res_df["ถปภ.(หยุด)"]
        res_df["รวมเวรทั้งหมด"] = res_df["รวมเวรธรรมดา"] + res_df["รวมเวรวันหยุด"]
        
        # จัดตำแหน่งโครงสร้างคอลัมน์ให้อ่านง่ายสอดคล้องกัน
        cols_order = [
            "โอพีดี(ธรรมดา)", "วอร์ด(ธรรมดา)", "ถปภ.(ธรรมดา)", "รวมเวรธรรมดา",
            "โอพีดี(หยุด)", "วอร์ด(หยุด)", "ถปภ.(หยุด)", "รวมเวรวันหยุด", 
            "รวมเวรทั้งหมด"
        ]
        return res_df[cols_order]

    # --- ตารางสรุปภาระงานละเอียดแยกช่วงเวลา ---
    st.divider()
    st.header("📊 ตารางสรุปจำนวนเวรแยกช่วงเวลา (ภาษาไทยพร้อมช่องรวมสรุป)")
    
    st.subheader(f"1. ช่วงแรก (ก่อนแพทย์คนล่าสุดเริ่มงาน : ก่อน {format_thai_date(l_start)})")
    df_b = build_summary_table(s_before)
    if not df_b.empty: st.table(df_b)
    else: st.write("ไม่มีประวัติในช่วงเวลานี้")

    st.subheader(f"2. ช่วงสมบูรณ์ (เริ่มคำนวณปรับสมดุลเวรใหม่ : ตั้งแต่ {format_thai_date(l_start)})")
    df_a = build_summary_table(s_after)
    if not df_a.empty: st.table(df_a)
    else: st.write("ยังไม่ถึงเกณฑ์เวลาดังกล่าว")

    # --- ตารางวิเคราะห์เทศกาลวันหยุดราชการต่อเนื่อง ---
    st.divider()
    st.header("🏖️ ตารางสรุปการทำงานช่วงวันหยุดยาวราชการ (จำนวนวันที่โดนสุ่มให้มาเข้าเวร)")
    st.caption("วิเคราะห์ข้อมูลโปร่งใส: บ่งบอกว่าในเทศกาลวันหยุดต่อเนื่องตามปฏิทิน (เช่น ช่วง 3 วัน หรือ 4 วัน) แต่ละคนต้องสละเวลามาปฏิบัติงานจริงกี่วัน")
    
    h_rows = []
    for name, cats in hol_stats.items():
        h_rows.append({
            "ชื่อแพทย์": name,
            "ช่วงหยุดยาว 2 วัน (วัน)": cats[2],
            "ช่วงหยุดยาว 3 วัน (วัน)": cats[3],
            "ช่วงหยุดยาว 4 วัน (วัน)": cats[4],
            "ช่วงหยุดยาว 5 วันขึ้นไป (วัน)": cats["5วันขึ้นไป"],
            "รวมวันหยุดยาวที่ต้องทำงาน (วัน)": cats[2] + cats[3] + cats[4] + cats["5วันขึ้นไป"]
        })
    st.table(pd.DataFrame(h_rows).set_index("ชื่อแพทย์"))

else:
    st.info("👈 เพิ่มรายชื่อแพทย์ วันที่เริ่มทำงาน และตั้งค่าปี พ.ศ. ที่แถบเมนูด้านซ้ายเพื่อเริ่มต้นรันระบบ")
