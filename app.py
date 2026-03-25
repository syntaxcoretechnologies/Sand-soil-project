import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
from fpdf import FPDF

# --- 1. CONFIG & FILENAMES ---
DATA_FILE = "ksd_master_v56.csv"
VE_FILE = "ksd_vehicles_v56.csv"
LO_FILE = "ksd_landowners_v56.csv" 
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

def save_data(file_path, df):
    try:
        df.to_csv(file_path, index=False)
    except Exception as e:
        st.error(f"Error saving data: {e}")

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
if 'landowners' not in st.session_state:
    st.session_state.landowners = pd.read_csv(LO_FILE).to_dict('records') if os.path.exists(LO_FILE) else []

# --- 4. PDF ENGINE (ඔයා එවපු PDF එකේ format එකටම) ---
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15); self.set_text_color(230, 126, 34) 
        self.cell(0, 10, SHOP_NAME, 0, 1, 'C'); self.ln(5)

def create_pdf(report_name, df, summary_dict):
    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        
        # Report Title
        pdf.cell(200, 10, txt=str(report_name).replace("_", " "), ln=True, align='C')
        pdf.ln(5)
        
        # Summary Section (ගණන් හිලව් පෙන්වන කොටස)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(200, 10, txt="Summary Report:", ln=True)
        pdf.set_font("Arial", size=10)
        
        for key, value in summary_dict.items():
            pdf.cell(200, 8, txt=f"{key}: {value}", ln=True)
        
        pdf.ln(10)
        
        # Table Headers (ටේබල් එකේ මාතෘකා)
        cols = df.columns.tolist()
        pdf.set_font("Arial", 'B', 8)
        
        # Column පළල තීරණය කිරීම
        col_width = 190 / len(cols) if len(cols) > 0 else 30
        
        for col in cols:
            pdf.cell(col_width, 10, str(col), 1)
        pdf.ln()
        
        # Table Data (දත්ත පේළි)
        pdf.set_font("Arial", size=8)
        for _, row in df.iterrows():
            for col in cols:
                # ඕනෑම දත්තයක් String එකක් බවට හරවා පෙන්වීම (KeyError වැළැක්වීමට)
                val = str(row.get(col, ""))
                pdf.cell(col_width, 8, val, 1)
            pdf.ln()
            
        # File එක සේව් කිරීම
        file_path = f"{report_name}.pdf"
        pdf.output(file_path)
        return file_path
        
    except Exception as e:
        print(f"PDF Error: {e}")
        return None
    
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
        
        amt = float(row.get('Amount', 0)) if r_type == "Expense" else 0.0
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
elif menu == "🏗️ Site Operations":
    st.markdown(f"<h2 style='color: #E67E22;'>🏗️ Site Operations & Stock Manager</h2>", unsafe_allow_html=True)
    
    op = st.radio("Select Activity Type", ["🚜 Excavator Work Log", "💰 Sales Out", "📥 Stock Inward (To Plant)"], horizontal=True)
    v_list = st.session_state.ve_db["No"].tolist() if not st.session_state.ve_db.empty else ["N/A"]
    
    # පද්ධතියේ දැනට ඉන්න Drivers සහ Landowners ලිස්ට් එක ගන්නවා
    d_list = st.session_state.dr_db["Name"].tolist() if not st.session_state.dr_db.empty else ["No Drivers Registered"]
    l_list = [l["Name"] for l in st.session_state.landowners] if st.session_state.landowners else ["No Owners Registered"]

    with st.form("site_f", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            v = st.selectbox("Select Vehicle / Machine", v_list if op != "📥 Stock Inward (To Plant)" else ["Internal / Third Party"])
            d = st.date_input("Date", datetime.now().date())
            material = st.selectbox("Material Type", ["Sand", "Soil", "Other"]) if (op == "💰 Sales Out" or op == "📥 Stock Inward (To Plant)") else ""
            
            # Stock Inward එකකදී පමණක් Landowner සහ Driver තෝරන්න දෙනවා
            if op == "📥 Stock Inward (To Plant)":
                src_owner = st.selectbox("Source (Landowner)", l_list)
                src_driver = st.selectbox("Driver/Operator", d_list)
        
        with col2:
            if "Excavator" in op:
                val_label = "Work Hours"
                unit = "Hrs"
            else:
                val_label = "Qty (Cubes)"
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
                
                # Amount එක Calculate කිරීම
                calculated_amount = val * r
                q, h = (0, val) if "Excavator" in op else (val, 0)
                
                # Note එකට Landowner සහ Driver ගේ විස්තර එකතු කිරීම (රිපෝට් වලදී ලේසි වෙන්න)
                final_note = n
                if op == "📥 Stock Inward (To Plant)":
                    final_note = f"{n} | Owner: {src_owner} | Drv: {src_driver}"
                
                new_row = pd.DataFrame([[
                    len(st.session_state.df)+1, d, "", record_type, cat, v, final_note, calculated_amount, q, 0, h, r, "Done"
                ]], columns=st.session_state.df.columns)
                
                st.session_state.df = pd.concat([st.session_state.df, new_row], ignore_index=True)
                save_all()
                st.success(f"Successfully recorded! Total: Rs.{calculated_amount:,.2f}")
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
elif menu == "📑 Reports Center":
    st.markdown("<h2 style='color: #8E44AD;'>📑 Business Reports Center</h2>", unsafe_allow_html=True)
    
    df_raw = st.session_state.df.copy()
    df_raw['Date'] = pd.to_datetime(df_raw['Date']).dt.date

    # 1. ටැබ් ටික හදනවා
   # මෙන්න මේ පේළිය විතරක් replace කරන්න:
    # --- Tabs Definition (මෙන්න මේ කොටස replace කරන්න) ---
    tabs_list = [
        "💰 Daily Income", 
        "📊 Profit & Loss", 
        "📈 Material Gross", 
        "🚜 Vehicle Settlement", 
        "👷 Driver Summary", 
        "🏡 Landowner Report", 
        "📑 Daily Log",
        "⛽ Shed Report"
    ]
    
    r_inc, r_prof, r_gross, r1, r2, r_land, r3, r4 = st.tabs(tabs_list)
    
    # 2. Date Filter එක
    col_d1, col_d2 = st.columns(2)
    with col_d1: f_d = st.date_input("From Date", datetime.now().date() - timedelta(days=30), key="r_from")
    with col_d2: t_d = st.date_input("To Date", datetime.now().date(), key="r_to")

    df_f = df_raw[(df_raw["Date"] >= f_d) & (df_raw["Date"] <= t_d)].copy()

    with r_land:
        st.subheader("🏡 Landowner Ledger & Settlement Report")
        l_names = [l["Name"] for l in st.session_state.landowners] if st.session_state.landowners else []
        
        if not l_names:
            st.warning("No Landowners registered yet.")
        else:
            sel_lan = st.selectbox("Select Landowner", l_names, key="lan_sel_box")
            if sel_lan:
                # 1. 'Record_Type' column එක නැත්නම් ඒක හදාගන්නවා (KeyError එක වැළැක්වීමට)
                if "Record_Type" not in df_f.columns:
                    df_f["Record_Type"] = "Unknown"
                
                # 2. Billing (කපපු පස් ප්‍රමාණය) - Note එකේ නම තියෙන ඒවා පෙරමු
                lan_stock = df_f[(df_f["Note"].fillna("").str.contains(f"Owner: {sel_lan}", case=False))].copy()
                
                # 3. Payments (ගෙවපු සල්ලි) - Entity එකේ නම තියෙන ඒවා
                lan_pays = df_f[(df_f["Entity"].fillna("").str.contains(sel_lan, case=False)) & 
                                (df_f["Category"].str.contains("Payment|Settlement", na=False, case=False))].copy()
                
                # 4. ගණනය කිරීම් (Column එක තියෙනවාද කියලා බලලා)
                q_col = 'Qty_Cubes' if 'Qty_Cubes' in lan_stock.columns else 'Qty'
                t_cubes = lan_stock[q_col].sum() if q_col in lan_stock.columns else 0
                t_bill = lan_stock['Amount'].sum() if 'Amount' in lan_stock.columns else 0
                t_paid = lan_pays['Amount'].sum() if 'Amount' in lan_pays.columns else 0
                bal = t_bill - t_paid
                
                # Metrics
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Total Cubes", f"{t_cubes:.2f}")
                c2.metric("Total Bill", f"{t_bill:,.2f}")
                c3.metric("Paid", f"{t_paid:,.2f}")
                c4.metric("Balance Due", f"{bal:,.2f}", delta_color="inverse")
                
                st.divider()
                col_l, col_r = st.columns(2)
                with col_l:
                    st.write("🚜 Stock Records")
                    # පෙන්විය යුතු columns තියෙනවාද බලමු
                    s_cols = ['Date', q_col, 'Rate_At_Time', 'Amount']
                    disp_s = [c for c in s_cols if c in lan_stock.columns]
                    st.dataframe(lan_stock[disp_s], use_container_width=True)
                with col_r:
                    st.write("💰 Payment Records")
                    p_cols = ['Date', 'Amount', 'Note']
                    disp_p = [c for c in p_cols if c in lan_pays.columns]
                    st.dataframe(lan_pays[disp_p], use_container_width=True)
    
    # --- TAB: DAILY INCOME REPORT (FIXED) ---
    with r_inc:
        st.subheader("Daily Sales & Income Statement")
        
        # 1. Column names වල තියෙන හිස්තැන් අයින් කරලා Clean කරමු
        df_f.columns = [c.strip() for c in df_f.columns]
        
        # 2. Sales Out records විතරක් පෙරමු
        daily_sales = df_f[df_f["Category"].str.contains("Sales Out", na=False)].copy()
        
        if not daily_sales.empty:
            # 3. මෙතනදී Column එකක් නැති වුණොත් Error එකක් එන එක නවත්වන්න check එකක් දාමු
            available_cols = daily_sales.columns.tolist()
            required_cols = ['Date', 'Category', 'Entity', 'Qty_Cubes', 'Rate_At_Time', 'Amount']
            
            # පද්ධතියේ තියෙන column ටික විතරක් තෝරා ගමු (KeyError වැළැක්වීමට)
            final_cols = [c for c in required_cols if c in available_cols]
            
            display_sales = daily_sales[final_cols].copy()
            
            # 4. ටේබල් එකේ Column names ලස්සන කරමු (Rename)
            rename_dict = {
                'Date': 'Date', 'Category': 'Material', 'Entity': 'Vehicle/Client', 
                'Qty_Cubes': 'Qty', 'Rate_At_Time': 'Rate', 'Amount': 'Total Amount'
            }
            display_sales.rename(columns=rename_dict, inplace=True)
            
            st.dataframe(display_sales, use_container_width=True)
            
            # මුළු මුදල පෙන්වීම
            if 'Total Amount' in display_sales.columns:
                total_daily_inc = display_sales['Total Amount'].sum()
                st.success(f"Selected Period Total Income: **LKR {total_daily_inc:,.2f}**")
            
            # PDF Button එක (කලින් විදිහටම)
            if st.button("📥 Download Daily Income PDF"):
                inc_summary = {
                    "Report Type": "Daily Income Statement",
                    "Period": f"{f_d} to {t_d}",
                    "Total Items": len(display_sales),
                    "Total Gross Income": f"LKR {display_sales['Total Amount'].sum():,.2f}" if 'Total Amount' in display_sales.columns else "0.00"
                }
                pdf_fn = create_pdf(f"Daily_Income", display_sales, inc_summary)
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

   # --- TAB: VEHICLE SETTLEMENT (STABLE VERSION) ---
    
    with r1:
        st.subheader("🚜 Vehicle & Machine Settlement")
        
        # වාහන ලැයිස්තුව ලබා ගැනීම
        v_list = st.session_state.ve_db["No"].tolist() if not st.session_state.ve_db.empty else ["N/A"]
        selected_ve = st.selectbox("Select Vehicle/Machine", v_list, key="v_settle_select_final")
        
        if selected_ve and selected_ve != "N/A":
            # 1. දත්ත පෙරමු (අදාළ වාහනයට පමණක්)
            ve_records = df_f[df_f['Entity'] == selected_ve].copy()
            
            if not ve_records.empty:
                # 'Record_Type' සහ 'Work_Hours' නැතිනම් හදාගන්නවා
                if "Record_Type" not in ve_records.columns: ve_records["Record_Type"] = "Unknown"
                if "Work_Hours" not in ve_records.columns: ve_records["Work_Hours"] = 0
                
                # 2. වර්ගය හඳුනා ගැනීම
                is_exc = any(x in str(selected_ve).upper() for x in ["EX", "PC", "EXCAVATOR"])
                
                # 3. පොදු වියදම් (Fuel, Advance, Repair)
                exp_mask = (ve_records["Record_Type"] == "Expense") | \
                           (ve_records["Category"].str.contains("Fuel|Repair|Food|Advance", na=False, case=False))
                total_exp = pd.to_numeric(ve_records[exp_mask]["Amount"], errors='coerce').sum()

                # --- UI DISPLAY (වර්ගය අනුව වෙනස් වේ) ---
                st.info(f"📍 Viewing Report for: **{selected_ve}** ({'Excavator' if is_exc else 'Lorry'})")
                
                c1, c2, c3 = st.columns(3)

                if is_exc:
                    # --- EXCAVATOR UI ---
                    # පැය ගණන සහ රේට් එක numeric කරගමු
                    ve_records['Work_Hours'] = pd.to_numeric(ve_records['Work_Hours'], errors='coerce').fillna(0)
                    ve_records['Rate_At_Time'] = pd.to_numeric(ve_records.get('Rate_At_Time', 0), errors='coerce').fillna(0)
                    
                    total_hrs = ve_records['Work_Hours'].sum()
                    gross_earning = (ve_records['Work_Hours'] * ve_records['Rate_At_Time']).sum()
                    net_profit = gross_earning - total_exp

                    c1.metric("Total Work Hours", f"{total_hrs:.2f} hrs")
                    c2.metric("Gross Earning", f"Rs. {gross_earning:,.2f}")
                    c3.metric("Net Profit", f"Rs. {net_profit:,.2f}", delta=f"{net_profit:,.2f}")
                    
                    # Excavator එකට වැදගත් columns
                    display_cols = ['Date', 'Category', 'Work_Hours', 'Rate_At_Time', 'Amount', 'Note']
                else:
                    # --- LORRY UI ---
                    total_cubes = pd.to_numeric(ve_records.get('Qty_Cubes', 0), errors='coerce').sum()
                    
                    c1.metric("Total Cubes", f"{total_cubes:.2f} m3")
                    c2.metric("Total Expenses", f"Rs. {total_exp:,.2f}")
                    c3.write("ℹ️ Rented Lorry. No hourly earnings tracked.")
                    
                    # Lorry එකට වැදගත් columns
                    display_cols = ['Date', 'Category', 'Qty_Cubes', 'Amount', 'Note']

                st.divider()

                # --- PDF GENERATION ---
                if st.button("📥 Download Settlement PDF", key="btn_pdf_v_final"):
                    summary = {
                        "Vehicle": selected_ve,
                        "Period": f"{f_d} to {t_d}",
                        "Total Expenses": f"Rs. {total_exp:,.2f}"
                    }
                    if is_exc:
                        summary["Total Hours"] = f"{total_hrs:.2f}"
                        summary["Net Profit"] = f"Rs. {net_profit:,.2f}"
                    else:
                        summary["Total Cubes"] = f"{total_cubes:.2f}"

                    available_pdf = [c for c in display_cols if c in ve_records.columns]
                    pdf_path = create_pdf(f"Settlement_{selected_ve}", ve_records[available_pdf], summary)
                    if pdf_path and os.path.exists(pdf_path):
                        with open(pdf_path, "rb") as f:
                            st.download_button("📩 Save PDF", f, file_name=f"{selected_ve}_Report.pdf")

                # --- TABLE DISPLAY ---
                st.write(f"📋 **Detailed Transaction Log**")
                final_cols = [c for c in display_cols if c in ve_records.columns]
                st.dataframe(ve_records[final_cols], use_container_width=True)
            else:
                st.warning(f"No records found for {selected_ve} in the selected period.")
    # --- TAB 2: DRIVER SUMMARY (FIXED) ---
    with r2:
        st.subheader("👷 Driver Work & Payment Summary")
        dr_list = st.session_state.dr_db["Name"].tolist() if not st.session_state.dr_db.empty else []
        sel_dr = st.selectbox("Select Driver", ["All"] + dr_list, key="dr_sel_box")
        
        if sel_dr:
            # 1. Driver ව filter කරමු
            if sel_dr != "All":
                dr_rep = df_f[df_f["Note"].fillna("").astype(str).str.contains(sel_dr, case=False)].copy()
            else:
                dr_rep = df_f[df_f["Category"].str.contains("Salary|Advance", na=False)].copy()
            
            # 2. මුළු ගෙවීම් ගණනය කරමු
            total_paid = pd.to_numeric(dr_rep['Amount'], errors='coerce').sum()
            st.metric(f"Total for {sel_dr}", f"Rs. {total_paid:,.2f}")
            
            # 3. පෙන්විය යුතු Columns ටික (තියෙන ඒවා විතරක් තෝරා ගනී)
            req_cols = ['Date', 'Category', 'Entity', 'Vehicle', 'Note', 'Amount']
            available_cols = [c for c in req_cols if c in dr_rep.columns]
            
            # 4. Table එක පෙන්වමු (KeyError එකක් එන්නේ නැත)
            st.dataframe(dr_rep[available_cols], use_container_width=True)
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
        st.title("⚙️ System Setup & Configuration")
        st.write("Welcome to Setup! Register your resources below.") # මේක පේනවාද බලන්න මචං

        # 1. Initialize Session States (Error නොවෙන්න මුලින්ම මේවා ඕනේ)
        if "drivers" not in st.session_state:
            st.session_state.drivers = []
        if "landowners" not in st.session_state:
            st.session_state.landowners = []

        # 2. Tabs නිර්මාණය කිරීම
        t_veh, t_dri, t_lan = st.tabs(["🚜 Vehicles", "👷 Drivers", "🏡 Landowners"])

        # --- TAB: VEHICLES ---
        with t_veh:
            st.subheader("Register Vehicle")
            with st.form("v_form", clear_on_submit=True):
                v_no = st.text_input("Vehicle Number")
                v_type = st.selectbox("Type", ["Lorry", "Excavator", "JCB", "Other"])
                if st.form_submit_button("Add Vehicle"):
                    if v_no:
                        new_v = pd.DataFrame([{"No": v_no, "Type": v_type}])
                        st.session_state.ve_db = pd.concat([st.session_state.ve_db, new_v], ignore_index=True)
                        save_data(VE_FILE, st.session_state.ve_db)
                        st.success(f"Added {v_no}")
                        st.rerun()

        # --- TAB: DRIVERS ---
        with t_dri:
            st.subheader("Register Driver")
            with st.form("d_form", clear_on_submit=True):
                d_name = st.text_input("Driver Name")
                d_phone = st.text_input("Phone Number")
                if st.form_submit_button("Add Driver"):
                    if d_name:
                        st.session_state.drivers.append({"Name": d_name, "Phone": d_phone})
                        st.success(f"Added Driver {d_name}")
                        st.rerun()

        # --- TAB: LANDOWNERS ---
        with t_lan:
            st.subheader("Register Landowner")
            with st.form("l_form", clear_on_submit=True):
                l_name = st.text_input("Owner Name")
                l_loc = st.text_input("Location")
                if st.form_submit_button("Add Owner"):
                    if l_name:
                        st.session_state.landowners.append({"Name": l_name, "Location": l_loc})
                        st.success(f"Added Owner {l_name}")
                        st.rerun()

        st.divider()
        st.info("Currently registered data can be viewed in the Reports Center.")

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
