import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
from fpdf import FPDF

# --- CONFIG ---
DATA_FILE = "ksd_pro_data.csv"
VE_FILE = "ksd_ve_db.csv"
SHOP_NAME = "🏗️ K. SIRIWARDHANA SAND CONSTRUCTION PRO"

def load_data(file, cols):
    if os.path.exists(file): return pd.read_csv(file)
    return pd.DataFrame(columns=cols)

# PDF Receipt Function
def generate_trip_sheet(date, cust, vno, qty, amt):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt=SHOP_NAME, ln=True, align='C')
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="OFFICIAL TRIP SHEET / INVOICE", ln=True, align='C')
    pdf.ln(10)
    pdf.cell(100, 10, txt=f"Date: {date}")
    pdf.cell(100, 10, txt=f"Vehicle No: {vno}", ln=True)
    pdf.cell(100, 10, txt=f"Customer: {cust}")
    pdf.cell(100, 10, txt=f"Quantity: {qty} Cubes", ln=True)
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(200, 10, txt=f"TOTAL AMOUNT: Rs. {amt:,.2f}", ln=True)
    pdf.set_font("Arial", size=10)
    pdf.ln(20)
    pdf.cell(100, 10, txt="........................", ln=False)
    pdf.cell(100, 10, txt="........................", ln=True)
    pdf.cell(100, 10, txt="Issued By", ln=False)
    pdf.cell(100, 10, txt="Customer/Driver", ln=True)
    fname = f"Trip_{vno}_{date}.pdf"
    pdf.output(fname)
    return fname

st.set_page_config(page_title=SHOP_NAME, layout="wide")
st.markdown(f"<h1 style='text-align: center; color: #E67E22;'>{SHOP_NAME}</h1>", unsafe_allow_html=True)

df = load_data(DATA_FILE, ["ID", "Date", "Type", "Category", "Entity", "Note", "Amount", "Qty", "Fuel_Ltr", "Hours", "Status"])
ve_db = load_data(VE_FILE, ["No", "Type", "Owner"])

# --- SIDEBAR ---
st.sidebar.header("📅 Filters & Controls")
start_d = st.sidebar.date_input("From", datetime.now().date() - timedelta(days=7))
end_d = st.sidebar.date_input("To", datetime.now().date())
menu = ["📊 Dashboard", "💰 Sales & Trip Sheets", "🚜 Fleet & Fuel Efficiency", "🚚 Stock Management", "💸 Debtors (Naya)", "📝 Setup"]
choice = st.sidebar.selectbox("Menu", menu)

# --- 1. DASHBOARD ---
if choice == "📊 Dashboard":
    st.subheader("Live Business Health")
    # Stock Calculation
    s_in = df[df["Category"] == "Soil In"]["Qty"].sum()
    s_out = df[df["Category"] == "Sand Sale"]["Qty"].sum()
    stock = s_in - s_out
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Current Sand Stock", f"{stock} Cubes")
    c2.metric("Total Income", f"Rs. {df[df['Type']=='Income']['Amount'].sum():,.0f}")
    c3.metric("Total Expenses", f"Rs. {df[df['Type']=='Expense']['Amount'].sum():,.0f}")
    
    # Low Stock Alert
    if stock < 20:
        st.error(f"⚠️ LOW STOCK ALERT: Only {stock} cubes remaining! Plan for soil arrival.")

# --- 2. SALES & TRIP SHEETS ---
elif choice == "💰 Sales & Trip Sheets":
    st.subheader("New Sand Sale")
    with st.form("sale_f", clear_on_submit=True):
        d = st.date_input("Date")
        cust = st.text_input("Customer Name")
        vno = st.text_input("Vehicle No")
        qty = st.number_input("Cubes", min_value=0.0)
        amt = st.number_input("Amount (Rs.)", min_value=0.0)
        stat = st.selectbox("Payment Status", ["Paid", "Credit (Naya)"])
        if st.form_submit_button("Record Sale & Print"):
            new_id = len(df)+1
            new_r = pd.DataFrame([[new_id, d, "Income", "Sand Sale", cust, vno, amt, qty, 0, 0, stat]], columns=df.columns)
            df = pd.concat([df, new_r], ignore_index=True)
            df.to_csv(DATA_FILE, index=False)
            f = generate_trip_sheet(d, cust, vno, qty, amt)
            st.success("Sale Saved!")
            with open(f, "rb") as file:
                st.download_button("📩 Download Trip Sheet PDF", file, file_name=f)

# --- 3. FLEET & FUEL EFFICIENCY ---
elif choice == "🚜 Fleet & Fuel Efficiency":
    st.subheader("Vehicle Fuel Performance")
    selected_v = st.selectbox("Select Vehicle", ve_db["No"].tolist())
    if selected_v:
        v_rows = df[df["Entity"] == selected_v]
        f_ltr = v_rows["Fuel_Ltr"].sum()
        f_qty = v_rows["Qty"].sum()
        f_hrs = v_rows["Hours"].sum()
        
        c1, c2 = st.columns(2)
        if f_qty > 0: c1.metric("Efficiency (Ltr/Cube)", f"{f_ltr/f_qty:.2f}")
        if f_hrs > 0: c2.metric("Efficiency (Ltr/Hour)", f"{f_ltr/f_hrs:.2f}")
        st.dataframe(v_rows)

    with st.form("fuel_f"):
        st.write("#### Add Fuel/Work Entry")
        fd = st.date_input("Date")
        fv = st.selectbox("Vehicle", ve_db["No"].tolist())
        fl = st.number_input("Liters", min_value=0.0)
        fq = st.number_input("Cubes Done", min_value=0.0)
        fh = st.number_input("Hours Worked (Excavator)", min_value=0.0)
        fa = st.number_input("Fuel Cost (Rs.)", min_value=0.0)
        if st.form_submit_button("Save"):
            new_r = pd.DataFrame([[len(df)+1, fd, "Expense", "Fuel/Work", fv, "", fa, fq, fl, fh, "Paid"]], columns=df.columns)
            df = pd.concat([df, new_r], ignore_index=True)
            df.to_csv(DATA_FILE, index=False)
            st.rerun()

# --- 4. DEBTORS (NAYA) ---
elif choice == "💸 Debtors (Naya)":
    st.subheader("Customers with Outstanding Payments")
    debtors = df[df["Status"] == "Credit (Naya)"]
    st.table(debtors[["Date", "Entity", "Note", "Qty", "Amount"]])
    st.info(f"Total Outstanding: Rs. {debtors['Amount'].sum():,.2f}")

# --- 5. SETUP ---
elif choice == "📝 Setup":
    st.write("### Register Vehicles")
    with st.form("v_reg"):
        v_no = st.text_input("No")
        v_ty = st.selectbox("Type", ["Lorry", "Excavator"])
        v_ow = st.text_input("Owner")
        if st.form_submit_button("Register"):
            new_v = pd.DataFrame([[v_no, v_ty, v_ow]], columns=ve_db.columns)
            ve_db = pd.concat([ve_db, new_v], ignore_index=True)
            ve_db.to_csv(VE_FILE, index=False)
            st.rerun()
    st.dataframe(ve_db)