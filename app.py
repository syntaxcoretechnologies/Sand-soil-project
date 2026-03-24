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

menu = st.sidebar.selectbox("MAIN MENU", ["📊 Dashboard", "🏗️ Site Operations", "💰 Finance & Shed", "⚙️ System Setup", "📑 Reports Center", "⚙️ Data Manager"])

if menu == "📊 Dashboard":
    # --- මෙන්න මෙතන ඉඳන් පල්ලෙහාට තියෙන හැම පේළියක්ම 'if' එකට වඩා ඇතුළට වෙන්න ඕනේ ---
    df = st.session_state.df.copy()
    if not df.empty:
        # --- Income එක ගණනය කිරීම ---
        df['Calculated_Income'] = (pd.to_numeric(df['Qty_Cubes'], errors='coerce').fillna(0) + 
                                   pd.to_numeric(df['Hours'], errors='coerce').fillna(0)) * \
                                   pd.to_numeric(df['Rate_At_Time'], errors='coerce').fillna(0)
        
        ti = df[df["Type"] == "Process"]["Calculated_Income"].sum()
        te = pd.to_numeric(df[df["Type"] == "Expense"]["Amount"], errors='coerce').sum()
        
        f_debt = df[df["Category"] == "Fuel Entry"]["Amount"].sum() - df[df["Category"] == "Shed Payment"]["Amount"].sum()
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Income", f"Rs. {ti:,.2f}")
        m2.metric("Total Expenses", f"Rs. {te:,.2f}")
        m3.metric("Net Cashflow", f"Rs. {ti-te:,.2f}")
        m4.metric("Shed Debt", f"Rs. {f_debt:,.2f}")
        
        st.divider()
        st.subheader("Daily Income Trend")
        st.line_chart(df[df["Type"] == "Process"].groupby('Date')['Calculated_Income'].sum())
    else:
        st.info("No data available to display in Dashboard.")

# --- මීළඟට එන 'elif' එක ආයෙත් 'if' පේළියටම කෙළින් තියෙන්න ඕනේ ---
    elif menu == "🏗️ Site Operations":
        # (කලින් තිබුණු Site Operations Code එක මෙතනට...)
    
    
    # --- 7. SITE OPERATIONS (v57 FULL FIX) ---
    elif menu == "🏗️ Site Operations":
    st.markdown(f"<h2 style='color: #E67E22;'>🏗️ Site Operations</h2>", unsafe_allow_html=True)
    
    op = st.radio("Select Activity Type", ["🚛 Lorry Work Log", "🚜 Excavator Work Log", "💰 Sales Out"], horizontal=True)
    
    v_list = st.session_state.ve_db["No"].tolist() if not st.session_state.ve_db.empty else ["N/A"]
    
    with st.form("site_f", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            v = st.selectbox("Select Vehicle / Machine", v_list)
            d = st.date_input("Date", datetime.now().date())
            
            material = ""
            if op == "💰 Sales Out":
                material = st.selectbox("Material Type", ["Sand", "Soil", "Other"])
        
        with col2:
            # වර්ගය අනුව label එක තෝරනවා
            if "Lorry" in op:
                val_label = "Qty (Cubes)"
                unit = "Cubes"
            elif "Excavator" in op:
                val_label = "Work Hours"
                unit = "Hrs"
            else:
                val_label = f"Sales Qty ({material})"
                unit = "Cubes/Units"
                
            # Default අගයන් 0.0 විදියට දුන්නා (මැනුවල් ටයිප් කරන්න ඕන නිසා)
            val = st.number_input(val_label, min_value=0.0, step=0.5, value=0.0)
            r = st.number_input(f"Enter Rate per {unit}", min_value=0.0, step=100.0, value=0.0)
        
        n = st.text_input("Additional Note (Location, Trip details etc.)")
        submit = st.form_submit_button("📥 Save Record")
        
        if submit:
            if v == "N/A":
                st.error("Please add a vehicle in Setup first!")
            elif val <= 0:
                st.error(f"Please enter a valid {val_label}")
            elif r <= 0:
                st.error(f"Please enter the Rate for this work!")
            else:
                display_cat = f"{op} ({material})" if material else op
                q, h = (val, 0) if "Lorry" in op or "Sales" in op else (0, val)
                
                new_data = pd.DataFrame([[
                    len(st.session_state.df) + 1, d, "", "Process", 
                    display_cat, v, n, 0, q, 0, h, r, "Done"
                ]], columns=st.session_state.df.columns)
                
                st.session_state.df = pd.concat([st.session_state.df, new_data], ignore_index=True)
                save_all()
                st.success(f"Successfully recorded {display_cat} for {v}")
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
elif menu == "📑 Reports Center":
    r1, r2, r3, r4 = st.tabs(["🚜 Vehicle Settlement", "👷 Driver Summary", "📑 Daily Log", "⛽ Shed Report"])
    f_d, t_d = st.date_input("From", datetime.now().date()-timedelta(days=30)), st.date_input("To")
    df_f = st.session_state.df[(st.session_state.df["Date"] >= f_d) & (st.session_state.df["Date"] <= t_d)]
    
    with r1:
        sel_ve = st.selectbox("Select Vehicle", st.session_state.ve_db["No"].tolist() if not st.session_state.ve_db.empty else [])
        if sel_ve:
            # වාහනයට අදාළ දත්ත පෙරා ගැනීම
            v_rep = df_f[df_f["Entity"] == sel_ve].copy()
            
            if not v_rep.empty:
                # වැදගත්ම කොටස: 
                # හැම පේළියකම (Qty + Hours) එකතුව ඒ පේළියේ තිබෙන Rate එකෙන්ම වැඩි කරනවා
                v_rep['Income_Calc'] = (v_rep['Qty_Cubes'] + v_rep['Hours']) * v_rep['Rate_At_Time']
                
                # රේට් එක අනුව ගෲප් කරලා රිපෝට් එක හදනවා
                rate_summary = v_rep[v_rep['Rate_At_Time'] > 0].groupby('Rate_At_Time').apply(
                    lambda x: pd.Series({
                        'Total_Units': (x['Qty_Cubes'] + x['Hours']).sum(),
                        'Total_Income': x['Income_Calc'].sum()
                    })
                ).reset_index()

                rate_list = []
                for _, row in rate_summary.iterrows():
                    rate_list.append({
                        'rate': row['Rate_At_Time'], 
                        'qty': row['Total_Units'], 
                        'subtotal': row['Total_Income']
                    })

                gross = v_rep['Income_Calc'].sum()
                deduct = v_rep[v_rep["Type"] == "Expense"]["Amount"].sum()
                net = gross - deduct
                
                st.metric("Net Balance (LKR)", f"{net:,.2f}")
                
                # Table එක පෙන්වද්දී Rate එකත් එක්කම පෙන්වන්න
                st.dataframe(v_rep[['Date', 'Category', 'Note', 'Qty_Cubes', 'Hours', 'Rate_At_Time', 'Income_Calc']])
                
                if st.button("Download PDF Settlement"):
                    summary = {
                        "Vehicle No": sel_ve,
                        "Gross Earnings": f"{gross:,.2f}",
                        "Total Expenses": f"{deduct:,.2f}",
                        "Net Settlement": f"{net:,.2f}",
                        "Rate_Breakdown": rate_list
                    }
                    fn = create_pdf(f"Settlement_{sel_ve}", v_rep, summary)
                    with open(fn, "rb") as f: st.download_button("📩 Download PDF", f, file_name=fn)
    with r2:
        sel_dr = st.selectbox("Select Driver", st.session_state.dr_db["Name"].tolist() if not st.session_state.dr_db.empty else [])
        if sel_dr:
            # --- මෙතන තමයි වැදගත්ම වෙනස්කම ---
            # Note column එක string එකක් බවට හරවා පරීක්ෂා කිරීම (Error එක එන තැන)
            dr_rep = df_f[df_f["Note"].astype(str).str.contains(f"Driver: {sel_dr}", na=False)].copy()
            
            total_dr = dr_rep['Amount'].sum()
            st.metric(f"Total Paid to {sel_dr}", f"Rs. {total_dr:,.2f}")
            st.dataframe(dr_rep, use_container_width=True)
            
            if st.button(f"Download {sel_dr} Report"):
                sum_dr = {"Driver": sel_dr, "Period": f"{f_d} to {t_d}", "Total Paid": f"{total_dr:,.2f}"}
                fn = create_pdf(f"Driver_{sel_dr}", dr_rep, sum_dr)
                with open(fn, "rb") as f: 
                    st.download_button("📩 Get PDF", f, file_name=fn)
    
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
