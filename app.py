import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
from fpdf import FPDF

# --- CONFIG & FILENAMES ---
DATA_FILE = "ksd_master_v15.csv"
VE_FILE = "ksd_vehicles_v15.csv"
DR_FILE = "ksd_drivers_v15.csv"
SHOP_NAME = "K. SIRIWARDHANA SAND CONSTRUCTION PRO"

# --- HELPER FUNCTIONS ---
def load_data(file, cols):
    if os.path.exists(file): 
        d = pd.read_csv(file)
        if 'Date' in d.columns:
            d['Date'] = pd.to_datetime(d['Date']).dt.date
        return d
    return pd.DataFrame(columns=cols)

# --- PDF GENERATOR CLASS ---
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.set_text_color(230, 126, 34) 
        self.cell(0, 10, SHOP_NAME, 0, 1, 'C')
        self.set_font('Arial', '', 9)
        self.set_text_color(0, 0, 0)
        self.cell(0, 5, 'Official Business Transaction Report', 0, 1, 'C')
        self.ln(10)
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

def create_pdf(title, data_df, summary_dict):
    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 12)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 10, f"STATEMENT: {title.upper()}", 1, 1, 'L', True)
    pdf.ln(5)
    for k, v in summary_dict.items():
        pdf.set_font("Arial", 'B', 10); pdf.cell(60, 8, f"{k}:", 1); pdf.set_font("Arial", '', 10); pdf.cell(0, 8, f" {v}", 1, 1)
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 9); pdf.set_fill_color(230, 126, 34); pdf.set_text_color(255, 255, 255)
    cols = ["Date", "Category", "Note", "Qty/Hrs", "Amount"]
    widths = [30, 40, 60, 25, 35]
    for i in range(len(cols)): pdf.cell(widths[i], 8, cols[i], 1, 0, 'C', True)
    pdf.ln(); pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", '', 8)
    for _, row in data_df.iterrows():
        pdf.cell(widths[0], 7, str(row['Date']), 1); pdf.cell(widths[1], 7, str(row['Category']), 1); pdf.cell(widths[2], 7, str(row['Note'])[:35], 1)
        val = row['Qty_Cubes'] if row['Qty_Cubes'] > 0 else row['Hours']
        pdf.cell(widths[3], 7, f"{val}", 1, 0, 'C'); pdf.cell(widths[4], 7, f"{row['Amount']:,.2f}", 1, 0, 'R'); pdf.ln()
    fname = f"Statement_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
    pdf.output(fname); return fname

# --- UI SETUP ---
st.set_page_config(page_title=SHOP_NAME, layout="wide")
df = load_data(DATA_FILE, ["ID", "Date", "Time", "Type", "Category", "Entity", "Note", "Amount", "Qty_Cubes", "Fuel_Ltr", "Hours", "Status"])
ve_db = load_data(VE_FILE, ["No", "Type", "Owner", "Current_Driver"])
dr_db = load_data(DR_FILE, ["Name", "Phone", "Daily_Salary"])

# --- EXPANDED SIDEBAR MENU ---
st.sidebar.title("KSD NAVIGATION")
main_mode = st.sidebar.radio("SELECT SECTOR", ["📊 Dashboard", "⚙️ Management", "🏗️ Operations", "📑 Reporting"])

choice = ""
if main_mode == "📊 Dashboard":
    choice = "📊 Dashboard"
elif main_mode == "⚙️ Management":
    choice = st.sidebar.selectbox("Sub Menu", ["👷 Driver Setup", "🚜 Vehicle Setup"])
elif main_mode == "🏗️ Operations":
    choice = st.sidebar.selectbox("Sub Menu", ["⛽ Fuel Tracking", "🚚 Stock In (Soil)", "💰 Sales Out", "🚜 Machine Performance", "💸 Driver Payroll"])
elif main_mode == "📑 Reporting":
    choice = "📑 Advanced Reports"

st.markdown(f"<h1 style='text-align: center; color: #E67E22;'>{choice}</h1>", unsafe_allow_html=True)

# --- 1. DASHBOARD ---
if choice == "📊 Dashboard":
    inc = df[df["Type"] == "Income"]["Amount"].sum()
    exp = df[df["Type"] == "Expense"]["Amount"].sum()
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Income", f"Rs. {inc:,.2f}")
    c2.metric("Total Expenses", f"Rs. {exp:,.2f}")
    c3.metric("Net Profit", f"Rs. {inc-exp:,.2f}")
    if not df.empty: st.area_chart(df.groupby("Date")["Amount"].sum())

# --- 2. DRIVER SETUP ---
elif choice == "👷 Driver Setup":
    with st.form("dr_f", clear_on_submit=True):
        c1, c2 = st.columns(2)
        n = c1.text_input("Name"); p = c2.text_input("Phone"); s = c1.number_input("Salary", min_value=0.0)
        if st.form_submit_button("Add Driver"):
            new = pd.DataFrame([[n, p, s]], columns=dr_db.columns)
            dr_db = pd.concat([dr_db, new], ignore_index=True); dr_db.to_csv(DR_FILE, index=False); st.rerun()
    st.table(dr_db)

# --- 3. VEHICLE SETUP ---
elif choice == "🚜 Vehicle Setup":
    if dr_db.empty: st.warning("Add drivers first!")
    else:
        with st.form("ve_f"):
            c1, c2 = st.columns(2)
            v_no = c1.text_input("Vehicle No"); v_ty = c2.selectbox("Type", ["Lorry", "Excavator", "Machine"])
            v_dr = c1.selectbox("Driver", dr_db["Name"].tolist()); v_ow = c2.text_input("Owner")
            if st.form_submit_button("Add Vehicle"):
                new = pd.DataFrame([[v_no, v_ty, v_ow, v_dr]], columns=ve_db.columns)
                ve_db = pd.concat([ve_db, new], ignore_index=True); ve_db.to_csv(VE_FILE, index=False); st.rerun()
    st.dataframe(ve_db, use_container_width=True)

# --- 4. FUEL TRACKING (WITH CREDIT SETTLEMENT) ---
elif choice == "⛽ Fuel Tracking":
    tab_f1, tab_f2 = st.tabs(["⛽ Log New Fuel", "💰 Settle Station Bills"])
    
    with tab_f1:
        st.subheader("Record Fuel Intake (Credit)")
        with st.form("fuel_f", clear_on_submit=True):
            d = st.date_input("Date")
            v = st.selectbox("Vehicle", ve_db["No"].tolist() if not ve_db.empty else ["No Vehicles"])
            ltr = st.number_input("Liters", min_value=0.0)
            cost = st.number_input("Bill Amount (Rs.)", min_value=0.0)
            station = st.text_input("Fuel Station Name", "Petrol Shed")
            if st.form_submit_button("Record Bill (Pending)"):
                # Status eka 'Pending' widiyata save wenawa
                new_r = pd.DataFrame([[len(df)+1, d, "", "Expense", "Fuel Entry", v, f"Station: {station}", cost, 0, ltr, 0, "Pending"]], columns=df.columns)
                df = pd.concat([df, new_r], ignore_index=True)
                df.to_csv(DATA_FILE, index=False)
                st.success(f"Bill recorded as Pending for {v}")
                st.rerun()

        # Display Pending Bills
        pending_fuel = df[(df["Category"] == "Fuel Entry") & (df["Status"] == "Pending")]
        if not pending_fuel.empty:
            st.warning(f"Outstanding Fuel Amount: Rs. {pending_fuel['Amount'].sum():,.2f}")
            st.dataframe(pending_fuel[["Date", "Entity", "Fuel_Ltr", "Amount", "Note"]], use_container_width=True)

    with tab_f2:
        st.subheader("Settle Outstanding Bills")
        unpaid = df[(df["Category"] == "Fuel Entry") & (df["Status"] == "Pending")]
        
        if unpaid.empty:
            st.success("All fuel bills are settled! ✅")
        else:
            # Select which vehicle's bill to settle
            to_settle = st.selectbox("Select Bill to Settle", unpaid.apply(lambda x: f"ID:{x['ID']} | {x['Date']} | {x['Entity']} | Rs.{x['Amount']}", axis=1))
            sel_id = int(to_settle.split("|")[0].split(":")[1])
            
            if st.button("Mark as Paid ✅"):
                df.loc[df['ID'] == sel_id, 'Status'] = 'Paid'
                df.to_csv(DATA_FILE, index=False)
                st.success("Bill settled successfully!")
                st.rerun()

# --- 5. STOCK IN ---
elif choice == "🚚 Stock In (Soil)":
    with st.form("stock_f", clear_on_submit=True):
        d = st.date_input("Date"); v_sup = st.text_input("Supplier Vehicle"); q = st.number_input("Cubes")
        if st.form_submit_button("Add Stock"):
            new = pd.DataFrame([[len(df)+1, d, "", "Process", "Soil In", v_sup, "In", 0, q, 0, 0, "Done"]], columns=df.columns)
            df = pd.concat([df, new], ignore_index=True); df.to_csv(DATA_FILE, index=False); st.success("Stock Added!"); st.rerun()

# --- 6. SALES OUT ---
elif choice == "💰 Sales Out":
    with st.form("sale_f", clear_on_submit=True):
        c1, c2 = st.columns(2); d = c1.date_input("Date"); t = c2.time_input("Time")
        it = c1.selectbox("Item", ["Sand Sale", "Soil Sale"]); v_cust = c2.text_input("Customer Vehicle"); q = c1.number_input("Cubes"); a = c2.number_input("Amount")
        if st.form_submit_button("Record Sale"):
            new = pd.DataFrame([[len(df)+1, d, t.strftime("%H:%M"), "Income", it, v_cust, "Sale", a, q, 0, 0, "Paid"]], columns=df.columns)
            df = pd.concat([df, new], ignore_index=True); df.to_csv(DATA_FILE, index=False); st.success("Sale Recorded!"); st.rerun()

# --- 7. MACHINE PERFORMANCE ---
elif choice == "🚜 Machine Performance":
    t1, t2 = st.tabs(["🏗️ Excavator", "🚚 Lorry"])
    with t1:
        exs = ve_db[ve_db["Type"]=="Excavator"]["No"].tolist()
        if exs:
            sel = st.selectbox("Select Excavator", exs); d_ex = st.date_input("Date", key="exd"); h = st.number_input("Hours Worked")
            if st.button("Log Hours"):
                new = pd.DataFrame([[len(df)+1, d_ex, "", "Work", "Work Entry", sel, "Digging", 0, 0, 0, h, "Done"]], columns=df.columns)
                df = pd.concat([df, new], ignore_index=True); df.to_csv(DATA_FILE, index=False); st.success("Hours Logged!"); st.rerun()
        else: st.info("No Excavators found.")
    with t2:
        lrs = ve_db[ve_db["Type"]=="Lorry"]["No"].tolist()
        if lrs:
            sel_lr = st.selectbox("Select Lorry", lrs); d_lr = st.date_input("Date", key="lrd"); q_lr = st.number_input("Cubes Added")
            if st.button("Log Cubes"):
                new = pd.DataFrame([[len(df)+1, d_lr, "", "Work", "Work Entry", sel_lr, "Transport", 0, q_lr, 0, 0, "Done"]], columns=df.columns)
                df = pd.concat([df, new], ignore_index=True); df.to_csv(DATA_FILE, index=False); st.success("Cubes Logged!"); st.rerun()
        else: st.info("No Lorries found.")

# --- 8. DRIVER PAYROLL ---
elif choice == "💸 Driver Payroll":
    if dr_db.empty: st.warning("No drivers registered.")
    else:
        with st.form("pay_f", clear_on_submit=True):
            sel_dr = st.selectbox("Driver Name", dr_db["Name"].tolist())
            p_ty = st.selectbox("Type", ["Advance", "Salary Payment"])
            p_am = st.number_input("Amount (Rs.)", min_value=0.0)
            if st.form_submit_button("Save Payment"):
                new = pd.DataFrame([[len(df)+1, datetime.now().date(), "", "Expense", p_ty, sel_dr, "Driver Payment", p_am, 0, 0, 0, "Paid"]], columns=df.columns)
                df = pd.concat([df, new], ignore_index=True); df.to_csv(DATA_FILE, index=False); st.success("Payment Saved!"); st.rerun()

# --- 9. ADVANCED REPORTS ---
elif choice == "📑 Advanced Reports":
    rt = st.selectbox("Report Category", ["Vehicle Owner Statement", "Driver Statement"])
    f_d = st.date_input("Start Date", datetime.now().date()-timedelta(days=30))
    t_d = st.date_input("End Date", datetime.now().date())
    
    if rt == "Vehicle Owner Statement" and not ve_db.empty:
        sv = st.selectbox("Vehicle No", ve_db["No"].tolist())
        v_info = ve_db[ve_db["No"]==sv]
        if not v_info.empty:
            v_owner = v_info["Owner"].values[0]
            v_data = df[(df["Entity"]==sv) & (df["Date"]>=f_d) & (df["Date"]<=t_d)]
            st.write(f"### Report for: {v_owner} ({sv})")
            st.dataframe(v_data, use_container_width=True)
            if st.button("Download PDF"):
                summary = {"Owner": v_owner, "Vehicle": sv, "Period": f"{f_d} to {t_d}", "Total Cubes": v_data["Qty_Cubes"].sum(), "Fuel Cost": f"Rs. {v_data[v_data['Category']=='Fuel Entry']['Amount'].sum():,.2f}"}
                fn = create_pdf(f"Vehicle_{sv}", v_data, summary)
                with open(fn, "rb") as file: st.download_button("📩 Download PDF", file, file_name=fn)
    elif rt == "Driver Statement" and not dr_db.empty:
        sd = st.selectbox("Select Driver", dr_db["Name"].tolist())
        d_data = df[(df["Entity"]==sd) & (df["Date"]>=f_d) & (df["Date"]<=t_d)]
        st.write(f"### Report for: {sd}")
        st.dataframe(d_data, use_container_width=True)
        if st.button("Download Driver PDF"):
            summary = {"Driver": sd, "Period": f"{f_d} to {t_d}", "Total Advances": f"Rs. {d_data[d_data['Category']=='Advance']['Amount'].sum():,.2f}"}
            fn = create_pdf(f"Driver_{sd}", d_data, summary)
            with open(fn, "rb") as file: st.download_button("📩 Download PDF", file, file_name=fn)
