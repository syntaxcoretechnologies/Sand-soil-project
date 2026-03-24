import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
from fpdf import FPDF

# --- 1. CONFIG & FILENAMES ---
DATA_FILE = "ksd_master_v56.csv"
VE_FILE = "ksd_vehicles_v56.csv"
DR_FILE = "ksd_drivers_v56.csv"
LO_FILE = "ksd_landowners_v56.csv" # අලුතින් එකතු කළා
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
    # Landowners සේව් කිරීම
    if "landowners" in st.session_state:
        pd.DataFrame(st.session_state.landowners).to_csv(LO_FILE, index=False)

# --- 3. SESSION STATE ---
cols_master = ["ID", "Date", "Time", "Type", "Category", "Entity", "Note", "Amount", "Qty_Cubes", "Fuel_Ltr", "Hours", "Rate_At_Time", "Status"]
if 'df' not in st.session_state:
    st.session_state.df = load_data(DATA_FILE, cols_master)
if 've_db' not in st.session_state:
    st.session_state.ve_db = load_data(VE_FILE, ["No", "Type", "Owner", "Rate_Per_Unit"])
if 'dr_db' not in st.session_state:
    st.session_state.dr_db = load_data(DR_FILE, ["Name", "Phone", "Daily_Salary"])
if 'landowners' not in st.session_state:
    st.session_state.landowners = pd.read_csv(LO_FILE).to_dict('records') if os.path.exists(LO_FILE) else []

# --- 4. PDF ENGINE ---
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15); self.set_text_color(230, 126, 34) 
        self.cell(0, 10, SHOP_NAME, 0, 1, 'C'); self.ln(5)

def create_pdf(title, data_df, summary_dict):
    pdf = PDF()
    pdf.add_page()
    def safe_text(text):
        if text is None: return ""
        return str(text).encode("latin-1", "ignore").decode("latin-1")

    pdf.set_font("Arial", 'B', 12)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 10, safe_text(f"STATEMENT: {title.upper()}"), 1, 1, 'L', fill=True)
    pdf.ln(2)
    
    pdf.set_font("Arial", 'B', 10)
    for k, v in summary_dict.items():
        if k not in ["Rate_Breakdown"]:
            clean_v = str(v).replace("Rs.", "LKR")
            pdf.cell(50, 8, safe_text(k) + ":", 1)
            pdf.set_font("Arial", '', 10)
            pdf.cell(0, 8, " " + safe_text(clean_v), 1, 1)
            pdf.set_font("Arial", 'B', 10)
    
    pdf.ln(8)
    pdf.set_font("Arial", 'B', 9)
    headers = ["Date", "Category", "Note", "Rate", "Amount"]
    w = [25, 35, 60, 30, 40]
    for i, h in enumerate(headers):
        pdf.cell(w[i], 8, safe_text(h), 1, 0, 'C', fill=True)
    pdf.ln()
    
    pdf.set_font("Arial", '', 8)
    total_exp = 0
    for _, row in data_df.iterrows():
        pdf.cell(w[0], 7, safe_text(row['Date']), 1)
        pdf.cell(w[1], 7, safe_text(row['Category']), 1)
        pdf.cell(w[2], 7, safe_text(row['Note'])[:35], 1)
        rate_val = f"{row['Rate_At_Time']:,.2f}" if row['Rate_At_Time'] > 0 else "-"
        pdf.cell(w[3], 7, safe_text(rate_val), 1, 0, 'R')
        amt = float(row['Amount']) if row['Type'] == "Expense" or row['Type'] == "Process" else 0.0
        total_exp += amt
        pdf.cell(w[4], 7, f"{amt:,.2f}", 1, 0, 'R')
        pdf.ln()
    
    pdf.set_font("Arial", 'B', 9)
    pdf.cell(sum(w[:4]), 10, "TOTAL LKR", 1, 0, 'R')
    pdf.cell(w[4], 10, f"{total_exp:,.2f}", 1, 1, 'R')
    
    fn = f"Settlement_{datetime.now().strftime('%H%M%S')}.pdf"
    pdf.output(fn)
    return fn

# --- 5. UI LAYOUT ---
st.set_page_config(page_title=SHOP_NAME, layout="wide")
st.sidebar.title("🏗️ KSD ERP v5.6")

menu = st.sidebar.selectbox("MAIN MENU", ["📊 Dashboard", "🏗️ Site Operations", "💰 Finance & Shed", "⚙️ System Setup", "📑 Reports Center", "⚙️ Data Manager"])

# --- DASHBOARD ---
if menu == "📊 Dashboard":
    st.markdown("<h2 style='color: #2E86C1;'>📊 Business Overview</h2>", unsafe_allow_html=True)
    df = st.session_state.df.copy()
    
    if not df.empty:
        st.subheader("📅 Filter Transactions")
        col_f1, col_f2 = st.columns(2)
        with col_f1: start_date = st.date_input("From Date", datetime.now().date() - timedelta(days=7))
        with col_f2: end_date = st.date_input("To Date", datetime.now().date())
        
        df['Date'] = pd.to_datetime(df['Date']).dt.date
        mask = (df['Date'] >= start_date) & (df['Date'] <= end_date)
        filtered_df = df.loc[mask].copy()

        if not filtered_df.empty:
            sales_df = filtered_df[filtered_df["Category"].str.contains("Sales Out", na=False)].copy()
            real_income = sales_df['Amount'].sum()
            total_expenses = pd.to_numeric(filtered_df[filtered_df["Type"] == "Expense"]["Amount"], errors='coerce').sum()

            m1, m2, m3 = st.columns(3)
            m1.metric("Net Sales Income", f"Rs. {real_income:,.2f}")
            m2.metric("Total Expenses", f"Rs. {total_expenses:,.2f}")
            m3.metric("Net Cashflow", f"Rs. {real_income - total_expenses:,.2f}")

            st.divider()
            st.subheader("📦 Plant Stock Balance (Current)")
            s_col1, s_col2 = st.columns(2)
            full_df = st.session_state.df.copy()
            s_in = full_df[full_df["Category"].str.contains("Stock Inward", na=False) & full_df["Category"].str.contains("Sand", na=False)]["Qty_Cubes"].sum()
            s_out = full_df[full_df["Category"].str.contains("Sales Out", na=False) & full_df["Category"].str.contains("Sand", na=False)]["Qty_Cubes"].sum()
            so_in = full_df[full_df["Category"].str.contains("Stock Inward", na=False) & full_df["Category"].str.contains("Soil", na=False)]["Qty_Cubes"].sum()
            so_out = full_df[full_df["Category"].str.contains("Sales Out", na=False) & full_df["Category"].str.contains("Soil", na=False)]["Qty_Cubes"].sum()
            s_col1.metric("Sand Remaining", f"{s_in - s_out:.2f} Cubes")
            s_col2.metric("Soil Remaining", f"{so_in - so_out:.2f} Cubes")

# --- SITE OPERATIONS ---
elif menu == "🏗️ Site Operations":
    st.markdown(f"<h2 style='color: #E67E22;'>🏗️ Site Operations & Stock Manager</h2>", unsafe_allow_html=True)
    op = st.radio("Select Activity Type", ["🚜 Excavator Work Log", "💰 Sales Out", "📥 Stock Inward (To Plant)"], horizontal=True)
    
    v_list = st.session_state.ve_db["No"].tolist() if not st.session_state.ve_db.empty else ["N/A"]
    d_list = [d["Name"] for d in st.session_state.drivers] if st.session_state.drivers else ["Register Drivers in Setup"]
    l_list = [l["Name"] for l in st.session_state.landowners] if st.session_state.landowners else ["Register Owners in Setup"]

    with st.form("site_f", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            v = st.selectbox("Select Vehicle / Machine", v_list if op != "📥 Stock Inward (To Plant)" else ["Internal / Third Party"])
            dt = st.date_input("Date", datetime.now().date())
            material = st.selectbox("Material Type", ["Sand", "Soil", "Other"]) if (op == "💰 Sales Out" or op == "📥 Stock Inward (To Plant)") else ""
            
        with col2:
            val_label = "Work Hours" if "Excavator" in op else "Qty (Cubes)"
            unit = "Hrs" if "Excavator" in op else "Cubes"
            val = st.number_input(val_label, min_value=0.0, step=0.5)
            r = st.number_input(f"Rate per {unit} (LKR)", min_value=0.0, step=100.0)
            
            # Dynamic Source/Driver Selection
            if op == "📥 Stock Inward (To Plant)":
                src = st.selectbox("Source (Landowner)", l_list)
                drv = st.selectbox("Driver/Operator", d_list)
            else:
                src, drv = "N/A", "N/A"

        n = st.text_input("Additional Note")
        
        if st.form_submit_button("📥 Save Record"):
            if val > 0 and r > 0:
                calc_amt = val * r
                q, h = (0, val) if "Excavator" in op else (val, 0)
                final_note = f"{n} | Owner: {src} | Drv: {drv}" if op == "📥 Stock Inward (To Plant)" else n
                
                new_row = pd.DataFrame([[len(st.session_state.df)+1, dt, "", "Process", f"{op} ({material})", v, final_note, calc_amt, q, 0, h, r, "Done"]], columns=st.session_state.df.columns)
                st.session_state.df = pd.concat([st.session_state.df, new_row], ignore_index=True)
                save_all()
                st.success("Successfully recorded!")
                st.rerun()

# --- FINANCE & SHED ---
elif menu == "💰 Finance & Shed":
    fin = st.radio("Finance Category", ["⛽ Fuel & Shed", "🔧 Repairs", "💸 Payroll", "🏦 Owner Advances", "🧾 Others"], horizontal=True)
    v_list = st.session_state.ve_db["No"].tolist() if not st.session_state.ve_db.empty else ["N/A"]
    
    if fin == "💸 Payroll":
        with st.form("pay", clear_on_submit=True):
            dr = st.selectbox("Driver", [d["Name"] for d in st.session_state.drivers] if st.session_state.drivers else ["N/A"])
            am, ty = st.number_input("Amount"), st.selectbox("Type", ["Driver Advance", "Salary"])
            if st.form_submit_button("Save Payroll"):
                new = pd.DataFrame([[len(st.session_state.df)+1, datetime.now().date(), "", "Expense", ty, "Staff", f"Driver: {dr}", am, 0, 0, 0, 0, "Paid"]], columns=st.session_state.df.columns)
                st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()
    # (Other Finance categories remain same as your original)
    elif fin == "⛽ Fuel & Shed":
        f1, f2 = st.tabs(["⛽ Log Fuel Bill", "💳 Settle Shed Payments"])
        with f1:
            with st.form("fuel"):
                d, v, l, c = st.date_input("Date"), st.selectbox("Vehicle", v_list), st.number_input("Liters"), st.number_input("Cost")
                if st.form_submit_button("Save Fuel"):
                    new = pd.DataFrame([[len(st.session_state.df)+1, d, "", "Expense", "Fuel Entry", v, "Shed bill", c, 0, l, 0, 0, "Pending"]], columns=st.session_state.df.columns)
                    st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()
        with f2:
            with st.form("shed_p"):
                am = st.number_input("Amount Paid")
                if st.form_submit_button("Record Payment"):
                    new = pd.DataFrame([[len(st.session_state.df)+1, datetime.now().date(), "", "Expense", "Shed Payment", "Shed", "Payment", am, 0, 0, 0, 0, "Paid"]], columns=st.session_state.df.columns)
                    st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()

# --- SYSTEM SETUP ---
elif menu == "⚙️ System Setup":
    st.title("⚙️ System Setup & Configuration")
    t_v, t_d, t_l = st.tabs(["🚜 Vehicles", "👷 Drivers", "🏡 Landowners"])
    
    with t_v:
        st.subheader("Vehicle Registration")
        with st.form("v_reg", clear_on_submit=True):
            v_no = st.text_input("Vehicle Number")
            v_ty = st.selectbox("Type", ["Lorry", "Excavator", "JCB"])
            if st.form_submit_button("Add Vehicle"):
                new_v = pd.DataFrame([{"No": v_no, "Type": v_ty, "Owner": "Own", "Rate_Per_Unit": 0}])
                st.session_state.ve_db = pd.concat([st.session_state.ve_db, new_v], ignore_index=True)
                save_all(); st.success(f"Added {v_no}"); st.rerun()

    with t_d:
        st.subheader("Driver Registration")
        with st.form("d_reg", clear_on_submit=True):
            name = st.text_input("Driver Name")
            phone = st.text_input("Phone Number")
            if st.form_submit_button("Add Driver"):
                st.session_state.drivers.append({"Name": name, "Phone": phone})
                save_all(); st.success(f"Driver {name} Added!"); st.rerun()
        st.write("**Current Drivers:**", pd.DataFrame(st.session_state.drivers) if st.session_state.drivers else "None")

    with t_l:
        st.subheader("Landowner Registration")
        with st.form("l_reg", clear_on_submit=True):
            name = st.text_input("Landowner Name")
            loc = st.text_input("Location")
            if st.form_submit_button("Add Owner"):
                st.session_state.landowners.append({"Name": name, "Location": loc})
                save_all(); st.success(f"Owner {name} Added!"); st.rerun()
        st.write("**Current Owners:**", pd.DataFrame(st.session_state.landowners) if st.session_state.landowners else "None")

# --- REPORTS CENTER ---
elif menu == "📑 Reports Center":
    st.title("📑 Business Reports Center")
    r1, r2, r3, r4 = st.tabs(["🚜 Vehicle Settlement", "👷 Driver Summary", "🏡 Landowner Report", "📑 Daily Log"])
    
    df_f = st.session_state.df.copy()
    df_f['Date'] = pd.to_datetime(df_f['Date']).dt.date
    
    with r1:
        v_sel = st.selectbox("Select Vehicle", st.session_state.ve_db["No"].tolist() if not st.session_state.ve_db.empty else ["N/A"])
        v_data = df_f[df_f["Entity"] == v_sel]
        st.dataframe(v_data, use_container_width=True)
        if st.button("Generate PDF"):
            path = create_pdf(f"{v_sel}_Report", v_data, {"Vehicle": v_sel, "Total Records": len(v_data)})
            with open(path, "rb") as f: st.download_button("Download PDF", f, file_name=f"{v_sel}.pdf")

    with r2:
        dr_sel = st.selectbox("Select Driver", [d["Name"] for d in st.session_state.drivers])
        dr_data = df_f[df_f["Note"].str.contains(dr_sel, na=False)]
        st.write(f"Total Transactions for {dr_sel}: {len(dr_data)}")
        st.dataframe(dr_data, use_container_width=True)

    with r3:
        lo_sel = st.selectbox("Select Landowner", [l["Name"] for l in st.session_state.landowners])
        lo_data = df_f[df_f["Note"].str.contains(lo_sel, na=False)]
        st.metric("Total Cubes from Owner", f"{lo_data['Qty_Cubes'].sum():.2f}")
        st.dataframe(lo_data, use_container_width=True)

    with r4:
        st.dataframe(df_f, use_container_width=True)

# --- DATA MANAGER ---
elif menu == "⚙️ Data Manager":
    st.title("⚙️ Data Manager")
    st.dataframe(st.session_state.df)
    if st.button("Clear All Data (Careful!)"):
        st.session_state.df = pd.DataFrame(columns=cols_master)
        save_all(); st.rerun()
