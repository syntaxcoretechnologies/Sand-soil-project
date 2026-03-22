import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
from fpdf import FPDF

# --- CONFIG & FILENAMES ---
DATA_FILE = "ksd_main_final.csv"
VE_FILE = "ksd_vehicles_final.csv"
DR_FILE = "ksd_drivers_final.csv"
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
        self.set_text_color(230, 126, 34) # Orange Theme
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
    
    # Title Box
    pdf.set_font("Arial", 'B', 12)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 10, f"STATEMENT: {title.upper()}", 1, 1, 'L', True)
    pdf.set_font("Arial", '', 10)
    pdf.ln(5)
    
    # Summary Table
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(0, 8, "SUMMARY DETAILS", 0, 1)
    pdf.set_font("Arial", '', 10)
    for k, v in summary_dict.items():
        pdf.cell(60, 8, f"{k}:", 1, 0, 'L')
        pdf.cell(0, 8, f" {v}", 1, 1, 'L')
    pdf.ln(10)

    # Transaction Table Header
    pdf.set_font("Arial", 'B', 9)
    pdf.set_fill_color(230, 126, 34)
    pdf.set_text_color(255, 255, 255)
    cols = ["Date", "Category", "Note", "Qty/Hrs", "Amount"]
    widths = [30, 40, 60, 25, 35]
    for i in range(len(cols)):
        pdf.cell(widths[i], 8, cols[i], 1, 0, 'C', True)
    pdf.ln()
    
    # Table Data
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", '', 8)
    for _, row in data_df.iterrows():
        pdf.cell(widths[0], 7, str(row['Date']), 1)
        pdf.cell(widths[1], 7, str(row['Category']), 1)
        pdf.cell(widths[2], 7, str(row['Note'])[:35], 1)
        val = row['Qty_Cubes'] if row['Qty_Cubes'] > 0 else row['Hours']
        pdf.cell(widths[3], 7, f"{val}", 1, 0, 'C')
        pdf.cell(widths[4], 7, f"{row['Amount']:,.2f}", 1, 0, 'R')
        pdf.ln()
    
    fname = f"Statement_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
    pdf.output(fname)
    return fname

# --- UI SETUP ---
st.set_page_config(page_title=SHOP_NAME, layout="wide")
st.markdown(f"<h1 style='text-align: center; color: #E67E22;'>{SHOP_NAME}</h1>", unsafe_allow_html=True)

# Initializing Databases
df = load_data(DATA_FILE, ["ID", "Date", "Time", "Type", "Category", "Entity", "Note", "Amount", "Qty_Cubes", "Fuel_Ltr", "Hours", "Status"])
ve_db = load_data(VE_FILE, ["No", "Type", "Owner", "Current_Driver"])
dr_db = load_data(DR_FILE, ["Name", "Phone", "Daily_Salary"])

# --- SIDEBAR MENU ---
menu = ["📊 Dashboard", "👷 Driver Setup", "🚜 Vehicle Setup", "⛽ Fuel Tracking", "🚚 Stock In (Soil)", "💰 Sales Out (Sand/Soil)", "💸 Driver Payroll", "🚜 Machine Performance", "📑 Advanced Reports"]
choice = st.sidebar.selectbox("Main Menu", menu)

# --- 1. DRIVER SETUP ---
if choice == "👷 Driver Setup":
    st.subheader("Manage Drivers")
    with st.form("dr_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        name = col1.text_input("Driver Name")
        phone = col2.text_input("Phone Number")
        salary = col1.number_input("Daily Salary (Rs.)", min_value=0.0)
        if st.form_submit_button("Register Driver"):
            new_dr = pd.DataFrame([[name, phone, salary]], columns=dr_db.columns)
            dr_db = pd.concat([dr_db, new_dr], ignore_index=True)
            dr_db.to_csv(DR_FILE, index=False)
            st.success(f"Driver {name} Registered!")
            st.rerun()
    st.table(dr_db)

# --- 2. VEHICLE SETUP ---
elif choice == "🚜 Vehicle Setup":
    st.subheader("Manage Fleet")
    if dr_db.empty: st.warning("Add a Driver first!")
    else:
        with st.form("ve_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            v_no = col1.text_input("Vehicle No")
            v_ty = col2.selectbox("Type", ["Lorry", "Excavator", "Machine"])
            v_dr = col1.selectbox("Assign Driver", dr_db["Name"].tolist())
            v_ow = col2.text_input("Owner Name")
            if st.form_submit_button("Register Vehicle"):
                new_v = pd.DataFrame([[v_no, v_ty, v_ow, v_dr]], columns=ve_db.columns)
                ve_db = pd.concat([ve_db, new_v], ignore_index=True)
                ve_db.to_csv(VE_FILE, index=False)
                st.success("Vehicle Registered!")
                st.rerun()
        st.dataframe(ve_db, use_container_width=True)

# --- 3. FUEL TRACKING ---
elif choice == "⛽ Fuel Tracking":
    st.subheader("Fuel History")
    col1, col2, col3 = st.columns(3)
    sel_v = col1.selectbox("Filter Vehicle", ["All"] + ve_db["No"].tolist())
    f_date = col2.date_input("From", datetime.now().date() - timedelta(days=30))
    t_date = col3.date_input("To", datetime.now().date())
    
    fuel_df = df[(df["Category"] == "Fuel Entry") & (df["Date"] >= f_date) & (df["Date"] <= t_date)]
    if sel_v != "All": fuel_df = fuel_df[fuel_df["Entity"] == sel_v]
    
    st.metric("Total Fuel Cost", f"Rs. {fuel_df['Amount'].sum():,.2f}")
    st.dataframe(fuel_df[["Date", "Entity", "Fuel_Ltr", "Amount"]], use_container_width=True)

    with st.expander("Add New Fuel Entry"):
        with st.form("fuel_f", clear_on_submit=True):
            d = st.date_input("Date")
            v = st.selectbox("Vehicle", ve_db["No"].tolist())
            ltr = st.number_input("Liters", min_value=0.0)
            cost = st.number_input("Cost (Rs.)", min_value=0.0)
            if st.form_submit_button("Save Fuel"):
                new_r = pd.DataFrame([[len(df)+1, d, "", "Expense", "Fuel Entry", v, "Fueling", cost, 0, ltr, 0, "Paid"]], columns=df.columns)
                df = pd.concat([df, new_r], ignore_index=True)
                df.to_csv(DATA_FILE, index=False)
                st.success("Fuel Recorded!")
                st.rerun()

# --- 4. STOCK IN (SOIL) ---
elif choice == "🚚 Stock In (Soil)":
    st.subheader("Raw Soil (Pas) Plant In")
    col1, col2 = st.columns(2)
    f_date = col1.date_input("From", datetime.now().date() - timedelta(days=7))
    t_date = col2.date_input("To", datetime.now().date())
    
    soil_in = df[(df["Category"] == "Soil In") & (df["Date"] >= f_date) & (df["Date"] <= t_date)]
    st.metric("Total Cubes In", f"{soil_in['Qty_Cubes'].sum()}")
    st.dataframe(soil_in[["Date", "Entity", "Qty_Cubes"]], use_container_width=True)

    with st.expander("Record Soil In"):
        with st.form("soil_f"):
            d = st.date_input("Date")
            v = st.text_input("Supplier Vehicle")
            qty = st.number_input("Cubes", min_value=0.0)
            if st.form_submit_button("Add Stock"):
                new_r = pd.DataFrame([[len(df)+1, d, "", "Process", "Soil In", v, "In", 0, qty, 0, 0, "Done"]], columns=df.columns)
                df = pd.concat([df, new_r], ignore_index=True)
                df.to_csv(DATA_FILE, index=False)
                st.success("Stock Added!")
                st.rerun()

# --- 5. SALES OUT ---
elif choice == "💰 Sales Out (Sand/Soil)":
    st.subheader("Sales History (Out)")
    col1, col2 = st.columns(2)
    f_date = col1.date_input("Date From", datetime.now().date() - timedelta(days=7))
    t_date = col2.date_input("Date To", datetime.now().date())
    
    sales_df = df[(df["Type"] == "Income") & (df["Date"] >= f_date) & (df["Date"] <= t_date)]
    st.dataframe(sales_df[["Date", "Time", "Category", "Entity", "Qty_Cubes", "Amount"]], use_container_width=True)

    with st.expander("Record Sale Out"):
        with st.form("sale_f"):
            d = st.date_input("Date")
            t = st.time_input("Time")
            item = st.selectbox("Item", ["Sand Sale", "Soil Sale"])
            v = st.text_input("Transport Vehicle No")
            qty = st.number_input("Cubes", min_value=0.0)
            amt = st.number_input("Amount", min_value=0.0)
            if st.form_submit_button("Record Sale"):
                new_r = pd.DataFrame([[len(df)+1, d, t.strftime("%H:%M"), "Income", item, v, "Sale", amt, qty, 0, 0, "Paid"]], columns=df.columns)
                df = pd.concat([df, new_r], ignore_index=True)
                df.to_csv(DATA_FILE, index=False)
                st.success("Sale Recorded!")
                st.rerun()

# --- 6. DRIVER PAYROLL ---
elif choice == "💸 Driver Payroll":
    st.subheader("Driver Salary & Advances")
    if dr_db.empty: st.warning("Register drivers first!")
    else:
        sel_dr = st.selectbox("Select Driver", dr_db["Name"].tolist())
        dr_data = df[df["Entity"] == sel_dr]
        
        c1, c2 = st.columns(2)
        c1.metric("Advances Taken", f"Rs. {dr_data[dr_data['Category']=='Advance']['Amount'].sum():,.2f}")
        c2.metric("Salary Paid", f"Rs. {dr_data[dr_data['Category']=='Salary Payment']['Amount'].sum():,.2f}")
        
        st.dataframe(dr_data[["Date", "Category", "Amount", "Note"]], use_container_width=True)

        with st.form("pay_dr", clear_on_submit=True):
            p_date = st.date_input("Date")
            p_type = st.selectbox("Type", ["Advance", "Salary Payment"])
            p_amt = st.number_input("Amount (Rs.)", min_value=0.0)
            p_note = st.text_input("Note")
            if st.form_submit_button("Save Payment"):
                new_r = pd.DataFrame([[len(df)+1, p_date, "", "Expense", p_type, sel_dr, p_note, p_amt, 0, 0, 0, "Paid"]], columns=df.columns)
                df = pd.concat([df, new_r], ignore_index=True)
                df.to_csv(DATA_FILE, index=False)
                st.success("Payment Recorded!")
                st.rerun()

# --- 7. MACHINE PERFORMANCE (TABS) ---
elif choice == "🚜 Machine Performance":
    st.subheader("Performance Logs")
    if ve_db.empty: st.warning("Register fleet first!")
    else:
        tab1, tab2 = st.tabs(["🏗️ Excavator", "🚚 Lorry"])
        with tab1:
            ex_list = ve_db[ve_db["Type"] == "Excavator"]["No"].tolist()
            if ex_list:
                sel_ex = st.selectbox("Select Excavator", ex_list)
                ex_data = df[df["Entity"] == sel_ex]
                st.metric("Total Hours Worked", f"{ex_data['Hours'].sum()} hrs")
                with st.form("ex_f", clear_on_submit=True):
                    d = st.date_input("Date")
                    h = st.number_input("Hours", min_value=0.0)
                    if st.form_submit_button("Log Hours"):
                        new_r = pd.DataFrame([[len(df)+1, d, "", "Work", "Work Entry", sel_ex, "", 0, 0, 0, h, "Done"]], columns=df.columns)
                        df = pd.concat([df, new_r], ignore_index=True); df.to_csv(DATA_FILE, index=False)
                        st.success("Logged!"); st.rerun()
        with tab2:
            lr_list = ve_db[ve_db["Type"] == "Lorry"]["No"].tolist()
            if lr_list:
                sel_lr = st.selectbox("Select Lorry", lr_list)
                lr_data = df[df["Entity"] == sel_lr]
                st.metric("Total Cubes", f"{lr_data['Qty_Cubes'].sum()}")
                with st.form("lr_f", clear_on_submit=True):
                    d = st.date_input("Date")
                    q = st.number_input("Cubes", min_value=0.0)
                    if st.form_submit_button("Log Cubes"):
                        new_r = pd.DataFrame([[len(df)+1, d, "", "Work", "Work Entry", sel_lr, "", 0, q, 0, 0, "Done"]], columns=df.columns)
                        df = pd.concat([df, new_r], ignore_index=True); df.to_csv(DATA_FILE, index=False)
                        st.success("Logged!"); st.rerun()

# --- 8. ADVANCED REPORTS (PDF) ---
elif choice == "📑 Advanced Reports":
    st.subheader("📑 Advanced Report Generator")
    col1, col2, col3 = st.columns(3)
    rep_type = col1.selectbox("Category", ["Vehicle Owner Statement", "Driver Statement"])
    range_type = col2.selectbox("Period", ["Daily", "Weekly", "Monthly", "Custom"])
    
    today = datetime.now().date()
    start_date = today - timedelta(days=30) if range_type == "Custom" else today
    if range_type == "Weekly": start_date = today - timedelta(days=7)
    if range_type == "Monthly": start_date = today - timedelta(days=30)
    
    f_date = col3.date_input("From", start_date)
    t_date = col3.date_input("To", today)

    if rep_type == "Vehicle Owner Statement":
        sel_v = st.selectbox("Vehicle", ve_db["No"].tolist())
        v_owner = ve_db[ve_db["No"] == sel_v]["Owner"].values[0]
        v_data = df[(df["Entity"] == sel_v) & (df["Date"] >= f_date) & (df["Date"] <= t_date)]
        
        sum_dict = {
            "Vehicle": sel_v, "Owner": v_owner, "Period": f"{f_date} to {t_date}",
            "Work (C/H)": f"{v_data['Qty_Cubes'].sum()} / {v_data['Hours'].sum()}",
            "Fuel Cost": f"Rs. {v_data[v_data['Category']=='Fuel Entry']['Amount'].sum():,.2f}"
        }
        st.dataframe(v_data)
        if st.button("Download Vehicle Statement"):
            fname = create_pdf(f"Vehicle_{sel_v}", v_data, sum_dict)
            with open(fname, "rb") as f: st.download_button("📩 PDF", f, file_name=fname)

    elif rep_type == "Driver Statement":
        sel_dr = st.selectbox("Driver", dr_db["Name"].tolist())
        dr_data = df[(df["Entity"] == sel_dr) & (df["Date"] >= f_date) & (df["Date"] <= t_date)]
        sum_dict = {"Driver": sel_dr, "Advances": f"Rs. {dr_data[dr_data['Category']=='Advance']['Amount'].sum():,.2f}", "Period": f"{f_date} to {t_date}"}
        st.dataframe(dr_data)
        if st.button("Download Driver Statement"):
            fname = create_pdf(f"Driver_{sel_dr}", dr_data, sum_dict)
            with open(fname, "rb") as f: st.download_button("📩 PDF", f, file_name=fname)

# --- 9. DASHBOARD ---
elif choice == "📊 Dashboard":
    st.subheader("Business Summary")
    c1, c2, c3 = st.columns(3)
    inc = df[df["Type"] == "Income"]["Amount"].sum()
    exp = df[df["Type"] == "Expense"]["Amount"].sum()
    c1.metric("Total Income", f"Rs. {inc:,.0f}")
    c2.metric("Total Expense", f"Rs. {exp:,.0f}")
    c3.metric("Net Profit", f"Rs. {inc-exp:,.0f}")
    if not df.empty: st.line_chart(df.groupby("Date")["Amount"].sum())
