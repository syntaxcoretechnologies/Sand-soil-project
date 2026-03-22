import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
from fpdf import FPDF

# --- CONFIG & FILENAMES ---
# Version eka v24 kale aluth columns (Status) nisa parana data ekka patalenne nathi wenna
DATA_FILE = "ksd_master_v24.csv"
VE_FILE = "ksd_vehicles_v24.csv"
DR_FILE = "ksd_drivers_v24.csv"
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
        pdf.cell(38, 7, f"{val}", 1, 0, 'C'); pdf.cell(38, 7, f"{row['Amount']:,.2f}", 1, 0, 'R'); pdf.ln()
    fname = f"Report_{datetime.now().strftime('%H%M%S')}.pdf"
    pdf.output(fname); return fname

# --- UI SETUP ---
st.set_page_config(page_title=SHOP_NAME, layout="wide")
df = load_data(DATA_FILE, ["ID", "Date", "Time", "Type", "Category", "Entity", "Note", "Amount", "Qty_Cubes", "Fuel_Ltr", "Hours", "Status"])
ve_db = load_data(VE_FILE, ["No", "Type", "Owner", "Current_Driver"])
dr_db = load_data(DR_FILE, ["Name", "Phone", "Daily_Salary"])

# --- NAVIGATION ---
st.sidebar.title("🛠️ KSD ERP SYSTEM")
main_sector = st.sidebar.selectbox("MAIN CATEGORY", [
    "📊 Overview & Analytics", 
    "🏗️ Site Operations", 
    "💰 Financial Management", 
    "⚙️ System Configuration", 
    "📑 Reports & Data"
])

choice = ""
if main_sector == "📊 Overview & Analytics": choice = "Dashboard"
elif main_sector == "🏗️ Site Operations": choice = st.sidebar.radio("Operation", ["🚚 Stock In (Soil)", "💰 Sales Out (Sand/Soil)", "🚜 Machine Performance"])
elif main_sector == "💰 Financial Management": choice = st.sidebar.radio("Finance", ["⛽ Fuel & Shed Settlements", "💸 Driver Payroll", "🧾 Other Expenses"])
elif main_sector == "⚙️ System Configuration": choice = st.sidebar.radio("Setup", ["👷 Driver Setup", "🚜 Vehicle Setup", "📝 General Notes"])
elif main_sector == "📑 Reports & Data": choice = "Advanced Reports"

st.markdown(f"<h1 style='text-align: center; color: #E67E22;'>{choice}</h1>", unsafe_allow_html=True)

# --- 1. DASHBOARD ---
if choice == "Dashboard":
    ti = df[df["Type"] == "Income"]["Amount"].sum()
    te = df[df["Type"] == "Expense"]["Amount"].sum()
    fuel_debt = df[(df["Category"] == "Fuel Entry") & (df["Status"] == "Pending")]["Amount"].sum()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Income", f"Rs. {ti:,.2f}")
    m2.metric("Total Expenses", f"Rs. {te:,.2f}")
    m3.metric("Net Profit", f"Rs. {ti-te:,.2f}")
    m4.metric("Shed Debt (Naya)", f"Rs. {fuel_debt:,.2f}", delta_color="inverse")
    
    st.divider()
    c_l, c_r = st.columns(2)
    with c_l:
        st.write("### 📈 Cashflow Trend")
        if not df.empty:
            daily = df.groupby(['Date', 'Type'])['Amount'].sum().unstack().fillna(0)
            st.area_chart(daily)
    with c_r:
        st.write("### 📂 Expense Distribution")
        if not df.empty:
            exp_sum = df[df["Type"]=="Expense"].groupby("Category")["Amount"].sum()
            st.bar_chart(exp_sum)

# --- 2. SITE OPERATIONS ---
elif choice == "🚚 Stock In (Soil)":
    with st.form("stk_f"):
        d = st.date_input("Date"); v = st.text_input("Supplier/Vehicle"); q = st.number_input("Cubes")
        if st.form_submit_button("Add Stock"):
            new = pd.DataFrame([[len(df)+1, d, "", "Process", "Soil In", v, "In", 0, q, 0, 0, "Done"]], columns=df.columns)
            df = pd.concat([df, new], ignore_index=True); df.to_csv(DATA_FILE, index=False); st.rerun()

elif choice == "💰 Sales Out (Sand/Soil)":
    with st.form("sale_f"):
        d = st.date_input("Date"); it = st.selectbox("Item", ["Sand Sale", "Soil Sale"]); q = st.number_input("Cubes"); a = st.number_input("Amount")
        if st.form_submit_button("Record Sale"):
            new = pd.DataFrame([[len(df)+1, d, "", "Income", it, "Cash", "Sale", a, q, 0, 0, "Paid"]], columns=df.columns)
            df = pd.concat([df, new], ignore_index=True); df.to_csv(DATA_FILE, index=False); st.rerun()

elif choice == "🚜 Machine Performance":
    t1, t2 = st.tabs(["🏗️ Excavator", "🚚 Lorry"])
    with t1:
        exs = ve_db[ve_db["Type"]=="Excavator"]["No"].tolist()
        if exs:
            with st.form("ex_f", clear_on_submit=True):
                sel = st.selectbox("Select Excavator", exs); d_ex = st.date_input("Date"); h = st.number_input("Hours Worked"); am = st.number_input("Cost/Payment"); nt = st.text_input("Job Description")
                if st.form_submit_button("Log Excavator Work"):
                    new = pd.DataFrame([[len(df)+1, d_ex, "", "Expense", "Machine Work", sel, nt, am, 0, 0, h, "Done"]], columns=df.columns)
                    df = pd.concat([df, new], ignore_index=True); df.to_csv(DATA_FILE, index=False); st.success("Logged!"); st.rerun()
    with t2:
        lrs = ve_db[ve_db["Type"]=="Lorry"]["No"].tolist()
        if lrs:
            with st.form("lr_f", clear_on_submit=True):
                sel = st.selectbox("Select Lorry", lrs); d_lr = st.date_input("Date"); q = st.number_input("Cubes Transported"); am = st.number_input("Hire Amount"); nt = st.text_input("Trip Details")
                if st.form_submit_button("Log Lorry Trip"):
                    new = pd.DataFrame([[len(df)+1, d_lr, "", "Expense", "Lorry Trip", sel, nt, am, q, 0, 0, "Done"]], columns=df.columns)
                    df = pd.concat([df, new], ignore_index=True); df.to_csv(DATA_FILE, index=False); st.success("Logged!"); st.rerun()

# --- 3. FINANCIALS ---
elif choice == "⛽ Fuel & Shed Settlements":
    tab1, tab2 = st.tabs(["⛽ Log New Fuel Bill", "💳 Settle Pending Bills"])
    with tab1:
        with st.form("fuel_f", clear_on_submit=True):
            d = st.date_input("Date"); v = st.selectbox("Vehicle", ve_db["No"].tolist() if not ve_db.empty else ["None"]); l = st.number_input("Liters"); c = st.number_input("Bill Cost"); s = st.text_input("Shed Name")
            if st.form_submit_button("Record Credit Bill"):
                new = pd.DataFrame([[len(df)+1, d, "", "Expense", "Fuel Entry", v, f"Shed: {s}", c, 0, l, 0, "Pending"]], columns=df.columns)
                df = pd.concat([df, new], ignore_index=True); df.to_csv(DATA_FILE, index=False); st.success("Recorded!"); st.rerun()
    with tab2:
        pending = df[(df["Category"] == "Fuel Entry") & (df["Status"] == "Pending")]
        if pending.empty: st.success("No pending fuel bills!")
        else:
            st.dataframe(pending[["Date", "Entity", "Note", "Amount", "Status"]], use_container_width=True)
            sel_bill = st.selectbox("Select Bill to Settle", pending.apply(lambda x: f"ID:{x['ID']} | {x['Entity']} | Rs.{x['Amount']}", axis=1))
            if st.button("Mark as Paid ✅"):
                sid = int(sel_bill.split("|")[0].split(":")[1])
                df.loc[df['ID'] == sid, 'Status'] = 'Paid'; df.to_csv(DATA_FILE, index=False); st.rerun()

elif choice == "💸 Driver Payroll":
    if not dr_db.empty:
        with st.form("pay"):
            dr = st.selectbox("Driver", dr_db["Name"].tolist()); ty = st.selectbox("Type", ["Advance", "Salary Payment"]); am = st.number_input("Amount")
            if st.form_submit_button("Save Payment"):
                new = pd.DataFrame([[len(df)+1, datetime.now().date(), "", "Expense", ty, dr, "Payroll", am, 0, 0, 0, "Paid"]], columns=df.columns)
                df = pd.concat([df, new], ignore_index=True); df.to_csv(DATA_FILE, index=False); st.rerun()

elif choice == "🧾 Other Expenses":
    with st.form("oth"):
        d = st.date_input("Date"); cat = st.selectbox("Type", ["Repair", "Food", "Maintenance", "Other"]); amt = st.number_input("Amount"); nt = st.text_area("Note")
        if st.form_submit_button("Save"):
            new = pd.DataFrame([[len(df)+1, d, "", "Expense", cat, "Admin", nt, amt, 0, 0, 0, "Paid"]], columns=df.columns)
            df = pd.concat([df, new], ignore_index=True); df.to_csv(DATA_FILE, index=False); st.rerun()

# --- 4. CONFIGURATION ---
elif choice == "👷 Driver Setup":
    with st.form("dr"):
        n = st.text_input("Name"); p = st.text_input("Phone"); s = st.number_input("Daily Salary")
        if st.form_submit_button("Add Driver"):
            new = pd.DataFrame([[n,p,s]], columns=dr_db.columns)
            dr_db = pd.concat([dr_db, new], ignore_index=True); dr_db.to_csv(DR_FILE, index=False); st.rerun()
    st.table(dr_db)

elif choice == "🚜 Vehicle Setup":
    with st.form("ve"):
        v = st.text_input("No"); t = st.selectbox("Type",["Lorry","Excavator"]); o = st.text_input("Owner"); dr = st.selectbox("Driver", dr_db["Name"].tolist() if not dr_db.empty else ["None"])
        if st.form_submit_button("Add Vehicle"):
            new = pd.DataFrame([[v,t,o,dr]], columns=ve_db.columns)
            ve_db = pd.concat([ve_db, new], ignore_index=True); ve_db.to_csv(VE_FILE, index=False); st.rerun()
    st.table(ve_db)

elif choice == "📝 General Notes":
    with st.form("nt"):
        t = st.text_input("Title"); m = st.text_area("Note")
        if st.form_submit_button("Save"):
            new = pd.DataFrame([[len(df)+1, datetime.now().date(), "", "Info", "General Note", "Admin", t, 0, 0, 0, 0, m]], columns=df.columns)
            df = pd.concat([df, new], ignore_index=True); df.to_csv(DATA_FILE, index=False); st.rerun()
    for i, r in df[df["Category"]=="General Note"].iloc[::-1].iterrows():
        with st.expander(f"📌 {r['Date']} - {r['Note']}"): st.write(r['Status'])

# --- 5. ADVANCED REPORTS ---
elif choice == "Advanced Reports":
    rep_mode = st.radio("Statement Type", ["Driver Summary", "Vehicle Performance", "All Transactions"], horizontal=True)
    f = st.date_input("From Date", datetime.now().date()-timedelta(days=30)); t = st.date_input("To Date")
    
    if rep_mode == "Driver Summary" and not dr_db.empty:
        sel = st.selectbox("Select Driver", dr_db["Name"].tolist())
        data = df[(df["Entity"] == sel) & (df["Date"] >= f) & (df["Date"] <= t)]
        adv = data[data["Category"] == "Advance"]["Amount"].sum()
        sal = data[data["Category"] == "Salary Payment"]["Amount"].sum()
        st.info(f"Driver: {sel} | Advances: Rs.{adv:,.2f} | Paid: Rs.{sal:,.2f}")
        st.dataframe(data, use_container_width=True)
    
    elif rep_mode == "Vehicle Performance" and not ve_db.empty:
        sel = st.selectbox("Select Vehicle", ve_db["No"].tolist())
        data = df[(df["Entity"] == sel) & (df["Date"] >= f) & (df["Date"] <= t)]
        total_hrs = data["Hours"].sum(); total_c = data["Qty_Cubes"].sum(); total_cost = data["Amount"].sum()
        st.info(f"Vehicle: {sel} | Hrs: {total_hrs} | Cubes: {total_c} | Total Cost: Rs.{total_cost:,.2f}")
        st.dataframe(data, use_container_width=True)
    
    else:
        view = df[(df["Date"]>=f) & (df["Date"]<=t)]
        st.dataframe(view, use_container_width=True)
    
    if st.button("Generate PDF Report"):
        fn = create_pdf("KSD_Statement", df[(df["Date"]>=f) & (df["Date"]<=t)], {"Period": f"{f} to {t}"})
        with open(fn, "rb") as fl: st.download_button("📩 Download PDF", fl, file_name=fn)
