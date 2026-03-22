import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
from fpdf import FPDF

# --- CONFIG & FILENAMES ---
DATA_FILE = "ksd_master_v19.csv"
VE_FILE = "ksd_vehicles_v19.csv"
DR_FILE = "ksd_drivers_v19.csv"
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

# --- 🚀 EXPANDED NAVIGATION LOGIC ---
st.sidebar.title("🛠️ KSD ERP SYSTEM")
st.sidebar.markdown("---")

# Step 1: Main Category Selection
main_sector = st.sidebar.selectbox("MAIN CATEGORY", [
    "📊 Overview & Analytics",
    "🏗️ Site Operations",
    "💰 Financial Management",
    "⚙️ System Configuration",
    "📑 Reports & Data"
])

choice = ""

# Step 2: Sub-Menu Logic
if main_sector == "📊 Overview & Analytics":
    choice = "Dashboard"

elif main_sector == "🏗️ Site Operations":
    choice = st.sidebar.radio("Operation Type", [
        "🚚 Stock In (Soil)", 
        "💰 Sales Out (Sand/Soil)", 
        "🚜 Machine Performance (Excavator/Lorry)"
    ])

elif main_sector == "💰 Financial Management":
    choice = st.sidebar.radio("Finance Type", [
        "⛽ Fuel Bill Entry",
        "💳 Shed Credit Settlements",
        "💸 Driver Payroll",
        "🧾 Other Expenses (Repair/Food)"
    ])

elif main_sector == "⚙️ System Configuration":
    choice = st.sidebar.radio("Setup Type", [
        "👷 Driver Setup",
        "🚜 Vehicle Setup",
        "📝 General Notes"
    ])

elif main_sector == "📑 Reports & Data":
    choice = "Advanced Reports"

st.markdown(f"<h1 style='text-align: center; color: #E67E22;'>{choice}</h1>", unsafe_allow_html=True)
st.sidebar.markdown("---")

# --- SECTION LOGIC ---

# 1. DASHBOARD
if choice == "Dashboard":
    ti = df[df["Type"] == "Income"]["Amount"].sum()
    te = df[df["Type"] == "Expense"]["Amount"].sum()
    fd = df[(df["Category"] == "Fuel Entry") & (df["Status"] == "Pending")]["Amount"].sum()
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Income", f"Rs. {ti:,.2f}")
    c2.metric("Total Expenses", f"Rs. {te:,.2f}", delta_color="inverse")
    c3.metric("Net Profit", f"Rs. {ti-te:,.2f}")
    c4.metric("Fuel Debt", f"Rs. {fd:,.2f}", delta_color="inverse")
    
    st.divider()
    col_l, col_r = st.columns(2)
    with col_l:
        st.write("### 📈 Cashflow Trend")
        if not df.empty:
            daily = df.groupby(['Date', 'Type'])['Amount'].sum().unstack().fillna(0)
            st.area_chart(daily)
    with col_r:
        st.write("### 📂 Expense Breakdown")
        if not df.empty:
            exp_sum = df[df["Type"]=="Expense"].groupby("Category")["Amount"].sum()
            st.bar_chart(exp_sum)

# 2. SITE OPERATIONS
elif choice == "🚚 Stock In (Soil)":
    with st.form("stk_f"):
        d = st.date_input("Date"); v = st.text_input("Supplier Vehicle"); q = st.number_input("Cubes")
        if st.form_submit_button("Save Stock In"):
            new = pd.DataFrame([[len(df)+1, d, "", "Process", "Soil In", v, "Stock Entry", 0, q, 0, 0, "Done"]], columns=df.columns)
            df = pd.concat([df, new], ignore_index=True); df.to_csv(DATA_FILE, index=False); st.rerun()

elif choice == "💰 Sales Out (Sand/Soil)":
    with st.form("sale_f"):
        d = st.date_input("Date"); it = st.selectbox("Item", ["Sand Sale", "Soil Sale"]); q = st.number_input("Cubes"); a = st.number_input("Total Amount")
        if st.form_submit_button("Record Sale"):
            new = pd.DataFrame([[len(df)+1, d, "", "Income", it, "Cash", "Sale Out", a, q, 0, 0, "Paid"]], columns=df.columns)
            df = pd.concat([df, new], ignore_index=True); df.to_csv(DATA_FILE, index=False); st.rerun()

elif choice == "🚜 Machine Performance (Excavator/Lorry)":
    t1, t2 = st.tabs(["🏗️ Excavator", "🚚 Lorry"])
    with t1:
        exs = ve_db[ve_db["Type"]=="Excavator"]["No"].tolist()
        if exs:
            with st.form("ex_f"):
                sel = st.selectbox("Excavator", exs); h = st.number_input("Hours"); am = st.number_input("Cost/Payment"); nt = st.text_input("Job Description")
                if st.form_submit_button("Log Excavator"):
                    new = pd.DataFrame([[len(df)+1, datetime.now().date(), "", "Expense", "Machine Work", sel, nt, am, 0, 0, h, "Done"]], columns=df.columns)
                    df = pd.concat([df, new], ignore_index=True); df.to_csv(DATA_FILE, index=False); st.rerun()
    with t2:
        lrs = ve_db[ve_db["Type"]=="Lorry"]["No"].tolist()
        if lrs:
            with st.form("lr_f"):
                sel = st.selectbox("Lorry", lrs); q = st.number_input("Cubes"); am = st.number_input("Hire/Cost"); nt = st.text_input("Location")
                if st.form_submit_button("Log Lorry"):
                    new = pd.DataFrame([[len(df)+1, datetime.now().date(), "", "Expense", "Lorry Trip", sel, nt, am, q, 0, 0, "Done"]], columns=df.columns)
                    df = pd.concat([df, new], ignore_index=True); df.to_csv(DATA_FILE, index=False); st.rerun()

# 3. FINANCIALS
elif choice == "⛽ Fuel Bill Entry":
    with st.form("fuel_f"):
        d = st.date_input("Date"); v = st.selectbox("Vehicle", ve_db["No"].tolist() if not ve_db.empty else ["None"]); l = st.number_input("Liters"); c = st.number_input("Bill Cost"); stn = st.text_input("Shed Name")
        if st.form_submit_button("Log Fuel Bill (Credit)"):
            new = pd.DataFrame([[len(df)+1, d, "", "Expense", "Fuel Entry", v, f"Shed: {stn}", c, 0, l, 0, "Pending"]], columns=df.columns)
            df = pd.concat([df, new], ignore_index=True); df.to_csv(DATA_FILE, index=False); st.rerun()

elif choice == "💳 Shed Credit Settlements":
    pending = df[(df["Category"] == "Fuel Entry") & (df["Status"] == "Pending")]
    if pending.empty: st.success("No debts!")
    else:
        st.dataframe(pending[["Date", "Entity", "Note", "Amount"]], use_container_width=True)
        sel = st.selectbox("Settle Bill", pending.apply(lambda x: f"ID:{x['ID']} | Rs.{x['Amount']}", axis=1))
        if st.button("Mark as Paid ✅"):
            sid = int(sel.split("|")[0].split(":")[1])
            df.loc[df['ID'] == sid, 'Status'] = 'Paid'; df.to_csv(DATA_FILE, index=False); st.rerun()

elif choice == "💸 Driver Payroll":
    if not dr_db.empty:
        with st.form("pay_f"):
            dr = st.selectbox("Driver", dr_db["Name"].tolist()); ty = st.selectbox("Type", ["Advance", "Salary Payment"]); am = st.number_input("Amount")
            if st.form_submit_button("Save Payment"):
                new = pd.DataFrame([[len(df)+1, datetime.now().date(), "", "Expense", ty, dr, "Pay", am, 0, 0, 0, "Paid"]], columns=df.columns)
                df = pd.concat([df, new], ignore_index=True); df.to_csv(DATA_FILE, index=False); st.rerun()

elif choice == "🧾 Other Expenses (Repair/Food)":
    with st.form("oth_f"):
        d = st.date_input("Date"); cat = st.selectbox("Category", ["Repair", "Food", "Maintenance", "Rent", "Other"]); am = st.number_input("Amount"); nt = st.text_area("Note")
        if st.form_submit_button("Save Expense"):
            new = pd.DataFrame([[len(df)+1, d, "", "Expense", cat, "Admin", nt, am, 0, 0, 0, "Paid"]], columns=df.columns)
            df = pd.concat([df, new], ignore_index=True); df.to_csv(DATA_FILE, index=False); st.rerun()

# 4. CONFIGURATION
elif choice == "👷 Driver Setup":
    with st.form("dr"):
        n = st.text_input("Name"); p = st.text_input("Phone"); s = st.number_input("Salary")
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
        t = st.text_input("Title"); m = st.text_area("Details")
        if st.form_submit_button("Save Note"):
            new = pd.DataFrame([[len(df)+1, datetime.now().date(), "", "Info", "General Note", "Admin", t, 0, 0, 0, 0, m]], columns=df.columns)
            df = pd.concat([df, new], ignore_index=True); df.to_csv(DATA_FILE, index=False); st.rerun()
    for i, r in df[df["Category"]=="General Note"].iloc[::-1].iterrows():
        with st.expander(f"📌 {r['Date']} - {r['Note']}"): st.write(r['Status'])

# 5. REPORTS
elif choice == "Advanced Reports":
    rt = st.selectbox("Report Category", ["Vehicle Owner Statement", "Driver Statement"])
    f = st.date_input("From", datetime.now().date()-timedelta(days=30)); t = st.date_input("To")
    if not df.empty:
        view = df[(df["Date"]>=f) & (df["Date"]<=t)]
        st.dataframe(view, use_container_width=True)
        if st.button("Download PDF Statement"):
            fn = create_pdf("Report", view, {"Period": f"{f} to {t}"})
            with open(fn, "rb") as fl: st.download_button("📩 Download PDF", fl, file_name=fn)
