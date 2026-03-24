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

# --- 4. PDF ENGINE (ඔයා එවපු PDF එකේ format එකටම) ---
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15); self.set_text_color(230, 126, 34) 
        self.cell(0, 10, SHOP_NAME, 0, 1, 'C'); self.ln(5)

def create_pdf(title, data_df, summary_dict):
    pdf = PDF()
    pdf.add_page()
    
    # Unicode Error එන එක නතර කරන්න safe_text කියන function එක පාවිච්චි කරමු
    def safe_text(text):
        if text is None: return ""
        # Latin-1 වලට සපෝට් නොකරන අකුරු (සිංහල, Emojis) අයින් කරනවා
        return str(text).encode("latin-1", "ignore").decode("latin-1")

    pdf.set_font("Arial", 'B', 12)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 10, safe_text(f"STATEMENT: {title.upper()}"), 1, 1, 'L', fill=True)
    pdf.ln(2)
    
    # Summary Section
    pdf.set_font("Arial", 'B', 10)
    for k, v in summary_dict.items():
        # රුපියල් සලකුණ වෙනුවට LKR පාවිච්චි කිරීම ආරක්ෂිතයි
        val = str(v).replace("Rs.", "LKR")
        pdf.cell(50, 8, safe_text(k) + ":", 1)
        pdf.set_font("Arial", '', 10)
        pdf.cell(0, 8, " " + safe_text(val), 1, 1)
        pdf.set_font("Arial", 'B', 10)
    
    pdf.ln(8)
    
    # Table Header
    pdf.set_font("Arial", 'B', 9)
    headers = ["Date", "Category", "Note", "Qty/Hrs", "Amount"]
    w = [25, 35, 65, 25, 40]
    for i, h in enumerate(headers):
        pdf.cell(w[i], 8, safe_text(h), 1, 0, 'C', fill=True)
    pdf.ln()
    
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", '', 8)
    
    total_exp = 0
    for _, row in data_df.iterrows():
        pdf.cell(w[0], 7, safe_text(row['Date']), 1)
        pdf.cell(w[1], 7, safe_text(row['Category']), 1)
        
        # Note එකේ සිංහල අකුරු තිබුණොත් ඒක ignore කරනවා
        clean_note = safe_text(row['Note'])[:40]
        pdf.cell(w[2], 7, clean_note, 1)
        
        qty = row['Hours'] if row['Hours'] > 0 else (row['Qty_Cubes'] if row['Qty_Cubes'] > 0 else "-")
        pdf.cell(w[3], 7, safe_text(qty), 1, 0, 'C')
        
        amt = float(row['Amount']) if row['Type'] == "Expense" else 0.0
        total_exp += amt
        pdf.cell(w[4], 7, f"{amt:,.2f}", 1, 0, 'R')
        pdf.ln()
    
    # Grand Total
    pdf.set_font("Arial", 'B', 9)
    pdf.cell(sum(w[:4]), 10, "GRAND TOTAL (EXPENSES) LKR", 1, 0, 'R')
    pdf.cell(w[4], 10, f"{total_exp:,.2f}", 1, 1, 'R')
    
    # Output file
    fn = f"Settlement_{datetime.now().strftime('%H%M%S')}.pdf"
    try:
        pdf.output(fn)
    except Exception as e:
        # තවමත් error එකක් එනවා නම් නිකන්ම output කරනවා (fallback)
        pdf.output(fn, 'F')
        
    return fn

# --- 5. UI LAYOUT & DASHBOARD ---
st.set_page_config(page_title=SHOP_NAME, layout="wide")
st.sidebar.title("🏗️ KSD ERP v5.6")
menu = st.sidebar.selectbox("MAIN MENU", ["📊 Dashboard", "🏗️ Site Operations", "💰 Finance & Shed", "⚙️ System Setup", "📑 Reports Center"])

if menu == "📊 Dashboard":
    df = st.session_state.df
    if not df.empty:
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
        ti, te = df[df["Type"] == "Income"]["Amount"].sum(), df[df["Type"] == "Expense"]["Amount"].sum()
        f_debt = df[df["Category"] == "Fuel Entry"]["Amount"].sum() - df[df["Category"] == "Shed Payment"]["Amount"].sum()
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Income", f"Rs. {ti:,.2f}"); m2.metric("Total Expenses", f"Rs. {te:,.2f}")
        m3.metric("Net Cashflow", f"Rs. {ti-te:,.2f}"); m4.metric("Shed Debt", f"Rs. {f_debt:,.2f}")
        st.divider(); st.area_chart(df.groupby(['Date', 'Type'])['Amount'].sum().unstack().fillna(0))

# --- 7. SITE OPERATIONS (v56 Full) ---
elif menu == "🏗️ Site Operations":
    op = st.radio("Activity", ["🚛 Lorry Work Log", "🚜 Excavator Work Log", "💰 Sales Out (Sand/Soil)"], horizontal=True)
    v_list = st.session_state.ve_db["No"].tolist() if not st.session_state.ve_db.empty else ["N/A"]
    with st.form("site_f"):
        v = st.selectbox("Vehicle", v_list)
        def_r = st.session_state.ve_db[st.session_state.ve_db["No"]==v]["Rate_Per_Unit"].values[0] if v != "N/A" else 0.0
        d, val, r, n = st.date_input("Date"), st.number_input("Qty (Cubes/Hours)", step=0.5), st.number_input("Rate (Dynamic)", value=float(def_r)), st.text_input("Note")
        if st.form_submit_button("Save Log"):
            q, h = (val, 0) if "Lorry" in op else (0, val)
            new = pd.DataFrame([[len(st.session_state.df)+1, d, "", "Process", op, v, n, 0, q, 0, h, r, "Done"]], columns=st.session_state.df.columns)
            st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()

# --- 8. FINANCE & SHED (v56 FULL) ---
elif menu == "💰 Finance & Shed":
    fin = st.radio("Finance Category", ["⛽ Fuel & Shed", "🔧 Repairs", "💸 Payroll", "🏦 Owner Advances", "🧾 Others"], horizontal=True)
    v_list = st.session_state.ve_db["No"].tolist() if not st.session_state.ve_db.empty else ["N/A"]
    
    if fin == "⛽ Fuel & Shed":
        f1, f2 = st.tabs(["⛽ Log Fuel Bill", "💳 Settle Shed Payments"])
        with f1:
            with st.form("fuel"):
                d, v, l, c = st.date_input("Date"), st.selectbox("Vehicle", v_list), st.number_input("Liters"), st.number_input("Cost")
                if st.form_submit_button("Save Fuel"):
                    new = pd.DataFrame([[len(st.session_state.df)+1, d, "", "Expense", "Fuel Entry", v, "Shed bill", c, 0, l, 0, 0, "Pending"]], columns=st.session_state.df.columns)
                    st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()
        with f2:
            with st.form("shed_pay"):
                am, ref = st.number_input("Amount Paid"), st.text_input("Reference")
                if st.form_submit_button("Record Payment"):
                    new = pd.DataFrame([[len(st.session_state.df)+1, datetime.now().date(), "", "Expense", "Shed Payment", "Shed", ref, am, 0, 0, 0, 0, "Paid"]], columns=st.session_state.df.columns)
                    st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()

    elif fin == "🔧 Repairs":
        with st.form("rep"):
            d, v, am, nt = st.date_input("Date"), st.selectbox("Vehicle", v_list), st.number_input("Cost"), st.text_input("Detail")
            if st.form_submit_button("Save Repair"):
                new = pd.DataFrame([[len(st.session_state.df)+1, d, "", "Expense", "Repair", v, nt, am, 0, 0, 0, 0, "Paid"]], columns=st.session_state.df.columns)
                st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()

    elif fin == "💸 Payroll":
        with st.form("pay"):
            dr = st.selectbox("Driver", st.session_state.dr_db["Name"].tolist() if not st.session_state.dr_db.empty else ["N/A"])
            am, ty, v_rel = st.number_input("Amount"), st.selectbox("Type", ["Driver Advance", "Salary"]), st.selectbox("Vehicle", v_list)
            if st.form_submit_button("Save Payroll"):
                new = pd.DataFrame([[len(st.session_state.df)+1, datetime.now().date(), "", "Expense", ty, v_rel, f"Driver: {dr}", am, 0, 0, 0, 0, "Paid"]], columns=st.session_state.df.columns)
                st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()

    elif fin == "🏦 Owner Advances":
        with st.form("own_adv"):
            d, v, am, nt = st.date_input("Date"), st.selectbox("Vehicle", v_list), st.number_input("Amount"), st.text_input("Note")
            if st.form_submit_button("Save Advance"):
                new = pd.DataFrame([[len(st.session_state.df)+1, d, "", "Expense", "Owner Advance", v, nt, am, 0, 0, 0, 0, "Paid"]], columns=st.session_state.df.columns)
                st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()

    elif fin == "🧾 Others":
        with st.form("oth"):
            d, cat, nt, am = st.date_input("Date"), st.selectbox("Category", ["Food", "Rent", "Utility", "Misc"]), st.text_input("Note"), st.number_input("Amount")
            if st.form_submit_button("Save Other"):
                new = pd.DataFrame([[len(st.session_state.df)+1, d, "", "Expense", cat, "Admin", nt, am, 0, 0, 0, 0, "Paid"]], columns=st.session_state.df.columns)
                st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()

# --- 9. SYSTEM SETUP ---
elif menu == "⚙️ System Setup":
    t1, t2 = st.tabs(["👷 Drivers", "🚜 Vehicles"])
    with t1:
        with st.form("dr"):
            n, p, s = st.text_input("Name"), st.text_input("Phone"), st.number_input("Salary")
            if st.form_submit_button("Add Driver"):
                st.session_state.dr_db = pd.concat([st.session_state.dr_db, pd.DataFrame([[n,p,s]], columns=st.session_state.dr_db.columns)], ignore_index=True); save_all(); st.rerun()
        st.table(st.session_state.dr_db)
    with t2:
        with st.form("ve"):
            v, t, r, o = st.text_input("No"), st.selectbox("Type", ["Lorry", "Excavator"]), st.number_input("Rate"), st.text_input("Owner")
            if st.form_submit_button("Add Vehicle"):
                st.session_state.ve_db = pd.concat([st.session_state.ve_db, pd.DataFrame([[v,t,o,r]], columns=st.session_state.ve_db.columns)], ignore_index=True); save_all(); st.rerun()
        st.table(st.session_state.ve_db)

# --- 10. REPORTS CENTER (UPDATED WITH DRIVER & SHED PDF) ---
elif menu == "📑 Reports Center":
    r1, r2, r3, r4 = st.tabs(["🚜 Vehicle Settlement", "👷 Driver Summary", "📑 Daily Log", "⛽ Shed Report"])
    f_d, t_d = st.date_input("From", datetime.now().date()-timedelta(days=30)), st.date_input("To")
    df_f = st.session_state.df[(st.session_state.df["Date"] >= f_d) & (st.session_state.df["Date"] <= t_d)]
    
    with r1:
        sel_ve = st.selectbox("Select Vehicle", st.session_state.ve_db["No"].tolist() if not st.session_state.ve_db.empty else [])
        if sel_ve:
            v_rep = df_f[df_f["Entity"] == sel_ve].copy()
            if not v_rep.empty:
                v_rep['Income_Calc'] = (v_rep['Hours'] + v_rep['Qty_Cubes']) * v_rep['Rate_At_Time']
                gross = v_rep['Income_Calc'].sum(); deduct = v_rep[v_rep["Type"] == "Expense"]["Amount"].sum(); net = gross - deduct
                st.metric("Net Balance", f"Rs. {net:,.2f}"); st.dataframe(v_rep)
                if st.button("Download PDF Settlement"):
                    avg_r = v_rep[v_rep['Rate_At_Time']>0]['Rate_At_Time'].iloc[0] if not v_rep[v_rep['Rate_At_Time']>0].empty else 0
                    summary = {"Vehicle": sel_ve, "Total Cubes/Hrs": (v_rep['Hours']+v_rep['Qty_Cubes']).sum(), "Rate": f"{avg_r:,.2f}", "Gross": f"{gross:,.2f}", "Net": f"{net:,.2f}"}
                    fn = create_pdf(f"Settlement_{sel_ve}", v_rep, summary)
                    with open(fn, "rb") as f: st.download_button("📩 Download PDF", f, file_name=fn)
    
    with r2:
        sel_dr = st.selectbox("Select Driver", st.session_state.dr_db["Name"].tolist() if not st.session_state.dr_db.empty else [])
        if sel_dr:
            dr_rep = df_f[df_f["Note"].str.contains(f"Driver: {sel_dr}", na=False)].copy()
            total_dr = dr_rep['Amount'].sum()
            st.metric(f"Total Paid to {sel_dr}", f"Rs. {total_dr:,.2f}"); st.dataframe(dr_rep)
            if st.button(f"Download {sel_dr} Report"):
                sum_dr = {"Driver": sel_dr, "Period": f"{f_d} to {t_d}", "Total Paid": f"{total_dr:,.2f}"}
                fn = create_pdf(f"Driver_{sel_dr}", dr_rep, sum_dr)
                with open(fn, "rb") as f: st.download_button("📩 Get PDF", f, file_name=fn)
    
    with r3:
        st.dataframe(df_f)
        st.metric("Total Expenses in Period", f"Rs. {df_f[df_f['Type']=='Expense']['Amount'].sum():,.2f}")

    with r4:
        st.subheader("Shed Summary")
        fuel_total = df_f[df_f["Category"] == "Fuel Entry"]["Amount"].sum()
        paid_total = df_f[df_f["Category"] == "Shed Payment"]["Amount"].sum()
        debt = fuel_total - paid_total
        c1, c2, c3 = st.columns(3)
        c1.metric("Fuel Bill", f"Rs. {fuel_total:,.2f}"); c2.metric("Paid", f"Rs. {paid_total:,.2f}"); c3.metric("Debt", f"Rs. {debt:,.2f}")
        shed_logs = df_f[df_f["Entity"] == "Shed"].copy()
        st.dataframe(shed_logs)
        if st.button("Download Shed PDF"):
            sum_sh = {"Report": "Shed Settlement", "Total Bill": f"{fuel_total:,.2f}", "Total Paid": f"{paid_total:,.2f}", "Net Debt": f"{debt:,.2f}"}
            fn = create_pdf("Shed_Statement", shed_logs, sum_sh)
            with open(fn, "rb") as f: st.download_button("📩 Download Shed PDF", f, file_name=fn)
