import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
from fpdf import FPDF

# --- 1. CONFIG & FILENAMES ---
DATA_FILE = "ksd_master_final_v66.csv"
VE_FILE = "ksd_vehicles_final_v66.csv"
DR_FILE = "ksd_drivers_final_v66.csv"
SHOP_NAME = "K. SIRIWARDHANA SAND CONSTRUCTION PRO"

# --- 2. DATA ENGINE ---
def load_data(file, cols):
    if os.path.exists(file): 
        try:
            d = pd.read_csv(file, low_memory=False)
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
    cols = ["Date", "Category", "Entity", "Note", "Amount"]
    for c in cols: pdf.cell(38, 8, c, 1, 0, 'C')
    pdf.ln(); pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", '', 8)
    for _, row in data_df.iterrows():
        pdf.cell(38, 7, str(row['Date']), 1); pdf.cell(38, 7, str(row['Category']), 1); pdf.cell(38, 7, str(row['Entity']), 1)
        pdf.cell(38, 7, str(row['Note'])[:20], 1); pdf.cell(38, 7, f"{float(row['Amount']):,.2f}", 1, 0, 'R'); pdf.ln()
    fname = f"Report_{datetime.now().strftime('%H%M%S')}.pdf"
    pdf.output(fname); return fname

# --- 5. UI LAYOUT (v49 Structure) ---
st.set_page_config(page_title=SHOP_NAME, layout="wide", page_icon="🏗️")
st.sidebar.title("🏗️ KSD ERP v6.6")
main_sector = st.sidebar.selectbox("MAIN MENU", ["📊 Dashboard & Data Manager", "🏗️ Site Operations", "⛽ Finance & Shed", "⚙️ System Setup", "📑 Reports Center"])

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
            
            # ණය ගණනය කිරීම
            unpaid_fuel = df[(df["Category"] == "Fuel Entry") & (df["Status"] == "Unpaid")]["Amount"].sum()
            settled_payments = df[df["Category"] == "Shed Settle"]["Amount"].sum()
            current_debt = unpaid_fuel - settled_payments
            
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total Income", f"Rs. {ti:,.2f}"); m2.metric("Total Expenses", f"Rs. {te:,.2f}")
            m3.metric("Net Cashflow", f"Rs. {ti-te:,.2f}"); m4.metric("Shed Debt", f"Rs. {current_debt:,.2f}", delta_color="inverse")
            st.divider(); daily = df.groupby(['Date', 'Type'])['Amount'].sum().unstack().fillna(0); st.area_chart(daily)
        else: st.info("No data yet.")
    with t2:
        st.subheader("Edit/Delete Transactions")
        if not st.session_state.df.empty:
            for i, row in st.session_state.df.iloc[::-1].head(15).iterrows():
                c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
                c1.write(f"**{row['Date']}** | {row['Category']} ({row['Entity']})")
                c2.write(f"Rs. {float(row['Amount']):,.2f}"); c3.write(f"[{row['Status']}]")
                if c4.button("🗑️", key=f"del_{i}"):
                    st.session_state.df = st.session_state.df.drop(i); save_all(); st.rerun()

# --- 7. SITE OPERATIONS ---
elif main_sector == "🏗️ Site Operations":
    op = st.sidebar.radio("Activity", ["🚚 Stock In (Soil/Lorry)", "💰 Sales Out (Sand/Soil)", "🚜 Excavator Work Log"])
    v_list = st.session_state.ve_db["No"].tolist() if not st.session_state.ve_db.empty else ["N/A"]
    if op == "🚚 Stock In (Soil/Lorry)":
        with st.form("stk_f"):
            d, v = st.date_input("Date"), st.selectbox("Select Lorry", v_list)
            q, n = st.number_input("Cubes Received", step=0.5), st.text_input("Supplier/Note")
            if st.form_submit_button("Add Stock In"):
                new = pd.DataFrame([[len(st.session_state.df)+1, d, "", "Process", "Stock In", v, n, 0, q, 0, 0, "Done"]], columns=st.session_state.df.columns)
                st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()
    elif op == "💰 Sales Out (Sand/Soil)":
        with st.form("sale_f"):
            d, it = st.date_input("Date"), st.selectbox("Item", ["Sand Sale", "Soil Sale"])
            q, a = st.number_input("Cubes Sold", step=0.5), st.number_input("Amount Received")
            if st.form_submit_button("Record Sale"):
                new = pd.DataFrame([[len(st.session_state.df)+1, d, "", "Income", it, "Cash", "Sale Out", a, q, 0, 0, "Paid"]], columns=st.session_state.df.columns)
                st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()
    elif op == "🚜 Excavator Work Log":
        with st.form("mach_f"):
            v = st.selectbox("Select Excavator", st.session_state.ve_db[st.session_state.ve_db["Type"]=="Excavator"]["No"].tolist() if not st.session_state.ve_db.empty else ["N/A"])
            d, h = st.date_input("Date"), st.number_input("Hours Worked", step=0.5)
            n = st.text_input("Location/Note")
            if st.form_submit_button("Log Hours"):
                new = pd.DataFrame([[len(st.session_state.df)+1, d, "", "Process", "Work Hours", v, n, 0, 0, 0, h, "Done"]], columns=st.session_state.df.columns)
                st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()

# --- 8. FINANCE & SHED (Finalized) ---
elif main_sector == "⛽ Finance & Shed":
    fin_mode = st.sidebar.radio("Finance Options", ["⛽ Fuel & Shed", "💳 Settle Payment", "🔧 Repairs", "💸 Payroll", "🏦 Owner Advance", "🧾 Others"])
    v_list = st.session_state.ve_db["No"].tolist() if not st.session_state.ve_db.empty else ["N/A"]
    
    if fin_mode == "⛽ Fuel & Shed":
        st.subheader("Add Fuel Entry")
        with st.form("fuel_f"):
            d, v = st.date_input("Date"), st.selectbox("Vehicle", v_list)
            l, am = st.number_input("Liters", step=0.1), st.number_input("Amount (Rs.)")
            stt = st.selectbox("Status", ["Unpaid (Credit)", "Paid (Cash)"])
            nt = st.text_input("Shed Details")
            if st.form_submit_button("Save Fuel"):
                f_s = "Unpaid" if "Unpaid" in stt else "Paid"
                new = pd.DataFrame([[len(st.session_state.df)+1, d, "", "Expense", "Fuel Entry", v, f"Shed: {nt}", am, 0, l, 0, f_s]], columns=st.session_state.df.columns)
                st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()

    elif fin_mode == "💳 Settle Payment":
        st.subheader("Settle Shed Outstanding Debt")
        with st.form("set_f"):
            d, am = st.date_input("Date"), st.number_input("Amount Paid to Shed")
            ref = st.text_input("Payment Reference (e.g. Cheque/Slip No)")
            if st.form_submit_button("Confirm Payment"):
                new = pd.DataFrame([[len(st.session_state.df)+1, d, "", "Expense", "Shed Settle", "Shed", ref, am, 0, 0, 0, "Paid"]], columns=st.session_state.df.columns)
                st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()

    elif fin_mode == "🔧 Repairs":
        with st.form("rep"):
            d, v, n, a = st.date_input("Date"), st.selectbox("Vehicle", v_list), st.text_input("Repair Details"), st.number_input("Cost")
            if st.form_submit_button("Save Repair"):
                new = pd.DataFrame([[len(st.session_state.df)+1, d, "", "Expense", "Repair", v, n, a, 0, 0, 0, "Paid"]], columns=st.session_state.df.columns)
                st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()

    elif fin_mode == "💸 Payroll":
        with st.form("pay"):
            dr_names = st.session_state.dr_db["Name"].tolist() if not st.session_state.dr_db.empty else ["N/A"]
            d, dr = st.date_input("Date"), st.selectbox("Driver", dr_names)
            am, ty = st.number_input("Amount"), st.selectbox("Type", ["Salary", "Driver Advance", "Food"])
            v_rel = st.selectbox("Linked Vehicle", v_list)
            if st.form_submit_button("Save Payroll"):
                new = pd.DataFrame([[len(st.session_state.df)+1, d, "", "Expense", ty, v_rel, f"Driver: {dr}", am, 0, 0, 0, "Paid"]], columns=st.session_state.df.columns)
                st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()

    elif fin_mode == "🏦 Owner Advance":
        with st.form("own"):
            d, v, am, nt = st.date_input("Date"), st.selectbox("Owner/Vehicle", v_list), st.number_input("Amount"), st.text_input("Note")
            if st.form_submit_button("Save Advance"):
                new = pd.DataFrame([[len(st.session_state.df)+1, d, "", "Expense", "Owner Advance", v, nt, am, 0, 0, 0, "Paid"]], columns=st.session_state.df.columns)
                st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()

    elif fin_mode == "🧾 Others":
        with st.form("oth"):
            d, cat, nt, am = st.date_input("Date"), st.selectbox("Category", ["Food", "Rent", "Utility", "Misc"]), st.text_area("Note"), st.number_input("Amount")
            if st.form_submit_button("Save Other"):
                new = pd.DataFrame([[len(st.session_state.df)+1, d, "", "Expense", cat, "Admin", nt, am, 0, 0, 0, "Paid"]], columns=st.session_state.df.columns)
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
    r1, r2, r3 = st.tabs(["🚜 Vehicle Settlement", "⛽ Shed Report", "📑 Daily Log"])
    f_d, t_d = st.date_input("From", datetime.now().date()-timedelta(days=30)), st.date_input("To")
    df_f = st.session_state.df[(st.session_state.df["Date"] >= f_d) & (st.session_state.df["Date"] <= t_d)]
    
    with r1:
        v_list = st.session_state.ve_db["No"].tolist()
        if v_list:
            sel_ve = st.selectbox("Select Vehicle", v_list)
            v_rep = df_f[df_f["Entity"] == sel_ve]
            st.dataframe(v_rep, use_container_width=True)
            if st.button("Download PDF Statement"):
                fn = create_pdf(f"Settlement_{sel_ve}", v_rep, {"Vehicle": sel_ve, "Total Spent": v_rep[v_rep["Type"]=="Expense"]["Amount"].sum()})
                with open(fn, "rb") as f: st.download_button("📩 Download PDF", f, file_name=fn)

    with r2:
        st.subheader("Shed Debt Summary")
        unp = df_f[(df_f["Category"] == "Fuel Entry") & (df_f["Status"] == "Unpaid")]
        setl = df_f[df_f["Category"] == "Shed Settle"]
        c1, c2, c3 = st.columns(3)
        c1.metric("Credit Taken", f"Rs. {unp['Amount'].sum():,.2f}")
        c2.metric("Total Settled", f"Rs. {setl['Amount'].sum():,.2f}")
        c3.metric("Outstanding", f"Rs. {unp['Amount'].sum() - setl['Amount'].sum():,.2f}")
        st.write("---")
        st.write("Recent Settlements")
        st.dataframe(setl, use_container_width=True)

    with r3:
        st.dataframe(df_f, use_container_width=True)
