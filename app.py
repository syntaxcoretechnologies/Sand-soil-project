import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
from fpdf import FPDF

# --- 1. CONFIG & FILENAMES ---
DATA_FILE = "ksd_master_v56.csv"
VE_FILE = "ksd_vehicles_v56.csv"
DR_FILE = "ksd_drivers_v56.csv"
LANDOWNER_FILE = "landowners.csv"
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
        except: 
            return pd.DataFrame(columns=cols)
    return pd.DataFrame(columns=cols)

def save_all():
    # පරණ දත්ත සේව් කිරීම
    st.session_state.df.to_csv(DATA_FILE, index=False)
    st.session_state.ve_db.to_csv(VE_FILE, index=False)
    st.session_state.dr_db.to_csv(DR_FILE, index=False)
    
    # --- අලුත් Landowners සේව් කිරීම ---
    if 'landowners' in st.session_state and st.session_state.landowners:
        pd.DataFrame(st.session_state.landowners).to_csv(LANDOWNER_FILE, index=False)

# --- 3. SESSION STATE (මෙතන තමයි ඔක්කොම ලෝඩ් වෙන්නේ) ---

# 1. 'Name' කියන එක cols_master එකට අලුතින් එකතු කළා
cols_master = ["ID", "Date", "Time", "Type", "Category", "Name", "Entity", "Note", "Amount", "Qty_Cubes", "Fuel_Ltr", "Hours", "Rate_At_Time", "Status"]

if 'df' not in st.session_state:
    st.session_state.df = load_data(DATA_FILE, cols_master)
    
    # වැදගත්ම දේ: පරණ File එකේ 'Name' කොලම් එක නැත්නම් ඒක අලුතින් පද්ධතියට හඳුන්වා දෙනවා
    if not st.session_state.df.empty and "Name" not in st.session_state.df.columns:
        st.session_state.df["Name"] = ""

if 've_db' not in st.session_state:
    st.session_state.ve_db = load_data(VE_FILE, ["No", "Type", "Owner", "Rate_Per_Unit"])

if 'dr_db' not in st.session_state:
    st.session_state.dr_db = load_data(DR_FILE, ["Name", "Phone", "Daily_Salary"])

# --- Landowners දත්ත නිවැරදිව ලෝඩ් කිරීම ---
if 'landowners' not in st.session_state:
    if os.path.exists(LANDOWNER_FILE):
        try:
            temp_ld = pd.read_csv(LANDOWNER_FILE)
            st.session_state.landowners = temp_ld.to_dict('records')
        except:
            st.session_state.landowners = []
    else:
        st.session_state.landowners = []
# --- 4. PDF ENGINE (පැහැදිලිව Earnings සහ Expenses වෙන් කරන සම්පූර්ණ කෝඩ් එක) ---
class PDF(FPDF):
    def header(self):
        # ආයතනයේ නම (Title)
        self.set_font('Arial', 'B', 15)
        self.set_text_color(230, 126, 34) 
        self.cell(0, 10, "K. SIRIWARDHANA SAND CONSTRUCTION PROJECT", 0, 1, 'C')
        self.ln(5)

def create_pdf(title, data_df, summary_dict):
    pdf = PDF()
    pdf.add_page()
    
    def safe_text(text):
        if text is None or str(text) == "nan": return ""
        return str(text).encode("latin-1", "ignore").decode("latin-1")

    # Statement Title කොටස
    pdf.set_font("Arial", 'B', 12)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 10, safe_text(f"STATEMENT: {title.upper()}"), 1, 1, 'L', fill=True)
    pdf.ln(2)
    
    # --- Summary Section (මූලික විස්තර) ---
    pdf.set_font("Arial", 'B', 10)
    for k, v in summary_dict.items():
        if k != "Rate_Breakdown":
            pdf.cell(50, 8, safe_text(k) + ":", 1)
            pdf.set_font("Arial", '', 10)
            pdf.cell(0, 8, " " + safe_text(v), 1, 1)
            pdf.set_font("Arial", 'B', 10)

    # --- Table Header ---
    pdf.ln(8)
    pdf.set_font("Arial", 'B', 9)
    headers = ["Date", "Category", "Description", "Qty/Hr", "Rate", "Amount"]
    w = [22, 35, 50, 15, 25, 43]
    pdf.set_fill_color(220, 220, 220)
    for i, h in enumerate(headers):
        pdf.cell(w[i], 8, safe_text(h), 1, 0, 'C', fill=True)
    pdf.ln()
    
    # --- Data Rows ---
    pdf.set_font("Arial", '', 8)
    total_earn = 0
    total_exp = 0
    
    for _, row in data_df.iterrows():
        pdf.cell(w[0], 7, safe_text(str(row.get('Date', '-'))), 1)
        pdf.cell(w[1], 7, safe_text(str(row.get('Category', 'N/A'))), 1)
        
        # Note එක Safe විදිහට ගැනීම
        note_val = str(row.get('Note', ''))
        pdf.cell(w[2], 7, safe_text(note_val)[:30], 1)
        
        # Qty සහ Work Hours ගණනය කිරීම
        w_hrs = row.get('Work_Hours', 0)
        q_cubes = row.get('Qty_Cubes', 0)
        qty = w_hrs if w_hrs > 0 else q_cubes
        
        pdf.cell(w[3], 7, f"{qty}" if qty > 0 else "-", 1, 0, 'C')
        
        rate = row['Rate_At_Time']
        pdf.cell(w[4], 7, f"{rate:,.2f}" if rate > 0 else "-", 1, 0, 'R')
        
        amt = float(row['Amount'])
        category = str(row['Category'])
        
        # --- වැදගත්ම තැන: ආදායම සහ වියදම වෙන් කිරීම ---
        
        # 1. වාහනයේ කුලී ආදායම (Earnings) - Work Log හෝ Hire පමණි
        if "Work Log" in category or "Hire" in category or row['Type'] == "Process":
            total_earn += amt
            pdf.set_text_color(0, 0, 0)
            pdf.cell(w[5], 7, f"{amt:,.2f}", 1, 0, 'R')
            
        # 2. වාහනයේ සැබෑ වියදම් (Expenses) - Fuel, Repair, Payroll, Advance
        elif any(exp in category for exp in ["Fuel", "Repair", "Advance", "Payroll", "Salary"]):
            total_exp += amt
            pdf.set_text_color(200, 0, 0) # වියදම් රතු පාටින්
            pdf.cell(w[5], 7, f"({amt:,.2f})", 1, 0, 'R')
            pdf.set_text_color(0, 0, 0)
            
        # 3. අනෙකුත් දේවල් (Sales Out වැනි දෑ) - Table එකේ පෙන්වයි, නමුත් එකතුවට නොගනී
        else:
            pdf.set_text_color(100, 100, 100) # ලා අළු පාටින්
            pdf.cell(w[5], 7, f"{amt:,.2f}", 1, 0, 'R')
            pdf.set_text_color(0, 0, 0)
            
        pdf.ln()
    
    # --- අවසාන එකතුව (Final Totals) ---
    pdf.ln(2)
    pdf.set_font("Arial", 'B', 9)
    
    # Gross Earnings
    pdf.cell(sum(w[:5]), 8, "GROSS EARNINGS (LKR)", 1, 0, 'R')
    pdf.cell(w[5], 8, f"{total_earn:,.2f}", 1, 1, 'R')
    
    # Total Expenses (වාහනයට අදාළ වියදම් පමණි)
    pdf.cell(sum(w[:5]), 8, "TOTAL EXPENSES (LKR)", 1, 0, 'R')
    pdf.cell(w[5], 8, f"{total_exp:,.2f}", 1, 1, 'R')
    
    # Net Balance
    pdf.set_fill_color(230, 126, 34); pdf.set_text_color(255, 255, 255)
    pdf.cell(sum(w[:5]), 10, "NET SETTLEMENT BALANCE (LKR)", 1, 0, 'R', fill=True)
    pdf.cell(w[5], 10, f"{(total_earn - total_exp):,.2f}", 1, 1, 'R', fill=True)
    
    # PDF එක Save කිරීම
    fn = f"Settlement_{datetime.now().strftime('%H%M%S')}.pdf"
    pdf.output(fn)
    return fn

# --- Landowner PDF Engine (මේක අලුතින්ම දාන කොටස) ---
def create_landowner_pdf(title, data_df, summary_dict):
    pdf = PDF() # මෙතන PDF කියන්නේ ඔයා උඩින්ම හදපු class එක
    pdf.add_page()
    
    def safe_text(text):
        if text is None or str(text) == "nan": return ""
        return str(text).encode("latin-1", "ignore").decode("latin-1")

    pdf.set_font("Arial", 'B', 12)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 10, safe_text(f"LANDOWNER STATEMENT: {title.upper()}"), 1, 1, 'L', fill=True)
    pdf.ln(2)
    
    # Summary Section
    pdf.set_font("Arial", 'B', 10)
    for k, v in summary_dict.items():
        pdf.cell(50, 8, safe_text(k) + ":", 1)
        pdf.set_font("Arial", '', 10)
        pdf.cell(0, 8, " " + safe_text(v), 1, 1)
        pdf.set_font("Arial", 'B', 10)

    pdf.ln(8)
    pdf.set_font("Arial", 'B', 9)
    headers = ["Date", "Category", "Note", "Cubes", "Rate", "Amount"]
    w = [22, 35, 50, 15, 25, 43]
    pdf.set_fill_color(220, 220, 220)
    for i, h in enumerate(headers):
        pdf.cell(w[i], 8, safe_text(h), 1, 0, 'C', fill=True)
    pdf.ln()
    
    pdf.set_font("Arial", '', 8)
    total_payable = 0
    total_paid = 0
    
    for _, row in data_df.iterrows():
        pdf.cell(w[0], 7, safe_text(row['Date']), 1)
        pdf.cell(w[1], 7, safe_text(row['Category']), 1)
        pdf.cell(w[2], 7, safe_text(row['Note'])[:30], 1)
        
        cubes = row['Qty_Cubes']
        pdf.cell(w[3], 7, f"{cubes}" if cubes > 0 else "-", 1, 0, 'C')
        
        rate = row['Rate_At_Time']
        pdf.cell(w[4], 7, f"{rate:,.2f}" if rate > 0 else "-", 1, 0, 'R')
        
        amt = float(row['Amount'])
        category = str(row['Category'])
        
        if "Inward" in category or "Inward" in str(row.get('Record_Type', '')):
            total_payable += amt
            pdf.cell(w[5], 7, f"{amt:,.2f}", 1, 0, 'R')
        elif any(x in category for x in ["Advance", "Payment"]):
            total_paid += amt
            pdf.set_text_color(200, 0, 0)
            pdf.cell(w[5], 7, f"({amt:,.2f})", 1, 0, 'R')
            pdf.set_text_color(0, 0, 0)
        else:
            pdf.cell(w[5], 7, "-", 1, 0, 'R')
        pdf.ln()
    
    pdf.ln(2); pdf.set_font("Arial", 'B', 9)
    pdf.cell(sum(w[:5]), 8, "TOTAL PAYABLE FOR CUBES (LKR)", 1, 0, 'R')
    pdf.cell(w[5], 8, f"{total_payable:,.2f}", 1, 1, 'R')
    pdf.cell(sum(w[:5]), 8, "TOTAL ADVANCES PAID (LKR)", 1, 0, 'R')
    pdf.cell(w[5], 8, f"{total_paid:,.2f}", 1, 1, 'R')
    pdf.set_fill_color(39, 174, 96); pdf.set_text_color(255, 255, 255)
    pdf.cell(sum(w[:5]), 10, "NET BALANCE TO BE PAID (LKR)", 1, 0, 'R', fill=True)
    pdf.cell(w[5], 10, f"{(total_payable - total_paid):,.2f}", 1, 1, 'R', fill=True)
    
    fn = f"Landowner_Settlement_{datetime.now().strftime('%H%M%S')}.pdf"
    pdf.output(fn)
    return fn
    
# --- 5. UI LAYOUT & DASHBOARD ---
st.set_page_config(page_title=SHOP_NAME, layout="wide")
st.sidebar.title("🏗️ KSD ERP v5.6")

# මේ පේළිය පිටුවේ වම් කෙළවරේ සිටම පටන් ගන්න (No spaces)
menu = st.sidebar.selectbox("MAIN MENU", ["📊 Dashboard", "🏗️ Site Operations","👤 Manage Landowners", "💰 Finance & Shed", "⚙️ System Setup", "📑 Reports Center", "⚙️ Data Manager"])


# --- 1. DASHBOARD SECTION (සම්පූර්ණ එකම මෙතන තියෙනවා) ---
if menu == "📊 Dashboard":
    st.markdown("<h2 style='color: #2E86C1;'>📊 Business Overview</h2>", unsafe_allow_html=True)
    df = st.session_state.df.copy()
    
    if not df.empty:
        # --- DATE FILTER ---
        st.subheader("📅 Filter Transactions")
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            start_date = st.date_input("From Date", datetime.now().date() - timedelta(days=7))
        with col_f2:
            end_date = st.date_input("To Date", datetime.now().date())
        
        df['Date'] = pd.to_datetime(df['Date']).dt.date
        mask = (df['Date'] >= start_date) & (df['Date'] <= end_date)
        filtered_df = df.loc[mask].copy()

        if not filtered_df.empty:
            # --- FINANCIAL METRICS ---
            sales_df = filtered_df[filtered_df["Category"].str.contains("Sales Out", na=False)].copy()
            sales_df['Income'] = pd.to_numeric(sales_df['Qty_Cubes'], errors='coerce').fillna(0) * \
                                 pd.to_numeric(sales_df['Rate_At_Time'], errors='coerce').fillna(0)
            real_income = sales_df['Income'].sum()
            total_expenses = pd.to_numeric(filtered_df[filtered_df["Type"] == "Expense"]["Amount"], errors='coerce').sum()

            m1, m2, m3 = st.columns(3)
            m1.metric("Net Sales Income", f"Rs. {real_income:,.2f}")
            m2.metric("Total Expenses", f"Rs. {total_expenses:,.2f}")
            m3.metric("Net Cashflow", f"Rs. {real_income - total_expenses:,.2f}")

            st.divider()

            # ==========================================
            # 📦 STOCK BALANCE (අපි අන්තිමට හදපු කොටස)
            # ==========================================
            st.subheader("📦 Plant Stock Balance (Current)")
            s_col1, s_col2 = st.columns(2)
            
            # මුළු ඉතිහාසයම පරීක්ෂා කර stock එක ගණනය කිරීම
            full_df = st.session_state.df.copy()
            
            # Sand Calculation
            s_in = full_df[full_df["Category"].str.contains("Stock Inward", na=False) & 
                           full_df["Category"].str.contains("Sand", na=False)]["Qty_Cubes"].sum()
            s_out = full_df[full_df["Category"].str.contains("Sales Out", na=False) & 
                            full_df["Category"].str.contains("Sand", na=False)]["Qty_Cubes"].sum()
            
            # Soil Calculation
            so_in = full_df[full_df["Category"].str.contains("Stock Inward", na=False) & 
                            full_df["Category"].str.contains("Soil", na=False)]["Qty_Cubes"].sum()
            so_out = full_df[full_df["Category"].str.contains("Sales Out", na=False) & 
                             full_df["Category"].str.contains("Soil", na=False)]["Qty_Cubes"].sum()

            s_col1.metric("Sand Remaining", f"{s_in - s_out:.2f} Cubes", delta=f"In: {s_in} | Out: {s_out}")
            s_col2.metric("Soil Remaining", f"{so_in - so_out:.2f} Cubes", delta=f"In: {so_in} | Out: {so_out}")
            # ==========================================

            st.divider()
            st.subheader("Daily Income Trend")
            st.line_chart(sales_df.groupby('Date')['Income'].sum())
        else:
            st.warning("තෝරාගත් දින පරාසය තුළ දත්ත නැත.")
    else:
        st.info("පද්ධතියේ දත්ත කිසිවක් නැත.")

# --- 2. SITE OPERATIONS SECTION ---
# මේ 'elif' එක පටන් ගන්න ඕනේ උඩ තියෙන 'if menu == "📊 Dashboard":' එකට කෙළින්ම පල්ලෙහායින්
# --- කලින් තිබුණු Site Operations එක අයින් කරලා මේක දාන්න ---
elif menu == "🏗️ Site Operations":
    st.markdown(f"<h2 style='color: #E67E22;'>🏗️ Site Operations & Stock Manager</h2>", unsafe_allow_html=True)
    
    op = st.radio("Select Activity Type", ["🚜 Excavator Work Log", "💰 Sales Out", "📥 Stock Inward (To Plant)"], horizontal=True)
    
    v_list = st.session_state.ve_db["No"].tolist() if not st.session_state.ve_db.empty else ["N/A"]
    d_list = st.session_state.dr_db["Name"].tolist() if not st.session_state.dr_db.empty else ["No Drivers Registered"]
    l_list = [owner["Name"] for owner in st.session_state.landowners] if st.session_state.landowners else ["No Owners Registered"]

    with st.form("site_f", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            v = st.selectbox("Select Vehicle / Machine", v_list if op != "📥 Stock Inward (To Plant)" else ["Internal / Third Party"])
            d = st.date_input("Date", datetime.now().date())
            material = st.selectbox("Material Type", ["Sand", "Soil", "Other"]) if (op == "💰 Sales Out" or op == "📥 Stock Inward (To Plant)") else ""
            
            if op == "📥 Stock Inward (To Plant)":
                src_owner = st.selectbox("Source (Landowner)", l_list)
                src_driver = st.selectbox("Driver/Operator", d_list)
        
        with col2:
            val_label = "Work Hours" if "Excavator" in op else "Qty (Cubes)"
            unit = "Hrs" if "Excavator" in op else "Cubes"
            val = st.number_input(val_label, min_value=0.0, step=0.5, value=0.0)
            r = st.number_input(f"Enter Rate per {unit} (LKR)", min_value=0.0, step=100.0, value=0.0)
            
        n = st.text_input("Additional Note")
        
        if st.form_submit_button("📥 Save Record"):
            # ... (අනිත් වැලිඩේෂන් ටික තිබුණාවෙ) ...
            
            # මචං, අපි බලමු මේ variable එකට නම එනවද කියලා
            entry_name = str(src_owner) if op == "📥 Stock Inward (To Plant)" else str(v)
            
            # --- DEBUG: මේකෙන් අපිට බලාගන්න පුළුවන් නම මොකක්ද කියලා සේව් වෙන්න කලින් ---
            st.write(f"Saving name: {entry_name}") 

            new_data = {
                "ID": int(len(st.session_state.df) + 1),
                "Date": d,
                "Name": entry_name,  # <--- කෙලින්ම variable එක දැම්මා
                "Record_Type": "Inward" if op == "📥 Stock Inward (To Plant)" else "Process",
                "Category": f"{op} ({material})" if material else op,
                "Entity": v,
                "Note": f"{n} | Drv: {src_driver}" if op == "📥 Stock Inward (To Plant)" else n,
                "Amount": float(val * r),
                "Qty_Cubes": float(val) if "Qty" in val_label else 0.0,
                "Expense": 0.0,
                "Work_Hours": float(val) if "Hours" in val_label else 0.0,
                "Rate_At_Time": float(r),
                "Status": "Done"
            }
            
            # DataFrame එකට එකතු කිරීම
            st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_data])], ignore_index=True)
            save_all()
            st.success(f"Saved: {entry_name}")
            st.rerun()

    # Today's Logs පෙන්වීම
    st.divider()
    st.subheader("Today's Logs")
    temp_df = st.session_state.df.copy()
    temp_df['Date'] = pd.to_datetime(temp_df['Date']).dt.date
    today_df = temp_df[temp_df["Date"] == datetime.now().date()]
    st.dataframe(today_df, use_container_width=True)
    
# --- 8. FINANCE & SHED (v56 FULL) ---
elif menu == "💰 Finance & Shed":
    fin = st.radio("Finance Category", ["⛽ Fuel & Shed", "🔧 Repairs", "💸 Payroll", "🏦 Owner Advances", "🧾 Others"], horizontal=True)
    v_list = st.session_state.ve_db["No"].tolist() if not st.session_state.ve_db.empty else ["N/A"]
    
    if fin == "⛽ Fuel & Shed":
        f1, f2 = st.tabs(["⛽ Log Fuel Bill", "💳 Settle Shed Payments"])
        with f1:
            with st.form("fuel", clear_on_submit=True):
                d, v, l, c = st.date_input("Date"), st.selectbox("Vehicle", v_list), st.number_input("Liters"), st.number_input("Cost")
                if st.form_submit_button("Save Fuel"):
                    # Dictionary එකක් ලෙස දත්ත සැකසීම
                    new_data = {
                        "ID": len(st.session_state.df) + 1, "Date": d, "Time": "", "Type": "Expense",
                        "Category": "Fuel Entry", "Entity": v, "Note": "Shed bill", "Amount": c,
                        "Qty_Cubes": 0, "Fuel_Ltr": l, "Hours": 0, "Rate_At_Time": 0, "Status": "Pending"
                    }
                    st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_data])], ignore_index=True)
                    save_all(); st.rerun()
        with f2:
            with st.form("shed_pay", clear_on_submit=True):
                am, ref = st.number_input("Amount Paid"), st.text_input("Reference")
                if st.form_submit_button("Record Payment"):
                    new_data = {
                        "ID": len(st.session_state.df) + 1, "Date": datetime.now().date(), "Time": "", "Type": "Expense",
                        "Category": "Shed Payment", "Entity": "Shed", "Note": ref, "Amount": am,
                        "Qty_Cubes": 0, "Fuel_Ltr": 0, "Hours": 0, "Rate_At_Time": 0, "Status": "Paid"
                    }
                    st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_data])], ignore_index=True)
                    save_all(); st.rerun()

    elif fin == "🔧 Repairs":
        with st.form("rep", clear_on_submit=True):
            d, v, am, nt = st.date_input("Date"), st.selectbox("Vehicle", v_list), st.number_input("Cost"), st.text_input("Detail")
            if st.form_submit_button("Save Repair"):
                new_data = {
                    "ID": len(st.session_state.df) + 1, "Date": d, "Time": "", "Type": "Expense",
                    "Category": "Repair", "Entity": v, "Note": nt, "Amount": am,
                    "Qty_Cubes": 0, "Fuel_Ltr": 0, "Hours": 0, "Rate_At_Time": 0, "Status": "Paid"
                }
                st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_data])], ignore_index=True)
                save_all(); st.rerun()

    elif fin == "💸 Payroll":
        dr_names = st.session_state.dr_db["Name"].tolist() if not st.session_state.dr_db.empty else ["N/A"]
        with st.form("pay", clear_on_submit=True):
            dr = st.selectbox("Driver", dr_names)
            am, ty, v_rel = st.number_input("Amount"), st.selectbox("Type", ["Driver Advance", "Salary"]), st.selectbox("Vehicle", v_list)
            if st.form_submit_button("Save Payroll"):
                new_data = {
                    "ID": len(st.session_state.df) + 1, "Date": datetime.now().date(), "Time": "", "Type": "Expense",
                    "Category": ty, "Entity": v_rel, "Note": f"Driver: {dr}", "Amount": am,
                    "Qty_Cubes": 0, "Fuel_Ltr": 0, "Hours": 0, "Rate_At_Time": 0, "Status": "Paid"
                }
                st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_data])], ignore_index=True)
                save_all(); st.rerun()

    elif fin == "🏦 Owner Advances":
        with st.form("own_adv", clear_on_submit=True):
            d, v, am, nt = st.date_input("Date"), st.selectbox("Vehicle", v_list), st.number_input("Amount"), st.text_input("Note")
            if st.form_submit_button("Save Advance"):
                new_data = {
                    "ID": len(st.session_state.df) + 1, "Date": d, "Time": "", "Type": "Expense",
                    "Category": "Owner Advance", "Entity": v, "Note": nt, "Amount": am,
                    "Qty_Cubes": 0, "Fuel_Ltr": 0, "Hours": 0, "Rate_At_Time": 0, "Status": "Paid"
                }
                st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_data])], ignore_index=True)
                save_all(); st.rerun()

    elif fin == "🧾 Others":
        with st.form("oth"):
            d, cat, nt, am = st.date_input("Date"), st.selectbox("Category", ["Food", "Rent", "Utility", "Misc"]), st.text_input("Note"), st.number_input("Amount")
            if st.form_submit_button("Save Other"):
                new_data = {
                    "ID": len(st.session_state.df) + 1, "Date": d, "Time": "", "Type": "Expense",
                    "Category": cat, "Entity": "Admin", "Note": nt, "Amount": am,
                    "Qty_Cubes": 0, "Fuel_Ltr": 0, "Hours": 0, "Rate_At_Time": 0, "Status": "Paid"
                }
                st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_data])], ignore_index=True)
                save_all(); st.rerun()

# --- 9. SYSTEM SETUP ---
elif menu == "📑 Reports Center":
    st.markdown("<h2 style='color: #8E44AD;'>📑 Business Reports Center</h2>", unsafe_allow_html=True)
    
    # Column Fixes
    df_raw = st.session_state.df.copy()
    df_raw.columns = [str(c).strip() for c in df_raw.columns]
    df_raw.rename(columns={'Vehicle No': 'Vehicle', 'Vehicle_No': 'Vehicle', 'Entity': 'Vehicle'}, inplace=True)

    # Tabs

    r_inc, r_prof, r_gross, r1, r2, r3, r4 = st.tabs([
        "💰 Daily Income Report", 
        "📊 Profit/Loss Analysis",
        "📈 Material Gross Earnings", # Aluth Tab eka
        "🚜 Vehicle Settlement", 
        "👷 Driver Summary", 
        "📑 Daily Log", 
        "⛽ Shed Report"
    ])
    
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        f_d = st.date_input("From Date", datetime.now().date() - timedelta(days=30), key="r_from")
    with col_d2:
        t_d = st.date_input("To Date", datetime.now().date(), key="r_to")

    df_raw['Date'] = pd.to_datetime(df_raw['Date']).dt.date
    df_f = df_raw[(df_raw["Date"] >= f_d) & (df_raw["Date"] <= t_d)].copy()
    
    # --- TAB: DAILY INCOME REPORT (FIXED) ---
    with r_inc:
        st.subheader("Daily Sales & Income Statement")
        
        df_f.columns = [c.strip() for c in df_f.columns]
        daily_sales = df_f[df_f["Category"].str.contains("Sales Out", na=False)].copy()
        
        if not daily_sales.empty:
            # 1. PDF එකේ calculation වලට අවශ්‍ය හැම column එකක්ම මෙතනට දැම්මා
            # Work_Hours සහ Qty_Cubes දෙකම අනිවාර්යයෙන්ම තියෙන්න ඕනේ
            required_cols = ['Date', 'Category', 'Name', 'Note', 'Qty_Cubes', 'Work_Hours', 'Rate_At_Time', 'Amount']
            available_cols = daily_sales.columns.tolist()
            final_cols = [c for c in required_cols if c in available_cols]
            
            # PDF එකට යවන දත්ත (දැන් මෙතන 'Work_Hours' තියෙනවා)
            pdf_data = daily_sales[final_cols].copy() 

            # 2. Display කරන්න විතරක් Rename කරපු එකක් හදාගමු
            display_sales = pdf_data.copy()
            rename_dict = {
                'Date': 'Date', 'Category': 'Material', 'Name': 'Client/Owner', 
                'Note': 'Description', 'Qty_Cubes': 'Qty', 'Rate_At_Time': 'Rate', 'Amount': 'Total Amount'
            }
            display_sales.rename(columns=rename_dict, inplace=True)
            
            st.dataframe(display_sales, use_container_width=True)
            
            if 'Total Amount' in display_sales.columns:
                total_daily_inc = display_sales['Total Amount'].sum()
                st.success(f"Selected Period Total Income: **LKR {total_daily_inc:,.2f}**")
            
            # 3. PDF Button එක
            if st.button("📥 Download Daily Income PDF"):
                inc_summary = {
                    "Report Type": "Daily Income Statement",
                    "Period": f"{f_d} to {t_d}",
                    "Total Items": len(pdf_data),
                    "Total Gross Income": f"LKR {pdf_data['Amount'].sum():,.2f}" if 'Amount' in pdf_data.columns else "0.00"
                }
                # මෙතනදී අපි යවන්නේ Rename නොකරපු 'pdf_data' එක. එතකොට 'Category' කොලම් එක ඒකේ තියෙනවා.
                pdf_fn = create_pdf(f"Daily_Income", pdf_data, inc_summary)
                with open(pdf_fn, "rb") as f:
                    st.download_button("📩 Click to Download PDF", f, file_name=f"Income_Report_{f_d}.pdf")
        else:
            st.warning("තෝරාගත් දින පරාසය තුළ Sales records කිසිවක් නැත.")
            
    # --- TAB: PROFIT/LOSS ANALYSIS ---
    with r_prof:
        st.subheader("Daily Profit & Loss Analysis")
        if not df_f.empty:
            # Income (Sales)
            inc_data = df_f[df_f["Category"].str.contains("Sales Out", na=False)].copy()
            inc_data['Val'] = pd.to_numeric(inc_data['Amount'], errors='coerce').fillna(0)
            
            # Expense (All Expenses)
            exp_data = df_f[df_f["Type"] == "Expense"].copy()
            exp_data['Val'] = pd.to_numeric(exp_data['Amount'], errors='coerce').fillna(0)

            d_inc = inc_data.groupby('Date')['Val'].sum()
            d_exp = exp_data.groupby('Date')['Val'].sum()
            
            profit_df = pd.concat([d_inc, d_exp], axis=1).fillna(0)
            profit_df.columns = ['Income', 'Expense']
            profit_df['Net Profit'] = profit_df['Income'] - profit_df['Expense']
            
            st.bar_chart(profit_df[['Income', 'Expense']])
            st.dataframe(profit_df.style.format("{:,.2f}"), use_container_width=True)
            
            # Totals
            t_i, t_e = profit_df['Income'].sum(), profit_df['Expense'].sum()
            st.info(f"Summary: Total Income: LKR {t_i:,.2f} | Total Expense: LKR {t_e:,.2f} | Net Profit: LKR {t_i-t_e:,.2f}")

    # --- TAB: MATERIAL GROSS EARNINGS (FIXED) ---
    with r_gross:
        st.subheader("Material Gross Earnings (Sales Revenue)")
        
        # 1. Column names වල හිස්තැන් අයින් කරලා Clean කරමු
        df_f.columns = [c.strip() for c in df_f.columns]
        
        # 2. Sales records පමණක් පෙරමු
        gross_df = df_f[df_f["Category"].str.contains("Sales Out", na=False)].copy()
        
        if not gross_df.empty:
            # 3. Material Type එක වෙන් කරගමු
            gross_df['Material_Type'] = gross_df['Category'].apply(
                lambda x: "Sand" if "Sand" in x else ("Soil" if "Soil" in x else "Other")
            )
            
            # 4. Amount column එක තියෙනවාද බලමු (ගණනය කිරීම් වලට)
            if 'Amount' in gross_df.columns:
                gross_df['Amount'] = pd.to_numeric(gross_df['Amount'], errors='coerce').fillna(0)
                summary_gross = gross_df.groupby('Material_Type')['Amount'].sum().reset_index()
                summary_gross.columns = ['Material', 'Total Gross Earning (LKR)']
                
                col_g1, col_g2 = st.columns([1, 2])
                with col_g1:
                    st.write("**Earnings by Material:**")
                    st.dataframe(summary_gross.style.format({"Total Gross Earning (LKR)": "{:,.2f}"}), use_container_width=True)
                
                with col_g2:
                    st.bar_chart(data=summary_gross, x='Material', y='Total Gross Earning (LKR)')
            
            st.divider()
            st.write("**Detailed Sales Log:**")
            
            # 5. Column එකක් නැති වුණොත් Error එක එන එක මෙතනින් නවත්වනවා
            req_cols = ['Date', 'Entity', 'Category', 'Qty_Cubes', 'Amount']
            available_cols = [c for c in req_cols if c in gross_df.columns]
            
            # තියෙන Column ටික විතරක් පෙන්වන්න
            st.dataframe(gross_df[available_cols], use_container_width=True)
        else:
            st.info("No sales records found for the selected period.")

    # --- TAB 1: VEHICLE SETTLEMENT ---
   # 1. වාහන ලැයිස්තුව ලබා ගනිමු
    v_list = st.session_state.ve_db["No"].tolist() if not st.session_state.ve_db.empty else ["N/A"]

    with r1:
        st.subheader("Vehicle / Machine Settlement")
        
        selected_ve = st.selectbox("Select Vehicle to Settle", v_list, key="settle_ve")
        
        if selected_ve and selected_ve != "N/A":
            # 2. වාහනය පෙන්වන Column එක මොකක්ද කියලා බුද්ධිමත්ව සොයා ගනිමු
            # 'Entity' නැත්නම් 'Vehicle' හෝ 'Vehicle_No' තියෙනවාද බලනවා
            col_options = ['Entity', 'Vehicle', 'Vehicle_No', 'Machine', 'No']
            target_col = next((c for c in col_options if c in df_f.columns), None)
            
            if target_col:
                ve_records = df_f[df_f[target_col] == selected_ve].copy()
                
                if not ve_records.empty:
                    # Excavator එකක්ද කියා පරීක්ෂා කිරීම
                    is_excavator = any(x in selected_ve.upper() for x in ["EX", "PC", "EXCAVATOR"])
                    
                    # Earnings සහ Expenses ගණනය කිරීම
                    # Amount column එකේ නමත් check කරනවා (Spaces තිබුණොත් අයින් කරලා)
                    df_f.columns = [c.strip() for c in df_f.columns]
                    
                    if is_excavator:
                        gross_earning = pd.to_numeric(ve_records['Amount'], errors='coerce').sum()
                    else:
                        gross_earning = 0.0
                    
                    total_exp = pd.to_numeric(ve_records[ve_records["Type"] == "Expense"]["Amount"], errors='coerce').sum()
                    net_balance = gross_earning - total_exp
                    
                    # Metrics
                    c1, c2, c3 = st.columns(3)
                    if is_excavator:
                        c1.metric("Gross Earning (Work)", f"Rs. {gross_earning:,.2f}")
                    else:
                        c1.metric("Gross Earning", "Rs. 0.00", delta="Rented Lorry", delta_color="off")
                    
                    c2.metric("Total Expenses", f"Rs. {total_exp:,.2f}")
                    c3.metric("Net Settlement", f"Rs. {net_balance:,.2f}")
                    
                    st.divider()

                    # PDF Download Button
                    if st.button("📥 Download Settlement PDF"):
                        summary_data = {
                            "Vehicle/Machine": selected_ve,
                            "Type": "Excavator (Own)" if is_excavator else "Lorry (Rented)",
                            "Gross Earnings": f"Rs. {gross_earning:,.2f}",
                            "Total Expenses": f"Rs. {total_exp:,.2f}",
                            "Net Balance": f"Rs. {net_balance:,.2f}",
                            "Period": f"{f_d} to {t_d}"
                        }
                        pdf_path = create_pdf("Settlement_Report", ve_records, summary_data)
                        with open(pdf_path, "rb") as f:
                            st.download_button("📩 Download PDF", f, file_name=f"{selected_ve}_Settlement.pdf")

                    st.write(f"**Detailed Transaction Log for {selected_ve}:**")
                    display_cols = ['Date', 'Category', 'Qty_Cubes', 'Work_Hours', 'Amount', 'Type']
                    safe_cols = [c for c in display_cols if c in ve_records.columns]
                    st.dataframe(ve_records[safe_cols], use_container_width=True)
                else:
                    st.info(f"No records found for {selected_ve} in the selected period.")
            else:
                st.error("Could not find a 'Vehicle' or 'Entity' column in your data records.")
                # --- මෙන්න මෙතනින් පටන් ගන්න (Landowner Settlement Section) ---
 
     # --- Landowner Settlement Section (No Date Filter Version) ---
        st.divider()
        st.subheader("👤 Landowner Settlement (Testing)")

        if "landowners" in st.session_state and st.session_state.landowners:
            reg_names = [owner['Name'] for owner in st.session_state.landowners]
            selected_lo = st.selectbox("Select Landowner", sorted(reg_names), key="test_fix_101")

            if selected_lo:
                # අපි කෙලින්ම මුළු ඩේටාබේස් එකම (st.session_state.df) පාවිච්චි කරමු
                full_db = st.session_state.df.copy()
                
                # නම සර්ච් කිරීම
                search_n = str(selected_lo).strip().lower()
                lo_records = full_db[full_db['Name'].astype(str).str.strip().str.lower() == search_n].copy()
                
                if not lo_records.empty:
                    st.success(f"දත්ත {len(lo_records)} ක් හමු වුණා!")
                    st.dataframe(lo_records)
                else:
                    st.error(f"'{selected_lo}' නමින් කිසිදු දත්තයක් මුළු ඩේටාබේස් එකේම නැහැ.")
                    st.write("ඩේටාබේස් එකේ දැනට තියෙන නම්:", full_db['Name'].unique().tolist())
        else:
            st.warning("No Registered Landowners.")
            
    # --- TAB 2: DRIVER SUMMARY ---
    with r2:
        dr_list = st.session_state.dr_db["Name"].tolist() if not st.session_state.dr_db.empty else []
        sel_dr = st.selectbox("Select Driver", dr_list)
        if sel_dr:
            dr_rep = df_f[df_f["Note"].fillna("").astype(str).str.contains(sel_dr, case=False)].copy()
            st.metric(f"Total Paid to {sel_dr}", f"Rs. {pd.to_numeric(dr_rep['Amount'], errors='coerce').sum():,.2f}")
            st.dataframe(dr_rep[['Date', 'Category', 'Vehicle', 'Note', 'Amount']], use_container_width=True)

    # --- TAB 3: DAILY LOG ---
    with r3:
        st.dataframe(df_f, use_container_width=True)

    # --- TAB 4: SHED REPORT ---
    with r4:
        shed_f = df_f[df_f["Category"].str.contains("Fuel|Shed", na=False, case=False)].copy()
        f_bill = pd.to_numeric(shed_f[shed_f["Category"] == "Fuel Entry"]["Amount"], errors='coerce').sum()
        p_paid = pd.to_numeric(shed_f[shed_f["Category"] == "Shed Payment"]["Amount"], errors='coerce').sum()
        st.metric("Shed Debt", f"Rs. {f_bill - p_paid:,.2f}")
        st.dataframe(shed_f, use_container_width=True)

# --- 10. SYSTEM SETUP (මේ කොටස අලුතින් ඇතුළත් කරන්න) ---
elif menu == "⚙️ System Setup":
    st.markdown("<h2 style='color: #2E86C1;'>⚙️ System Configuration</h2>", unsafe_allow_html=True)
    
    # Tabs දෙකක් සාදමු
    # වාහන සහ ඩ්‍රයිවර්ස්ලා setup කරන tabs දෙක (නිවැරදි Indentation සහිතව)
    setup_tab1, setup_tab2 = st.tabs(["🚜 Vehicles", "👷 Drivers"])

    with setup_tab1:
        st.subheader("🚜 Add New Vehicle / Machine")
        with st.form("v_setup_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                v_no = st.text_input("Vehicle Number")
                v_type = st.selectbox("Vehicle Type", ["Tipper", "Excavator", "JCB", "Tractor", "Other"])
            with col2:
                v_owner = st.text_input("Owner Name")
                v_rate = st.number_input("Rate per Unit", min_value=0.0)
            
            if st.form_submit_button("✅ Register Vehicle"):
                if v_no:
                    new_v = pd.DataFrame([[v_no, v_type, v_owner, v_rate]], columns=["No", "Type", "Owner", "Rate_Per_Unit"])
                    st.session_state.ve_db = pd.concat([st.session_state.ve_db, new_v], ignore_index=True)
                    save_all()
                    st.success(f"Vehicle {v_no} registered!")
                    st.rerun()

        # Vehicle Edit/Delete Section (මෙතන හිස්තැන් පේළියට තියෙන්න ඕනේ)
        if not st.session_state.ve_db.empty:
            st.divider()
            ve_to_manage = st.selectbox("Select Vehicle to Manage", st.session_state.ve_db["No"].tolist())
            curr_ve = st.session_state.ve_db[st.session_state.ve_db["No"] == ve_to_manage].iloc[0]
            with st.expander(f"Edit {ve_to_manage}"):
                # ... (edit code) ...
                if st.button("Delete Vehicle ❌"):
                    st.session_state.ve_db = st.session_state.ve_db[st.session_state.ve_db["No"] != ve_to_manage]
                    save_all(); st.rerun()

    with setup_tab2:
        st.subheader("Add New Driver / Operator")
        with st.form("d_setup_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                d_name = st.text_input("Driver Name")
            with col2:
                d_salary = st.number_input("Daily Salary", min_value=0.0)
            d_phone = st.text_input("Contact Number")
            
            if st.form_submit_button("✅ Register Driver"):
                if d_name:
                    new_d = pd.DataFrame([[d_name, d_phone, d_salary]], columns=["Name", "Phone", "Daily_Salary"])
                    st.session_state.dr_db = pd.concat([st.session_state.dr_db, new_d], ignore_index=True)
                    save_all(); st.success("Driver registered!"); st.rerun()

        # Driver Edit/Delete Section
        if not st.session_state.dr_db.empty:
            st.divider()
            dr_to_manage = st.selectbox("Select Driver to Manage", st.session_state.dr_db["Name"].tolist())
            with st.expander(f"Edit {dr_to_manage}"):
                # ... (edit code) ...
                if st.button("Delete Driver ❌"):
                    st.session_state.dr_db = st.session_state.dr_db[st.session_state.dr_db["Name"] != dr_to_manage]
                    save_all(); st.rerun()
                    
# --- මේක වෙනම Menu එකක් විදිහට පල්ලෙහායින් දාන්න ---
elif menu == "👤 Manage Landowners":
    st.markdown("<h2 style='color: #2ECC71;'>👤 Landowner Management</h2>", unsafe_allow_html=True)
    
    # 1. අලුත් Landowner කෙනෙක් ඇතුළත් කරන Form එක
    with st.form("landowner_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            owner_name = st.text_input("Landowner Name")
            contact_no = st.text_input("Contact Number")
        with col2:
            land_name = st.text_input("Land Name / Location")
            agreement_rate = st.number_input("Agreed Rate per Cube (LKR)", min_value=0.0, step=100.0)
            
        if st.form_submit_button("➕ Register Landowner"):
            if owner_name and land_name:
                new_owner = {
                    "Name": owner_name,
                    "Land": land_name,
                    "Contact": contact_no,
                    "Rate": agreement_rate
                }
                st.session_state.landowners.append(new_owner)
                save_all() # දත්ත සේව් කරන්න
                st.success(f"Owner {owner_name} registered successfully!")
                st.rerun()
            else:
                st.error("Please fill Name and Land details!")

    # 2. දැනට ඉන්න අයව Table එකක් විදිහට පෙන්වීම
    st.divider()
    st.subheader("Registered Landowners")
    if st.session_state.landowners:
        owner_df = pd.DataFrame(st.session_state.landowners)
        st.dataframe(owner_df, use_container_width=True)
    else:
        st.info("No landowners registered yet.")


# --- 11. DATA MANAGER (EDIT / DELETE) ---
elif menu == "⚙️ Data Manager":
    st.markdown(f"<h2 style='color: #E67E22;'>⚙️ Data Manager</h2>", unsafe_allow_html=True)
    st.info("මෙහිදී ඔබට වැරදිලාවත් ඇතුළත් කළ දත්ත Edit කිරීමට හෝ Delete කිරීමට හැකියාව ඇත.")
    
    if st.session_state.df.empty:
        st.warning("No data found in the system.")
    else:
        # ID එකෙන් Record එක සොයා ගැනීම
        search_id = st.number_input("Enter Record ID to Edit/Delete", min_value=1, step=1)
        
        # DataFrame එකේ index එක හරියටම අල්ලගන්නවා
        record_idx = st.session_state.df.index[st.session_state.df["ID"] == search_id].tolist()
        
        if record_idx:
            idx = record_idx[0]
            record = st.session_state.df.loc[idx]
            
            st.write("Current Data for ID:", search_id)
            st.dataframe(pd.DataFrame([record])) # තෝරාගත් row එක විතරක් පෙන්වයි
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("📝 Edit Record")
                with st.form("edit_record_form"):
                    u_date = st.date_input("Date", value=record["Date"])
                    u_entity = st.text_input("Vehicle / Entity", value=record["Entity"])
                    u_note = st.text_input("Note", value=record["Note"])
                    u_amount = st.number_input("Amount", value=float(record["Amount"]))
                    u_qty = st.number_input("Qty (Cubes)", value=float(record["Qty_Cubes"]))
                    u_hours = st.number_input("Hours", value=float(record["Hours"]))
                    u_rate = st.number_input("Rate", value=float(record["Rate_At_Time"]))
                    
                    if st.form_submit_button("✅ Update Now"):
                        st.session_state.df.at[idx, "Date"] = u_date
                        st.session_state.df.at[idx, "Entity"] = u_entity
                        st.session_state.df.at[idx, "Note"] = u_note
                        st.session_state.df.at[idx, "Amount"] = u_amount
                        st.session_state.df.at[idx, "Qty_Cubes"] = u_qty
                        st.session_state.df.at[idx, "Hours"] = u_hours
                        st.session_state.df.at[idx, "Rate_At_Time"] = u_rate
                        
                        save_all() # CSV එකට save කරනවා
                        st.success("Record updated successfully!")
                        st.rerun()

            with col2:
                st.subheader("🗑️ Delete Record")
                st.error("ප්‍රවේසමෙන්! මෙය මැකූ පසු නැවත ලබාගත නොහැක.")
                if st.button("🔥 Confirm Permanent Delete"):
                    st.session_state.df = st.session_state.df.drop(idx).reset_index(drop=True)
                    save_all()
                    st.success("Record deleted!")
                    st.rerun()
        else:
            st.warning("Could not find a record with that ID. Please check the ID in the table below.")

        # පහළින් සම්පූර්ණ දත්ත වගුව පෙන්වනවා ID එක ලේසියෙන් බලාගන්න
        st.divider()
        st.write("All Transactions (Use ID from here):")
        # අලුත්ම දත්ත උඩට එන විදියට පෙන්වනවා
        st.dataframe(st.session_state.df.sort_values(by="ID", ascending=False), use_container_width=True)
