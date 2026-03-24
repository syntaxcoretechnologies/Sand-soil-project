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
    cols = ["Date", "Category", "Rate", "Qty/Hrs", "Amount"]
    for c in cols: pdf.cell(38, 8, c, 1, 0, 'C')
    pdf.ln(); pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", '', 8)
    for _, row in data_df.iterrows():
        pdf.cell(38, 7, str(row['Date']), 1); pdf.cell(38, 7, str(row['Category']), 1)
        r = float(row['Rate_At_Time']) if row['Rate_At_Time'] > 0 else 0
        q = row['Hours'] if row['Hours'] > 0 else (row['Qty_Cubes'] if row['Qty_Cubes'] > 0 else 0)
        a = float(row['Amount']) if row['Type'] == "Expense" else (q * r)
        pdf.cell(38, 7, f"{r:,.2f}", 1, 0, 'R'); pdf.cell(38, 7, f"{q}", 1, 0, 'C'); pdf.cell(38, 7, f"{a:,.2f}", 1, 0, 'R'); pdf.ln()
    fname = f"Report_{datetime.now().strftime('%H%M%S')}.pdf"
    pdf.output(fname); return fname

# --- 5. UI LAYOUT ---
st.set_page_config(page_title=SHOP_NAME, layout="wide", page_icon="🏗️")
st.sidebar.title("🏗️ KSD ERP v5.6")
main_sector = st.sidebar.selectbox("MAIN MENU", ["📊 Dashboard & Data Manager", "🏗️ Site Operations", "💰 Finance & Shed", "⚙️ System Setup", "📑 Reports Center"])
st.markdown(f"<h1 style='text-align: center; color: #E67E22;'>{main_sector}</h1>", unsafe_allow_html=True)

# --- 6. DASHBOARD & DATA MANAGER ---
if main_sector == "📊 Dashboard & Data Manager":
    t1, t2 = st.tabs(["📈 Analytics Dashboard", "🛠️ Manage Transactions"])
    with t1:
        df = st.session_state.df
        if not df.empty:
            df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
            ti = df[df["Type"] == "Income"]["Amount"].sum()
            te = df[df["Type"] == "Expense"]["Amount"].sum()
            f_debt = df[df["Category"] == "Fuel Entry"]["Amount"].sum() - df[df["Category"] == "Shed Payment"]["Amount"].sum()
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total Income", f"Rs. {ti:,.2f}"); m2.metric("Total Expenses", f"Rs. {te:,.2f}")
            m3.metric("Net Cashflow", f"Rs. {ti-te:,.2f}"); m4.metric("Shed Debt", f"Rs. {f_debt:,.2f}")
            st.divider(); daily = df.groupby(['Date', 'Type'])['Amount'].sum().unstack().fillna(0); st.area_chart(daily)
    with t2:
        if not st.session_state.df.empty:
            for i, row in st.session_state.df.iloc[::-1].head(15).iterrows():
                c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
                c1.write(f"**{row['Date']}** | {row['Category']} ({row['Entity']})")
                c2.write(f"Rs. {float(row['Amount']):,.2f}"); c3.write(f"Note: {row['Note']}")
                if c4.button("🗑️", key=f"del_{i}"):
                    st.session_state.df = st.session_state.df.drop(i); save_all(); st.rerun()

# --- 7. SITE OPERATIONS ---
elif main_sector == "🏗️ Site Operations":
    op = st.radio("Activity", ["🚛 Lorry Work Log", "🚜 Excavator Work Log", "💰 Sales Out (Sand/Soil)"], horizontal=True)
    v_list = st.session_state.ve_db["No"].tolist() if not st.session_state.ve_db.empty else ["N/A"]
    if op == "🚛 Lorry Work Log":
        with st.form("lorry_f"):
            v = st.selectbox("Select Lorry", st.session_state.ve_db[st.session_state.ve_db["Type"]=="Lorry"]["No"].tolist() if not st.session_state.ve_db.empty else ["N/A"])
            def_rate = st.session_state.ve_db[st.session_state.ve_db["No"]==v]["Rate_Per_Unit"].values[0] if v != "N/A" else 0.0
            d, q, n, r = st.date_input("Date"), st.number_input("Cubes Loaded", step=0.5), st.text_input("Trip Details"), st.number_input("Rate for this day", value=float(def_rate))
            if st.form_submit_button("Record Trip"):
                new = pd.DataFrame([[len(st.session_state.df)+1, d, "", "Process", "Lorry Work", v, n, 0, q, 0, 0, r, "Done"]], columns=st.session_state.df.columns)
                st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()
    elif op == "🚜 Excavator Work Log":
        with st.form("exc_f"):
            v = st.selectbox("Select Excavator", st.session_state.ve_db[st.session_state.ve_db["Type"]=="Excavator"]["No"].tolist() if not st.session_state.ve_db.empty else ["N/A"])
            def_rate = st.session_state.ve_db[st.session_state.ve_db["No"]==v]["Rate_Per_Unit"].values[0] if v != "N/A" else 0.0
            d, h, n, r = st.date_input("Date"), st.number_input("Hours Worked", step=0.5), st.text_input("Site Location"), st.number_input("Rate for this day", value=float(def_rate))
            if st.form_submit_button("Record Hours"):
                new = pd.DataFrame([[len(st.session_state.df)+1, d, "", "Process", "Work Hours", v, n, 0, 0, 0, h, r, "Done"]], columns=st.session_state.df.columns)
                st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()
    elif op == "💰 Sales Out (Sand/Soil)":
        with st.form("sale_f"):
            d, it, q, a = st.date_input("Date"), st.selectbox("Item", ["Sand Sale", "Soil Sale"]), st.number_input("Cubes"), st.number_input("Amount")
            if st.form_submit_button("Record Sale"):
                new = pd.DataFrame([[len(st.session_state.df)+1, d, "", "Income", it, "Cash", "Sales", a, q, 0, 0, 0, "Paid"]], columns=st.session_state.df.columns)
                st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()

# --- 8. FINANCE & SHED (FULL FIX) ---
elif main_sector == "💰 Finance & Shed":
    fin = st.sidebar.radio("Finance", ["⛽ Fuel & Shed", "🔧 Repairs", "💸 Payroll & Advance", "🏦 Owner Advances", "🧾 Others"])
    v_list = st.session_state.ve_db["No"].tolist() if not st.session_state.ve_db.empty else ["N/A"]
    
    if fin == "⛽ Fuel & Shed":
        t1, t2 = st.tabs(["⛽ Log Fuel Bill", "💳 Settle Shed Payments"])
        with t1:
            with st.form("fuel"):
                d, v, l, c = st.date_input("Date"), st.selectbox("Vehicle", v_list), st.number_input("Liters"), st.number_input("Cost")
                if st.form_submit_button("Save"):
                    new = pd.DataFrame([[len(st.session_state.df)+1, d, "", "Expense", "Fuel Entry", v, "Shed Bill", c, 0, l, 0, 0, "Pending"]], columns=st.session_state.df.columns)
                    st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()
        with t2:
            with st.form("shed_pay"):
                amt, ref = st.number_input("Amount Paid"), st.text_input("Reference")
                if st.form_submit_button("Record Payment"):
                    new = pd.DataFrame([[len(st.session_state.df)+1, datetime.now().date(), "", "Expense", "Shed Payment", "Shed", ref, amt, 0, 0, 0, 0, "Paid"]], columns=st.session_state.df.columns)
                    st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()
    
    elif fin == "🔧 Repairs":
        with st.form("rep"):
            d, v, nt, am = st.date_input("Date"), st.selectbox("Vehicle", v_list), st.text_input("Detail"), st.number_input("Cost")
            if st.form_submit_button("Save Repair"):
                new = pd.DataFrame([[len(st.session_state.df)+1, d, "", "Expense", "Repair", v, nt, am, 0, 0, 0, 0, "Paid"]], columns=st.session_state.df.columns)
                st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()
                
    elif fin == "💸 Payroll & Advance":
        with st.form("pay"):
            d = st.date_input("Date")
            dr = st.selectbox("Driver", st.session_state.dr_db["Name"].tolist() if not st.session_state.dr_db.empty else ["N/A"])
            am, ty, v_rel = st.number_input("Amount"), st.selectbox("Type", ["Driver Advance", "Salary"]), st.selectbox("Vehicle", v_list)
            if st.form_submit_button("Save"):
                new = pd.DataFrame([[len(st.session_state.df)+1, d, "", "Expense", ty, v_rel, f"Driver: {dr}", am, 0, 0, 0, 0, "Paid"]], columns=st.session_state.df.columns)
                st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()

    elif fin == "🏦 Owner Advances":
        with st.form("own_adv"):
            d, v, am, nt = st.date_input("Date"), st.selectbox("Vehicle", v_list), st.number_input("Advance Amount"), st.text_input("Note")
            if st.form_submit_button("Save Owner Advance"):
                new = pd.DataFrame([[len(st.session_state.df)+1, d, "", "Expense", "Owner Advance", v, nt, am, 0, 0, 0, 0, "Paid"]], columns=st.session_state.df.columns)
                st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()

    elif fin == "🧾 Others":
        with st.form("oth"):
            d, cat, nt, am = st.date_input("Date"), st.selectbox("Category", ["Food", "Rent", "Misc", "Utility"]), st.text_input("Note"), st.number_input("Amount")
            if st.form_submit_button("Save Other Expense"):
                new = pd.DataFrame([[len(st.session_state.df)+1, d, "", "Expense", cat, "Admin", nt, am, 0, 0, 0, 0, "Paid"]], columns=st.session_state.df.columns)
                st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()

# --- 9. SYSTEM SETUP ---
elif main_sector == "⚙️ System Setup":
    s1, s2 = st.tabs(["👷 Drivers", "🚜 Vehicles"])
    with s1:
        with st.form("dr"):
            n, p, s = st.text_input("Name"), st.text_input("Phone"), st.number_input("Daily Salary")
            if st.form_submit_button("Add Driver"):
                new = pd.DataFrame([[n,p,s]], columns=st.session_state.dr_db.columns)
                st.session_state.dr_db = pd.concat([st.session_state.dr_db, new], ignore_index=True); save_all(); st.rerun()
        st.table(st.session_state.dr_db)
    with s2:
        with st.form("ve"):
            v, t, r, o = st.text_input("Vehicle No"), st.selectbox("Type", ["Excavator", "Lorry"]), st.number_input("Rate"), st.text_input("Owner")
            if st.form_submit_button("Add Vehicle"):
                new = pd.DataFrame([[v,t,o,r]], columns=st.session_state.ve_db.columns)
                st.session_state.ve_db = pd.concat([st.session_state.ve_db, new], ignore_index=True); save_all(); st.rerun()
        st.table(st.session_state.ve_db)

# --- 10. REPORTS CENTER ---
elif main_sector == "📑 Reports Center":
    r1, r2, r3 = st.tabs(["🚜 Vehicle Settlement", "👷 Driver Summary", "📑 Daily Log"])
    f_d, t_d = st.date_input("From", datetime.now().date()-timedelta(days=30)), st.date_input("To")
    df_f = st.session_state.df[(st.session_state.df["Date"] >= f_d) & (st.session_state.df["Date"] <= t_d)]
    with r1:
        v_list = st.session_state.ve_db["No"].tolist()
        if v_list:
            sel_ve = st.selectbox("Select Vehicle", v_list)
            v_rep = df_f[df_f["Entity"] == sel_ve].copy()
            if not v_rep.empty:
                v_rep['Subtotal'] = (v_rep['Hours'] + v_rep['Qty_Cubes']) * v_rep['Rate_At_Time']
                g_pay = v_rep['Subtotal'].sum(); deduct = v_rep[v_rep["Type"] == "Expense"]["Amount"].sum(); net = g_pay - deduct
                c1, c2, c3 = st.columns(3)
                c1.metric("Gross Pay", f"Rs. {g_pay:,.2f}"); c2.metric("Expenses", f"Rs. {deduct:,.2f}"); c3.metric("NET TO OWNER", f"Rs. {net:,.2f}")
                st.dataframe(v_rep, use_container_width=True)
                if st.button("Download Vehicle PDF"):
                    fn = create_pdf(f"Settlement_{sel_ve}", v_rep, {"Vehicle": sel_ve, "Net": f"Rs. {net:,.2f}"})
                    with open(fn, "rb") as f: st.download_button("📩 Download PDF", f, file_name=fn)
    with r2:
        dr_list = st.session_state.dr_db["Name"].tolist()
        if dr_list:
            sel_dr = st.selectbox("Select Driver", dr_list)
            dr_rep = df_f[df_f["Note"].str.contains(f"Driver: {sel_dr}", case=False, na=False)]
            total_paid = dr_rep['Amount'].sum()
            st.metric(f"Total Paid to {sel_dr}", f"Rs. {total_paid:,.2f}")
            st.dataframe(dr_rep, use_container_width=True)
            if st.button("Download Driver PDF"):
                fn = create_pdf(f"Driver_{sel_dr}", dr_rep, {"Driver": sel_dr, "Total": f"Rs. {total_paid:,.2f}"})
                with open(fn, "rb") as f: st.download_button("📩 Download PDF", f, file_name=fn)
    with r3:
        st.dataframe(df_f, use_container_width=True)
