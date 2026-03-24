import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
from fpdf import FPDF

# --- 1. CONFIG & FILENAMES ---
DATA_FILE = "ksd_master_v56.csv"
VE_FILE = "ksd_vehicles_v56.csv"
DR_FILE = "ksd_drivers_v56.csv"
SHOP_NAME = "K. SIRIWARDHANA SAND CONSTRUCTION PRO"

# --- 2. DATA ENGINE ---
def load_data(file, cols):
    if os.path.exists(file): 
        try:
            d = pd.read_csv(file)
            if 'Date' in d.columns:
                d['Date'] = pd.to_datetime(d['Date']).dt.date
            for col in cols:
                if col not in d.columns: d[col] = 0
            return d
        except: return pd.DataFrame(columns=cols)
    return pd.DataFrame(columns=cols)

def save_all():
    st.session_state.df.to_csv(DATA_FILE, index=False)
    st.session_state.ve_db.to_csv(VE_FILE, index=False)
    st.session_state.dr_db.to_csv(DR_FILE, index=False)

# --- 3. SESSION STATE ---
cols_master = ["ID", "Date", "Time", "Type", "Category", "Entity", "Note", "Amount", "Qty_Cubes", "Fuel_Ltr", "Hours", "Rate_At_Time", "Status"]
if 'df' not in st.session_state:
    st.session_state.df = load_data(DATA_FILE, cols_master)
if 've_db' not in st.session_state:
    st.session_state.ve_db = load_data(VE_FILE, ["No", "Type", "Owner", "Rate_Per_Unit"])
if 'dr_db' not in st.session_state:
    st.session_state.dr_db = load_data(DR_FILE, ["Name", "Phone", "Daily_Salary"])

# --- 4. PDF REPORT GENERATOR (AS PER YOUR PDF) ---
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15); self.set_text_color(230, 126, 34) 
        self.cell(0, 10, SHOP_NAME, 0, 1, 'C'); self.ln(5)

def create_pdf(title, data_df, summary_dict):
    pdf = PDF(); pdf.add_page(); pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, f"STATEMENT: {title.upper()}", 1, 1, 'L'); pdf.ln(2)
    
    # Summary Section (Top part of your PDF)
    for k, v in summary_dict.items():
        pdf.set_font("Arial", 'B', 10); pdf.cell(50, 8, f"{k}:", 1)
        pdf.set_font("Arial", '', 10); pdf.cell(0, 8, f" {v}", 1, 1)
    
    pdf.ln(8); pdf.set_font("Arial", 'B', 9)
    # Table Header
    cols = ["Date", "Category", "Note", "Qty/Hrs", "Amount"]
    w = [25, 35, 65, 25, 40]
    for i, c in enumerate(cols): pdf.cell(w[i], 8, c, 1, 0, 'C')
    pdf.ln(); pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", '', 8)
    
    total_exp = 0
    for _, row in data_df.iterrows():
        pdf.cell(w[0], 7, str(row['Date']), 1)
        pdf.cell(w[1], 7, str(row['Category']), 1)
        pdf.cell(w[2], 7, str(row['Note'])[:40], 1)
        qty = row['Hours'] if row['Hours'] > 0 else (row['Qty_Cubes'] if row['Qty_Cubes'] > 0 else "-")
        pdf.cell(w[3], 7, f"{qty}", 1, 0, 'C')
        amt = float(row['Amount']) if row['Type'] == "Expense" else 0.0
        total_exp += amt
        pdf.cell(w[4], 7, f"{amt:,.2f}", 1, 0, 'R'); pdf.ln()
    
    pdf.set_font("Arial", 'B', 9); pdf.cell(sum(w[:4]), 10, "GRAND TOTAL (EXPENSES)", 1, 0, 'R')
    pdf.cell(w[4], 10, f"Rs. {total_exp:,.2f}", 1, 1, 'R')
    fn = f"Report_{datetime.now().strftime('%H%M%S')}.pdf"; pdf.output(fn); return fn

# --- 5. UI LAYOUT ---
st.set_page_config(page_title=SHOP_NAME, layout="wide")
st.sidebar.title("🏗️ KSD ERP v5.6")
menu = st.sidebar.selectbox("MAIN MENU", ["📊 Dashboard", "🏗️ Site Operations", "💰 Finance & Shed", "⚙️ System Setup", "📑 Reports Center"])

# --- 6. DASHBOARD ---
if menu == "📊 Dashboard":
    df = st.session_state.df
    if not df.empty:
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
        ti, te = df[df["Type"] == "Income"]["Amount"].sum(), df[df["Type"] == "Expense"]["Amount"].sum()
        f_debt = df[df["Category"] == "Fuel Entry"]["Amount"].sum() - df[df["Category"] == "Shed Payment"]["Amount"].sum()
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Income", f"Rs. {ti:,.2f}"); m2.metric("Expenses", f"Rs. {te:,.2f}"); m3.metric("Net", f"Rs. {ti-te:,.2f}"); m4.metric("Shed Debt", f"Rs. {f_debt:,.2f}")
        st.divider(); st.area_chart(df.groupby(['Date', 'Type'])['Amount'].sum().unstack().fillna(0))

# --- 7. SITE OPERATIONS ---
elif menu == "🏗️ Site Operations":
    op = st.radio("Activity", ["🚛 Lorry Log", "🚜 Excavator Log", "💰 Sales Out"], horizontal=True)
    v_list = st.session_state.ve_db["No"].tolist() if not st.session_state.ve_db.empty else ["N/A"]
    with st.form("site_f"):
        v = st.selectbox("Vehicle", v_list)
        def_rate = st.session_state.ve_db[st.session_state.ve_db["No"]==v]["Rate_Per_Unit"].values[0] if v != "N/A" else 0.0
        d, val, r, n = st.date_input("Date"), st.number_input("Qty", step=0.5), st.number_input("Rate (Dynamic)", value=float(def_rate)), st.text_input("Note")
        if st.form_submit_button("Save"):
            q, h = (val, 0) if "Lorry" in op else (0, val)
            new = pd.DataFrame([[len(st.session_state.df)+1, d, "", "Process", op, v, n, 0, q, 0, h, r, "Done"]], columns=st.session_state.df.columns)
            st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()

# --- 8. FINANCE & SHED (FULL v56) ---
elif menu == "💰 Finance & Shed":
    fin = st.radio("Finance Category", ["⛽ Fuel & Shed", "🔧 Repairs", "💸 Payroll", "🏦 Owner Advance", "🧾 Others"], horizontal=True)
    v_list = st.session_state.ve_db["No"].tolist() if not st.session_state.ve_db.empty else ["N/A"]
    
    if fin == "⛽ Fuel & Shed":
        f1, f2 = st.tabs(["⛽ Fuel Entry", "💳 Shed Payment"])
        with f1:
            with st.form("fuel"):
                d, v, l, c = st.date_input("Date"), st.selectbox("Vehicle", v_list), st.number_input("Liters"), st.number_input("Cost")
                if st.form_submit_button("Save Fuel"):
                    new = pd.DataFrame([[len(st.session_state.df)+1, d, "", "Expense", "Fuel Entry", v, "Shed", c, 0, l, 0, 0, "Pending"]], columns=st.session_state.df.columns)
                    st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()
        with f2:
            with st.form("shed_p"):
                am, ref = st.number_input("Amount Paid to Shed"), st.text_input("Ref")
                if st.form_submit_button("Record Shed Settlement"):
                    new = pd.DataFrame([[len(st.session_state.df)+1, datetime.now().date(), "", "Expense", "Shed Payment", "Shed", ref, am, 0, 0, 0, 0, "Paid"]], columns=st.session_state.df.columns)
                    st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()

    elif fin == "🔧 Repairs":
        with st.form("rep"):
            d, v, am, nt = st.date_input("Date"), st.selectbox("Vehicle", v_list), st.number_input("Cost"), st.text_input("Detail")
            if st.form_submit_button("Save Repair"):
                new = pd.DataFrame([[len(st.session_state.df)+1, d, "", "Expense", "Repair", v, nt, am, 0, 0, 0, 0, "Paid"]], columns=st.session_state.df.columns)
                st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()

    elif fin == "💸 Payroll":
        with st.form("pay"):
            dr = st.selectbox("Driver", st.session_state.dr_db["Name"].tolist() if not st.session_state.dr_db.empty else ["N/A"])
            am, ty, v_rel = st.number_input("Amount"), st.selectbox("Type", ["Driver Advance", "Salary"]), st.selectbox("Vehicle", v_list)
            if st.form_submit_button("Save Pay"):
                new = pd.DataFrame([[len(st.session_state.df)+1, datetime.now().date(), "", "Expense", ty, v_rel, f"Driver: {dr}", am, 0, 0, 0, 0, "Paid"]], columns=st.session_state.df.columns)
                st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()

    elif fin == "🏦 Owner Advance":
        with st.form("own"):
            d, v, am, nt = st.date_input("Date"), st.selectbox("Vehicle", v_list), st.number_input("Amount"), st.text_input("Note")
            if st.form_submit_button("Save Owner Adv"):
                new = pd.DataFrame([[len(st.session_state.df)+1, d, "", "Expense", "Owner Advance", v, nt, am, 0, 0, 0, 0, "Paid"]], columns=st.session_state.df.columns)
                st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()

    elif fin == "🧾 Others":
        with st.form("oth"):
            d, cat, nt, am = st.date_input("Date"), st.selectbox("Cat", ["Food", "Rent", "Misc"]), st.text_input("Note"), st.number_input("Amount")
            if st.form_submit_button("Save"):
                new = pd.DataFrame([[len(st.session_state.df)+1, d, "", "Expense", cat, "Admin", nt, am, 0, 0, 0, 0, "Paid"]], columns=st.session_state.df.columns)
                st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()

# --- 9. SETUP ---
elif menu == "⚙️ System Setup":
    t1, t2 = st.tabs(["Drivers", "Vehicles"])
    with t1:
        with st.form("dr"):
            n, p, s = st.text_input("Name"), st.text_input("Phone"), st.number_input("Salary")
            if st.form_submit_button("Add"):
                st.session_state.dr_db = pd.concat([st.session_state.dr_db, pd.DataFrame([[n,p,s]], columns=st.session_state.dr_db.columns)], ignore_index=True); save_all(); st.rerun()
        st.table(st.session_state.dr_db)
    with t2:
        with st.form("ve"):
            v, t, r, o = st.text_input("No"), st.selectbox("Type", ["Lorry", "Excavator"]), st.number_input("Rate"), st.text_input("Owner")
            if st.form_submit_button("Add"):
                st.session_state.ve_db = pd.concat([st.session_state.ve_db, pd.DataFrame([[v,t,o,r]], columns=st.session_state.ve_db.columns)], ignore_index=True); save_all(); st.rerun()
        st.table(st.session_state.ve_db)

# --- 10. REPORTS CENTER ---
elif menu == "📑 Reports Center":
    f_d, t_d = st.date_input("From", datetime.now().date()-timedelta(days=30)), st.date_input("To")
    df_f = st.session_state.df[(st.session_state.df["Date"] >= f_d) & (st.session_state.df["Date"] <= t_d)]
    sel_ve = st.selectbox("Vehicle", st.session_state.ve_db["No"].tolist() if not st.session_state.ve_db.empty else [])
    if sel_ve:
        v_rep = df_f[df_f["Entity"] == sel_ve].copy()
        if not v_rep.empty:
            v_rep['Earnings'] = (v_rep['Hours'] + v_rep['Qty_Cubes']) * v_rep['Rate_At_Time']
            gross = v_rep['Earnings'].sum(); deduct = v_rep[v_rep["Type"] == "Expense"]["Amount"].sum(); net = gross - deduct
            st.metric("Net Settlement", f"Rs. {net:,.2f}")
            if st.button("Download PDF"):
                summary = {"Vehicle": sel_ve, "Total Qty": (v_rep['Hours']+v_rep['Qty_Cubes']).sum(), "Gross": f"{gross:,.2f}", "Net": f"{net:,.2f}"}
                fn = create_pdf(f"Settlement_{sel_ve}", v_rep, summary)
                with open(fn, "rb") as f: st.download_button("📩 Download PDF", f, file_name=fn)
