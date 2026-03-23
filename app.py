import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
from fpdf import FPDF

# --- 1. CONFIG & FILENAMES ---
DATA_FILE = "ksd_master_v39.csv"
VE_FILE = "ksd_vehicles_v39.csv"
DR_FILE = "ksd_drivers_v39.csv"
SHOP_NAME = "K. SIRIWARDHANA SAND CONSTRUCTION PRO"

# --- 2. DATA ENGINE (FILE HANDLING) ---
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

# --- 4. PDF GENERATOR ---
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
st.sidebar.title("🛠️ KSD ERP v3.9")
main_sector = st.sidebar.selectbox("MAIN MENU", ["📊 Dashboard", "🏗️ Site Operations", "💰 Finance & Shed", "⚙️ System Setup", "📑 Reports Center"])

st.markdown(f"<h1 style='text-align: center; color: #E67E22;'>{main_sector}</h1>", unsafe_allow_html=True)

# --- 6. SECTOR: DASHBOARD ---
if main_sector == "📊 Dashboard":
    df = st.session_state.df
    if not df.empty:
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
        ti = df[df["Type"] == "Income"]["Amount"].sum()
        te = df[df["Type"] == "Expense"]["Amount"].sum()
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Income", f"Rs. {ti:,.2f}")
        m2.metric("Total Expenses", f"Rs. {te:,.2f}")
        m3.metric("Net Cashflow", f"Rs. {ti-te:,.2f}", delta=float(ti-te))
        
        st.subheader("Recent Activity")
        st.dataframe(df.iloc[::-1].head(15), use_container_width=True)
        
        if st.button("🗑️ Delete Last Entry"):
            st.session_state.df = st.session_state.df[:-1]; save_all(); st.rerun()
    else:
        st.info("No data found. Start by adding records.")

# --- 7. SECTOR: SITE OPERATIONS ---
elif main_sector == "🏗️ Site Operations":
    op = st.sidebar.radio("Activity", ["🚜 Machine Work (Income)", "🚚 Stock In (Soil)", "💰 Sales Out"])
    
    if op == "🚜 Machine Work (Income)":
        with st.form("mach_f", clear_on_submit=True):
            d = st.date_input("Date")
            v = st.selectbox("Vehicle/Machine", st.session_state.ve_db["No"].tolist())
            h = st.number_input("Hours Worked", min_value=0.0)
            a = st.number_input("Total Amount Earned (Rs.)", min_value=0.0)
            n = st.text_input("Note (Location / Client)")
            if st.form_submit_button("Record Work"):
                new = pd.DataFrame([[len(st.session_state.df)+1, d, "", "Income", "Machine Work", v, n, a, 0, 0, h, "Done"]], columns=st.session_state.df.columns)
                st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()

    elif op == "🚚 Stock In (Soil)":
        with st.form("stk_in"):
            d = st.date_input("Date"); v = st.text_input("Supplier/Vehicle"); q = st.number_input("Cubes")
            if st.form_submit_button("Log Stock In"):
                new = pd.DataFrame([[len(st.session_state.df)+1, d, "", "Process", "Soil In", v, "Inbound", 0, q, 0, 0, "Done"]], columns=st.session_state.df.columns)
                st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()

# --- 8. SECTOR: FINANCE & SHED ---
elif main_sector == "💰 Finance & Shed":
    fin = st.sidebar.radio("Category", ["⛽ Fuel / Diesel", "🔧 Repair & Parts", "💸 Advance & Salary"])
    with st.form("fin_form", clear_on_submit=True):
        d = st.date_input("Date")
        entities = st.session_state.ve_db["No"].tolist() + st.session_state.dr_db["Name"].tolist()
        ent = st.selectbox("Entity", entities if entities else ["None"])
        amt = st.number_input("Amount (Rs.)", min_value=0.0)
        note = st.text_input("Details")
        if st.form_submit_button("Save Expense"):
            cat = "Fuel" if "Fuel" in fin else ("Repair" if "Repair" in fin else "Advance")
            new = pd.DataFrame([[len(st.session_state.df)+1, d, "", "Expense", cat, ent, note, amt, 0, 0, 0, "Paid"]], columns=st.session_state.df.columns)
            st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()

# --- 9. SECTOR: SYSTEM SETUP ---
elif main_sector == "⚙️ System Setup":
    t1, t2 = st.tabs(["🚜 Machines", "👷 Drivers"])
    with t1:
        with st.form("ve_add"):
            no = st.text_input("Machine No"); tp = st.selectbox("Type", ["Excavator", "Lorry"])
            if st.form_submit_button("Add Machine"):
                new = pd.DataFrame([[no, tp, "Owner", ""]], columns=st.session_state.ve_db.columns)
                st.session_state.ve_db = pd.concat([st.session_state.ve_db, new], ignore_index=True); save_all(); st.rerun()
        st.table(st.session_state.ve_db)
    with t2:
        with st.form("dr_add"):
            nm = st.text_input("Name"); ph = st.text_input("Phone")
            if st.form_submit_button("Add Driver"):
                new = pd.DataFrame([[nm, ph, 0]], columns=st.session_state.dr_db.columns)
                st.session_state.dr_db = pd.concat([st.session_state.dr_db, new], ignore_index=True); save_all(); st.rerun()
        st.table(st.session_state.dr_db)

# --- 10. SECTOR: REPORTS CENTER (THE SK200 LOGIC) ---
elif main_sector == "📑 Reports Center":
    st.subheader("Machine Profit/Loss Statement")
    col1, col2 = st.columns(2)
    with col1: sel_ve = st.selectbox("Select Machine", st.session_state.ve_db["No"].tolist())
    with col2: f_d = st.date_input("From"); t_d = st.date_input("To")
    
    rep_df = st.session_state.df[(st.session_state.df["Date"]>=f_d) & (st.session_state.df["Date"]<=t_d) & (st.session_state.df["Entity"] == sel_ve)]
    
    if not rep_df.empty:
        gross = rep_df[rep_df["Category"] == "Machine Work"]["Amount"].sum()
        dsl = rep_df[rep_df["Category"] == "Fuel"]["Amount"].sum()
        rep = rep_df[rep_df["Category"] == "Repair"]["Amount"].sum()
        adv = rep_df[rep_df["Category"] == "Advance"]["Amount"].sum()
        balance = gross - (dsl + rep + adv)
        
        st.markdown(f"""
        <div style="background-color:#fdf2e9; padding:20px; border-radius:10px; border-left: 5px solid #e67e22;">
            <h3 style="margin-top:0;">Summary: {sel_ve}</h3>
            <p><b>Machine Work Income:</b> Rs. {gross:,.2f}</p>
            <p style="color:red;"><b>Diesel/Fuel Cost:</b> - Rs. {dsl:,.2f}</p>
            <p style="color:red;"><b>Repairs & Advances:</b> - Rs. {rep + adv:,.2f}</p>
            <hr><h2 style="color:#1e8449;">NET BALANCE: Rs. {balance:,.2f}</h2>
        </div>
        """, unsafe_allow_html=True)
        
        st.dataframe(rep_df[["Date", "Category", "Note", "Hours", "Amount"]], use_container_width=True)
        
        if st.button("Generate PDF Report"):
            summary = {"Machine": sel_ve, "Gross": f"Rs. {gross:,.2f}", "Expenses": f"Rs. {dsl+rep+adv:,.2f}", "NET": f"Rs. {balance:,.2f}"}
            fn = create_pdf(f"Report_{sel_ve}", rep_df, summary)
            with open(fn, "rb") as fl: st.download_button("📩 Download PDF", fl, file_name=fn)
