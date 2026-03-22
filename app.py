import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
from fpdf import FPDF

# --- CONFIG & FILENAMES ---
DATA_FILE = "ksd_master_v21.csv"
VE_FILE = "ksd_vehicles_v21.csv"
DR_FILE = "ksd_drivers_v21.csv"
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
    pdf.ln(); pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", '', 8)
    for _, row in data_df.iterrows():
        pdf.cell(38, 7, str(row['Date']), 1); pdf.cell(38, 7, str(row['Category']), 1); pdf.cell(38, 7, str(row['Note'])[:20], 1)
        val = row['Qty_Cubes'] if row['Qty_Cubes'] > 0 else row['Hours']
        pdf.cell(38, 7, f"{val}", 1, 0, 'C'); pdf.cell(38, 7, f"{row['Amount']:,.2f}", 1, 0, 'R'); pdf.ln()
    fname = f"Report_{datetime.now().strftime('%H%M%S')}.pdf"
    pdf.output(fname); return fname

# --- UI SETUP ---
st.set_page_config(page_title=SHOP_NAME, layout="wide")
df = load_data(DATA_FILE, ["ID", "Date", "Time", "Type", "Category", "Entity", "Note", "Amount", "Qty_Cubes", "Fuel_Ltr", "Hours", "Status"])
ve_db = load_data(VE_FILE, ["No", "Type", "Owner", "Current_Driver"])
dr_db = load_data(DR_FILE, ["Name", "Phone", "Daily_Salary"])

# --- EXPANDED NAVIGATION ---
st.sidebar.title("🛠️ KSD ERP SYSTEM")
st.sidebar.markdown("---")

main_sector = st.sidebar.selectbox("MAIN CATEGORY", [
    "📊 Overview & Analytics",
    "🏗️ Site Operations",
    "💰 Financial Management",
    "⚙️ System Configuration",
    "📑 Reports & Data"
])

choice = ""
if main_sector == "📊 Overview & Analytics":
    choice = "Dashboard"
elif main_sector == "🏗️ Site Operations":
    choice = st.sidebar.radio("Operation Type", ["🚚 Stock In (Soil)", "💰 Sales Out (Sand/Soil)", "🚜 Machine Performance"])
elif main_sector == "💰 Financial Management":
    choice = st.sidebar.radio("Finance Type", ["⛽ Fuel Bill Entry", "💳 Shed Credit Settlements", "💸 Driver Payroll", "🧾 Other Expenses"])
elif main_sector == "⚙️ System Configuration":
    choice = st.sidebar.radio("Setup Type", ["👷 Driver Setup", "🚜 Vehicle Setup", "📝 General Notes"])
elif main_sector == "📑 Reports & Data":
    choice = "Advanced Reports"

st.markdown(f"<h1 style='text-align: center; color: #E67E22;'>{choice}</h1>", unsafe_allow_html=True)

# --- 1. DASHBOARD ---
if choice == "Dashboard":
    ti = df[df["Type"] == "Income"]["Amount"].sum()
    te = df[df["Type"] == "Expense"]["Amount"].sum()
    fd = df[(df["Category"] == "Fuel Entry") & (df["Status"] == "Pending")]["Amount"].sum()
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Income", f"Rs. {ti:,.2f}")
    m2.metric("Total Expenses", f"Rs. {te:,.2f}", delta_color="inverse")
    m3.metric("Net Profit", f"Rs. {ti-te:,.2f}")
    m4.metric("Fuel Debt (Shed)", f"Rs. {fd:,.2f}", delta_color="inverse")
    
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
    with st.form("stk_f", clear_on_submit=True):
        d = st.date_input("Date"); v = st.text_input("Supplier/Vehicle"); q = st.number_input("Cubes")
        if st.form_submit_button("Save Stock"):
            new = pd.DataFrame([[len(df)+1, d, "", "Process", "Soil In", v, "Inbound", 0, q, 0, 0, "Done"]], columns=df.columns)
            df = pd.concat([df, new], ignore_index=True); df.to_csv(DATA_FILE, index=False); st.success("Saved!"); st.rerun()

elif choice == "💰 Sales Out (Sand/Soil)":
    with st.form("sale_f", clear_on_submit=True):
        d = st.date_input("Date"); it = st.selectbox("Item", ["Sand Sale", "Soil Sale"]); q = st.number_input("Cubes"); a = st.number_input("Amount")
        if st.form_submit_button("Record Sale"):
            new = pd.DataFrame([[len(df)+1, d, "", "Income", it, "Cash", "Sale", a, q, 0, 0, "Paid"]], columns=df.columns)
            df = pd.concat([df, new], ignore_index=True); df.to_csv(DATA_FILE, index=False); st.success("Sold!"); st.rerun()

elif choice == "🚜 Machine Performance":
    t1, t2 = st.tabs(["🏗️ Excavator", "🚚 Lorry"])
    with t1:
        exs = ve_db[ve_db["Type"]=="Excavator"]["No"].tolist()
        if exs:
            with st.form("ex_f", clear_on_submit=True):
                sel = st.selectbox("Excavator", exs); d_ex = st.date_input("Date"); h = st.number_input("Hours"); am = st.number_input("Cost/Payment"); nt = st.text_input("Job Description")
                if st.form_submit_button("Log Excavator Work"):
                    new = pd.DataFrame([[len(df)+1, d_ex, "", "Expense", "Machine Work", sel, nt, am, 0, 0, h, "Done"]], columns=df.columns)
                    df = pd.concat([df, new], ignore_index=True); df.to_csv(DATA_FILE, index=False); st.success("Logged!"); st.rerun()
    with t2:
        lrs = ve_db[ve_db["Type"]=="Lorry"]["No"].tolist()
        if lrs:
            with st.form("lr_f", clear_on_submit=True):
                sel = st.selectbox("Lorry", lrs); d_lr = st.date_input("Date"); q = st.number_input("Cubes"); am = st.number_input("Hire Amount"); nt = st.text_input("Trip Details")
                if st.form_submit_button("Log Lorry Trip"):
                    new = pd.DataFrame([[len(df)+1, d_lr, "", "Expense", "Lorry Trip", sel, nt, am, q, 0, 0, "Done"]], columns=df.columns)
                    df = pd.concat([df, new], ignore_index=True); df.to_csv(DATA_FILE, index=False); st.success("Logged!"); st.rerun()

# --- 3. FINANCIALS ---
elif choice == "⛽ Fuel Bill Entry":
    with st.form("fuel_f", clear_on_submit=True):
        d = st.date_input("Date"); v = st.selectbox("Vehicle", ve_db["No"].tolist() if not ve_db.empty else ["None"]); l = st.number_input("Liters"); c = st.number_input("Bill Amount"); s = st.text_input("Shed Name")
        if st.form_submit_button("Log Bill (Credit)"):
            new = pd.DataFrame([[len(df)+1, d, "", "Expense", "Fuel Entry", v, f"Shed: {s}", c, 0, l, 0, "Pending"]], columns=df.columns)
            df = pd.concat([df, new], ignore_index=True); df.to_csv(DATA_FILE, index=False); st.success("Bill Recorded!"); st.rerun()

elif choice == "💳 Shed Credit Settlements":
    pending = df[(df["Category"] == "Fuel Entry") & (df["Status"] == "Pending")]
    if pending.empty: st.success("All clear!")
    else:
        st.dataframe(pending[["Date", "Entity", "Note", "Amount"]], use_container_width=True)
        sel = st.selectbox("Select to Pay", pending.apply(lambda x: f"ID:{x['ID']} | {x['Entity']} | Rs.{x['Amount']}", axis=1))
        if st.button("Mark as Paid ✅"):
            sid = int(sel.split("|")[0].split(":")[1])
            df.loc[df['ID'] == sid, 'Status'] = 'Paid'; df.to_csv(DATA_FILE, index=False); st.rerun()

elif choice == "💸 Driver Payroll":
    if not dr_db.empty:
        with st.form("pay_f", clear_on_submit=True):
            dr = st.selectbox("Driver", dr_db["Name"].tolist()); ty = st.selectbox("Type", ["Advance", "Salary"]); am = st.number_input("Amount")
            if st.form_submit_button("Record Payment"):
                new = pd.DataFrame([[len(df)+1, datetime.now().date(), "", "Expense", ty, dr, "Payroll", am, 0, 0, 0, "Paid"]], columns=df.columns)
                df = pd.concat([df, new], ignore_index=True); df.to_csv(DATA_FILE, index=False); st.rerun()

elif choice == "🧾 Other Expenses":
    with st.form("oth_f", clear_on_submit=True):
        d = st.date_input("Date"); cat = st.selectbox("Category", ["Repair", "Food", "Rent", "Other"]); am = st.number_input("Amount"); nt = st.text_area("Note")
        if st.form_submit_button("Save Expense"):
            new = pd.DataFrame([[len(df)+1, d, "", "Expense", cat, "Admin", nt, am, 0, 0, 0, "Paid"]], columns=df.columns)
            df = pd.concat([df, new], ignore_index=True); df.to_csv(DATA_FILE, index=False); st.rerun()

# --- 4. CONFIGURATION ---
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

elif choice == "📝 General Notes":
    with st.form("nt"):
        t = st.text_input("Title"); m = st.text_area("Details")
        if st.form_submit_button("Save"):
            new = pd.DataFrame([[len(df)+1, datetime.now().date(), "", "Info", "General Note", "Admin", t, 0, 0, 0, 0, m]], columns=df.columns)
            df = pd.concat([df, new], ignore_index=True); df.to_csv(DATA_FILE, index=False); st.rerun()
    for i, r in df[df["Category"]=="General Note"].iloc[::-1].iterrows():
        with st.expander(f"📌 {r['Date']} - {r['Note']}"): st.write(r['Status'])

# --- 5. ADVANCED REPORTS (FILTERED BY DRIVER/VEHICLE) ---
elif choice == "Advanced Reports":
    st.subheader("Filter & Generate Statements")
    
    report_type = st.radio("Select Report Type", ["Driver Summary", "Vehicle/Machine Summary", "Full Transaction Log"], horizontal=True)
    
    col1, col2 = st.columns(2)
    f_date = col1.date_input("From Date", datetime.now().date() - timedelta(days=30))
    t_date = col2.date_input("To Date", datetime.now().date())

    # --- DRIVER SUMMARY ---
    if report_type == "Driver Summary":
        if not dr_db.empty:
            sel_dr = st.selectbox("Select Driver", dr_db["Name"].tolist())
            # Driver ge data filter kirima
            dr_data = df[(df["Entity"] == sel_dr) & (df["Date"] >= f_date) & (df["Date"] <= t_date)]
            
            # Calculations
            advances = dr_data[dr_data["Category"] == "Advance"]["Amount"].sum()
            salary_paid = dr_data[dr_data["Category"] == "Salary Payment"]["Amount"].sum()
            days_worked = len(dr_data[dr_data["Category"] == "Work Entry"]["Date"].unique())
            
            st.info(f"Summary for {sel_dr} from {f_date} to {t_date}")
            c1, c2, c3 = st.columns(3)
            c1.metric("Days Worked", f"{days_worked} Days")
            c2.metric("Total Advances", f"Rs. {advances:,.2f}")
            c3.metric("Salary Paid", f"Rs. {salary_paid:,.2f}")
            
            st.dataframe(dr_data[["Date", "Category", "Note", "Amount"]], use_container_width=True)
            
            if st.button("Generate Driver PDF"):
                fn = create_pdf(f"Driver_{sel_dr}", dr_data, {"Driver": sel_dr, "Period": f"{f_date} to {t_date}", "Work Days": days_worked})
                with open(fn, "rb") as f: st.download_button("📩 Download PDF", f, file_name=fn)
        else: st.warning("No drivers found.")

    # --- VEHICLE SUMMARY ---
    elif report_type == "Vehicle/Machine Summary":
        if not ve_db.empty:
            sel_ve = st.selectbox("Select Vehicle/Machine", ve_db["No"].tolist())
            ve_data = df[(df["Entity"] == sel_ve) & (df["Date"] >= f_date) & (df["Date"] <= t_date)]
            
            # Calculations
            total_fuel = ve_data[ve_data["Category"] == "Fuel Entry"]["Amount"].sum()
            total_work_cost = ve_data[ve_data["Category"].isin(["Machine Work", "Lorry Trip"])]["Amount"].sum()
            total_hrs = ve_data["Hours"].sum()
            total_cubes = ve_data["Qty_Cubes"].sum()
            
            st.info(f"Performance for {sel_ve}")
            v1, v2, v3, v4 = st.columns(4)
            v1.metric("Total Fuel Cost", f"Rs. {total_fuel:,.2f}")
            v2.metric("Operation Cost", f"Rs. {total_work_cost:,.2f}")
            if total_hrs > 0: v3.metric("Total Hours", f"{total_hrs} Hrs")
            if total_cubes > 0: v4.metric("Total Cubes", f"{total_cubes} Cubes")
            
            st.dataframe(ve_data[["Date", "Category", "Note", "Hours", "Qty_Cubes", "Amount"]], use_container_width=True)
            
            if st.button("Generate Vehicle PDF"):
                fn = create_pdf(f"Vehicle_{sel_ve}", ve_data, {"Vehicle": sel_ve, "Total Fuel": total_fuel, "Work Cost": total_work_cost})
                with open(fn, "rb") as f: st.download_button("📩 Download PDF", f, file_name=fn)
        else: st.warning("No vehicles found.")

    # --- FULL LOG ---
    else:
        full_view = df[(df["Date"] >= f_date) & (df["Date"] <= t_date)]
        st.dataframe(full_view, use_container_width=True)
