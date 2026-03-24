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
    
    def safe_text(text):
        if text is None: return ""
        return str(text).encode("latin-1", "ignore").decode("latin-1")

    pdf.set_font("Arial", 'B', 12)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 10, safe_text(f"STATEMENT: {title.upper()}"), 1, 1, 'L', fill=True)
    pdf.ln(2)
    
    # --- Summary Section (Basic Info) ---
    pdf.set_font("Arial", 'B', 10)
    for k, v in summary_dict.items():
        if k not in ["Rate_Breakdown"]: # Rate breakdown එක summary එකේ යටින් දාමු
            clean_v = str(v).replace("Rs.", "LKR")
            pdf.cell(50, 8, safe_text(k) + ":", 1)
            pdf.set_font("Arial", '', 10)
            pdf.cell(0, 8, " " + safe_text(clean_v), 1, 1)
            pdf.set_font("Arial", 'B', 10)
    
    # --- අලුත් කොටස: Rate-wise Breakdown ---
    if "Rate_Breakdown" in summary_dict:
        pdf.ln(5)
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(0, 8, "Earnings Breakdown (By Rate):", 0, 1)
        pdf.set_font("Arial", 'B', 9)
        pdf.cell(40, 8, "Rate (LKR)", 1, 0, 'C', fill=True)
        pdf.cell(40, 8, "Qty/Hrs", 1, 0, 'C', fill=True)
        pdf.cell(50, 8, "Sub-Total (LKR)", 1, 1, 'C', fill=True)
        pdf.set_font("Arial", '', 9)
        for rb in summary_dict["Rate_Breakdown"]:
            pdf.cell(40, 7, f"{rb['rate']:,.2f}", 1, 0, 'R')
            pdf.cell(40, 7, f"{rb['qty']}", 1, 0, 'C')
            pdf.cell(50, 7, f"{rb['subtotal']:,.2f}", 1, 1, 'R')

    pdf.ln(8)
    
    # --- Main Transaction Table ---
    pdf.set_font("Arial", 'B', 9)
    headers = ["Date", "Category", "Note", "Rate", "Amount"] # Rate එකත් table එකට දැම්මා
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
        
        # Rate එක පෙන්වනවා (වැඩක් නම් පමණක්)
        rate_val = f"{row['Rate_At_Time']:,.2f}" if row['Rate_At_Time'] > 0 else "-"
        pdf.cell(w[3], 7, safe_text(rate_val), 1, 0, 'R')
        
        amt = float(row['Amount']) if row['Type'] == "Expense" else 0.0
        total_exp += amt
        pdf.cell(w[4], 7, f"{amt:,.2f}", 1, 0, 'R')
        pdf.ln()
    
    # Grand Total
    pdf.set_font("Arial", 'B', 9)
    pdf.cell(sum(w[:4]), 10, "GRAND TOTAL (EXPENSES) LKR", 1, 0, 'R')
    pdf.cell(w[4], 10, f"{total_exp:,.2f}", 1, 1, 'R')
    
    fn = f"Settlement_{datetime.now().strftime('%H%M%S')}.pdf"
    pdf.output(fn)
    return fn

# --- 5. UI LAYOUT & DASHBOARD ---
st.set_page_config(page_title=SHOP_NAME, layout="wide")
st.sidebar.title("🏗️ KSD ERP v5.6")

# මේ පේළිය පිටුවේ වම් කෙළවරේ සිටම පටන් ගන්න (No spaces)
menu = st.sidebar.selectbox("MAIN MENU", ["📊 Dashboard", "🏗️ Site Operations", "💰 Finance & Shed", "⚙️ System Setup", "📑 Reports Center", "⚙️ Data Manager"])

# --- 1. DASHBOARD SECTION ---
# --- 1. DASHBOARD SECTION (UPDATED) ---
if menu == "📊 Dashboard":
    st.markdown("<h2 style='color: #2E86C1;'>📊 Business Overview</h2>", unsafe_allow_html=True)
    df = st.session_state.df.copy()
    
    if not df.empty:
        # --- DATE FILTER ---
        st.subheader("📅 Filter by Date")
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            start_date = st.date_input("From Date", datetime.now().date() - timedelta(days=7))
        with col_f2:
            end_date = st.date_input("To Date", datetime.now().date())
        
        df['Date'] = pd.to_datetime(df['Date']).dt.date
        mask = (df['Date'] >= start_date) & (df['Date'] <= end_date)
        filtered_df = df.loc[mask].copy()

        if not filtered_df.empty:
            # --- 1. ඇත්තම ආදායම (Sales Only) ---
            # සල්ලි අතට ලැබෙන්නේ විකුණපුවාම විතරයි
            sales_df = filtered_df[filtered_df["Category"].str.contains("Sales Out", na=False)].copy()
            sales_df['Income'] = pd.to_numeric(sales_df['Qty_Cubes'], errors='coerce').fillna(0) * \
                                 pd.to_numeric(sales_df['Rate_At_Time'], errors='coerce').fillna(0)
            real_income = sales_df['Income'].sum()

            # --- 2. අභ්‍යන්තර වැඩ (Internal Work Log - Not Earning) ---
            # ලොරි සහ බැකෝ වැඩ කළ වටිනාකම (මේක Income එකට එකතු කරන්නේ නැහැ)
            work_df = filtered_df[filtered_df["Category"].str.contains("Work Log", na=False)].copy()
            work_val = (pd.to_numeric(work_df['Qty_Cubes'], errors='coerce').fillna(0) + 
                        pd.to_numeric(work_df['Hours'], errors='coerce').fillna(0)) * \
                        pd.to_numeric(work_df['Rate_At_Time'], errors='coerce').fillna(0)
            total_work_done = work_val.sum()

            # --- 3. වියදම් (Expenses) ---
            total_expenses = pd.to_numeric(filtered_df[filtered_df["Type"] == "Expense"]["Amount"], errors='coerce').sum()

            # --- 4. METRICS පෙන්වීම ---
            m1, m2, m3, m4 = st.columns(4)
            # පළවෙනි 3 සල්ලි ගැන
            m1.metric("Net Sales Income", f"Rs. {real_income:,.2f}")
            m2.metric("Total Expenses", f"Rs. {total_expenses:,.2f}")
            m3.metric("Net Cashflow", f"Rs. {real_income - total_expenses:,.2f}")
            # 4 වෙනි එක ප්ලාන්ට් එකේ වැඩ නිම කළ වටිනාකම (Earning නොවේ)
            m4.metric("Internal Work Value", f"Rs. {total_work_done:,.2f}")

            st.warning("⚠️ 'Internal Work Value' යනු ලොරි/බැකෝ ප්ලාන්ට් එක ඇතුළේ කළ වැඩ වල වටිනාකමයි. මෙය ඔබගේ අතට ලැබෙන සැබෑ මුදල (Cashflow) ලෙස ගණන් නොගැනේ.")
            
            st.divider()
            

            # --- 5. STOCK BALANCE (PLANT) ---
            st.subheader("📦 Plant Stock Balance (Current)")
            s_col1, s_col2 = st.columns(2)
            sand_in = df[df["Category"].str.contains("Stock Inward \(Sand\)", na=False)]["Qty_Cubes"].sum()
            sand_out = df[df["Category"].str.contains("Sales Out \(Sand\)", na=False)]["Qty_Cubes"].sum()
            soil_in = df[df["Category"].str.contains("Stock Inward \(Soil\)", na=False)]["Qty_Cubes"].sum()
            soil_out = df[df["Category"].str.contains("Sales Out \(Soil\)", na=False)]["Qty_Cubes"].sum()

            s_col1.metric("Sand Remaining", f"{sand_in - sand_out:.2f} Cubes")
            s_col2.metric("Soil Remaining", f"{soil_in - soil_out:.2f} Cubes")

            st.divider()
            st.subheader("Daily Income Trend (Sales Only)")
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
    
    # මෙතන Activity Type එක තෝරනවා
    op = st.radio("Select Activity Type", ["🚛 Lorry Work Log", "🚜 Excavator Work Log", "💰 Sales Out", "📥 Stock Inward (To Plant)"], horizontal=True)
    
    v_list = st.session_state.ve_db["No"].tolist() if not st.session_state.ve_db.empty else ["N/A"]
    
    with st.form("site_f", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            # Stock inward එකට වාහනයක් ඕනෙම නැති නිසා 'Internal' කියලා එනවා
            v = st.selectbox("Select Vehicle / Machine", v_list if op != "📥 Stock Inward (To Plant)" else ["Internal / Third Party"])
            d = st.date_input("Date", datetime.now().date())
            # Material එක ඕන වෙන්නේ Sales සහ Stock Inward වලට විතරයි
            material = st.selectbox("Material Type", ["Sand", "Soil", "Other"]) if (op == "💰 Sales Out" or op == "📥 Stock Inward (To Plant)") else ""
        
        with col2:
            # --- මෙන්න මෙතනදී තමයි Excavator ද ලොරි ද කියලා අඳුරගන්නේ ---
            if "Excavator" in op:
                val_label = "Work Hours (පැය ගණන)"
                unit = "Hrs"
            else:
                val_label = "Qty (Cubes - කියුබ් ගණන)"
                unit = "Cubes"
                
            val = st.number_input(val_label, min_value=0.0, step=0.5, value=0.0)
            r = st.number_input(f"Enter Rate per {unit} (LKR)", min_value=0.0, step=100.0, value=0.0)
            
        n = st.text_input("Additional Note")
        
        if st.form_submit_button("📥 Save Record"):
            if val <= 0: 
                st.error(f"Enter valid {val_label}!")
            elif r <= 0:
                st.error("Enter valid Rate!")
            else:
                record_type = "Inward" if op == "📥 Stock Inward (To Plant)" else "Process"
                cat = f"{op} ({material})" if material else op
                
                # Excavator නම් Hours වලටත්, අනෙක්වා Qty_Cubes වලටත් දත්ත වෙන් කරනවා
                q, h = (0, val) if "Excavator" in op else (val, 0)
                
                new_row = pd.DataFrame([[
                    len(st.session_state.df)+1, d, "", record_type, cat, v, n, 0, q, 0, h, r, "Done"
                ]], columns=st.session_state.df.columns)
                
                st.session_state.df = pd.concat([st.session_state.df, new_row], ignore_index=True)
                save_all()
                st.success(f"Successfully recorded {op}!")
                st.rerun()
    
    
    st.divider()
    st.subheader("Today's Logs")
    today_df = st.session_state.df[st.session_state.df["Date"] == datetime.now().date()]
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
                    new = pd.DataFrame([[len(st.session_state.df)+1, d, "", "Expense", "Fuel Entry", v, "Shed bill", c, 0, l, 0, 0, "Pending"]], columns=st.session_state.df.columns)
                    st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()
        with f2:
            with st.form("shed_pay", clear_on_submit=True):
                am, ref = st.number_input("Amount Paid"), st.text_input("Reference")
                if st.form_submit_button("Record Payment"):
                    new = pd.DataFrame([[len(st.session_state.df)+1, datetime.now().date(), "", "Expense", "Shed Payment", "Shed", ref, am, 0, 0, 0, 0, "Paid"]], columns=st.session_state.df.columns)
                    st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()

    elif fin == "🔧 Repairs":
        with st.form("rep", clear_on_submit=True):
            d, v, am, nt = st.date_input("Date"), st.selectbox("Vehicle", v_list), st.number_input("Cost"), st.text_input("Detail")
            if st.form_submit_button("Save Repair"):
                new = pd.DataFrame([[len(st.session_state.df)+1, d, "", "Expense", "Repair", v, nt, am, 0, 0, 0, 0, "Paid"]], columns=st.session_state.df.columns)
                st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()

    elif fin == "💸 Payroll":
        with st.form("pay", clear_on_submit=True):
            dr = st.selectbox("Driver", st.session_state.dr_db["Name"].tolist() if not st.session_state.dr_db.empty else ["N/A"])
            am, ty, v_rel = st.number_input("Amount"), st.selectbox("Type", ["Driver Advance", "Salary"]), st.selectbox("Vehicle", v_list)
            if st.form_submit_button("Save Payroll"):
                new = pd.DataFrame([[len(st.session_state.df)+1, datetime.now().date(), "", "Expense", ty, v_rel, f"Driver: {dr}", am, 0, 0, 0, 0, "Paid"]], columns=st.session_state.df.columns)
                st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()

    elif fin == "🏦 Owner Advances":
        with st.form("own_adv", clear_on_submit=True):
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
        with st.form("dr", clear_on_submit=True):
            n, p, s = st.text_input("Name"), st.text_input("Phone"), st.number_input("Salary")
            if st.form_submit_button("Add Driver"):
                st.session_state.dr_db = pd.concat([st.session_state.dr_db, pd.DataFrame([[n,p,s]], columns=st.session_state.dr_db.columns)], ignore_index=True); save_all(); st.rerun()
        st.table(st.session_state.dr_db)
    with t2:
        with st.form("ve", clear_on_submit=True):
            v, t, r, o = st.text_input("No"), st.selectbox("Type", ["Lorry", "Excavator"]), st.number_input("Rate"), st.text_input("Owner")
            if st.form_submit_button("Add Vehicle"):
                st.session_state.ve_db = pd.concat([st.session_state.ve_db, pd.DataFrame([[v,t,o,r]], columns=st.session_state.ve_db.columns)], ignore_index=True); save_all(); st.rerun()
        st.table(st.session_state.ve_db)

# --- 10. REPORTS CENTER (UPDATED WITH DRIVER & SHED PDF) ---
# --- මෙන්න මේ පේළිය හොයාගන්න ---
elif menu == "📑 Reports Center":
    st.markdown("<h2 style='color: #8E44AD;'>📑 Comprehensive Reports & Settlement</h2>", unsafe_allow_html=True)
    
    df_raw = st.session_state.df.copy()
    df_raw.columns = [str(c).strip() for c in df_raw.columns]
    
    rename_map = {
        'Vehicle No': 'Vehicle', 'Vehicle_No': 'Vehicle', 'Lorry No': 'Vehicle', 'vehicle': 'Vehicle',
        'Cat': 'Category', 'category': 'Category', 'Entity': 'Vehicle' # සමහර තැන්වල Entity ලෙස තිබිය හැක
    }
    df_raw.rename(columns=rename_map, inplace=True)

    r1, r2, r3, r4 = st.tabs(["🚜 Vehicle Settlement", "👷 Driver Summary", "📑 Daily Log", "⛽ Shed Report"])
    
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        f_d = st.date_input("From Date", datetime.now().date() - timedelta(days=30))
    with col_d2:
        t_d = st.date_input("To Date", datetime.now().date())

    df_raw['Date'] = pd.to_datetime(df_raw['Date']).dt.date
    df_f = df_raw[(df_raw["Date"] >= f_d) & (df_raw["Date"] <= t_d)].copy()

    # ---------------------------------------------------------
    # TAB 1: VEHICLE SETTLEMENT
    # ---------------------------------------------------------
    with r1:
        v_list = st.session_state.ve_db["No"].tolist() if not st.session_state.ve_db.empty else df_f["Vehicle"].unique().tolist()
        sel_ve = st.selectbox("Select Vehicle/Machine", v_list, key="sel_ve_rep")
        
        if sel_ve:
            v_rep = df_f[df_f["Vehicle"] == sel_ve].copy()
            if not v_rep.empty:
                is_excavator = v_rep["Category"].str.contains("Excavator", na=False).any()
                
                v_rep['Income_Calc'] = (pd.to_numeric(v_rep['Qty_Cubes'], errors='coerce').fillna(0) + 
                                       pd.to_numeric(v_rep['Hours'], errors='coerce').fillna(0)) * \
                                       pd.to_numeric(v_rep['Rate_At_Time'], errors='coerce').fillna(0)
                
                gross = v_rep[v_rep["Type"] == "Process"]['Income_Calc'].sum()
                deduct = pd.to_numeric(v_rep[v_rep["Type"] == "Expense"]["Amount"], errors='coerce').sum()
                net = gross - deduct

                st.metric(f"Net Settlement for {sel_ve}", f"Rs. {net:,.2f}")

                # Summary Table for PDF
                rate_summary = v_rep[v_rep['Type'] == "Process"].groupby('Rate_At_Time').agg({
                    'Qty_Cubes': 'sum', 'Hours': 'sum', 'Income_Calc': 'sum'
                }).reset_index()
                rate_summary['Total_Units'] = rate_summary['Hours'] if is_excavator else rate_summary['Qty_Cubes']
                
                st.write("**Earnings Breakdown**")
                st.table(rate_summary[['Rate_At_Time', 'Total_Units', 'Income_Calc']])
                
                # --- PDF DOWNLOAD SECTION ---
                st.divider()
                # මෙන්න මෙතන තමයි PDF එක හදන්නේ
                summary_data = {
                    "Vehicle No": sel_ve,
                    "Gross Earnings": f"{gross:,.2f}",
                    "Total Expenses": f"{deduct:,.2f}",
                    "Net Settlement": f"{net:,.2f}"
                }
                
                # CSV එකක් විදිහට දැනට ගන්න පුළුවන් (PDF එකට create_pdf function එක අවශ්‍යයි)
                csv = v_rep.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label=f"📥 Download {sel_ve} Settlement (CSV)",
                    data=csv,
                    file_name=f"Settlement_{sel_ve}_{f_d}.csv",
                    mime='text/csv',
                )
                
                # PDF එක Generate කරන්න (create_pdf function එක තියෙනවා නම් විතරක් මේක වැඩ කරයි)
                try:
                    if st.button("📄 Generate PDF Settlement"):
                        fn = create_pdf(f"Settlement_{sel_ve}", v_rep, summary_data)
                        with open(fn, "rb") as f:
                            st.download_button("📩 Click to Download PDF", f, file_name=fn)
                except NameError:
                    st.info("💡 PDF Generator එක පද්ධතියට සම්බන්ධ වෙමින් පවතී. දැනට CSV වාර්තාව බාගත කරන්න.")
            else:
                st.warning("මෙම වාහනයට අදාළ දත්ත නැත.")

    # ---------------------------------------------------------
    # TAB 2: DRIVER SUMMARY
    # ---------------------------------------------------------
    with r2:
        dr_list = st.session_state.dr_db["Name"].tolist() if not st.session_state.dr_db.empty else []
        sel_dr = st.selectbox("Select Driver", dr_list)
        
        if sel_dr:
            dr_rep = df_f[df_f["Note"].fillna("").astype(str).str.contains(sel_dr, case=False)].copy()
            total_dr = pd.to_numeric(dr_rep['Amount'], errors='coerce').sum()
            
            st.metric(f"Total Paid to {sel_dr}", f"Rs. {total_dr:,.2f}")
            
            # Safe Display
            cols = ['Date', 'Category', 'Vehicle', 'Note', 'Amount']
            available = [c for c in cols if c in dr_rep.columns]
            st.dataframe(dr_rep[available], use_container_width=True)
            
            # Download Button for Driver
            csv_dr = dr_rep.to_csv(index=False).encode('utf-8')
            st.download_button(f"📥 Download {sel_dr} Log (CSV)", csv_dr, f"Driver_{sel_dr}.csv", "text/csv")

    # ---------------------------------------------------------
    # TAB 3 & 4 (DAILY LOG & SHED)
    # ---------------------------------------------------------
    with r3:
        st.dataframe(df_f, use_container_width=True)
    
    with r4:
        st.subheader("Shed Debt Analysis")
        f_total = pd.to_numeric(df_f[df_f["Category"] == "Fuel Entry"]["Amount"], errors='coerce').sum()
        p_total = pd.to_numeric(df_f[df_f["Category"] == "Shed Payment"]["Amount"], errors='coerce').sum()
        st.metric("Balance to Pay", f"Rs. {f_total - p_total:,.2f}")
        st.dataframe(df_f[df_f["Category"].str.contains("Fuel|Shed", na=False)], use_container_width=True)
        
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
