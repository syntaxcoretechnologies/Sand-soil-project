import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
from fpdf import FPDF

# --- CONFIG & FILENAMES ---
DATA_FILE = "ksd_master_final_v25.csv"
VE_FILE = "ksd_vehicles_final_v25.csv"
DR_FILE = "ksd_drivers_final_v25.csv"
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
st.sidebar.title("🛠️ KSD ERP v1.0")
main_sector = st.sidebar.selectbox("MAIN MENU", [
    "📊 Dashboard", 
    "🏗️ Site Operations", 
    "💰 Finance & Shed", 
    "⚙️ System Setup", 
    "📑 Reports Center"
])

choice = ""
if main_sector == "📊 Dashboard": choice = "Dashboard"
elif main_sector == "🏗️ Site Operations": choice = st.sidebar.radio("Activity", ["🚚 Stock In (Soil)", "💰 Sales Out (Sand/Soil)", "🚜 Machine Performance"])
elif main_sector == "💰 Finance & Shed": choice = st.sidebar.radio("Finance", ["⛽ Fuel & Shed Payments", "💸 Driver Payroll", "🧾 Other Expenses"])
elif main_sector == "⚙️ System Setup": choice = st.sidebar.radio("Setup", ["👷 Driver Setup", "🚜 Vehicle Setup", "📝 General Notes"])
elif main_sector == "📑 Reports Center": choice = "Advanced Reports"

st.markdown(f"<h1 style='text-align: center; color: #E67E22;'>{choice}</h1>", unsafe_allow_html=True)

# --- 1. DASHBOARD ---
if choice == "Dashboard":
    ti = df[df["Type"] == "Income"]["Amount"].sum()
    te = df[df["Type"] == "Expense"]["Amount"].sum()
    # Fuel Debt Logic
    total_f_bills = df[df["Category"] == "Fuel Entry"]["Amount"].sum()
    total_f_paid = df[df["Category"] == "Shed Payment"]["Amount"].sum()
    fuel_debt = total_f_bills - total_f_paid

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
        st.write("### 📂 Expense Breakdown")
        if not df.empty:
            exp_sum = df[df["Type"]=="Expense"].groupby("Category")["Amount"].sum()
            st.bar_chart(exp_sum)

# --- 2. SITE OPERATIONS ---
elif choice == "🚚 Stock In (Soil)":
    with st.form("stk_f"):
        d = st.date_input("Date"); v = st.text_input("Supplier/Vehicle"); q = st.number_input("Cubes", min_value=0.0)
        if st.form_submit_button("Add Stock"):
            new = pd.DataFrame([[len(df)+1, d, "", "Process", "Soil In", v, "Inbound", 0, q, 0, 0, "Done"]], columns=df.columns)
            df = pd.concat([df, new], ignore_index=True); df.to_csv(DATA_FILE, index=False); st.rerun()

elif choice == "💰 Sales Out (Sand/Soil)":
    with st.form("sale_f"):
        d = st.date_input("Date"); it = st.selectbox("Item", ["Sand Sale", "Soil Sale"]); q = st.number_input("Cubes", min_value=0.0); a = st.number_input("Amount", min_value=0.0)
        if st.form_submit_button("Record Sale"):
            new = pd.DataFrame([[len(df)+1, d, "", "Income", it, "Cash", "Sale Out", a, q, 0, 0, "Paid"]], columns=df.columns)
            df = pd.concat([df, new], ignore_index=True); df.to_csv(DATA_FILE, index=False); st.rerun()

elif choice == "🚜 Machine Performance":
    t1, t2 = st.tabs(["🏗️ Excavator", "🚚 Lorry"])
    with t1:
        exs = ve_db[ve_db["Type"]=="Excavator"]["No"].tolist()
        if exs:
            with st.form("ex_f", clear_on_submit=True):
                sel = st.selectbox("Select Excavator", exs); d_ex = st.date_input("Date"); h = st.number_input("Hours Worked", min_value=0.0); am = st.number_input("Payment/Cost", min_value=0.0); nt = st.text_input("Job Description")
                if st.form_submit_button("Log Excavator"):
                    new = pd.DataFrame([[len(df)+1, d_ex, "", "Expense", "Machine Work", sel, nt, am, 0, 0, h, "Done"]], columns=df.columns)
                    df = pd.concat([df, new], ignore_index=True); df.to_csv(DATA_FILE, index=False); st.success("Logged!"); st.rerun()
    with t2:
        lrs = ve_db[ve_db["Type"]=="Lorry"]["No"].tolist()
        if lrs:
            with st.form("lr_f", clear_on_submit=True):
                sel = st.selectbox("Select Lorry", lrs); d_lr = st.date_input("Date"); q = st.number_input("Cubes Transported", min_value=0.0); am = st.number_input("Hire/Cost", min_value=0.0); nt = st.text_input("Trip Details")
                if st.form_submit_button("Log Lorry Trip"):
                    new = pd.DataFrame([[len(df)+1, d_lr, "", "Expense", "Lorry Trip", sel, nt, am, q, 0, 0, "Done"]], columns=df.columns)
                    df = pd.concat([df, new], ignore_index=True); df.to_csv(DATA_FILE, index=False); st.success("Logged!"); st.rerun()

# --- 3. FINANCE & SHED ---
elif choice == "⛽ Fuel & Shed Payments":
    tab1, tab2 = st.tabs(["⛽ Log New Fuel Bill", "💳 Settle Shed Payments"])
    with tab1:
        st.subheader("Log Credit Fuel Bill")
        with st.form("fuel_f", clear_on_submit=True):
            d = st.date_input("Date"); v = st.selectbox("Vehicle", ve_db["No"].tolist() if not ve_db.empty else ["None"]); l = st.number_input("Liters", min_value=0.0); c = st.number_input("Bill Cost", min_value=0.0); s = st.text_input("Shed Name")
            if st.form_submit_button("Save Bill (Credit)"):
                new = pd.DataFrame([[len(df)+1, d, "", "Expense", "Fuel Entry", v, f"Shed: {s}", c, 0, l, 0, "Pending"]], columns=df.columns)
                df = pd.concat([df, new], ignore_index=True); df.to_csv(DATA_FILE, index=False); st.success("Recorded!"); st.rerun()
    with tab2:
        # Debt calculation
        total_fb = df[df["Category"] == "Fuel Entry"]["Amount"].sum()
        total_fp = df[df["Category"] == "Shed Payment"]["Amount"].sum()
        rem_debt = total_fb - total_fp
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Fuel Cost", f"Rs. {total_fb:,.2f}")
        c2.metric("Total Paid", f"Rs. {total_fp:,.2f}")
        c3.metric("Remaining Debt", f"Rs. {rem_debt:,.2f}", delta_color="inverse")
        
        st.divider()
        st.subheader("Add Payment to Shed")
        with st.form("shed_pay"):
            p_date = st.date_input("Payment Date"); p_amt = st.number_input("Amount (Rs.)", min_value=0.0); p_ref = st.text_input("Reference (Cheque/Slip)")
            if st.form_submit_button("Record Payment"):
                new = pd.DataFrame([[len(df)+1, p_date, "", "Expense", "Shed Payment", "Shed", p_ref, p_amt, 0, 0, 0, "Paid"]], columns=df.columns)
                df = pd.concat([df, new], ignore_index=True); df.to_csv(DATA_FILE, index=False); st.success("Shed Payment Saved!"); st.rerun()

elif choice == "💸 Driver Payroll":
    if not dr_db.empty:
        with st.form("pay"):
            dr = st.selectbox("Driver", dr_db["Name"].tolist()); ty = st.selectbox("Type", ["Advance", "Salary Payment"]); am = st.number_input("Amount", min_value=0.0)
            if st.form_submit_button("Save Payroll Entry"):
                new = pd.DataFrame([[len(df)+1, datetime.now().date(), "", "Expense", ty, dr, "Payroll", am, 0, 0, 0, "Paid"]], columns=df.columns)
                df = pd.concat([df, new], ignore_index=True); df.to_csv(DATA_FILE, index=False); st.rerun()

elif choice == "🧾 Other Expenses":
    with st.form("oth"):
        d = st.date_input("Date"); cat = st.selectbox("Type", ["Repair", "Food", "Maintenance", "Rent", "Other"]); amt = st.number_input("Amount", min_value=0.0); nt = st.text_area("Note")
        if st.form_submit_button("Save Expense"):
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
        t = st.text_input("Title"); m = st.text_area("Details")
        if st.form_submit_button("Save Note"):
            new = pd.DataFrame([[len(df)+1, datetime.now().date(), "", "Info", "General Note", "Admin", t, 0, 0, 0, 0, m]], columns=df.columns)
            df = pd.concat([df, new], ignore_index=True); df.to_csv(DATA_FILE, index=False); st.rerun()
    for i, r in df[df["Category"]=="General Note"].iloc[::-1].iterrows():
        with st.expander(f"📌 {r['Date']} - {r['Note']}"): st.write(r['Status'])

# --- 5. ADVANCED REPORTS ---
elif choice == "Advanced Reports":
    st.subheader("Statement Generator")
    rep_mode = st.radio("Statement For", ["Driver", "Vehicle/Machine", "Shed Balance", "All Transactions"], horizontal=True)
    f = st.date_input("From", datetime.now().date()-timedelta(days=30)); t = st.date_input("To")
    
    rep_df = df[(df["Date"]>=f) & (df["Date"]<=t)]
    
    if rep_mode == "Driver" and not dr_db.empty:
        sel = st.selectbox("Select Driver", dr_db["Name"].tolist())
        rep_df = rep_df[rep_df["Entity"] == sel]
        st.dataframe(rep_df, use_container_width=True)
    
    elif rep_mode == "Vehicle/Machine" and not ve_db.empty:
        sel = st.selectbox("Select Vehicle", ve_db["No"].tolist())
        rep_df = rep_df[rep_df["Entity"] == sel]
        st.dataframe(rep_df, use_container_width=True)
        
    elif rep_mode == "Shed Balance":
        rep_df = rep_df[rep_df["Category"].isin(["Fuel Entry", "Shed Payment"])]
        st.dataframe(rep_df, use_container_width=True)

    else:
        st.dataframe(rep_df, use_container_width=True)
    
    if st.button("Generate PDF Statement"):
        fn = create_pdf("KSD_Report", rep_df, {"Period": f"{f} to {t}", "Report Type": rep_mode})
        with open(fn, "rb") as fl: st.download_button("📩 Download PDF", fl, file_name=fn)
