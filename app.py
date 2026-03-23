import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
from fpdf import FPDF

# --- 1. CONFIG & FILENAMES ---
DATA_FILE = "ksd_master_v50.csv"
VE_FILE = "ksd_vehicles_v50.csv"
DR_FILE = "ksd_drivers_v50.csv"
SHOP_NAME = "K. SIRIWARDHANA SAND CONSTRUCTION PRO"

# --- 2. DATA ENGINE ---
def load_data(file, cols):
    if os.path.exists(file): 
        try:
            d = pd.read_csv(file)
            if 'Date' in d.columns:
                d['Date'] = pd.to_datetime(d['Date']).dt.date
            return d
        except: return pd.DataFrame(columns=cols)
    return pd.DataFrame(columns=cols)

def save_all():
    st.session_state.df.to_csv(DATA_FILE, index=False)
    st.session_state.ve_db.to_csv(VE_FILE, index=False)
    st.session_state.dr_db.to_csv(DR_FILE, index=False)

# --- 3. SESSION STATE ---
if 'df' not in st.session_state:
    st.session_state.df = load_data(DATA_FILE, ["ID", "Date", "Time", "Type", "Category", "Entity", "Note", "Amount", "Qty_Cubes", "Fuel_Ltr", "Hours", "Status"])
if 've_db' not in st.session_state:
    st.session_state.ve_db = load_data(VE_FILE, ["No", "Type", "Owner", "Rate_Per_Unit"])
if 'dr_db' not in st.session_state:
    st.session_state.dr_db = load_data(DR_FILE, ["Name", "Phone", "Daily_Salary"])

# --- 4. PDF REPORT GENERATOR ---
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15); self.set_text_color(230, 126, 34) 
        self.cell(0, 10, SHOP_NAME, 0, 1, 'C'); self.ln(10)

def create_pdf(title, data_df, summary_dict):
    pdf = PDF(); pdf.add_page(); pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, f"STATEMENT: {title.upper()}", 1, 1, 'L')
    for k, v in summary_dict.items():
        pdf.set_font("Arial", 'B', 10); pdf.cell(60, 8, f"{k}:", 1); pdf.set_font("Arial", '', 10); pdf.cell(0, 8, f" {v}", 1, 1)
    pdf.ln(10); pdf.set_font("Arial", 'B', 9)
    cols = ["Date", "Category", "Note", "Qty/Hrs", "Amount"]
    for c in cols: pdf.cell(38, 8, c, 1, 0, 'C')
    pdf.ln(); pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", '', 8)
    for _, row in data_df.iterrows():
        pdf.cell(38, 7, str(row['Date']), 1); pdf.cell(38, 7, str(row['Category']), 1); pdf.cell(38, 7, str(row['Note'])[:20], 1)
        val = row['Hours'] if row['Hours'] > 0 else (row['Qty_Cubes'] if row['Qty_Cubes'] > 0 else "-")
        amt = float(row['Amount']) if not pd.isna(row['Amount']) else 0.0
        pdf.cell(38, 7, f"{val}", 1, 0, 'C'); pdf.cell(38, 7, f"{amt:,.2f}", 1, 0, 'R'); pdf.ln()
    fname = f"Report_{datetime.now().strftime('%H%M%S')}.pdf"
    pdf.output(fname); return fname

# --- 5. UI LAYOUT ---
st.set_page_config(page_title=SHOP_NAME, layout="wide")
st.sidebar.title("🏗️ KSD ERP v5.0")
main_sector = st.sidebar.selectbox("MAIN MENU", ["📊 Dashboard", "🏗️ Site Operations", "💰 Finance", "⚙️ Setup", "📑 Reports"])

st.markdown(f"<h1 style='text-align: center; color: #E67E22;'>{main_sector}</h1>", unsafe_allow_html=True)

# --- 6. DASHBOARD ---
if main_sector == "📊 Dashboard":
    df = st.session_state.df
    if not df.empty:
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
        ti, te = df[df["Type"] == "Income"]["Amount"].sum(), df[df["Type"] == "Expense"]["Amount"].sum()
        m1, m2, m3 = st.columns(3)
        m1.metric("Income", f"Rs. {ti:,.2f}"); m2.metric("Expense", f"Rs. {te:,.2f}"); m3.metric("Balance", f"Rs. {ti-te:,.2f}")
        st.divider(); st.area_chart(df.groupby(['Date', 'Type'])['Amount'].sum().unstack().fillna(0))
    else: st.info("No data yet.")

# --- 7. SITE OPERATIONS (UPDATED WITH LORRY LOG) ---
elif main_sector == "🏗️ Site Operations":
    op = st.radio("Select Activity", ["🚛 Lorry Work Log", "🚜 Excavator Work Log", "💰 Sand/Soil Sales"], horizontal=True)
    
    if op == "🚛 Lorry Work Log":
        with st.form("lorry_f"):
            v = st.selectbox("Select Lorry", st.session_state.ve_db[st.session_state.ve_db["Type"]=="Lorry"]["No"].tolist() if not st.session_state.ve_db.empty else ["N/A"])
            d = st.date_input("Date"); q = st.number_input("Cubes Loaded"); n = st.text_input("Trip Details/Destination")
            if st.form_submit_button("Record Lorry Trip"):
                new = pd.DataFrame([[len(st.session_state.df)+1, d, "", "Process", "Lorry Work", v, n, 0, q, 0, 0, "Done"]], columns=st.session_state.df.columns)
                st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()

    elif op == "🚜 Excavator Work Log":
        with st.form("exc_f"):
            v = st.selectbox("Select Excavator", st.session_state.ve_db[st.session_state.ve_db["Type"]=="Excavator"]["No"].tolist() if not st.session_state.ve_db.empty else ["N/A"])
            d = st.date_input("Date"); h = st.number_input("Hours Worked"); n = st.text_input("Site/Location")
            if st.form_submit_button("Record Machine Hours"):
                new = pd.DataFrame([[len(st.session_state.df)+1, d, "", "Process", "Work Hours", v, n, 0, 0, 0, h, "Done"]], columns=st.session_state.df.columns)
                st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()

    elif op == "💰 Sand/Soil Sales":
        with st.form("sale_f"):
            d = st.date_input("Date"); it = st.selectbox("Item", ["Sand Sale", "Soil Sale"]); q = st.number_input("Cubes"); a = st.number_input("Amount Paid")
            if st.form_submit_button("Record Sale"):
                new = pd.DataFrame([[len(st.session_state.df)+1, d, "", "Income", it, "Cash", "Sales", a, q, 0, 0, "Paid"]], columns=st.session_state.df.columns)
                st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()

# --- 8. FINANCE & SHED ---
elif main_sector == "💰 Finance":
    fin = st.sidebar.radio("Finance", ["⛽ Fuel & Shed", "🔧 Repairs", "💸 Payroll", "🏦 Owner Advances", "🧾 Others"])
    v_list = st.session_state.ve_db["No"].tolist()
    if fin == "⛽ Fuel & Shed":
        t1, t2 = st.tabs(["⛽ Log Fuel", "💳 Shed Payment"])
        with t1:
            with st.form("fuel"):
                d, v, l, c = st.date_input("Date"), st.selectbox("Vehicle", v_list), st.number_input("Liters"), st.number_input("Cost")
                if st.form_submit_button("Save"):
                    new = pd.DataFrame([[len(st.session_state.df)+1, d, "", "Expense", "Fuel Entry", v, "Shed Bill", c, 0, l, 0, "Pending"]], columns=st.session_state.df.columns)
                    st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()
        with t2:
            with st.form("spay"):
                amt = st.number_input("Amount"); ref = st.text_input("Ref")
                if st.form_submit_button("Record"):
                    new = pd.DataFrame([[len(st.session_state.df)+1, datetime.now().date(), "", "Expense", "Shed Payment", "Shed", ref, amt, 0, 0, 0, "Paid"]], columns=st.session_state.df.columns)
                    st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()
    elif fin == "💸 Payroll":
        with st.form("pay"):
            dr = st.selectbox("Driver", st.session_state.dr_db["Name"].tolist()); am = st.number_input("Amount"); ty = st.selectbox("Type", ["Driver Advance", "Salary"]); v_rel = st.selectbox("Vehicle", v_list)
            if st.form_submit_button("Save"):
                new = pd.DataFrame([[len(st.session_state.df)+1, datetime.now().date(), "", "Expense", ty, v_rel, f"Driver: {dr}", am, 0, 0, 0, "Paid"]], columns=st.session_state.df.columns)
                st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()
    elif fin == "🏦 Owner Advances":
        with st.form("own_adv"):
            v, am, nt = st.selectbox("Vehicle", v_list), st.number_input("Advance"), st.text_input("Note")
            if st.form_submit_button("Save"):
                new = pd.DataFrame([[len(st.session_state.df)+1, datetime.now().date(), "", "Expense", "Owner Advance", v, nt, am, 0, 0, 0, "Paid"]], columns=st.session_state.df.columns)
                st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()
    elif fin == "🔧 Repairs":
        with st.form("rep"):
            v, n, a = st.selectbox("Vehicle", v_list), st.text_input("Detail"), st.number_input("Cost")
            if st.form_submit_button("Save"):
                new = pd.DataFrame([[len(st.session_state.df)+1, datetime.now().date(), "", "Expense", "Repair", v, n, a, 0, 0, 0, "Paid"]], columns=st.session_state.df.columns)
                st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()
    elif fin == "🧾 Others":
        with st.form("oth"):
            cat, nt, am = st.selectbox("Cat", ["Food", "Misc"]), st.text_input("Note"), st.number_input("Amount")
            if st.form_submit_button("Save"):
                new = pd.DataFrame([[len(st.session_state.df)+1, datetime.now().date(), "", "Expense", cat, "Admin", nt, am, 0, 0, 0, "Paid"]], columns=st.session_state.df.columns)
                st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()

# --- 9. SYSTEM SETUP ---
elif main_sector == "⚙️ Setup":
    s1, s2 = st.tabs(["👷 Drivers", "🚜 Vehicles"])
    with s1:
        with st.form("dr"):
            n, p, s = st.text_input("Name"), st.text_input("Phone"), st.number_input("Salary")
            if st.form_submit_button("Add"):
                new = pd.DataFrame([[n,p,s]], columns=st.session_state.dr_db.columns)
                st.session_state.dr_db = pd.concat([st.session_state.dr_db, new], ignore_index=True); save_all(); st.rerun()
        st.table(st.session_state.dr_db)
    with s2:
        with st.form("ve"):
            v, t, r, o = st.text_input("No"), st.selectbox("Type", ["Excavator", "Lorry"]), st.number_input("Rate (Hr or Cube)"), st.text_input("Owner")
            if st.form_submit_button("Add"):
                new = pd.DataFrame([[v,t,o,r]], columns=st.session_state.ve_db.columns)
                st.session_state.ve_db = pd.concat([st.session_state.ve_db, new], ignore_index=True); save_all(); st.rerun()
        st.table(st.session_state.ve_db)

# --- 10. REPORTS CENTER (LORRY + EXCAVATOR LOGIC) ---
elif main_sector == "📑 Reports":
    st.subheader("Vehicle Settlement Report")
    v_list = st.session_state.ve_db["No"].tolist()
    if v_list:
        sel_ve = st.selectbox("Select Vehicle", v_list)
        f_d = st.date_input("From", datetime.now().date()-timedelta(days=30)); t_d = st.date_input("To")
        m_ve = st.session_state.ve_db[st.session_state.ve_db["No"] == sel_ve]
        v_type, rate = m_ve["Type"].values[0], m_ve["Rate_Per_Unit"].values[0]
        
        v_rep = st.session_state.df[(st.session_state.df["Entity"] == sel_ve) & (st.session_state.df["Date"]>=f_d) & (st.session_state.df["Date"]<=t_d)]
        
        if not v_rep.empty:
            units = v_rep[v_rep["Category"] == "Work Hours"]["Hours"].sum() if v_type == "Excavator" else v_rep[v_rep["Category"] == "Lorry Work"]["Qty_Cubes"].sum()
            label = "Total Hours" if v_type == "Excavator" else "Total Cubes"
            g_pay = units * rate
            deduct = v_rep[v_rep["Type"] == "Expense"]["Amount"].sum()
            net = g_pay - deduct
            
            c1, c2, c3 = st.columns(3)
            c1.metric(label, f"{units}"); c2.metric("Gross Pay", f"Rs. {g_pay:,.2f}"); c3.metric("NET BALANCE", f"Rs. {net:,.2f}")
            st.dataframe(v_rep[["Date", "Category", "Note", "Amount", "Qty_Cubes", "Hours"]], use_container_width=True)
            
            if st.button("Download PDF"):
                summary = {"Vehicle": sel_ve, label: units, "Rate": rate, "Gross": g_pay, "Net": net}
                fn = create_pdf(f"Settlement_{sel_ve}", v_rep, summary)
                with open(fn, "rb") as f: st.download_button("📩 Download", f, file_name=fn)
        else: st.info("No data.")
