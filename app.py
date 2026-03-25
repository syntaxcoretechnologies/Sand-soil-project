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
    
    with st.form("site_f", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            v = st.selectbox("Select Vehicle / Machine", v_list if op != "📥 Stock Inward (To Plant)" else ["Internal / Third Party"])
            d = st.date_input("Date", datetime.now().date())
            material = st.selectbox("Material Type", ["Sand", "Soil", "Other"]) if (op == "💰 Sales Out" or op == "📥 Stock Inward (To Plant)") else ""
        
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
        
        # මෙන්න මේ පේළිය (228) දැන් හරියටම with st.form එකට යටින් තියෙනවා
        if st.form_submit_button("📥 Save Record"):
            if val <= 0: 
                st.error(f"Enter valid {val_label}!")
            elif r <= 0:
                st.error("Enter valid Rate!")
            else:
                record_type = "Inward" if op == "📥 Stock Inward (To Plant)" else "Process"
                cat = f"{op} ({material})" if material else op
                
                # Amount එක මෙතනදී Calculate වෙනවා
                calculated_amount = val * r
                q, h = (0, val) if "Excavator" in op else (val, 0)
                
                new_row = pd.DataFrame([[
                    len(st.session_state.df)+1, d, "", record_type, cat, v, n, calculated_amount, q, 0, h, r, "Done"
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
    setup_tab1, setup_tab2 = st.tabs(["🚜 Vehicle Management", "👷 Driver Management"])
    
    # --- VEHICLE MANAGEMENT ---
    with setup_tab1:
        st.subheader("Add New Vehicle or Machine")
        with st.form("v_setup_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                v_no = st.text_input("Vehicle Number (Ex: LM-1234)")
                v_owner = st.text_input("Owner Name")
            with col2:
                v_type = st.selectbox("Category", ["Lorry", "Excavator", "JCB", "Tractor", "Other"])
                v_rate = st.number_input("Standard Rate (Optional)", min_value=0.0)
            
            if st.form_submit_button("✅ Register Vehicle"):
                if v_no:
                    new_v = pd.DataFrame([[v_no, v_type, v_owner, v_rate]], 
                                         columns=["No", "Type", "Owner", "Rate_Per_Unit"])
                    st.session_state.ve_db = pd.concat([st.session_state.ve_db, new_v], ignore_index=True)
                    save_all()
                    st.success(f"Vehicle {v_no} registered!")
                    st.rerun()
                else:
                    st.error("Please enter a vehicle number!")

        st.divider()
        st.subheader("Registered Vehicles")
        st.dataframe(st.session_state.ve_db, use_container_width=True)
        if st.button("🗑️ Clear Vehicle List"):
            st.session_state.ve_db = pd.DataFrame(columns=["No", "Type", "Owner", "Rate_Per_Unit"])
            save_all(); st.rerun()

    # --- DRIVER MANAGEMENT ---
    with setup_tab2:
        st.subheader("Add New Driver / Operator")
        with st.form("d_setup_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                d_name = st.text_input("Driver Name")
            with col2:
                d_salary = st.number_input("Daily Salary (Rs.)", min_value=0.0)
            d_phone = st.text_input("Contact Number")
            
            if st.form_submit_button("✅ Register Driver"):
                if d_name:
                    new_d = pd.DataFrame([[d_name, d_phone, d_salary]], 
                                         columns=["Name", "Phone", "Daily_Salary"])
                    st.session_state.dr_db = pd.concat([st.session_state.dr_db, new_d], ignore_index=True)
                    save_all()
                    st.success(f"Driver {d_name} registered!")
                    st.rerun()
                else:
                    st.error("Please enter a driver name!")

        st.divider()
        st.subheader("Registered Drivers")
        st.dataframe(st.session_state.dr_db, use_container_width=True)
        if st.button("🗑️ Clear Driver List"):
            st.session_state.dr_db = pd.DataFrame(columns=["Name", "Phone", "Daily_Salary"])
            save_all(); st.rerun()


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
