import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
from fpdf import FPDF

# --- CONFIG & FILENAMES ---
DATA_FILE = "ksd_master_v18.csv"
VE_FILE = "ksd_vehicles_v18.csv"
DR_FILE = "ksd_drivers_v18.csv"
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
main_mode = st.sidebar.radio("SELECT SECTOR", ["📊 Dashboard & Profit", "🏗️ Operations", "💳 Fuel & Shed Payments", "💸 Other Expenses", "⚙️ Management", "📑 Reporting"])

choice = ""
if main_mode == "📊 Dashboard & Profit": choice = "📊 Dashboard"
elif main_mode == "🏗️ Operations": choice = st.sidebar.selectbox("Sub Menu", ["🚚 Stock In (Soil)", "💰 Sales Out", "🚜 Machine Performance", "💸 Driver Payroll", "⛽ Fuel Intake"])
elif main_mode == "💳 Fuel & Shed Payments": choice = "💳 Fuel Credit & Shed"
elif main_mode == "💸 Other Expenses": choice = "💸 Other Expenses"
elif main_mode == "⚙️ Management": choice = st.sidebar.selectbox("Sub Menu", ["👷 Driver Setup", "🚜 Vehicle Setup", "📝 General Notes"])
elif main_mode == "📑 Reporting": choice = "📑 Advanced Reports"

st.markdown(f"<h1 style='text-align: center; color: #E67E22;'>{choice}</h1>", unsafe_allow_html=True)

# --- 1. DASHBOARD & PROFIT (FIXED NameError) ---
if choice == "📊 Dashboard":
    ti = df[df["Type"] == "Income"]["Amount"].sum()
    te = df[df["Type"] == "Expense"]["Amount"].sum()
    np = ti - te
    fd = df[(df["Category"] == "Fuel Entry") & (df["Status"] == "Pending")]["Amount"].sum()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Income", f"Rs. {ti:,.2f}")
    m2.metric("Total Expenses", f"Rs. {te:,.2f}", delta_color="inverse")
    m3.metric("Net Profit", f"Rs. {np:,.2f}")
    m4.metric("Fuel Debt", f"Rs. {fd:,.2f}", delta_color="inverse")

    st.divider()
    # ✅ FIX: Defining c_l and c_r correctly
    c_l, c_r = st.columns(2) 
    with c_l:
        st.write("### 📈 Daily Cashflow")
        if not df.empty:
            daily = df.groupby(['Date', 'Type'])['Amount'].sum().unstack().fillna(0)
            st.bar_chart(daily)
    with c_r:
        st.write("### 📂 Expense Breakdown")
        if not df.empty:
            exp_data = df[df["Type"]=="Expense"].groupby("Category")["Amount"].sum()
            st.write(exp_data)

# --- 2. FUEL INTAKE ---
elif choice == "⛽ Fuel Intake":
    with st.form("fuel_f", clear_on_submit=True):
        d = st.date_input("Date"); v = st.selectbox("Vehicle", ve_db["No"].tolist() if not ve_db.empty else ["None"])
        l = st.number_input("Liters"); c = st.number_input("Cost"); s = st.text_input("Shed Name")
        if st.form_submit_button("Log Bill"):
            new = pd.DataFrame([[len(df)+1, d, "", "Expense", "Fuel Entry", v, f"Shed: {s}", c, 0, l, 0, "Pending"]], columns=df.columns)
            df = pd.concat([df, new], ignore_index=True); df.to_csv(DATA_FILE, index=False); st.rerun()

# --- 3. FUEL CREDIT & SHED ---
elif choice == "💳 Fuel Credit & Shed":
    pending = df[(df["Category"] == "Fuel Entry") & (df["Status"] == "Pending")]
    if pending.empty: st.success("No outstanding fuel bills!")
    else:
        st.dataframe(pending[["Date", "Entity", "Note", "Amount"]], use_container_width=True)
        with st.form("set_f"):
            sel = st.selectbox("Select Bill", pending.apply(lambda x: f"ID:{x['ID']} | Rs.{x['Amount']}", axis=1))
            if st.form_submit_button("Mark Paid"):
                sid = int(sel.split("|")[0].split(":")[1])
                df.loc[df['ID'] == sid, 'Status'] = 'Paid'
                df.to_csv(DATA_FILE, index=False); st.rerun()

# --- 4. OTHER EXPENSES ---
elif choice == "💸 Other Expenses":
    with st.form("oth_f", clear_on_submit=True):
        d = st.date_input("Date"); cat = st.selectbox("Type", ["Repair", "Food", "Maintenance", "Other"])
        amt = st.number_input("Amount"); nt = st.text_area("Note")
        if st.form_submit_button("Save"):
            new = pd.DataFrame([[len(df)+1, d, "", "Expense", cat, "Admin", nt, amt, 0, 0, 0, "Paid"]], columns=df.columns)
            df = pd.concat([df, new], ignore_index=True); df.to_csv(DATA_FILE, index=False); st.rerun()

# --- 5. STOCK & SALES ---
elif choice == "🚚 Stock In (Soil)":
    with st.form("stk"):
        d = st.date_input("Date"); v = st.text_input("Supplier"); q = st.number_input("Cubes")
        if st.form_submit_button("Add Stock"):
            new = pd.DataFrame([[len(df)+1, d, "", "Process", "Soil In", v, "In", 0, q, 0, 0, "Done"]], columns=df.columns)
            df = pd.concat([df, new], ignore_index=True); df.to_csv(DATA_FILE, index=False); st.rerun()

elif choice == "💰 Sales Out":
    with st.form("sal"):
        d = st.date_input("Date"); it = st.selectbox("Item", ["Sand Sale", "Soil Sale"]); q = st.number_input("Cubes"); a = st.number_input("Amount")
        if st.form_submit_button("Save Sale"):
            new = pd.DataFrame([[len(df)+1, d, "", "Income", it, "Cash", "Sale", a, q, 0, 0, "Paid"]], columns=df.columns)
            df = pd.concat([df, new], ignore_index=True); df.to_csv(DATA_FILE, index=False); st.rerun()

# --- 6. DRIVER SETUP & PAYROLL ---
elif choice == "👷 Driver Setup":
    with st.form("dr"):
        n = st.text_input("Name"); p = st.text_input("Phone"); s = st.number_input("Daily Salary")
        if st.form_submit_button("Add"):
            new = pd.DataFrame([[n,p,s]], columns=dr_db.columns)
            dr_db = pd.concat([dr_db, new], ignore_index=True); dr_db.to_csv(DR_FILE, index=False); st.rerun()
    st.table(dr_db)

elif choice == "💸 Driver Payroll":
    if not dr_db.empty:
        with st.form("pay"):
            dr = st.selectbox("Driver", dr_db["Name"].tolist()); ty = st.selectbox("Type", ["Advance", "Salary"]); am = st.number_input("Amount")
            if st.form_submit_button("Save Pay"):
                new = pd.DataFrame([[len(df)+1, datetime.now().date(), "", "Expense", ty, dr, "Pay", am, 0, 0, 0, "Paid"]], columns=df.columns)
                df = pd.concat([df, new], ignore_index=True); df.to_csv(DATA_FILE, index=False); st.rerun()

# --- 7. VEHICLE & PERFORMANCE ---
elif choice == "🚜 Vehicle Setup":
    with st.form("ve"):
        v = st.text_input("No"); t = st.selectbox("Type",["Lorry","Excavator"]); o = st.text_input("Owner"); dr = st.selectbox("Driver", dr_db["Name"].tolist() if not dr_db.empty else ["None"])
        if st.form_submit_button("Add"):
            new = pd.DataFrame([[v,t,o,dr]], columns=ve_db.columns)
            ve_db = pd.concat([ve_db, new], ignore_index=True); ve_db.to_csv(VE_FILE, index=False); st.rerun()
    st.table(ve_db)

elif choice == "🚜 Machine Performance":
    t1, t2 = st.tabs(["🏗️ Excavator", "🚚 Lorry"])
    with t1:
        exs = ve_db[ve_db["Type"]=="Excavator"]["No"].tolist()
        if exs:
            sel = st.selectbox("Select", exs); h = st.number_input("Hours")
            if st.button("Log Hours"):
                new = pd.DataFrame([[len(df)+1, datetime.now().date(), "", "Work", "Work Entry", sel, "Work", 0, 0, 0, h, "Done"]], columns=df.columns)
                df = pd.concat([df, new], ignore_index=True); df.to_csv(DATA_FILE, index=False); st.rerun()
    with t2:
        lrs = ve_db[ve_db["Type"]=="Lorry"]["No"].tolist()
        if lrs:
            sel = st.selectbox("Select Lorry", lrs); q = st.number_input("Cubes")
            if st.button("Log Cubes"):
                new = pd.DataFrame([[len(df)+1, datetime.now().date(), "", "Work", "Work Entry", sel, "Work", 0, q, 0, 0, "Done"]], columns=df.columns)
                df = pd.concat([df, new], ignore_index=True); df.to_csv(DATA_FILE, index=False); st.rerun()

# --- 8. NOTES & REPORTS ---
elif choice == "📝 General Notes":
    with st.form("nt"):
        t = st.text_input("Title"); m = st.text_area("Note")
        if st.form_submit_button("Save"):
            new = pd.DataFrame([[len(df)+1, datetime.now().date(), "", "Info", "General Note", "Admin", t, 0, 0, 0, 0, m]], columns=df.columns)
            df = pd.concat([df, new], ignore_index=True); df.to_csv(DATA_FILE, index=False); st.rerun()
    for i, r in df[df["Category"]=="General Note"].iloc[::-1].iterrows():
        with st.expander(f"{r['Date']} - {r['Note']}"): st.write(r['Status'])

elif choice == "📑 Advanced Reports":
    rt = st.selectbox("Type", ["Vehicle Owner Statement", "Driver Statement"])
    if not df.empty:
        f = st.date_input("From", datetime.now().date()-timedelta(days=30)); t = st.date_input("To")
        if st.button("Generate View"):
            view = df[(df["Date"]>=f) & (df["Date"]<=t)]
            st.dataframe(view)
