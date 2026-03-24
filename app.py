import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
from fpdf import FPDF

# --- 1. CONFIG & FILENAMES ---
DATA_FILE = "ksd_master_v56.csv"
VE_FILE = "ksd_vehicles_v56.csv"
DR_FILE = "ksd_drivers_v56.csv"
SHOP_NAME = "K. SIRIWARDHANA SAND CONSTRUCTION PRO"

# --- 2. DATA ENGINE ---
def load_data(file, cols):
    if os.path.exists(file): 
        try:
            d = pd.read_csv(file)
            if 'Date' in d.columns:
                d['Date'] = pd.to_datetime(d['Date']).dt.date
            for col in cols:
                if col not in d.columns: d[col] = 0
            return d
        except: return pd.DataFrame(columns=cols)
    return pd.DataFrame(columns=cols)

def save_all():
    st.session_state.df.to_csv(DATA_FILE, index=False)
    st.session_state.ve_db.to_csv(VE_FILE, index=False)
    st.session_state.dr_db.to_csv(DR_FILE, index=False)

# --- 3. SESSION STATE ---
cols_master = ["ID", "Date", "Time", "Type", "Category", "Entity", "Note", "Amount", "Qty_Cubes", "Fuel_Ltr", "Hours", "Rate_At_Time", "Status"]
if 'df' not in st.session_state:
    st.session_state.df = load_data(DATA_FILE, cols_master)
if 've_db' not in st.session_state:
    st.session_state.ve_db = load_data(VE_FILE, ["No", "Type", "Owner", "Rate_Per_Unit"])
if 'dr_db' not in st.session_state:
    st.session_state.dr_db = load_data(DR_FILE, ["Name", "Phone", "Daily_Salary"])

# --- 4. PDF REPORT GENERATOR (UPDATED FORMAT) ---
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15); self.set_text_color(230, 126, 34) 
        self.cell(0, 10, SHOP_NAME, 0, 1, 'C'); self.ln(5)

def create_pdf(title, data_df, summary_dict):
    pdf = PDF(); pdf.add_page(); pdf.set_font("Arial", 'B', 12)
    
    # Settlement Header 
    pdf.cell(0, 10, f"STATEMENT: {title.upper()}", 1, 1, 'L'); pdf.ln(2)
    
    # Summary Box 
    for k, v in summary_dict.items():
        pdf.set_font("Arial", 'B', 10); pdf.cell(60, 8, f"{k}:", 1)
        pdf.set_font("Arial", '', 10); pdf.cell(0, 8, f" {v}", 1, 1)
    
    pdf.ln(10); pdf.set_font("Arial", 'B', 9)
    
    # Table Header 
    cols = ["Date", "Category", "Note", "Qty/Hrs", "Amount"]
    col_widths = [30, 40, 55, 25, 40]
    for i, c in enumerate(cols): pdf.cell(col_widths[i], 8, c, 1, 0, 'C')
    pdf.ln(); pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", '', 8)
    
    total_table_amt = 0.0
    for _, row in data_df.iterrows():
        pdf.cell(30, 7, str(row['Date']), 1)
        pdf.cell(40, 7, str(row['Category']), 1)
        pdf.cell(55, 7, str(row['Note'])[:30], 1)
        
        qty = row['Hours'] if row['Hours'] > 0 else (row['Qty_Cubes'] if row['Qty_Cubes'] > 0 else "")
        pdf.cell(25, 7, f"{qty}", 1, 0, 'C')
        
        amt = float(row['Amount']) if not pd.isna(row['Amount']) else 0.0
        total_table_amt += amt
        pdf.cell(40, 7, f"{amt:,.2f}" if amt > 0 else "0.00", 1, 0, 'R'); pdf.ln()
    
    # Grand Total Row 
    pdf.set_font("Arial", 'B', 9)
    pdf.cell(150, 10, "GRAND TOTAL", 1, 0, 'R')
    pdf.cell(40, 10, f"Rs. {total_table_amt:,.2f}", 1, 1, 'R')
    
    fname = f"Report_{datetime.now().strftime('%H%M%S')}.pdf"
    pdf.output(fname); return fname

# --- 5. UI LAYOUT ---
st.set_page_config(page_title=SHOP_NAME, layout="wide", page_icon="🏗️")
st.sidebar.title("🏗️ KSD ERP v5.6")
main_sector = st.sidebar.selectbox("MAIN MENU", ["📊 Dashboard", "🏗️ Site Ops", "💰 Finance", "⚙️ Setup", "📑 Reports"])
st.markdown(f"<h2 style='text-align: center; color: #E67E22;'>{main_sector}</h2>", unsafe_allow_html=True)

# --- 6. DASHBOARD ---
if main_sector == "📊 Dashboard":
    df = st.session_state.df
    if not df.empty:
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
        ti, te = df[df["Type"] == "Income"]["Amount"].sum(), df[df["Type"] == "Expense"]["Amount"].sum()
        m1, m2, m3 = st.columns(3)
        m1.metric("Income", f"Rs. {ti:,.2f}"); m2.metric("Expenses", f"Rs. {te:,.2f}"); m3.metric("Cashflow", f"Rs. {ti-te:,.2f}")
        st.divider(); st.area_chart(df.groupby(['Date', 'Type'])['Amount'].sum().unstack().fillna(0))

# --- 7. SITE OPERATIONS ---
elif main_sector == "🏗️ Site Ops":
    op = st.radio("Activity", ["🚛 Lorry", "🚜 Excavator", "💰 Sales"], horizontal=True)
    if op != "💰 Sales":
        with st.form("work_f"):
            v_type = "Lorry" if op == "🚛 Lorry" else "Excavator"
            v = st.selectbox("Vehicle", st.session_state.ve_db[st.session_state.ve_db["Type"]==v_type]["No"].tolist() if not st.session_state.ve_db.empty else ["N/A"])
            def_rate = st.session_state.ve_db[st.session_state.ve_db["No"]==v]["Rate_Per_Unit"].values[0] if v != "N/A" else 0.0
            d, val = st.date_input("Date"), st.number_input("Cubes/Hours", step=0.5)
            r = st.number_input("Rate for this day", value=float(def_rate))
            n = st.text_input("Note")
            if st.form_submit_button("Record"):
                q_val, h_val = (val, 0) if v_type == "Lorry" else (0, val)
                new = pd.DataFrame([[len(st.session_state.df)+1, d, "", "Process", f"{v_type} Work", v, n, 0, q_val, 0, h_val, r, "Done"]], columns=st.session_state.df.columns)
                st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()
    else:
        with st.form("sale_f"):
            d, it, q, a = st.date_input("Date"), st.selectbox("Item", ["Sand", "Soil"]), st.number_input("Cubes"), st.number_input("Amount")
            if st.form_submit_button("Record Sale"):
                new = pd.DataFrame([[len(st.session_state.df)+1, d, "", "Income", f"{it} Sale", "Cash", "Sales", a, q, 0, 0, 0, "Paid"]], columns=st.session_state.df.columns)
                st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()

# --- 8. FINANCE (FULL) ---
elif main_sector == "💰 Finance":
    fin = st.radio("Category", ["⛽ Fuel", "🔧 Repairs", "💸 Payroll", "🏦 Owner Adv", "🧾 Others"], horizontal=True)
    v_list = st.session_state.ve_db["No"].tolist() if not st.session_state.ve_db.empty else ["N/A"]
    with st.form("fin_f"):
        d, v = st.date_input("Date"), st.selectbox("Vehicle/Entity", v_list + ["Admin", "Shed"])
        am, nt = st.number_input("Amount"), st.text_input("Note/Ref")
        if fin == "⛽ Fuel": l = st.number_input("Liters")
        if st.form_submit_button("Save"):
            l_val = l if fin == "⛽ Fuel" else 0
            new = pd.DataFrame([[len(st.session_state.df)+1, d, "", "Expense", fin, v, nt, am, 0, l_val, 0, 0, "Paid"]], columns=st.session_state.df.columns)
            st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()

# --- 9. SETUP ---
elif main_sector == "⚙️ Setup":
    t1, t2 = st.tabs(["Drivers", "Vehicles"])
    with t1:
        with st.form("d_f"):
            n, p, s = st.text_input("Name"), st.text_input("Phone"), st.number_input("Salary")
            if st.form_submit_button("Add Driver"):
                st.session_state.dr_db = pd.concat([st.session_state.dr_db, pd.DataFrame([[n,p,s]], columns=st.session_state.dr_db.columns)], ignore_index=True); save_all(); st.rerun()
        st.table(st.session_state.dr_db)
    with t2:
        with st.form("v_f"):
            v, t, r, o = st.text_input("No"), st.selectbox("Type", ["Lorry", "Excavator"]), st.number_input("Rate"), st.text_input("Owner")
            if st.form_submit_button("Add Vehicle"):
                st.session_state.ve_db = pd.concat([st.session_state.ve_db, pd.DataFrame([[v,t,o,r]], columns=st.session_state.ve_db.columns)], ignore_index=True); save_all(); st.rerun()
        st.table(st.session_state.ve_db)

# --- 10. REPORTS (UPDATED) ---
elif main_sector == "📑 Reports":
    r1, r2 = st.tabs(["🚜 Vehicle Settlement", "👷 Driver Summary"])
    f_d, t_d = st.date_input("From", datetime.now().date()-timedelta(days=30)), st.date_input("To")
    df_f = st.session_state.df[(st.session_state.df["Date"] >= f_d) & (st.session_state.df["Date"] <= t_d)]
    
    with r1:
        sel_ve = st.selectbox("Select Vehicle", st.session_state.ve_db["No"].tolist() if not st.session_state.ve_db.empty else [])
        if sel_ve:
            v_rep = df_f[df_f["Entity"] == sel_ve].copy()
            units = (v_rep['Hours'] + v_rep['Qty_Cubes']).sum()
            # Calculate based on dynamic rate recorded 
            v_rep['Earnings'] = (v_rep['Hours'] + v_rep['Qty_Cubes']) * v_rep['Rate_At_Time']
            gross = v_rep['Earnings'].sum()
            deduct = v_rep[v_rep["Type"] == "Expense"]["Amount"].sum()
            net = gross - deduct
            
            st.metric("NET TO OWNER", f"Rs. {net:,.2f}")
            st.dataframe(v_rep, use_container_width=True)
            
            if st.button("Download PDF"):
                summary = {
                    "Vehicle": sel_ve,
                    "Total Cubes/Hrs": units,
                    "Gross Earnings": f"{gross:,.2f}",
                    "Total Deductions": f"{deduct:,.2f}",
                    "Net Settlement": f"{net:,.2f}"
                }
                fn = create_pdf(f"Settlement_{sel_ve}", v_rep, summary)
                with open(fn, "rb") as f: st.download_button("📩 Get Report", f, file_name=fn)
