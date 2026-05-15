import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import random
import json
import os

# ตั้งค่าหน้าจอและสไตล์
st.set_page_config(layout="wide", page_title="Medical Fair-Scheduler True Holiday Block")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;700&display=swap');
    html, body, [class*="css"], .stMarkdown, p, div, span, label { font-family: 'Sarabun', sans-serif !important; }
    th { border: 1px solid #000 !important; text-align: center !important; background-color: #f0f2f6; color: black !important; font-weight: bold; }
    td { border: 1px solid #000 !important; text-align: center !important; }
    .stDataFrame { font-size: 1.1rem; }
    </style>
""", unsafe_allow_html=True)

DB_FILE = "true_holiday_scheduler_db.json"

# --- SYSTEM DATABASE FUNCTIONS ---
def load_from_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            doctors = []
            for d in data.get("doctors", []):
                doctors.append({
                    "id": d["id"], "name": d["name"],
                    "start": datetime.strptime(d["start"], "%Y-%m-%d")
                })
            custom_holidays = {}
            for k, v in data.get("custom_holidays", {}).items():
                custom_holidays[datetime.strptime(k, "%Y-%m-%d")] = v
            return doctors, custom_holidays, data.get("selected_year", 2568)
        except:
            return [], {}, 2568
    return [], {}, 2568

def save_to_db():
    data = {
        "selected_year": st.session_state.selected_year,
        "doctors": [{
            "id": d["id"], "name": d["name"],
            "start": d["start"].strftime("%Y-%m-%d")
        } for d in st.session_state.doctors],
        "custom_holidays": {k.strftime("%Y-%m-%d"): v for k, v in st.session_state.all_active_holidays.items()}
    }
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

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

# --- Initialize Session State ---
db_docs, db_hols, db_year = load_from_db()

if 'doctors' not in st.session_state: st.session_state.doctors = db_docs
if 'all_active_holidays' not in st.session_state: st.session_state.all_active_holidays = db_hols
if 'selected_year' not in st.session_state: st.session_state.selected_year = db_year
if 'init_year' not in st.session_state: st.session_state.init_year = None

# --- SIDEBAR CONTROL PANEL ---
with st.sidebar:
    st.header("⚙️ ตั้งค่าระบบ")
    prev_year = st.session_state.selected_year
    st.session_state.selected_year = st.number_input("จัดเวรของปี พ.ศ. (เริ่ม มิ.ย.)", 2560, 2600, prev_year)
    
    if prev_year != st.session_state.selected_year:
        save_to_db()
        
    s_dt = datetime(st.session_state.selected_year - 543, 6, 1)
    e_dt = datetime(st.session_state.selected_year - 542, 5, 31)

    if st.session_state.init_year != st.session_state.selected_year:
        if not st.session_state.all_active_holidays:
            hols = get_fixed_holidays(st.session_state.selected_year)
            hols.update(get_fixed_holidays(st.session_state.selected_year + 1))
            st.session_state.all_active_holidays = {d: n for d, n in hols.items() if s_dt <= d <= e_dt}
        st.session_state.init_year = st.session_state.selected_year

    if st.button("🗑️ ล้างข้อมูลระบบและฐานข้อมูลทั้งหมด", use_container_width=True):
        if os.path.exists(DB_FILE):
            os.remove(DB_FILE)
        st.session_state.doctors = []
        st.session_state.all_active_holidays = {}
        st.session_state.init_year = None
        st.rerun()

    st.divider()
    st.header("👨‍⚕️ รายชื่อแพทย์")
    with st.form("doc_form", clear_on_submit=True):
        n_name = st.text_input("ชื่อแพทย์")
        n_start = st.date_input("เริ่มงานจริง", s_dt)
        if st.form_submit_button("➕ เพิ่มแพทย์"):
            if n_name:
                st.session_state.doctors.append({
                    "id": random.randint(100,999), 
                    "name": n_name.replace("หมอ", "").strip(), 
                    "start": datetime.combine(n_start, datetime.min.time())
                })
                save_to_db()
                st.rerun()

    for i, d in enumerate(st.session_state.doctors):
        c1, c2 = st.columns([4,1])
        c1.write(f"{d['name']} (เริ่ม {format_thai_date(d['start'])})")
        if c2.button("🗑️", key=f"d_{d['id']}"):
            st.session_state.doctors.pop(i)
            save_to_db()
            st.rerun()

    st.divider()
    st.header("📅 วันหยุดเพิ่มเติม")
    with st.form("h_form", clear_on_submit=True):
        h_date = st.date_input("เลือกวันที่", s_dt)
        h_name = st.text_input("ชื่อวันหยุด")
        if st.form_submit_button("💾 บันทึกวันหยุด"):
            if h_name:
                st.session_state.all_active_holidays[datetime.combine(h_date, datetime.min.time())] = h_name
                save_to_db()
                st.rerun()

    if st.session_state.all_active_holidays:
        st.subheader("🗑️ รายการวันหยุด")
        for d, name in sorted(st.session_state.all_active_holidays.items()):
            c1, c2 = st.columns([4,1])
            c1.caption(f"{format_thai_date(d)} - {name}")
            if c2.button("🗑️", key=f"h_{d.timestamp()}"):
                del st.session_state.all_active_holidays[d]
                save_to_db()
                st.rerun()

# --- CORE PROCESSING ENGINE ---
def generate_schedule():
    all_h = st.session_state.all_active_holidays
    docs = st.session_state.doctors
    if not docs: return pd.DataFrame(), {}, {}, None, {}
    
    latest_start_date = max([d['start'] for d in docs])
    doc_names = [d['name'] for d in docs]
    
    def create_stat_template():
        return {"โอพีดี(ธรรมดา)":0, "โอพีดี(หยุด)":0, "วอร์ด(ธรรมดา)":0, "วอร์ด(หยุด)":0, "ถปภ.(ธรรมดา)":0, "ถปภ.(หยุด)":0}
        
    stats_before = {n: create_stat_template() for n in doc_names}
    stats_after = {n: create_stat_template() for n in doc_names}
    
    load_score = {n: 0 for n in doc_names}
    
    data = []
    curr = s_dt
    last_month = -1
    
    while curr <= e_dt:
        if curr.month != last_month:
            m_name = ["", "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน", "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"][curr.month]
            data.append({"วันที่": f"--- {m_name} {get_thai_year(curr)} ---", "is_header": True})
            last_month = curr.month

        random.seed(int(curr.timestamp()))

        available_docs = sorted([d['name'] for d in docs if d['start'] <= curr])
        if not available_docs:
            curr += timedelta(days=1)
            continue

        h_text = all_h.get(curr, "")
        is_we = (curr.weekday() >= 5) or (h_text != "")
        score = 2 if is_we else 1
        day_type = "หยุด" if is_we else "ธรรมดา"

        def get_avg_load(name):
            doc_info = next(d for d in docs if d['name'] == name)
            days_worked = (curr - doc_info['start']).days + 1
            return load_score[name] / days_worked

        sorted_by_load = sorted(available_docs, key=lambda x: (get_avg_load(x), random.random()))
        v1 = sorted_by_load[0]
        v2 = sorted_by_load[1] if len(available_docs) > 1 else v1
        
        v3 = "-"
        if is_we or curr.weekday() == 4:
            v3_pool = [d for d in available_docs if d not in [v1, v2]]
            if v3_pool: v3 = random.choice(v3_pool)

        # บันทึกสถิติแยกประเภทเวร
        target_stats = stats_after if curr >= latest_start_date else stats_before
        target_stats[v1][f"โอพีดี({day_type})"] += 1
        target_stats[v2][f"วอร์ด({day_type})"] += 1
        load_score[v1] += score
        load_score[v2] += score
        if v3 != "-":
            target_stats[v3][f"ถปภ.({day_type})"] += 1
            load_score[v3] += score

        data.append({
            "วันที่": format_thai_date(curr), "วัน": ["อาทิตย์","จันทร์","อังคาร","พุธ","พฤหัสบดี","ศุกร์","เสาร์"][curr.weekday()+1 if curr.weekday() != 6 else 0],
            "เวรโอพีดี": v1, "เวรวอร์ด": v2, "เวรถปภ.": v3, "หมายเหตุ": h_text,
            "is_h": is_we, "is_header": False, "raw_date": curr
        })
        curr += timedelta(days=1)

    # --- LOGIC ค้นหากลุ่มก้อนวันหยุดต่อเนื่อง (เสาร์-อาทิตย์ หรือวันหยุดนักขัตฤกษ์ที่ติดกัน) ---
    holiday_blocks, current_block = [], []
    curr = s_dt
    while curr <= e_dt:
        is_h = (curr.weekday() >= 5) or (curr in all_h)
        if is_h: 
            current_block.append(curr)
        else:
            if len(current_block) >= 2: 
                holiday_blocks.append(current_block)
            current_block = []
        curr += timedelta(days=1)
    if len(current_block) >= 2: 
        holiday_blocks.append(current_block)

    # ตั้งต้นเก็บสถิติ "จำนวนครั้งแยกตามก้อนความยาววันหยุดต่อเนื่อง"
    hol_stats = {n: {2:0, 3:0, 4:0, "5วันขึ้นไป":0} for n in doc_names}
    df_clean = pd.DataFrame([r for r in data if not r.get("is_header")])
    
    if not df_clean.empty:
        for block in holiday_blocks:
            length = len(block)
            # แยกหมวดหมู่ตามความยาวของก้อนวันหยุดต่อเนื่องจริงตามปฏิทิน
            if length == 2: cat = 2
            elif length == 3: cat = 3
            elif length == 4: cat = 4
            else: cat = "5วันขึ้นไป"
            
            # ตรวจสอบแพทย์ทีละคน: ในก้อนวันหยุดเทศกาลนี้ (ไม่ว่าจะยาวกี่วัน) ถ้ามีชื่อไปเอี่ยวในเวรวันใดวันหนึ่ง ถือว่าโดนสุ่มไป 1 ครั้ง
            for n in doc_names:
                has_duty_in_this_block = False
                for day in block:
                    day_rows = df_clean[df_clean["raw_date"] == day]
                    if not day_rows.empty:
                        row = day_rows.iloc[0]
                        if n in [row["เวรโอพีดี"], row["เวรวอร์ด"], row["เวรถปภ."]]:
                            has_duty_in_this_block = True
                            break # เจอชื่อปุ๊บ หยุดสแกนวันอื่นในก้อนนี้ทันทีเพื่อไม่ให้นับซ้ำวัน
                
                if has_duty_in_this_block:
                    hol_stats[n][cat] += 1 # บันทึกแต้มเป็นเข้าเวรก้อนนี้ "1 ครั้ง"

    return pd.DataFrame(data), stats_before, stats_after, latest_start_date, hol_stats

# --- MAIN UI DISPLAY ---
st.title(f"🏥 ตารางเวรแพทย์ พ.ศ. {st.session_state.selected_year}")

if st.session_state.doctors:
    df, s_before, s_after, l_start, hol_stats = generate_schedule()

    def style_row(row):
        if row.get('is_header'): return ['background-color: #B2EBF2; color: black; font-weight: bold; border: 1px solid black;'] * len(row)
        return [f"background-color: {'#FFCDD2' if row.get('is_h') else 'white'}; color: black; border: 1px solid black; font-weight: bold;"] * len(row)

    show_cols = ["วันที่", "วัน", "เวรโอพีดี", "เวรวอร์ด", "เวรถปภ.", "หมายเหตุ"]
    st.dataframe(df.style.apply(style_row, axis=1).hide(axis='columns', subset=[c for c in df.columns if c not in show_cols]), height=500, use_container_width=True)

    # แปลงตารางสรุปภาระงาน (ไม่มีช่องยอดรวมรบกวนสายตาตามสีฟ้า)
    def build_summary_table(stats_dict):
        res_df = pd.DataFrame.from_dict(stats_dict, orient='index').fillna(0).astype(int)
        if res_df.empty: return res_df
        return res_df[["โอพีดี(ธรรมดา)", "วอร์ด(ธรรมดา)", "ถปภ.(ธรรมดา)", "โอพีดี(หยุด)", "วอร์ด(หยุด)", "ถปภ.(หยุด)"]]

    # --- ตารางสรุปจำนวนเวรรายบุคคล ---
    st.divider()
    st.header("📊 ตารางสรุปจำนวนเวรรายบุคคล (แยกประเภทเวรธรรมดา/หยุด)")
    
    st.subheader(f"1. ช่วงแรก (ก่อนแพทย์คนล่าสุดเริ่มงาน : ก่อน {format_thai_date(l_start)})")
    df_b = build_summary_table(s_before)
    if not df_b.empty: st.table(df_b)

    st.subheader(f"2. ช่วงปรับสมดุลเวรใหม่ (ตั้งแต่แพทย์คนล่าสุดเริ่มงาน : ตั้งแต่ {format_thai_date(l_start)})")
    df_a = build_summary_table(s_after)
    if not df_a.empty: st.table(df_a)

    st.subheader("🟢 3. สรุปภาระงานรวมทั้งหมดตลอดทั้งปี (ตาราง 1 + ตาราง 2)")
    if not df_b.empty and not df_a.empty:
        df_total = df_b.add(df_a, fill_value=0).astype(int)
        st.table(df_total)

    # --- ตารางวิเคราะห์เทศกาลวันหยุดราชการต่อเนื่อง (Logic แก้ไขถูกต้องตรงบรีฟ) ---
    st.divider()
    st.header("🏖️ ตารางสรุปการทำงานช่วงวันหยุดยาวราชการ (หน่วย: จำนวนครั้ง)")
    st.caption("ระบบคำนวณตามจริง: วิ่งค้นหาก้อนวันหยุดต่อเนื่องบนปฏิทิน หากแพทย์ท่านใดติดเวรในก้อนนั้นๆ (ไม่ว่าจะโดนกี่วันก็ตามในเทศกาลนั้น) จะนับเป็นสะสมก้อนประเภทนั้น 1 ครั้ง")
    
    h_rows = []
    for name, cats in hol_stats.items():
        h_rows.append({
            "ชื่อแพทย์": name, 
            "วันหยุดต่อเนื่อง 2 วัน (ครั้ง)": cats[2], 
            "วันหยุดต่อเนื่อง 3 วัน (ครั้ง)": cats[3],
            "วันหยุดต่อเนื่อง 4 วัน (ครั้ง)": cats[4], 
            "วันหยุดต่อเนื่อง 5 วันขึ้นไป (ครั้ง)": cats["5วันขึ้นไป"]
        })
    st.table(pd.DataFrame(h_rows).set_index("ชื่อแพทย์"))
else:
    st.info("👈 กรุณากรอกปี พ.ศ. และเพิ่มรายชื่อแพทย์ที่แถบควบคุมด้านซ้ายเพื่อเริ่มต้นใช้งาน")
