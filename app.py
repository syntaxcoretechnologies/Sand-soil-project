import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
from fpdf import FPDF

# --- 1. CONFIG & FILENAMES ---
DATA_FILE = "ksd_master_final_v37.csv"
VE_FILE = "ksd_vehicles_final_v37.csv"
DR_FILE = "ksd_drivers_final_v37.csv"
SHOP_NAME = "K. SIRIWARDHANA SAND CONSTRUCTION PRO"

# --- 2. DATA ENGINE (LOCAL CSV STORAGE) ---
def load_data(file, cols):
    if os.path.exists(file): 
        try:
            d = pd.read_csv(file)
            if 'Date' in d.columns:
                d['Date'] = pd.to_datetime(d['Date']).dt.date
            return d
        except:
            return pd.DataFrame(columns=cols)
    return pd.DataFrame(columns=cols)

def save_all():
    st.session_state.df.to_csv(DATA_FILE, index=False)
    st.session_state.ve_db.to_csv(VE_FILE, index=False)
    st.session_state.dr_db.to_csv(DR_FILE, index=False)

# --- 3. SESSION STATE INITIALIZATION ---
if 'df' not in st.session_state:
    st.session_state.df = load_data(DATA_FILE, ["ID", "Date", "Time", "Type", "Category", "Entity", "Note", "Amount", "Qty_Cubes", "Fuel_Ltr", "Hours", "Status"])
if 've_db' not in st.session_state:
    st.session_state.ve_db = load_data(VE_FILE, ["No", "Type", "Owner", "Current_Driver"])
if 'dr_db' not in st.session_state:
    st.session_state.dr_db = load_data(DR_FILE, ["Name", "Phone", "Daily_Salary"])

# --- 4. PDF REPORT GENERATOR ---
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

# --- 5. UI LAYOUT & SIDEBAR ---
st.set_page_config(page_title=SHOP_NAME, layout="wide", page_icon="🏗️")
st.sidebar.title("🏗️ KSD ERP v3.7")
main_sector = st.sidebar.selectbox("MAIN MENU", ["📊 Dashboard & Data Manager", "🏗️ Site Operations", "💰 Finance & Shed", "⚙️ System Setup", "📑 Reports Center"])

st.markdown(f"<h1 style='text-align: center; color: #E67E22;'>{main_sector}</h1>", unsafe_allow_html=True)

# --- 6. SECTOR: DASHBOARD & DATA MANAGER ---
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
            m1.metric("Total Income", f"Rs. {ti:,.2f}")
            m2.metric("Total Expenses", f"Rs. {te:,.2f}")
            m3.metric("Net Profit", f"Rs. {ti-te:,.2f}")
            m4.metric("Shed Debt", f"Rs. {f_debt:,.2f}", delta_color="inverse")
            st.divider()
            daily = df.groupby(['Date', 'Type'])['Amount'].sum().unstack().fillna(0)
            st.area_chart(daily)
        else:
            st.info("No data yet. Go to Site Operations or Finance to add records.")
            
    with t2:
        st.subheader("Edit/Delete Transactions")
        if not st.session_state.df.empty:
            for i, row in st.session_state.df.iloc[::-1].head(20).iterrows():
                c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
                c1.write(f"**{row['Date']}** | {row['Category']} ({row['Entity']})")
                amt_val = float(row['Amount']) if not pd.isna(row['Amount']) else 0.0
                c2.write(f"Rs. {amt_val:,.2f}")
                c3.write(f"Note: {row['Note']}")
                if c4.button("🗑️", key=f"del_{i}"):
                    st.session_state.df = st.session_state.df.drop(i); save_all(); st.rerun()

# --- 7. SECTOR: SITE OPERATIONS ---
elif main_sector == "🏗️ Site Operations":
    op = st.sidebar.radio("Activity", ["🚚 Stock In (Soil)", "💰 Sales Out (Sand/Soil)", "🚜 Machine Performance"])
    
    if op == "🚚 Stock In (Soil)":
        with st.form("stk_f"):
            d = st.date_input("Date"); v = st.text_input("Supplier/Vehicle"); q = st.number_input("Cubes", min_value=0.0)
            if st.form_submit_button("Add Stock"):
                new = pd.DataFrame([[len(st.session_state.df)+1, d, "", "Process", "Soil In", v, "Inbound", 0, q, 0, 0, "Done"]], columns=st.session_state.df.columns)
                st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()

    elif op == "💰 Sales Out (Sand/Soil)":
        with st.form("sale_f"):
            d = st.date_input("Date"); it = st.selectbox("Item", ["Sand Sale", "Soil Sale"]); q = st.number_input("Cubes"); a = st.number_input("Amount")
            if st.form_submit_button("Record Sale"):
                new = pd.DataFrame([[len(st.session_state.df)+1, d, "", "Income", it, "Cash", "Sale Out", a, q, 0, 0, "Paid"]], columns=st.session_state.df.columns)
                st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()

    elif op == "🚜 Machine Performance":
        t1, t2 = st.tabs(["🏗️ Excavator", "🚚 Lorry"])
        with t1:
            exs = st.session_state.ve_db[st.session_state.ve_db["Type"]=="Excavator"]["No"].tolist()
            with st.form("ex_f", clear_on_submit=True):
                sel = st.selectbox("Select Excavator", exs if exs else ["None"]); d_ex = st.date_input("Date"); h = st.number_input("Hours Worked"); am = st.number_input("Cost"); nt = st.text_input("Note")
                if st.form_submit_button("Log Excavator"):
                    new = pd.DataFrame([[len(st.session_state.df)+1, d_ex, "", "Expense", "Machine Work", sel, nt, am, 0, 0, h, "Done"]], columns=st.session_state.df.columns)
                    st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()
        with t2:
            lrs = st.session_state.ve_db[st.session_state.ve_db["Type"]=="Lorry"]["No"].tolist()
            with st.form("lr_f", clear_on_submit=True):
                sel = st.selectbox("Select Lorry", lrs if lrs else ["None"]); d_lr = st.date_input("Date"); q = st.number_input("Cubes"); am = st.number_input("Hire Cost"); nt = st.text_input("Trip Details")
                if st.form_submit_button("Log Lorry Trip"):
                    new = pd.DataFrame([[len(st.session_state.df)+1, d_lr, "", "Expense", "Lorry Trip", sel, nt, am, q, 0, 0, "Done"]], columns=st.session_state.df.columns)
                    st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()

# --- 8. SECTOR: FINANCE & SHED ---
elif main_sector == "💰 Finance & Shed":
    fin = st.sidebar.radio("Finance", ["⛽ Fuel & Shed Payments", "🔧 Vehicle Repairs", "💸 Driver Payroll", "🧾 Other Expenses"])
    
    if fin == "⛽ Fuel & Shed Payments":
        t1, t2 = st.tabs(["⛽ Log Fuel Bill", "💳 Settle Shed Payments"])
        with t1:
            with st.form("fuel_f", clear_on_submit=True):
                d = st.date_input("Date"); v = st.selectbox("Vehicle", st.session_state.ve_db["No"].tolist()); l = st.number_input("Liters"); c = st.number_input("Bill Cost"); s = st.text_input("Shed Name")
                if st.form_submit_button("Save Fuel Bill"):
                    new = pd.DataFrame([[len(st.session_state.df)+1, d, "", "Expense", "Fuel Entry", v, f"Shed: {s}", c, 0, l, 0, "Pending"]], columns=st.session_state.df.columns)
                    st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()
        with t2:
            st.subheader("Shed Settlement")
            with st.form("shed_pay"):
                p_amt = st.number_input("Amount Paid"); p_ref = st.text_input("Reference (Slip/Cheque)")
                if st.form_submit_button("Record Payment"):
                    new = pd.DataFrame([[len(st.session_state.df)+1, datetime.now().date(), "", "Expense", "Shed Payment", "Shed", p_ref, p_amt, 0, 0, 0, "Paid"]], columns=st.session_state.df.columns)
                    st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()

    elif fin == "🔧 Vehicle Repairs":
        st.subheader("Log Vehicle Repairs")
        with st.form("rep_f"):
            v_list = st.session_state.ve_db["No"].tolist()
            v = st.selectbox("Vehicle", v_list if v_list else ["None"]); n = st.text_input("What was repaired?"); a = st.number_input("Repair Cost")
            if st.form_submit_button("Save Repair Entry"):
                new = pd.DataFrame([[len(st.session_state.df)+1, datetime.now().date(), "", "Expense", "Repair", v, n, a, 0, 0, 0, "Paid"]], columns=st.session_state.df.columns)
                st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()

    elif fin == "💸 Driver Payroll":
        with st.form("pay_f"):
            dr_list = st.session_state.dr_db["Name"].tolist()
            dr = st.selectbox("Driver", dr_list if dr_list else ["None"]); am = st.number_input("Amount"); ty = st.selectbox("Type", ["Advance", "Salary", "Food Allowance"])
            if st.form_submit_button("Save Payroll"):
                new = pd.DataFrame([[len(st.session_state.df)+1, datetime.now().date(), "", "Expense", ty, dr, "Payroll", am, 0, 0, 0, "Paid"]], columns=st.session_state.df.columns)
                st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()

    elif fin == "🧾 Other Expenses":
        st.subheader("General Expenses (Food/Rent/Utility)")
        with st.form("oth_f"):
            cat = st.selectbox("Category", ["Food", "Rent", "Utility", "Maintenance", "Misc"]); nt = st.text_area("Note"); am = st.number_input("Amount")
            if st.form_submit_button("Save Other Expense"):
                new = pd.DataFrame([[len(st.session_state.df)+1, datetime.now().date(), "", "Expense", cat, "Admin", nt, am, 0, 0, 0, "Paid"]], columns=st.session_state.df.columns)
                st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()

# --- 9. SECTOR: SYSTEM SETUP ---
elif main_sector == "⚙️ System Setup":
    s1, s2 = st.tabs(["👷 Drivers", "🚜 Vehicles"])
    with s1:
        with st.form("dr_f"):
            n = st.text_input("Name"); p = st.text_input("Phone"); s = st.number_input("Daily Salary")
            if st.form_submit_button("Add Driver"):
                new = pd.DataFrame([[n,p,s]], columns=st.session_state.dr_db.columns)
                st.session_state.dr_db = pd.concat([st.session_state.dr_db, new], ignore_index=True); save_all(); st.rerun()
        st.table(st.session_state.dr_db)
        for i, r in st.session_state.dr_db.iterrows():
            if st.button(f"🗑️ Delete {r['Name']}", key=f"dr_{i}"):
                st.session_state.dr_db = st.session_state.dr_db.drop(i); save_all(); st.rerun()

    with s2:
        with st.form("ve_f"):
            v = st.text_input("No"); t = st.selectbox("Type", ["Lorry", "Excavator"]); o = st.text_input("Owner")
            if st.form_submit_button("Add Vehicle"):
                new = pd.DataFrame([[v,t,o,""]], columns=st.session_state.ve_db.columns)
                st.session_state.ve_db = pd.concat([st.session_state.ve_db, new], ignore_index=True); save_all(); st.rerun()
        st.table(st.session_state.ve_db)
        for i, r in st.session_state.ve_db.iterrows():
            if st.button(f"🗑️ Delete {r['No']}", key=f"ve_{i}"):
                st.session_state.ve_db = st.session_state.ve_db.drop(i); save_all(); st.rerun()

# --- 10. SECTOR: REPORTS CENTER (UPDATED) ---
elif main_sector == "📑 Reports Center":
    st.subheader("Advanced Statement Generator")
    rep_mode = st.radio("Statement For", ["Vehicle Summary", "Driver Summary", "General Transactions"], horizontal=True)
    f = st.date_input("From", datetime.now().date()-timedelta(days=30)); t = st.date_input("To")
    
    # Base filter by date
    rep_df = st.session_state.df[(st.session_state.df["Date"]>=f) & (st.session_state.df["Date"]<=t)]
    summary_data = {"Period": f"{f} to {t}", "Type": rep_mode}
    
    if rep_mode == "Driver Summary":
        dr_list = st.session_state.dr_db["Name"].tolist()
        if dr_list:
            sel_dr = st.selectbox("Select Driver", dr_list)
            rep_df = rep_df[rep_df["Entity"] == sel_dr]
            
            # Sub-metrics for Driver
            adv = rep_df[rep_df["Category"] == "Advance"]["Amount"].sum()
            sal = rep_df[rep_df["Category"] == "Salary"]["Amount"].sum()
            food = rep_df[rep_df["Category"] == "Food Allowance"]["Amount"].sum()
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Advances Taken", f"Rs. {adv:,.2f}")
            c2.metric("Salaries Paid", f"Rs. {sal:,.2f}")
            c3.metric("Total Paid Out", f"Rs. {adv+sal+food:,.2f}")
            
            summary_data["Driver"] = sel_dr
            summary_data["Total Payout"] = f"Rs. {adv+sal+food:,.2f}"
        else:
            st.warning("Please add drivers first.")

    elif rep_mode == "Vehicle Summary":
        v_list = st.session_state.ve_db["No"].tolist()
        if v_list:
            sel_ve = st.selectbox("Select Vehicle", v_list)
            rep_df = rep_df[rep_df["Entity"] == sel_ve]
            f_cost = rep_df[rep_df["Category"] == "Fuel Entry"]["Amount"].sum()
            rep_cost = rep_df[rep_df["Category"] == "Repair"]["Amount"].sum()
            
            c1, c2 = st.columns(2)
            c1.metric("Fuel Cost", f"Rs. {f_cost:,.2f}")
            c2.metric("Repair Cost", f"Rs. {rep_cost:,.2f}")
            
            summary_data["Vehicle"] = sel_ve
            summary_data["Total Maintenance"] = f"Rs. {f_cost+rep_cost:,.2f}"

    st.dataframe(rep_df, use_container_width=True)
    if st.button("Generate PDF Statement"):
        fn = create_pdf(f"KSD_{rep_mode}", rep_df, summary_data)
        with open(fn, "rb") as fl: st.download_button("📩 Download PDF", fl, file_name=fn)
