import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import random
import collections
import json
import os

# ตั้งค่าหน้าจอและสไตล์
st.set_page_config(layout="wide", page_title="Medical Fair-Scheduler DB Pro")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;700&display=swap');
    html, body, [class*="css"], .stMarkdown, p, div, span, label { font-family: 'Sarabun', sans-serif !important; }
    th { border: 1px solid #000 !important; text-align: center !important; background-color: #f0f2f6; color: black !important; font-weight: bold; }
    td { border: 1px solid #000 !important; text-align: center !important; }
    .stDataFrame { font-size: 1.1rem; }
    </style>
""", unsafe_allow_html=True)

DB_FILE = "scheduler_db.json"

# --- SYSTEM DATABASE FUNCTIONS (ระบบบันทึกข้อมูลถาวร) ---
def load_from_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            # แปลงสติงวันที่กลับเป็น datetime object
            doctors = []
            for d in data.get("doctors", []):
                doctors.append({
                    "id": d["id"], "name": d["name"],
                    "start": datetime.strptime(d["start"], "%Y-%m-%d")
                })
                
            custom_holidays = {}
            for k, v in data.get("custom_holidays", {}).items():
                custom_holidays[datetime.strptime(k, "%Y-%m-%d")] = v
                
            case_records = {}
            for k, v in data.get("case_records", {}).items():
                case_records[k] = v
                
            return doctors, custom_holidays, case_records, data.get("selected_year", 2568)
        except:
            return [], {}, {}, 2568
    return [], {}, {}, 2568

def save_to_db():
    data = {
        "selected_year": st.session_state.selected_year,
        "doctors": [{
            "id": d["id"], "name": d["name"],
            "start": d["start"].strftime("%Y-%m-%d")
        } for d in st.session_state.doctors],
        "custom_holidays": {k.strftime("%Y-%m-%d"): v for k, v in st.session_state.all_active_holidays.items()},
        "case_records": st.session_state.case_records
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
db_docs, db_hols, db_cases, db_year = load_from_db()

if 'doctors' not in st.session_state: st.session_state.doctors = db_docs
if 'all_active_holidays' not in st.session_state: st.session_state.all_active_holidays = db_hols
if 'case_records' not in st.session_state: st.session_state.case_records = db_cases
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
        st.session_state.case_records = {}
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
    st.header("📅 วันหยุดพิเศษ")
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
    if not docs: return pd.DataFrame(), {}, {}, None, {}, []
    
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

        # ล็อค Seed ด้วยวันเวลา เพื่อรักษาเสถียรภาพอดีตไม่ให้เปลี่ยนชื่อ
        random.seed(int(curr.timestamp()))

        available_docs = sorted([d['name'] for d in docs if d['start'] <= curr])
        if not available_docs:
            curr += timedelta(days=1)
            continue

        h_text = all_h.get(curr, "")
        is_we = (curr.weekday() >= 5) or (h_text != "")
        score = 2 if is_we else 1
        day_type = "หยุด" if is_we else "ธรรมดา"

        sorted_by_load = sorted(available_docs, key=lambda x: (load_score[x], random.random()))
        v1 = sorted_by_load[0]
        v2 = sorted_by_load[1] if len(available_docs) > 1 else v1
        
        v3 = "-"
        if is_we or curr.weekday() == 4:
            v3_pool = [d for d in available_docs if d not in [v1, v2]]
            if v3_pool: v3 = random.choice(v3_pool)

        # บันทึกยอดเวร
        target_stats = stats_after if curr >= latest_start_date else stats_before
        target_stats[v1][f"โอพีดี({day_type})"] += 1
        target_stats[v2][f"วอร์ด({day_type})"] += 1
        load_score[v1] += score
        load_score[v2] += score
        if v3 != "-":
            target_stats[v3][f"ถปภ.({day_type})"] += 1
            load_score[v3] += score

        # จัดการค่าเคสและคำนวณรายได้ประจำวัน
        date_str = curr.strftime("%Y-%m-%d")
        record = st.session_state.case_records.get(date_str, {"in_time": 0, "out_time": 0, "ward_case": 0})
        
        # คำนวณค่าเวรวอร์ดพื้นฐาน
        base_ward_fee = 1200.0 if is_we else 600.0
        
        # คำนวณเงินจากเคสสะสมประจำตำแหน่ง
        fee_in = record["in_time"] * 5.0
        fee_out = record["out_time"] * 50.0
        fee_ward = record["ward_case"] * 50.0
        
        total_day_income = base_ward_fee + fee_in + fee_out + fee_ward

        data.append({
            "วันที่": format_thai_date(curr), "วัน": ["อาทิตย์","จันทร์","อังคาร","พุธ","พฤหัสบดี","ศุกร์","เสาร์"][curr.weekday()+1 if curr.weekday() != 6 else 0],
            "โอพีดี": v1, "วอร์ด": v2, "ถปภ.": v3, "หมายเหตุ": h_text,
            "เคสในเวลา": record["in_time"], "เคสนอกเวลา": record["out_time"], "เคสวอร์ด": record["ward_case"],
            "ค่าเวรรวม (บาท)": total_day_income,
            "is_h": is_we, "is_header": False, "raw_date": curr
        })
        curr += timedelta(days=1)

    # ค้นหากลุ่มเทศกาลวันหยุดยาว
    holiday_blocks, current_block = [], []
    curr = s_dt
    while curr <= e_dt:
        is_h = (curr.weekday() >= 5) or (curr in all_h)
        if is_h: current_block.append(curr)
        else:
            if len(current_block) >= 2: holiday_blocks.append(current_block)
            current_block = []
        curr += timedelta(days=1)
    if len(current_block) >= 2: holiday_blocks.append(current_block)

    hol_stats = {n: {2:0, 3:0, 4:0, "5+":0} for n in doc_names}
    df_clean = pd.DataFrame([r for r in data if not r.get("is_header")])
    
    if not df_clean.empty:
        for block in holiday_blocks:
            length = len(block)
            cat = length if length in [2, 3, 4] else "5+"
            for day in block:
                day_rows = df_clean[df_clean["raw_date"] == day]
                if not day_rows.empty:
                    row = day_rows.iloc[0]
                    assigned = [row["โอพีดี"], row["วอร์ด"], row["ถปภ."]]
                    for n in doc_names:
                        if n in assigned: hol_stats[n][cat] += 1

    return pd.DataFrame(data), stats_before, stats_after, latest_start_date, hol_stats, data

# --- MAIN UI DISPLAY ---
st.title(f"🏥 ตารางเวรและบัญชีค่าตอบแทน พ.ศ. {st.session_state.selected_year}")

if st.session_state.doctors:
    df, s_before, s_after, l_start, hol_stats, raw_data_list = generate_schedule()

    # --- ส่วนที่ 1: คีย์บันทึกเคสรายวัน (จำลองจากภาพที่ 2) ---
    with st.expander("📝 คลิกเพื่อกรอกจำนวนเคสประจำวัน"):
        valid_dates = [r["raw_date"] for r in raw_data_list if not r["is_header"]]
        target_date = st.date_input("เลือกวันที่ต้องการบันทึกเคส", value=valid_dates[0], min_value=min(valid_dates), max_value=max(valid_dates))
        
        t_str = target_date.strftime("%Y-%m-%d")
        exist = st.session_state.case_records.get(t_str, {"in_time": 0, "out_time": 0, "ward_case": 0})
        
        col_c1, col_c2, col_c3 = st.columns(3)
        c_in = col_c1.number_input("เคสในเวลา (5.-)", 0, 1000, int(exist["in_time"]))
        c_out = col_c2.number_input("เคสนอกเวลา (50.-)", 0, 1000, int(exist["out_time"]))
        c_ward = col_c3.number_input("เคสวอร์ด (50.-)", 0, 1000, int(exist["ward_case"]))
        
        if st.button("💾 บันทึกสถิติเคสและอัปเดตบัญชีรายได้", use_container_width=True):
            st.session_state.case_records[t_str] = {"in_time": c_in, "out_time": c_out, "ward_case": c_ward}
            save_to_db()
            st.toast("บันทึกข้อมูลเรียบร้อยแล้วและทำการคำนวณบัญชีใหม่!", icon="💰")
            st.rerun()

    # แสดงผลตารางใหญ่
    def style_row(row):
        if row.get('is_header'): return ['background-color: #B2EBF2; color: black; font-weight: bold; border: 1px solid black;'] * len(row)
        return [f"background-color: {'#FFCDD2' if row.get('is_h') else 'white'}; color: black; border: 1px solid black; font-weight: bold;"] * len(row)

    show_cols = ["วันที่", "วัน", "โอพีดี", "วอร์ด", "ถปภ.", "หมายเหตุ", "เคสในเวลา", "เคสนอกเวลา", "เคสวอร์ด", "ค่าเวรรวม (บาท)"]
    st.dataframe(df.style.apply(style_row, axis=1).hide(axis='columns', subset=[c for c in df.columns if c not in show_cols]), height=500, use_container_width=True)

    # ฟังก์ชันช่วยจัดรูปแบบโครงสร้างพร้อมช่องผลรวมสุทธิ
    def build_summary_table(stats_dict):
        res_df = pd.DataFrame.from_dict(stats_dict, orient='index').fillna(0).astype(int)
        if res_df.empty: return res_df
        res_df["รวมเวรธรรมดา"] = res_df["โอพีดี(ธรรมดา)"] + res_df["วอร์ด(ธรรมดา)"] + res_df["ถปภ.(ธรรมดา)"]
        res_df["รวมเวรวันหยุด"] = res_df["โอพีดี(หยุด)"] + res_df["วอร์ด(หยุด)"] + res_df["ถปภ.(หยุด)"]
        res_df["รวมเวรทั้งหมด"] = res_df["รวมเวรธรรมดา"] + res_df["รวมเวรวันหยุด"]
        return res_df[["โอพีดี(ธรรมดา)", "วอร์ด(ธรรมดา)", "ถปภ.(ธรรมดา)", "รวมเวรธรรมดา", "โอพีดี(หยุด)", "วอร์ด(หยุด)", "ถปภ.(หยุด)", "รวมเวรวันหยุด", "รวมเวรทั้งหมด"]]

    # --- ตารางสรุปจำนวนเวรแยกช่วงเวลา (ภาพที่ 7) ---
    st.divider()
    st.header("📊 ตารางสรุปจำนวนเวรแยกช่วงเวลา (ภาษาไทยพร้อมช่องรวมสรุป)")
    
    st.subheader(f"1. ช่วงแรก (ก่อนแพทย์คนล่าสุดเริ่มงาน : ก่อน {format_thai_date(l_start)})")
    df_b = build_summary_table(s_before)
    if not df_b.empty: st.table(df_b)

    st.subheader(f"2. ช่วงสมบูรณ์ (เริ่มคำนวณปรับสมดุลเวรใหม่ : ตั้งแต่ {format_thai_date(l_start)})")
    df_a = build_summary_table(s_after)
    if not df_a.empty: st.table(df_a)

    # --- ส่วนที่เพิ่มตามต้องการ: สรุปภาระงานรวมทั้งปี (เส้นเขียวภาพที่ 7) ---
    st.subheader("🟢 3. สรุปภาระงานรวมทั้งหมดตลอดทั้งปี (ตาราง 1 + ตาราง 2)")
    if not df_b.empty and not df_a.empty:
        df_total = df_b.add(df_a, fill_value=0).astype(int)
        st.table(df_total)

    # --- ตารางรวมสรุปรายได้สะสมของแพทย์รายเดือน ---
    st.divider()
    st.header("💰 บัญชีสรุปยอดเงินรายได้รวมของแพทย์แต่ละคน")
    clean_rows = [r for r in raw_data_list if not r["is_header"]]
    income_map = {d["name"]: 0.0 for d in st.session_state.doctors}
    
    for r in clean_rows:
        income_map[r["โอพีดี"]] += r["ค่าเวรรวม (บาท)"] - (1200.0 if r["is_h"] else 600.0) # แยกปันผลเฉพาะค่าเคสและเวรส่วนตน
        income_map[r["วอร์ด"]] += (1200.0 if r["is_h"] else 600.0) # วอร์ดได้ค่าเวรหลักประจำวัน
        if r["ถปภ."] != "-":
            income_map[r["ถปภ."]] += 300.0 # สมมติฐานค่าเวรเสริมของถปภ.
            
    inc_df = pd.DataFrame.from_dict(income_map, orient='index', columns=["ประมาณการรายได้รวมทั้งปี (บาท)"])
    st.table(inc_df.style.format("{:,.2f}"))

    # --- ตารางวิเคราะห์เทศกาลวันหยุดราชการต่อเนื่อง ---
    st.divider()
    st.header("🏖️ ตารางสรุปการทำงานช่วงวันหยุดยาวราชการ (จำนวนวันที่โดนสุ่มให้มาเข้าเวร)")
    h_rows = []
    for name, cats in hol_stats.items():
        h_rows.append({
            "ชื่อแพทย์": name, "ช่วงหยุดยาว 2 วัน (วัน)": cats[2], "ช่วงหยุดยาว 3 วัน (วัน)": cats[3],
            "ช่วงหยุดยาว 4 วัน (วัน)": cats[4], "ช่วงหยุดยาว 5 วันขึ้นไป (วัน)": cats["5+"],
            "รวมวันหยุดยาวที่ต้องทำงาน (วัน)": cats[2] + cats[3] + cats[4] + cats["5+"]
        })
    st.table(pd.DataFrame(h_rows).set_index("ชื่อแพทย์"))
else:
    st.info("👈 กรุณากรอกปี พ.ศ. และเพิ่มรายชื่อแพทย์ที่แถบควบคุมด้านซ้ายเพื่อเปิดฐานข้อมูล")
