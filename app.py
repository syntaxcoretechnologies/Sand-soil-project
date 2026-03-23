import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
from fpdf import FPDF

# --- 1. CONFIG & FILENAMES ---
DATA_FILE = "ksd_master_v59.csv"
VE_FILE = "ksd_vehicles_v59.csv"
DR_FILE = "ksd_drivers_v59.csv"
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

# --- 5. UI SETUP ---
st.set_page_config(page_title=SHOP_NAME, layout="wide")
st.markdown(f"<h1 style='text-align: center; color: #E67E22;'>🏗️ {SHOP_NAME}</h1>", unsafe_allow_html=True)

with st.sidebar:
    st.title("Navigation")
    menu = st.radio("SELECT SECTION", ["📊 DASHBOARD", "🏗️ SITE OPERATIONS", "💰 FINANCE & SHED", "📑 REPORTS CENTER", "⚙️ SYSTEM SETUP"])
    st.divider()
    st.success("System Finalized (v5.9)")

# --- 6. DASHBOARD ---
if menu == "📊 DASHBOARD":
    st.subheader("Business Analytics")
    df = st.session_state.df
    if not df.empty:
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
        ti = df[df["Type"] == "Income"]["Amount"].sum()
        te = df[df["Type"] == "Expense"]["Amount"].sum()
        # Calculate Shed Credit (Unpaid Fuel)
        shed_credit = df[(df["Category"] == "Fuel Entry") & (df["Status"] == "Unpaid")]["Amount"].sum()
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Income", f"Rs. {ti:,.2f}")
        c2.metric("Total Expense", f"Rs. {te:,.2f}")
        c3.metric("Net Balance", f"Rs. {ti-te:,.2f}")
        c4.metric("SHED CREDIT", f"Rs. {shed_credit:,.2f}", delta="-Debt", delta_color="inverse")
        
        st.divider()
        st.subheader("Recent Activity Manager")
        for i, row in st.session_state.df.iloc[::-1].head(12).iterrows():
            col1, col2, col3, col4 = st.columns([5, 2, 2, 1])
            col1.write(f"**{row['Date']}** | {row['Category']} ({row['Entity']})")
            col2.write(f"Rs. {row['Amount']:,.2f}")
            col3.write(f"{row['Status']}")
            if col4.button("🗑️", key=f"del_{i}"):
                st.session_state.df = st.session_state.df.drop(i); save_all(); st.rerun()

# --- 7. SITE OPERATIONS ---
elif menu == "🏗️ SITE OPERATIONS":
    t1, t2, t3 = st.tabs(["🚛 Lorry Log", "🚜 Excavator Log", "💰 Sales Out"])
    with t1:
        with st.form("l_in"):
            cat = st.selectbox("Category", ["Soil In", "Sand In", "Lorry Work"])
            v = st.selectbox("Lorry No", st.session_state.ve_db[st.session_state.ve_db["Type"]=="Lorry"]["No"].tolist() if not st.session_state.ve_db.empty else ["N/A"])
            d, q, n = st.date_input("Date"), st.number_input("Cubes", step=0.5), st.text_input("Trip Details")
            if st.form_submit_button("Record Entry"):
                new = pd.DataFrame([[len(st.session_state.df)+1, d, "", "Process", cat, v, n, 0, q, 0, 0, "Done"]], columns=st.session_state.df.columns)
                st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()
    with t2:
        with st.form("e_log"):
            v = st.selectbox("Excavator", st.session_state.ve_db[st.session_state.ve_db["Type"]=="Excavator"]["No"].tolist() if not st.session_state.ve_db.empty else ["N/A"])
            d, h, n = st.date_input("Date"), st.number_input("Work Hours", step=0.5), st.text_input("Site Location")
            if st.form_submit_button("Save Hours"):
                new = pd.DataFrame([[len(st.session_state.df)+1, d, "", "Process", "Work Hours", v, n, 0, 0, 0, h, "Done"]], columns=st.session_state.df.columns)
                st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()
    with t3:
        with st.form("s_out"):
            d, it = st.date_input("Date"), st.selectbox("Item", ["Sand Sale", "Soil Sale"])
            q, a = st.number_input("Cubes"), st.number_input("Received Amount")
            if st.form_submit_button("Record Sale"):
                new = pd.DataFrame([[len(st.session_state.df)+1, d, "", "Income", it, "Cash", "Sales", a, q, 0, 0, "Paid"]], columns=st.session_state.df.columns)
                st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()

# --- 8. FINANCE & SHED ---
elif menu == "💰 FINANCE & SHED":
    f1, f2, f3 = st.tabs(["⛽ Shed & Fuel (Credit)", "🔧 Maintenance", "💸 Salaries & Advances"])
    v_list = st.session_state.ve_db["No"].tolist()
    with f1:
        with st.form("f_sh"):
            d, v = st.date_input("Date"), st.selectbox("Vehicle", v_list)
            l, c = st.number_input("Liters"), st.number_input("Total Amount")
            stt = st.selectbox("Payment Status", ["Unpaid", "Paid"])
            if st.form_submit_button("Record Fuel Bill"):
                new = pd.DataFrame([[len(st.session_state.df)+1, d, "", "Expense", "Fuel Entry", v, "Shed Bill", c, 0, l, 0, stt]], columns=st.session_state.df.columns)
                st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()
    with f2:
        with st.form("rep"):
            d, v, nt, am = st.date_input("Date"), st.selectbox("Vehicle", v_list), st.text_input("Repair Detail"), st.number_input("Amount")
            if st.form_submit_button("Save Repair"):
                new = pd.DataFrame([[len(st.session_state.df)+1, d, "", "Expense", "Repair", v, nt, am, 0, 0, 0, "Paid"]], columns=st.session_state.df.columns)
                st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()
    with f3:
        with st.form("pay"):
            d, dr = st.date_input("Date"), st.selectbox("Driver", st.session_state.dr_db["Name"].tolist() if not st.session_state.dr_db.empty else ["N/A"])
            ty, am = st.selectbox("Type", ["Salary", "Driver Advance", "Owner Advance"]), st.number_input("Amount")
            v_rel = st.selectbox("Related Vehicle", v_list)
            if st.form_submit_button("Save Payment"):
                new = pd.DataFrame([[len(st.session_state.df)+1, d, "", "Expense", ty, v_rel, f"Driver: {dr}", am, 0, 0, 0, "Paid"]], columns=st.session_state.df.columns)
                st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()

# --- 9. REPORTS CENTER ---
elif menu == "📑 REPORTS CENTER":
    r1, r2, r3, r4, r5 = st.tabs(["🚜 Settlement", "👷 Driver", "📈 Profit/Loss", "⛽ Shed Credit", "📑 General"])
    f_d, t_d = st.date_input("From", datetime.now().date()-timedelta(days=30)), st.date_input("To", datetime.now().date())
    
    df_all = st.session_state.df.copy()
    df_all['Amount'] = pd.to_numeric(df_all['Amount'], errors='coerce').fillna(0)
    df_filtered = df_all[(df_all["Date"] >= f_d) & (df_all["Date"] <= t_d)]

    with r1:
        v_list = st.session_state.ve_db["No"].tolist()
        if v_list:
            sel_ve = st.selectbox("Vehicle No", v_list)
            v_rep = df_filtered[df_filtered["Entity"].astype(str).str.upper() == str(sel_ve).upper()]
            if not v_rep.empty:
                m_ve = st.session_state.ve_db[st.session_state.ve_db["No"] == sel_ve]
                rate = m_ve["Rate_Per_Unit"].values[0]
                units = v_rep[v_rep["Category"] == "Work Hours"]["Hours"].sum() if m_ve["Type"].values[0] == "Excavator" else v_rep[v_rep["Category"].isin(["Lorry Work", "Soil In", "Sand In"])]["Qty_Cubes"].sum()
                g_pay = units * rate
                deduct = v_rep[v_rep["Type"] == "Expense"]["Amount"].sum()
                st.metric("NET PAYABLE", f"Rs. {g_pay - deduct:,.2f}")
                st.dataframe(v_rep[["Date", "Category", "Amount", "Qty_Cubes", "Hours", "Status"]], use_container_width=True)
                if st.button("Download Settlement PDF"):
                    fn = create_generic_pdf(f"Settlement_{sel_ve}", v_rep, {"Units": units, "Net": g_pay-deduct}, ["Date", "Category", "Amount"])
                    with open(fn, "rb") as f: st.download_button("📩 Download", f, file_name=fn)

    with r2:
        dr_list = st.session_state.dr_db["Name"].tolist()
        if dr_list:
            sel_dr = st.selectbox("Driver Name", dr_list)
            dr_rep = df_filtered[df_filtered["Note"].str.contains(str(sel_dr), case=False, na=False)]
            st.metric("Total Paid", f"Rs. {dr_rep['Amount'].sum():,.2f}")
            st.dataframe(dr_rep, use_container_width=True)

    with r3:
        inc = df_filtered[df_filtered["Type"] == "Income"]["Amount"].sum()
        # Operational calculation
        total_owner_pay = 0
        for _, v_row in st.session_state.ve_db.iterrows():
            v_data = df_filtered[df_filtered['Entity'].astype(str).str.upper() == str(v_row['No']).upper()]
            u = v_data[v_data["Category"] == "Work Hours"]["Hours"].sum() if v_row['Type'] == "Excavator" else v_data[v_data["Category"].isin(["Lorry Work", "Soil In", "Sand In"])]["Qty_Cubes"].sum()
            total_owner_pay += (u * v_row['Rate_Per_Unit'])
        other_exp = df_filtered[df_filtered["Type"] == "Expense"]["Amount"].sum() - df_filtered[df_filtered["Category"].isin(["Owner Advance", "Salary", "Driver Advance"])]["Amount"].sum()
        st.metric("ESTIMATED NET PROFIT", f"Rs. {inc - total_owner_pay - other_exp:,.2f}")

    with r4:
        st.subheader("Fuel Credit Statement (Unpaid Bills)")
        shed_rep = df_filtered[(df_filtered["Category"] == "Fuel Entry") & (df_filtered["Status"] == "Unpaid")]
        st.metric("TOTAL CREDIT TO BE PAID", f"Rs. {shed_rep['Amount'].sum():,.2f}")
        st.dataframe(shed_rep, use_container_width=True)
        if st.button("Download Shed Credit PDF"):
            fn = create_generic_pdf("Shed_Credit_Report", shed_rep, {"Total Debt": shed_rep['Amount'].sum()}, ["Date", "Entity", "Fuel_Ltr", "Amount"])
            with open(fn, "rb") as f: st.download_button("📩 Download PDF", f, file_name=fn)

    with r5:
        st.dataframe(df_filtered, use_container_width=True)

# --- 10. SYSTEM SETUP ---
elif menu == "⚙️ SYSTEM SETUP":
    s1, s2 = st.tabs(["👷 Drivers", "🚜 Vehicles"])
    with s1:
        with st.form("dr"):
            n, p, s = st.text_input("Name"), st.text_input("Phone"), st.number_input("Salary")
            if st.form_submit_button("Add Driver"):
                new = pd.DataFrame([[n,p,s]], columns=st.session_state.dr_db.columns)
                st.session_state.dr_db = pd.concat([st.session_state.dr_db, new], ignore_index=True); save_all(); st.rerun()
        st.table(st.session_state.dr_db)
    with s2:
        with st.form("ve"):
            v, t, r, o = st.text_input("No"), st.selectbox("Type", ["Excavator", "Lorry"]), st.number_input("Rate"), st.text_input("Owner")
            if st.form_submit_button("Add Vehicle"):
                new = pd.DataFrame([[v,t,o,r]], columns=st.session_state.ve_db.columns)
                st.session_state.ve_db = pd.concat([st.session_state.ve_db, new], ignore_index=True); save_all(); st.rerun()
        st.table(st.session_state.ve_db)
