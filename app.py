import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
from fpdf import FPDF

# --- 1. CONFIG & FILENAMES ---
DATA_FILE = "ksd_master_v61.csv"
VE_FILE = "ksd_vehicles_v61.csv"
DR_FILE = "ksd_drivers_v61.csv"
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

# --- 4. PDF GENERATOR ---
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 14); self.set_text_color(230, 126, 34) 
        self.cell(0, 10, SHOP_NAME, 0, 1, 'C'); self.ln(5)

def create_generic_pdf(title, data_df, summary_dict, columns_to_show):
    pdf = PDF(); pdf.add_page(); pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, f"REPORT: {title.upper()}", 1, 1, 'L'); pdf.ln(5)
    for k, v in summary_dict.items():
        pdf.set_font("Arial", 'B', 10); pdf.cell(50, 8, f"{k}:", 1, 0, 'L'); pdf.set_font("Arial", '', 10); pdf.cell(0, 8, f" {v}", 1, 1)
    pdf.ln(5); pdf.set_font("Arial", 'B', 8); col_width = 190 / len(columns_to_show)
    for c in columns_to_show: pdf.cell(col_width, 8, c, 1, 0, 'C')
    pdf.ln(); pdf.set_font("Arial", '', 8)
    for _, row in data_df.iterrows():
        for c in columns_to_show: pdf.cell(col_width, 7, str(row[c])[:25], 1)
        pdf.ln()
    fname = f"{title.replace(' ', '_')}.pdf"; pdf.output(fname); return fname

# --- 5. UI SETUP (v47 Navigation Style) ---
st.set_page_config(page_title=SHOP_NAME, layout="wide")
st.markdown(f"<h1 style='text-align: center; color: #E67E22;'>🏗️ {SHOP_NAME}</h1>", unsafe_allow_html=True)

with st.sidebar:
    st.title("Main Menu")
    menu = st.radio("SELECT SECTION", ["📊 DASHBOARD", "🏗️ SITE OPERATIONS", "⛽ SHED & FUEL", "💸 FINANCE & PAYROLL", "📑 REPORTS CENTER", "⚙️ SYSTEM SETUP"])
    st.divider()
    st.success("Final Master v6.1")

# --- 6. DASHBOARD ---
if menu == "📊 DASHBOARD":
    st.subheader("Business Analytics Overview")
    df = st.session_state.df
    if not df.empty:
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
        ti = df[df["Type"] == "Income"]["Amount"].sum()
        te = df[df["Type"] == "Expense"]["Amount"].sum()
        # Calculate Shed Debt (Unpaid fuel bills)
        debt = df[(df["Category"] == "Fuel Entry") & (df["Status"] == "Unpaid")]["Amount"].sum()
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Income", f"Rs. {ti:,.2f}")
        c2.metric("Total Expense", f"Rs. {te:,.2f}")
        c3.metric("Net Cash", f"Rs. {ti-te:,.2f}")
        c4.metric("SHED DEBT", f"Rs. {debt:,.2f}", delta="-Credit", delta_color="inverse")
        
        st.divider()
        st.subheader("Manage Records (Last 15 Activities)")
        for i, row in st.session_state.df.iloc[::-1].head(15).iterrows():
            col1, col2, col3, col4 = st.columns([5, 2, 2, 1])
            col1.write(f"**{row['Date']}** | {row['Category']} - {row['Entity']}")
            col2.write(f"Rs. {row['Amount']:,.2f}")
            col3.write(f"[{row['Status']}]")
            if col4.button("🗑️", key=f"del_{i}"):
                st.session_state.df = st.session_state.df.drop(i); save_all(); st.rerun()

# --- 7. SITE OPERATIONS ---
elif menu == "🏗️ SITE OPERATIONS":
    t1, t2, t3 = st.tabs(["🚛 Lorry (Soil/Sand In)", "🚜 Excavator Hours", "💰 Sales Log"])
    v_list = st.session_state.ve_db["No"].tolist() if not st.session_state.ve_db.empty else ["N/A"]
    
    with t1:
        with st.form("l_in"):
            cat = st.selectbox("Record Type", ["Soil In", "Sand In", "Lorry Work"])
            v = st.selectbox("Lorry Number", [n for n in v_list])
            d, q, n = st.date_input("Date"), st.number_input("Cubes", step=0.5), st.text_input("Trip Details")
            if st.form_submit_button("Save Lorry Record"):
                new = pd.DataFrame([[len(st.session_state.df)+1, d, "", "Process", cat, v, n, 0, q, 0, 0, "Done"]], columns=st.session_state.df.columns)
                st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()
    with t2:
        with st.form("e_log"):
            v = st.selectbox("Machine Number", [n for n in v_list])
            d, h, n = st.date_input("Date"), st.number_input("Working Hours", step=0.5), st.text_input("Site Location")
            if st.form_submit_button("Save Machine Record"):
                new = pd.DataFrame([[len(st.session_state.df)+1, d, "", "Process", "Work Hours", v, n, 0, 0, 0, h, "Done"]], columns=st.session_state.df.columns)
                st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()
    with t3:
        with st.form("s_out"):
            d, it = st.date_input("Date"), st.selectbox("Item Sold", ["Sand Sale", "Soil Sale"])
            q, a = st.number_input("Cubes Sold"), st.number_input("Cash Received")
            if st.form_submit_button("Save Sale Record"):
                new = pd.DataFrame([[len(st.session_state.df)+1, d, "", "Income", it, "Cash", "Sales", a, q, 0, 0, "Paid"]], columns=st.session_state.df.columns)
                st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()

# --- 8. SHED & FUEL (v47 Style Integrated) ---
elif menu == "⛽ SHED & FUEL":
    st.subheader("Manage Shed Credit & Fuel Bills")
    v_list = st.session_state.ve_db["No"].tolist() if not st.session_state.ve_db.empty else ["N/A"]
    
    with st.form("fuel_input"):
        c1, c2 = st.columns(2)
        d = c1.date_input("Fuel Date")
        v = c2.selectbox("Vehicle Number", v_list)
        l = c1.number_input("Liters Pumped", step=0.1)
        am = c2.number_input("Total Amount (Rs.)")
        stt = st.selectbox("Payment Status", ["Unpaid (Credit)", "Paid (Cash)"])
        nt = st.text_input("Fuel Bill Number / Station Name")
        
        if st.form_submit_button("Record Fuel Entry"):
            final_status = "Unpaid" if "Unpaid" in stt else "Paid"
            new = pd.DataFrame([[len(st.session_state.df)+1, d, "", "Expense", "Fuel Entry", v, nt, am, 0, l, 0, final_status]], columns=st.session_state.df.columns)
            st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()

# --- 9. FINANCE & PAYROLL ---
elif menu == "💸 FINANCE & PAYROLL":
    t1, t2 = st.tabs(["🔧 Repairs & Maintenance", "👷 Driver Wages & Advances"])
    v_list = st.session_state.ve_db["No"].tolist() if not st.session_state.ve_db.empty else ["N/A"]
    
    with t1:
        with st.form("rep"):
            d, v, nt, am = st.date_input("Date"), st.selectbox("Vehicle", v_list), st.text_input("Repair Note"), st.number_input("Cost")
            if st.form_submit_button("Save Repair Entry"):
                new = pd.DataFrame([[len(st.session_state.df)+1, d, "", "Expense", "Repair", v, nt, am, 0, 0, 0, "Paid"]], columns=st.session_state.df.columns)
                st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()
    with t2:
        dr_list = st.session_state.dr_db["Name"].tolist() if not st.session_state.dr_db.empty else ["N/A"]
        with st.form("pay"):
            d, dr = st.date_input("Date"), st.selectbox("Select Driver", dr_list)
            ty, am = st.selectbox("Type", ["Salary", "Driver Advance", "Owner Advance"]), st.number_input("Amount")
            v_rel = st.selectbox("Relates to Vehicle", v_list)
            if st.form_submit_button("Record Payment"):
                new = pd.DataFrame([[len(st.session_state.df)+1, d, "", "Expense", ty, v_rel, f"Driver: {dr}", am, 0, 0, 0, "Paid"]], columns=st.session_state.df.columns)
                st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()

# --- 10. REPORTS CENTER ---
elif menu == "📑 REPORTS CENTER":
    r1, r2, r3, r4 = st.tabs(["🚜 Vehicle Settlements", "⛽ Shed Statement", "📉 Profit/Loss", "📋 Full Log"])
    f_d, t_d = st.date_input("Start", datetime.now().date()-timedelta(days=30)), st.date_input("End", datetime.now().date())
    
    df_all = st.session_state.df.copy()
    df_all['Amount'] = pd.to_numeric(df_all['Amount'], errors='coerce').fillna(0)
    df_filtered = df_all[(df_all["Date"] >= f_d) & (df_all["Date"] <= t_d)]

    with r1:
        v_list = st.session_state.ve_db["No"].tolist()
        if v_list:
            sel_ve = st.selectbox("Select Vehicle No", v_list)
            v_rep = df_filtered[df_filtered["Entity"].astype(str).str.upper() == str(sel_ve).upper()]
            st.dataframe(v_rep, use_container_width=True)
            if st.button("Download Vehicle PDF"):
                fn = create_generic_pdf(f"Settlement_{sel_ve}", v_rep, {"Vehicle": sel_ve, "Period": f"{f_d} to {t_d}"}, ["Date", "Category", "Amount", "Status"])
                with open(fn, "rb") as f: st.download_button("📩 Download PDF", f, file_name=fn)
    
    with r2:
        st.subheader("Shed Credit (Unpaid Bills Only)")
        shed_rep = df_filtered[(df_filtered["Category"] == "Fuel Entry") & (df_filtered["Status"] == "Unpaid")]
        st.metric("Total Debt to Shed", f"Rs. {shed_rep['Amount'].sum():,.2f}")
        st.dataframe(shed_rep[["Date", "Entity", "Fuel_Ltr", "Amount", "Note"]], use_container_width=True)
        if st.button("Download Shed Debt PDF"):
            fn = create_generic_pdf("Shed_Debt_Report", shed_rep, {"Total Debt": shed_rep['Amount'].sum()}, ["Date", "Entity", "Amount"])
            with open(fn, "rb") as f: st.download_button("📩 Download Shed PDF", f, file_name=fn)

    with r3:
        inc = df_filtered[df_filtered["Type"] == "Income"]["Amount"].sum()
        total_owner_pay = 0
        for _, v_row in st.session_state.ve_db.iterrows():
            v_data = df_filtered[df_filtered['Entity'].astype(str).str.upper() == str(v_row['No']).upper()]
            u = v_data[v_data["Category"] == "Work Hours"]["Hours"].sum() if v_row['Type'] == "Excavator" else v_data[v_data["Category"].isin(["Lorry Work", "Soil In", "Sand In"])]["Qty_Cubes"].sum()
            total_owner_pay += (u * v_row['Rate_Per_Unit'])
        other_exp = df_filtered[df_filtered["Type"] == "Expense"]["Amount"].sum() - df_filtered[df_filtered["Category"].isin(["Owner Advance", "Salary", "Driver Advance"])]["Amount"].sum()
        st.metric("ESTIMATED NET PROFIT", f"Rs. {inc - total_owner_pay - other_exp:,.2f}")

    with r4:
        st.dataframe(df_filtered, use_container_width=True)

# --- 11. SYSTEM SETUP ---
elif menu == "⚙️ SYSTEM SETUP":
    s1, s2 = st.tabs(["👷 Drivers Directory", "🚜 Vehicle Fleet"])
    with s1:
        with st.form("dr"):
            n, p, s = st.text_input("Driver Name"), st.text_input("Mobile No"), st.number_input("Salary")
            if st.form_submit_button("Add New Driver"):
                new = pd.DataFrame([[n,p,s]], columns=st.session_state.dr_db.columns)
                st.session_state.dr_db = pd.concat([st.session_state.dr_db, new], ignore_index=True); save_all(); st.rerun()
        st.table(st.session_state.dr_db)
    with s2:
        with st.form("ve"):
            v, t, r, o = st.text_input("Vehicle No"), st.selectbox("Type", ["Excavator", "Lorry"]), st.number_input("Rate (per Cube/Hour)"), st.text_input("Owner Name")
            if st.form_submit_button("Add New Vehicle"):
                new = pd.DataFrame([[v,t,o,r]], columns=st.session_state.ve_db.columns)
                st.session_state.ve_db = pd.concat([st.session_state.ve_db, new], ignore_index=True); save_all(); st.rerun()
        st.table(st.session_state.ve_db)
