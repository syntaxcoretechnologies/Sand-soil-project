import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
from fpdf import FPDF

# --- CONFIG & DATABASE ---
DATA_FILE = "ksd_master_v3.csv"
VE_FILE = "ksd_fleet_db.csv"
SHOP_NAME = "🏗️ K. SIRIWARDHANA SAND CONSTRUCTION PRO"

def load_data(file, cols):
    if os.path.exists(file): return pd.read_csv(file)
    return pd.DataFrame(columns=cols)

# --- PDF GENERATOR ---
def generate_trip_sheet(date, cust, vno, qty, amt, item):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt=SHOP_NAME, ln=True, align='C')
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"OFFICIAL TRIP SHEET - {item.upper()}", ln=True, align='C')
    pdf.ln(10)
    pdf.cell(100, 10, txt=f"Date: {date}")
    pdf.cell(100, 10, txt=f"Vehicle No: {vno}", ln=True)
    pdf.cell(100, 10, txt=f"Customer: {cust}")
    pdf.cell(100, 10, txt=f"Item: {item} | Qty: {qty} Cubes", ln=True)
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(200, 10, txt=f"TOTAL AMOUNT: Rs. {amt:,.2f}", ln=True)
    pdf.ln(20)
    pdf.set_font("Arial", size=10)
    pdf.cell(100, 10, txt="........................", ln=False)
    pdf.cell(100, 10, txt="........................", ln=True)
    pdf.cell(100, 10, txt="Authorized Signature", ln=False)
    pdf.cell(100, 10, txt="Customer/Driver", ln=True)
    fname = f"Trip_{vno}_{date}.pdf"
    pdf.output(fname)
    return fname

# --- UI SETUP ---
st.set_page_config(page_title=SHOP_NAME, layout="wide")
st.markdown(f"<h1 style='text-align: center; color: #E67E22;'>{SHOP_NAME}</h1>", unsafe_allow_html=True)

df = load_data(DATA_FILE, ["ID", "Date", "Type", "Category", "Entity", "Note", "Amount", "Qty", "Fuel_Ltr", "Hours", "Status"])
ve_db = load_data(VE_FILE, ["No", "Type", "Owner"])

# --- SIDEBAR ---
st.sidebar.header("📅 Date Filter")
today = datetime.now().date()
start_d = st.sidebar.date_input("From", today - timedelta(days=30))
end_d = st.sidebar.date_input("To", today)

menu = ["📊 Dashboard", "💰 Sales (Sand/Soil)", "🚿 Washing & Production", "🚜 Fleet & Fuel Tracking", "💸 Expenses & Advances", "📑 Full Reports", "🛠️ System Setup"]
choice = st.sidebar.selectbox("Main Menu", menu)

# --- 1. DASHBOARD ---
if choice == "📊 Dashboard":
    st.subheader("Inventory & Financial Status")
    
    # Stock Logic
    soil_in = df[df["Category"] == "Soil Purchase"]["Qty"].sum()
    soil_sold = df[df["Category"] == "Soil Sale"]["Qty"].sum()
    soil_washed = df[df["Category"] == "Washing (Input)"]["Qty"].sum()
    
    sand_produced = df[df["Category"] == "Washing (Output)"]["Qty"].sum()
    sand_sold = df[df["Category"] == "Sand Sale"]["Qty"].sum()
    
    cur_soil = soil_in - soil_sold - soil_washed
    cur_sand = sand_produced - sand_sold
    
    inc = df[df["Type"] == "Income"]["Amount"].sum()
    exp = df[df["Type"] == "Expense"]["Amount"].sum()
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Current Soil Stock", f"{cur_soil} Cubes")
    c2.metric("Current Sand Stock", f"{cur_sand} Cubes")
    c3.metric("Total Income (Rs.)", f"{inc:,.0f}")
    c4.metric("Net Profit (Rs.)", f"{inc-exp:,.0f}")

    if cur_sand < 20: st.error(f"⚠️ LOW SAND STOCK: {cur_sand} cubes remaining!")
    st.divider()
    st.write("### Cash Flow Trend")
    st.line_chart(df.groupby("Date")["Amount"].sum())

# --- 2. SALES ---
elif choice == "💰 Sales (Sand/Soil)":
    st.subheader("Record New Sale")
    with st.form("sale_f", clear_on_submit=True):
        col1, col2 = st.columns(2)
        d = col1.date_input("Date")
        item = col2.selectbox("Select Item", ["Sand Sale", "Soil Sale"])
        cust = st.text_input("Customer Name")
        vno = st.text_input("Vehicle No")
        qty = st.number_input("Quantity (Cubes)", min_value=0.0)
        amt = st.number_input("Total Price (Rs.)", min_value=0.0)
        stat = st.selectbox("Payment Status", ["Paid", "Credit (Naya)"])
        
        if st.form_submit_button("Record Sale & Generate PDF"):
            new_r = pd.DataFrame([[len(df)+1, d, "Income", item, cust, vno, amt, qty, 0, 0, stat]], columns=df.columns)
            df = pd.concat([df, new_r], ignore_index=True)
            df.to_csv(DATA_FILE, index=False)
            f_pdf = generate_trip_sheet(d, cust, vno, qty, amt, item)
            st.success("Sale Recorded!")
            with open(f_pdf, "rb") as f:
                st.download_button("📩 Download Trip Sheet", f, file_name=f_pdf)

# --- 3. WASHING ---
elif choice == "🚿 Washing & Production":
    st.subheader("Soil Washing Process")
    with st.form("wash_f", clear_on_submit=True):
        d = st.date_input("Date")
        s_in = st.number_input("Soil Cubes Used (හේදු පස් ප්‍රමාණය)", min_value=0.0)
        s_out = st.number_input("Sand Cubes Produced (ලැබුණු වැලි ප්‍රමාණය)", min_value=0.0)
        if st.form_submit_button("Update Stock Balance"):
            r1 = pd.DataFrame([[len(df)+1, d, "Process", "Washing (Input)", "Plant", "Pas to Wash", 0, s_in, 0, 0, "Done"]], columns=df.columns)
            r2 = pd.DataFrame([[len(df)+2, d, "Process", "Washing (Output)", "Plant", "Washed Sand", 0, s_out, 0, 0, "Done"]], columns=df.columns)
            df = pd.concat([df, r1, r2], ignore_index=True)
            df.to_csv(DATA_FILE, index=False)
            st.success("Washing record updated!")

# --- 4. FLEET & FUEL ---
elif choice == "🚜 Fleet & Fuel Tracking":
    st.subheader("Vehicle Fuel & Performance")
    selected_v = st.selectbox("Select Vehicle", ve_db["No"].tolist() if not ve_db.empty else ["No Vehicles"])
    
    if selected_v != "No Vehicles":
        v_data = df[df["Entity"] == selected_v]
        f_ltr = v_data["Fuel_Ltr"].sum()
        f_qty = v_data["Qty"].sum()
        f_hrs = v_data["Hours"].sum()
        
        c1, c2 = st.columns(2)
        if f_qty > 0: c1.metric("Efficiency (Ltr/Cube)", f"{f_ltr/f_qty:.2f}")
        if f_hrs > 0: c2.metric("Efficiency (Ltr/Hour)", f"{f_ltr/f_hrs:.2f}")
        st.dataframe(v_data[["Date", "Category", "Fuel_Ltr", "Qty", "Hours", "Amount"]])

    with st.form("fuel_f"):
        st.write("#### Add Entry")
        fd = st.date_input("Date")
        fv = st.selectbox("Vehicle", ve_db["No"].tolist())
        fl = st.number_input("Liters", min_value=0.0)
        fq = st.number_input("Cubes Done (Lorries)", min_value=0.0)
        fh = st.number_input("Hours Worked (Excavators)", min_value=0.0)
        fa = st.number_input("Cost (Rs.)", min_value=0.0)
        if st.form_submit_button("Save Vehicle Record"):
            new_r = pd.DataFrame([[len(df)+1, fd, "Expense", "Fuel/Work", fv, "", fa, fq, fl, fh, "Paid"]], columns=df.columns)
            df = pd.concat([df, new_r], ignore_index=True)
            df.to_csv(DATA_FILE, index=False)
            st.rerun()

# --- 5. EXPENSES ---
elif choice == "💸 Expenses & Advances":
    st.subheader("Wages, Advances & Purchases")
    with st.form("exp_f"):
        d = st.date_input("Date")
        cat = st.selectbox("Category", ["Soil Purchase", "Employee Advance", "Driver Payment", "Vehicle Owner Payment", "Repair", "Other"])
        ent = st.text_input("Name/Entity")
        qty = st.number_input("Quantity (If Soil Purchase)", min_value=0.0)
        amt = st.number_input("Amount (Rs.)", min_value=0.0)
        if st.form_submit_button("Save Expense"):
            new_r = pd.DataFrame([[len(df)+1, d, "Expense", cat, ent, "", amt, qty, 0, 0, "Paid"]], columns=df.columns)
            df = pd.concat([df, new_r], ignore_index=True)
            df.to_csv(DATA_FILE, index=False)
            st.success("Expense recorded!")

# --- 6. REPORTS ---
elif choice == "📑 Full Reports":
    st.subheader("Data Explorer")
    st.dataframe(df, use_container_width=True)
    st.download_button("Download CSV Backup", df.to_csv(index=False), "KSD_Full_Backup.csv")

# --- 7. SETUP ---
elif choice == "🛠️ System Setup":
    st.subheader("Fleet Registration")
    with st.form("setup_v"):
        v_no = st.text_input("Vehicle No")
        v_ty = st.selectbox("Type", ["Lorry", "Excavator", "Machine"])
        v_ow = st.text_input("Owner Name")
        if st.form_submit_button("Register Vehicle"):
            new_v = pd.DataFrame([[v_no, v_ty, v_ow]], columns=ve_db.columns)
            ve_db = pd.concat([ve_db, new_v], ignore_index=True)
            ve_db.to_csv(VE_FILE, index=False)
            st.rerun()
    st.table(ve_db)
