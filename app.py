import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
from fpdf import FPDF

# --- 1. CONFIG & FILENAMES ---
DATA_FILE = "ksd_master_final_v40.csv"
VE_FILE = "ksd_vehicles_final_v40.csv"
DR_FILE = "ksd_drivers_final_v40.csv"
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
    st.session_state.ve_db = load_data(VE_FILE, ["No", "Type", "Owner", "Current_Driver"])
if 'dr_db' not in st.session_state:
    st.session_state.dr_db = load_data(DR_FILE, ["Name", "Phone", "Daily_Salary"])

# --- 4. PDF GENERATOR ---
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.set_text_color(230, 126, 34) 
        self.cell(0, 10, SHOP_NAME, 0, 1, 'C')
        self.ln(10)

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
        val = row['Qty_Cubes'] if row['Qty_Cubes'] > 0 else (row['Hours'] if row['Hours'] > 0 else "-")
        amt = float(row['Amount']) if not pd.isna(row['Amount']) else 0.0
        pdf.cell(38, 7, f"{val}", 1, 0, 'C'); pdf.cell(38, 7, f"{amt:,.2f}", 1, 0, 'R'); pdf.ln()
    fname = f"Report_{datetime.now().strftime('%H%M%S')}.pdf"
    pdf.output(fname); return fname

# --- 5. UI LAYOUT ---
st.set_page_config(page_title=SHOP_NAME, layout="wide", page_icon="🏗️")
st.sidebar.title("🏗️ KSD ERP v4.0")
main_sector = st.sidebar.selectbox("MAIN MENU", ["📊 Dashboard", "🏗️ Site Operations", "💰 Finance & Shed", "⚙️ System Setup", "📑 Reports Center"])

st.markdown(f"<h1 style='text-align: center; color: #E67E22;'>{main_sector}</h1>", unsafe_allow_html=True)

# --- 6. DASHBOARD ---
if main_sector == "📊 Dashboard":
    df = st.session_state.df
    if not df.empty:
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
        ti = df[df["Type"] == "Income"]["Amount"].sum()
        te = df[df["Type"] == "Expense"]["Amount"].sum()
        f_debt = df[df["Category"] == "Fuel Entry"]["Amount"].sum() - df[df["Category"] == "Shed Payment"]["Amount"].sum()
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Income", f"Rs. {ti:,.2f}")
        m2.metric("Total Expenses", f"Rs. {te:,.2f}")
        m3.metric("Net Cashflow", f"Rs. {ti-te:,.2f}")
        m4.metric("Shed Debt", f"Rs. {f_debt:,.2f}")
        
        st.divider()
        st.subheader("Recent Transactions")
        st.dataframe(df.iloc[::-1].head(15), use_container_width=True)
    else: st.info("No data yet. Go to Site Operations or Finance to add records.")

# --- 7. SITE OPERATIONS (INCOME & PERFORMANCE) ---
elif main_sector == "🏗️ Site Operations":
    op = st.sidebar.radio("Activity", ["💰 Sales Out (Sand/Soil)", "🚜 Machine Work (Income)", "🚚 Stock In (Soil)", "🚛 Lorry Trips"])
    
    if op == "💰 Sales Out (Sand/Soil)":
        with st.form("sale_f"):
            d = st.date_input("Date"); it = st.selectbox("Item", ["Sand Sale", "Soil Sale"]); q = st.number_input("Cubes"); a = st.number_input("Amount")
            if st.form_submit_button("Record Sale"):
                new = pd.DataFrame([[len(st.session_state.df)+1, d, "", "Income", it, "Cash", "Sale Out", a, q, 0, 0, "Paid"]], columns=st.session_state.df.columns)
                st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()

    elif op == "🚜 Machine Work (Income)":
        st.subheader("Record External Work/Income from Machines")
        with st.form("mach_inc"):
            d = st.date_input("Date")
            exs = st.session_state.ve_db[st.session_state.ve_db["Type"]=="Excavator"]["No"].tolist()
            sel = st.selectbox("Select Excavator", exs if exs else ["None"])
            h = st.number_input("Hours Worked"); a = st.number_input("Total Income Amount"); n = st.text_input("Note (Location/Client)")
            if st.form_submit_button("Log Machine Income"):
                new = pd.DataFrame([[len(st.session_state.df)+1, d, "", "Income", "Machine Work", sel, n, a, 0, 0, h, "Done"]], columns=st.session_state.df.columns)
                st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()

    elif op == "🚛 Lorry Trips":
        st.subheader("Log Lorry Trip Expenses")
        with st.form("lr_f"):
            lrs = st.session_state.ve_db[st.session_state.ve_db["Type"]=="Lorry"]["No"].tolist()
            sel = st.selectbox("Select Lorry", lrs if lrs else ["None"]); d_lr = st.date_input("Date"); q = st.number_input("Cubes"); am = st.number_input("Hire/Transport Cost"); nt = st.text_input("Trip Details")
            if st.form_submit_button("Log Lorry Trip"):
                new = pd.DataFrame([[len(st.session_state.df)+1, d_lr, "", "Expense", "Lorry Trip", sel, nt, am, q, 0, 0, "Done"]], columns=st.session_state.df.columns)
                st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()

# --- 8. FINANCE & SHED (EXPENSES) ---
elif main_sector == "💰 Finance & Shed":
    fin = st.sidebar.radio("Finance", ["⛽ Fuel & Shed", "🔧 Repairs", "💸 Payroll", "🧾 Others"])
    
    if fin == "⛽ Fuel & Shed":
        t1, t2 = st.tabs(["Log Fuel", "Settle Shed"])
        with t1:
            with st.form("fuel"):
                v = st.selectbox("Vehicle", st.session_state.ve_db["No"].tolist()); c = st.number_input("Bill Cost"); s = st.text_input("Shed")
                if st.form_submit_button("Save"):
                    new = pd.DataFrame([[len(st.session_state.df)+1, datetime.now().date(), "", "Expense", "Fuel Entry", v, f"Shed: {s}", c, 0, 0, 0, "Pending"]], columns=st.session_state.df.columns)
                    st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()
        with t2:
            with st.form("shed_p"):
                amt = st.number_input("Amount Paid"); ref = st.text_input("Ref")
                if st.form_submit_button("Settle"):
                    new = pd.DataFrame([[len(st.session_state.df)+1, datetime.now().date(), "", "Expense", "Shed Payment", "Shed", ref, amt, 0, 0, 0, "Paid"]], columns=st.session_state.df.columns)
                    st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()

    elif fin == "💸 Payroll":
        with st.form("pay"):
            dr = st.selectbox("Driver", st.session_state.dr_db["Name"].tolist()); am = st.number_input("Amount"); ty = st.selectbox("Type", ["Advance", "Salary"])
            if st.form_submit_button("Save Payroll"):
                new = pd.DataFrame([[len(st.session_state.df)+1, datetime.now().date(), "", "Expense", ty, dr, "Payroll", am, 0, 0, 0, "Paid"]], columns=st.session_state.df.columns)
                st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()

# --- 9. SYSTEM SETUP ---
elif main_sector == "⚙️ System Setup":
    st.subheader("Manage Resources")
    # (එයාගේ පරණ code එකේ තිබ්බ Setup logic එකමයි - Drivers & Vehicles ඇතුළත් කිරීම)
    # ... (මෙතන drivers/vehicles add කරන table ටික තියෙනවා)

# --- 10. REPORTS CENTER (THE PROFIT/LOSS UPDATE) ---
elif main_sector == "📑 Reports Center":
    st.subheader("Vehicle Profit/Loss Statement")
    v_list = st.session_state.ve_db["No"].tolist()
    sel_ve = st.selectbox("Select Vehicle", v_list)
    f = st.date_input("From", datetime.now().date()-timedelta(days=30)); t = st.date_input("To")
    
    rep_df = st.session_state.df[(st.session_state.df["Date"]>=f) & (st.session_state.df["Date"]<=t) & (st.session_state.df["Entity"] == sel_ve)]
    
    if not rep_df.empty:
        total_income = rep_df[rep_df["Type"] == "Income"]["Amount"].sum()
        total_diesel = rep_df[rep_df["Category"] == "Fuel Entry"]["Amount"].sum()
        total_repairs = rep_df[rep_df["Category"] == "Repair"]["Amount"].sum()
        total_advances = rep_df[rep_df["Category"] == "Advance"]["Amount"].sum()
        
        balance = total_income - (total_diesel + total_repairs + total_advances)
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Gross Income", f"Rs. {total_income:,.2f}")
        c2.metric("Fuel/Diesel", f"- Rs. {total_diesel:,.2f}")
        c3.metric("Repair/Adv", f"- Rs. {total_repairs + total_advances:,.2f}")
        c4.metric("NET BALANCE", f"Rs. {balance:,.2f}", delta=float(balance))
        
        st.table(rep_df[["Date", "Category", "Note", "Hours", "Amount"]])
        
        if st.button("Generate Statement PDF"):
            summary = {"Vehicle": sel_ve, "Gross": f"Rs. {total_income:,.2f}", "Diesel": f"Rs. {total_diesel:,.2f}", "Balance": f"Rs. {balance:,.2f}"}
            fn = create_pdf(f"Report_{sel_ve}", rep_df, summary)
            with open(fn, "rb") as fl: st.download_button("📩 Download PDF", fl, file_name=fn)
