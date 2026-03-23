import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
from fpdf import FPDF

# --- 1. CONFIG & FILENAMES ---
DATA_FILE = "ksd_master_final_v47.csv"
VE_FILE = "ksd_vehicles_final_v47.csv"
DR_FILE = "ksd_drivers_final_v47.csv"
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
    st.session_state.ve_db = load_data(VE_FILE, ["No", "Type", "Owner", "Rate_Per_Hour"])
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
    cols = ["Date", "Category", "Note", "Qty/Hrs", "Amount"]
    for c in cols: pdf.cell(38, 8, c, 1, 0, 'C')
    pdf.ln(); pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", '', 8)
    for _, row in data_df.iterrows():
        pdf.cell(38, 7, str(row['Date']), 1); pdf.cell(38, 7, str(row['Category']), 1); pdf.cell(38, 7, str(row['Note'])[:20], 1)
        val = row['Hours'] if row['Hours'] > 0 else (row['Qty_Cubes'] if row['Qty_Cubes'] > 0 else "-")
        amt = float(row['Amount']) if not pd.isna(row['Amount']) else 0.0
        pdf.cell(38, 7, f"{val}", 1, 0, 'C'); pdf.cell(38, 7, f"{amt:,.2f}", 1, 0, 'R'); pdf.ln()
    fname = f"Settlement_{datetime.now().strftime('%H%M%S')}.pdf"
    pdf.output(fname); return fname

# --- 5. UI LAYOUT ---
st.set_page_config(page_title=SHOP_NAME, layout="wide", page_icon="🏗️")
st.sidebar.title("🏗️ KSD ERP v4.7")
main_sector = st.sidebar.selectbox("MAIN MENU", ["📊 Dashboard & Data Manager", "🏗️ Site Operations", "💰 Finance & Shed", "⚙️ System Setup", "📑 Reports Center"])

st.markdown(f"<h1 style='text-align: center; color: #E67E22;'>{main_sector}</h1>", unsafe_allow_html=True)

# --- 6. DASHBOARD & DATA MANAGER (v3.7 Full) ---
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
        else: st.info("No data yet.")
    with t2:
        st.subheader("Edit/Delete Transactions")
        if not st.session_state.df.empty:
            for i, row in st.session_state.df.iloc[::-1].head(20).iterrows():
                c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
                c1.write(f"**{row['Date']}** | {row['Category']} ({row['Entity']})")
                amt_val = float(row['Amount']) if not pd.isna(row['Amount']) else 0.0
                c2.write(f"Rs. {amt_val:,.2f}"); c3.write(f"Note: {row['Note']}")
                if c4.button("🗑️", key=f"del_{i}"):
                    st.session_state.df = st.session_state.df.drop(i); save_all(); st.rerun()

# --- 7. SITE OPERATIONS (v3.7 Full + Machine Log) ---
elif main_sector == "🏗️ Site Operations":
    op = st.sidebar.radio("Activity", ["🚚 Stock In (Soil)", "💰 Sales Out (Sand/Soil)", "🚜 Machine Work Log"])
    if op == "🚚 Stock In (Soil)":
        with st.form("stk_f"):
            d = st.date_input("Date"); v = st.text_input("Supplier/Vehicle"); q = st.number_input("Cubes")
            if st.form_submit_button("Add Stock"):
                new = pd.DataFrame([[len(st.session_state.df)+1, d, "", "Process", "Soil In", v, "Inbound", 0, q, 0, 0, "Done"]], columns=st.session_state.df.columns)
                st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()
    elif op == "💰 Sales Out (Sand/Soil)":
        with st.form("sale_f"):
            d = st.date_input("Date"); it = st.selectbox("Item", ["Sand Sale", "Soil Sale"]); q = st.number_input("Cubes"); a = st.number_input("Amount")
            if st.form_submit_button("Record Sale"):
                new = pd.DataFrame([[len(st.session_state.df)+1, d, "", "Income", it, "Cash", "Sale Out", a, q, 0, 0, "Paid"]], columns=st.session_state.df.columns)
                st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()
    elif op == "🚜 Machine Work Log":
        st.subheader("Log Machine Work Hours")
        v_list = st.session_state.ve_db["No"].tolist()
        if v_list:
            with st.form("mach_f"):
                v = st.selectbox("Select Machine", v_list); d = st.date_input("Date"); h = st.number_input("Hours Worked"); n = st.text_input("Location/Note")
                if st.form_submit_button("Log Hours"):
                    new = pd.DataFrame([[len(st.session_state.df)+1, d, "", "Process", "Work Hours", v, n, 0, 0, 0, h, "Done"]], columns=st.session_state.df.columns)
                    st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()
        else: st.warning("Please add vehicles in System Setup.")

# --- 8. FINANCE & SHED (v3.7 Full + Owner/Driver Advances) ---
elif main_sector == "💰 Finance & Shed":
    fin = st.sidebar.radio("Finance", ["⛽ Fuel & Shed", "🔧 Repairs", "💸 Payroll & Advance", "🧾 Others", "🏦 Owner Advances"])
    v_list = st.session_state.ve_db["No"].tolist()
    
    if fin == "⛽ Fuel & Shed":
        t1, t2 = st.tabs(["⛽ Log Fuel Bill", "💳 Settle Shed Payments"])
        with t1:
            with st.form("fuel"):
                d = st.date_input("Date"); v = st.selectbox("Vehicle", v_list if v_list else ["N/A"]); l = st.number_input("Liters"); c = st.number_input("Bill Cost"); s = st.text_input("Shed Name")
                if st.form_submit_button("Save Fuel Bill"):
                    new = pd.DataFrame([[len(st.session_state.df)+1, d, "", "Expense", "Fuel Entry", v, f"Shed: {s}", c, 0, l, 0, "Pending"]], columns=st.session_state.df.columns)
                    st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()
        with t2:
            with st.form("shed_pay"):
                p_amt = st.number_input("Amount Paid"); p_ref = st.text_input("Reference (Slip/Cheque)")
                if st.form_submit_button("Record Payment"):
                    new = pd.DataFrame([[len(st.session_state.df)+1, datetime.now().date(), "", "Expense", "Shed Payment", "Shed", p_ref, p_amt, 0, 0, 0, "Paid"]], columns=st.session_state.df.columns)
                    st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()
    elif fin == "🔧 Repairs":
        with st.form("rep"):
            v = st.selectbox("Vehicle", v_list if v_list else ["N/A"]); n = st.text_input("Repair Details"); a = st.number_input("Cost")
            if st.form_submit_button("Save Repair"):
                new = pd.DataFrame([[len(st.session_state.df)+1, datetime.now().date(), "", "Expense", "Repair", v, n, a, 0, 0, 0, "Paid"]], columns=st.session_state.df.columns)
                st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()
    elif fin == "💸 Payroll & Advance":
        with st.form("pay"):
            dr = st.selectbox("Driver", st.session_state.dr_db["Name"].tolist() if not st.session_state.dr_db.empty else ["N/A"])
            am = st.number_input("Amount"); ty = st.selectbox("Type", ["Driver Advance", "Salary", "Food Allowance"]); v_rel = st.selectbox("Related Vehicle", v_list if v_list else ["N/A"])
            if st.form_submit_button("Save Payroll"):
                new = pd.DataFrame([[len(st.session_state.df)+1, datetime.now().date(), "", "Expense", ty, v_rel, f"Driver: {dr}", am, 0, 0, 0, "Paid"]], columns=st.session_state.df.columns)
                st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()
    elif fin == "🏦 Owner Advances":
        with st.form("own_adv"):
            v = st.selectbox("Vehicle/Owner", v_list if v_list else ["N/A"]); am = st.number_input("Advance Amount"); nt = st.text_input("Note")
            if st.form_submit_button("Save Owner Advance"):
                new = pd.DataFrame([[len(st.session_state.df)+1, datetime.now().date(), "", "Expense", "Owner Advance", v, nt, am, 0, 0, 0, "Paid"]], columns=st.session_state.df.columns)
                st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()
    elif fin == "🧾 Others":
        with st.form("oth"):
            cat = st.selectbox("Category", ["Food", "Rent", "Utility", "Misc"]); nt = st.text_area("Note"); am = st.number_input("Amount")
            if st.form_submit_button("Save Other"):
                new = pd.DataFrame([[len(st.session_state.df)+1, datetime.now().date(), "", "Expense", cat, "Admin", nt, am, 0, 0, 0, "Paid"]], columns=st.session_state.df.columns)
                st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()

# --- 9. SYSTEM SETUP ---
elif main_sector == "⚙️ System Setup":
    s1, s2 = st.tabs(["👷 Drivers", "🚜 Vehicles & Rates"])
    with s1:
        with st.form("dr"):
            n = st.text_input("Name"); p = st.text_input("Phone"); s = st.number_input("Daily Salary")
            if st.form_submit_button("Add Driver"):
                new = pd.DataFrame([[n,p,s]], columns=st.session_state.dr_db.columns)
                st.session_state.dr_db = pd.concat([st.session_state.dr_db, new], ignore_index=True); save_all(); st.rerun()
        st.table(st.session_state.dr_db)
    with s2:
        with st.form("ve"):
            v = st.text_input("Vehicle No"); t = st.selectbox("Type", ["Excavator", "Lorry"]); r = st.number_input("Rate Per Hour (Rs.)"); o = st.text_input("Owner")
            if st.form_submit_button("Add Vehicle"):
                new = pd.DataFrame([[v,t,o,r]], columns=st.session_state.ve_db.columns)
                st.session_state.ve_db = pd.concat([st.session_state.ve_db, new], ignore_index=True); save_all(); st.rerun()
        st.table(st.session_state.ve_db)

# --- 10. REPORTS CENTER (FIXED ALL ERRORS) ---
elif main_sector == "📑 Reports Center":
    st.subheader("Vehicle Owner Settlement Sheet")
    v_list = st.session_state.ve_db["No"].tolist()
    
    if not v_list:
        st.warning("No vehicles found. Please add them in System Setup.")
    else:
        # sel_ve මෙතන define කරන නිසා NameError එක එන්නේ නැහැ
        sel_ve = st.selectbox("Select Vehicle", v_list)
        f_date = st.date_input("From", datetime.now().date()-timedelta(days=30))
        t_date = st.date_input("To", datetime.now().date())
        
        # Safe rate fetching
        m_ve = st.session_state.ve_db[st.session_state.ve_db["No"] == sel_ve]
        rate = m_ve["Rate_Per_Hour"].values[0] if not m_ve.empty else 0.0
        
        # Filtering data
        rep_df = st.session_state.df[(st.session_state.df["Entity"] == sel_ve) & (st.session_state.df["Date"]>=f_date) & (st.session_state.df["Date"]<=t_date)]
        
        if not rep_df.empty:
            t_hrs = rep_df[rep_df["Category"] == "Work Hours"]["Hours"].sum()
            g_pay = t_hrs * rate
            fuel = rep_df[rep_df["Category"] == "Fuel Entry"]["Amount"].sum()
            repairs = rep_df[rep_df["Category"] == "Repair"]["Amount"].sum()
            d_adv = rep_df[rep_df["Category"] == "Driver Advance"]["Amount"].sum()
            o_adv = rep_df[rep_df["Category"] == "Owner Advance"]["Amount"].sum()
            
            total_exp = fuel + repairs + d_adv + o_adv
            net = g_pay - total_exp
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Hours", f"{t_hrs} Hrs"); c2.metric("Gross Pay", f"Rs. {g_pay:,.2f}"); c3.metric("NET TO OWNER", f"Rs. {net:,.2f}")
            
            st.divider()
            st.markdown(f"**Deductions:** Fuel: {fuel:,.2f} | Repair: {repairs:,.2f} | Driver Adv: {d_adv:,.2f} | Owner Adv: {o_adv:,.2f}")
            st.dataframe(rep_df[["Date", "Category", "Note", "Hours", "Amount"]], use_container_width=True)
            
            if st.button("Generate Settlement PDF"):
                summary = {"Vehicle": sel_ve, "Total Hours": t_hrs, "Gross": g_pay, "Expenses": total_exp, "Net Balance": net}
                fn = create_pdf(f"Settlement_{sel_ve}", rep_df, summary)
                with open(fn, "rb") as fl: st.download_button("📩 Download PDF", fl, file_name=fn)
        else:
            st.info("No records found for this period.")
