import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
from fpdf import FPDF

# --- CONFIG & FILENAMES ---
DATA_FILE = "ksd_master_v16.csv"
VE_FILE = "ksd_vehicles_v16.csv"
DR_FILE = "ksd_drivers_v16.csv"
SHOP_NAME = "K. SIRIWARDHANA SAND CONSTRUCTION PRO"

# --- HELPER FUNCTIONS ---
def load_data(file, cols):
    if os.path.exists(file): 
        d = pd.read_csv(file)
        if 'Date' in d.columns:
            d['Date'] = pd.to_datetime(d['Date']).dt.date
        return d
    return pd.DataFrame(columns=cols)

# --- PDF GENERATOR ---
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.set_text_color(230, 126, 34) 
        self.cell(0, 10, SHOP_NAME, 0, 1, 'C')
        self.ln(10)
    def footer(self):
        self.set_y(-15); self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

def create_pdf(title, data_df, summary_dict):
    pdf = PDF(); pdf.add_page(); pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, f"STATEMENT: {title.upper()}", 1, 1, 'L')
    for k, v in summary_dict.items():
        pdf.set_font("Arial", 'B', 10); pdf.cell(60, 8, f"{k}:", 1); pdf.set_font("Arial", '', 10); pdf.cell(0, 8, f" {v}", 1, 1)
    pdf.ln(10); pdf.set_font("Arial", 'B', 9)
    cols = ["Date", "Category", "Note", "Qty/Hrs", "Amount"]
    for c in cols: pdf.cell(38, 8, c, 1, 0, 'C')
    pdf.ln(); pdf.set_font("Arial", '', 8)
    for _, row in data_df.iterrows():
        pdf.cell(38, 7, str(row['Date']), 1); pdf.cell(38, 7, str(row['Category']), 1); pdf.cell(38, 7, str(row['Note'])[:20], 1)
        val = row['Qty_Cubes'] if row['Qty_Cubes'] > 0 else row['Hours']
        pdf.cell(38, 7, f"{val}", 1); pdf.cell(38, 7, f"{row['Amount']:,.2f}", 1); pdf.ln()
    fname = f"Report_{datetime.now().strftime('%H%M%S')}.pdf"
    pdf.output(fname); return fname

# --- UI SETUP ---
st.set_page_config(page_title=SHOP_NAME, layout="wide")
df = load_data(DATA_FILE, ["ID", "Date", "Time", "Type", "Category", "Entity", "Note", "Amount", "Qty_Cubes", "Fuel_Ltr", "Hours", "Status"])
ve_db = load_data(VE_FILE, ["No", "Type", "Owner", "Current_Driver"])
dr_db = load_data(DR_FILE, ["Name", "Phone", "Daily_Salary"])

# --- NAVIGATION ---
st.sidebar.title("KSD NAVIGATION")
main_mode = st.sidebar.radio("SELECT SECTOR", ["📊 Dashboard", "🏗️ Operations", "💳 Fuel Credit & Shed", "⚙️ Management", "📑 Reporting"])

choice = ""
if main_mode == "📊 Dashboard": choice = "📊 Dashboard"
elif main_mode == "🏗️ Operations": choice = st.sidebar.selectbox("Sub Menu", ["🚚 Stock In (Soil)", "💰 Sales Out", "🚜 Machine Performance", "💸 Driver Payroll", "⛽ Fuel Intake"])
elif main_mode == "💳 Fuel Credit & Shed": choice = "💳 Fuel Credit & Shed"
elif main_mode == "⚙️ Management": choice = st.sidebar.selectbox("Sub Menu", ["👷 Driver Setup", "🚜 Vehicle Setup"])
elif main_mode == "📑 Reporting": choice = "📑 Advanced Reports"

st.markdown(f"<h1 style='color: #E67E22;'>{choice}</h1>", unsafe_allow_html=True)

# --- 1. DASHBOARD ---
if choice == "📊 Dashboard":
    unpaid_fuel = df[(df["Category"] == "Fuel Entry") & (df["Status"] == "Pending")]["Amount"].sum()
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Income", f"Rs. {df[df['Type']=='Income']['Amount'].sum():,.2f}")
    c2.metric("Total Expenses", f"Rs. {df[df['Type']=='Expense']['Amount'].sum():,.2f}")
    c3.metric("Fuel Debt (Shed)", f"Rs. {unpaid_fuel:,.2f}", delta_color="inverse")
    if not df.empty: st.line_chart(df.groupby("Date")["Amount"].sum())

# --- 2. FUEL INTAKE (RECORD ONLY) ---
elif choice == "⛽ Fuel Intake":
    st.info("Record fuel taken from the shed. Payment can be settled in the 'Fuel Credit & Shed' menu.")
    with st.form("fuel_f", clear_on_submit=True):
        d = st.date_input("Date"); v = st.selectbox("Vehicle", ve_db["No"].tolist() if not ve_db.empty else ["No Vehicles"])
        l = st.number_input("Liters"); c = st.number_input("Bill Amount (Rs.)"); stn = st.text_input("Shed Name", "Petrol Shed")
        if st.form_submit_button("Log Fuel Bill"):
            new = pd.DataFrame([[len(df)+1, d, "", "Expense", "Fuel Entry", v, f"Shed: {stn}", c, 0, l, 0, "Pending"]], columns=df.columns)
            df = pd.concat([df, new], ignore_index=True); df.to_csv(DATA_FILE, index=False); st.success("Bill Recorded!"); st.rerun()

# --- 3. FUEL CREDIT & SHED (THE NEW MENU) ---
elif choice == "💳 Fuel Credit & Shed":
    pending_bills = df[(df["Category"] == "Fuel Entry") & (df["Status"] == "Pending")]
    
    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("Outstanding Fuel Bills")
        if pending_bills.empty: st.success("All shed bills are cleared! ✅")
        else: st.dataframe(pending_bills[["Date", "Entity", "Note", "Amount"]], use_container_width=True)
    
    with col2:
        st.subheader("Settle Payment")
        if not pending_bills.empty:
            st.metric("Total Debt", f"Rs. {pending_bills['Amount'].sum():,.2f}")
            bill_to_pay = st.selectbox("Select Bill to Pay", pending_bills.apply(lambda x: f"ID:{x['ID']} | {x['Entity']} | Rs.{x['Amount']}", axis=1))
            pay_date = st.date_input("Payment Date")
            if st.button("Mark as Paid ✅"):
                sel_id = int(bill_to_pay.split("|")[0].split(":")[1])
                df.loc[df['ID'] == sel_id, 'Status'] = 'Paid'
                df.loc[df['ID'] == sel_id, 'Date'] = pay_date # Optional: update to payment date
                df.to_csv(DATA_FILE, index=False); st.success("Payment Settled!"); st.rerun()

# --- REMAINING SECTIONS (Simplified for brevity) ---
elif choice == "👷 Driver Setup":
    with st.form("dr"):
        n = st.text_input("Name"); p = st.text_input("Phone"); s = st.number_input("Daily Salary")
        if st.form_submit_button("Add"):
            new = pd.DataFrame([[n,p,s]], columns=dr_db.columns)
            dr_db = pd.concat([dr_db, new], ignore_index=True); dr_db.to_csv(DR_FILE, index=False); st.rerun()
    st.table(dr_db)

elif choice == "🚜 Vehicle Setup":
    with st.form("ve"):
        v = st.text_input("No"); t = st.selectbox("Type",["Lorry","Excavator"]); o = st.text_input("Owner"); dr = st.selectbox("Driver", dr_db["Name"].tolist() if not dr_db.empty else ["None"])
        if st.form_submit_button("Add"):
            new = pd.DataFrame([[v,t,o,dr]], columns=ve_db.columns)
            ve_db = pd.concat([ve_db, new], ignore_index=True); ve_db.to_csv(VE_FILE, index=False); st.rerun()
    st.table(ve_db)

elif choice == "🚚 Stock In (Soil)":
    with st.form("stk"):
        d = st.date_input("Date"); s = st.text_input("Supplier"); q = st.number_input("Cubes")
        if st.form_submit_button("Add Stock"):
            new = pd.DataFrame([[len(df)+1, d, "", "Process", "Soil In", s, "In", 0, q, 0, 0, "Done"]], columns=df.columns)
            df = pd.concat([df, new], ignore_index=True); df.to_csv(DATA_FILE, index=False); st.rerun()

elif choice == "💰 Sales Out":
    with st.form("sal"):
        d = st.date_input("Date"); it = st.selectbox("Item", ["Sand", "Soil"]); q = st.number_input("Cubes"); a = st.number_input("Amount")
        if st.form_submit_button("Save Sale"):
            new = pd.DataFrame([[len(df)+1, d, "", "Income", it, "Cash", "Sale", a, q, 0, 0, "Paid"]], columns=df.columns)
            df = pd.concat([df, new], ignore_index=True); df.to_csv(DATA_FILE, index=False); st.rerun()

elif choice == "🚜 Machine Performance":
    t1, t2 = st.tabs(["🏗️ Excavator", "🚚 Lorry"])
    with t1:
        exs = ve_db[ve_db["Type"]=="Excavator"]["No"].tolist()
        if exs:
            sel = st.selectbox("Excavator", exs); h = st.number_input("Hours")
            if st.button("Log Hours"):
                new = pd.DataFrame([[len(df)+1, datetime.now().date(), "", "Work", "Work Entry", sel, "Work", 0, 0, 0, h, "Done"]], columns=df.columns)
                df = pd.concat([df, new], ignore_index=True); df.to_csv(DATA_FILE, index=False); st.rerun()
    with t2:
        lrs = ve_db[ve_db["Type"]=="Lorry"]["No"].tolist()
        if lrs:
            sel = st.selectbox("Lorry", lrs); q = st.number_input("Cubes")
            if st.button("Log Cubes"):
                new = pd.DataFrame([[len(df)+1, datetime.now().date(), "", "Work", "Work Entry", sel, "Work", 0, q, 0, 0, "Done"]], columns=df.columns)
                df = pd.concat([df, new], ignore_index=True); df.to_csv(DATA_FILE, index=False); st.rerun()

elif choice == "💸 Driver Payroll":
    drs = dr_db["Name"].tolist()
    if drs:
        sel = st.selectbox("Driver", drs); am = st.number_input("Amount")
        if st.button("Save Pay"):
            new = pd.DataFrame([[len(df)+1, datetime.now().date(), "", "Expense", "Advance", sel, "Pay", am, 0, 0, 0, "Paid"]], columns=df.columns)
            df = pd.concat([df, new], ignore_index=True); df.to_csv(DATA_FILE, index=False); st.rerun()

elif choice == "📑 Advanced Reports":
    rt = st.selectbox("Type", ["Vehicle Owner Statement", "Driver Statement"])
    if rt == "Vehicle Owner Statement" and not ve_db.empty:
        sv = st.selectbox("Vehicle", ve_db["No"].tolist())
        v_data = df[df["Entity"]==sv]
        st.dataframe(v_data)
        if st.button("Download"):
            fn = create_pdf(f"Vehicle_{sv}", v_data, {"Vehicle": sv})
            with open(fn, "rb") as f: st.download_button("📩 PDF", f, file_name=fn)
