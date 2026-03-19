import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
from fpdf import FPDF

# --- CONFIG & DATABASE ---
DATA_FILE = "ksd_master_final_v4.csv"
VE_FILE = "ksd_fleet_db.csv"
SHOP_NAME = "🏗️ K. SIRIWARDHANA SAND CONSTRUCTION PRO"

def load_data(file, cols):
    if os.path.exists(file): 
        d = pd.read_csv(file)
        d['Date'] = pd.to_datetime(d['Date']).dt.date
        return d
    return pd.DataFrame(columns=cols)

# PDF Generator (Same as before)
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
    pdf.output(f"Trip_{vno}_{date}.pdf")
    return f"Trip_{vno}_{date}.pdf"

# --- UI SETUP ---
st.set_page_config(page_title=SHOP_NAME, layout="wide")
st.markdown(f"<h1 style='text-align: center; color: #E67E22;'>{SHOP_NAME}</h1>", unsafe_allow_html=True)

df = load_data(DATA_FILE, ["ID", "Date", "Type", "Category", "Entity", "Note", "Amount", "Qty", "Fuel_Ltr", "Hours", "Status"])
ve_db = load_data(VE_FILE, ["No", "Type", "Owner"])

# --- SIDEBAR ---
menu = ["📊 Dashboard", "💰 Sales (Sand/Soil)", "🚿 Washing & Production", "⛽ Fuel Analytics", "🚜 Fleet & Work Entry", "💸 Expenses & Advances", "📑 Full Reports", "🛠️ System Setup"]
choice = st.sidebar.selectbox("Main Menu", menu)

# --- 1. DASHBOARD ---
if choice == "📊 Dashboard":
    st.subheader("Inventory & Financial Status")
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
    c1.metric("Soil Stock", f"{cur_soil} Cubes")
    c2.metric("Sand Stock", f"{cur_sand} Cubes")
    c3.metric("Total Income", f"Rs. {inc:,.0f}")
    c4.metric("Net Profit", f"Rs. {inc-exp:,.0f}")
    st.divider()
    st.line_chart(df.groupby("Date")["Amount"].sum())

# --- 2. SALES ---
elif choice == "💰 Sales (Sand/Soil)":
    st.subheader("Record New Sale")
    with st.form("sale_f", clear_on_submit=True):
        d = st.date_input("Date")
        item = st.selectbox("Select Item", ["Sand Sale", "Soil Sale"])
        cust = st.text_input("Customer Name")
        vno = st.text_input("Vehicle No")
        qty = st.number_input("Quantity (Cubes)", min_value=0.0)
        amt = st.number_input("Total Price (Rs.)", min_value=0.0)
        stat = st.selectbox("Status", ["Paid", "Credit (Naya)"])
        if st.form_submit_button("Record Sale & Print"):
            new_r = pd.DataFrame([[len(df)+1, d, "Income", item, cust, vno, amt, qty, 0, 0, stat]], columns=df.columns)
            df = pd.concat([df, new_r], ignore_index=True)
            df.to_csv(DATA_FILE, index=False)
            st.success("Sale Recorded!")

# --- 3. WASHING ---
elif choice == "🚿 Washing & Production":
    st.subheader("Soil Washing & Sand Production")
    with st.form("wash_f", clear_on_submit=True):
        d = st.date_input("Date")
        s_in = st.number_input("Soil Cubes Used (හේදු පස් ප්‍රමාණය)", min_value=0.0)
        s_out = st.number_input("Sand Cubes Produced (ලැබුණු වැලි ප්‍රමාණය)", min_value=0.0)
        if st.form_submit_button("Update Stock"):
            r1 = pd.DataFrame([[len(df)+1, d, "Process", "Washing (Input)", "Plant", "Wash In", 0, s_in, 0, 0, "Done"]], columns=df.columns)
            r2 = pd.DataFrame([[len(df)+2, d, "Process", "Washing (Output)", "Plant", "Sand Out", 0, s_out, 0, 0, "Done"]], columns=df.columns)
            df = pd.concat([df, r1, r2], ignore_index=True)
            df.to_csv(DATA_FILE, index=False)
            st.success("Inventory Updated!")

# --- 4. FUEL ANALYTICS ---
elif choice == "⛽ Fuel Analytics":
    st.subheader("Fuel Consumption Reports")
    col1, col2, col3 = st.columns(3)
    v_list = ve_db["No"].tolist()
    sel_v = col1.selectbox("Select Vehicle", ["All"] + v_list)
    f_date = col2.date_input("From", datetime.now().date() - timedelta(days=30))
    t_date = col3.date_input("To", datetime.now().date())
    
    fuel_df = df[(df["Category"] == "Fuel Entry") & (df["Date"] >= f_date) & (df["Date"] <= t_date)]
    if sel_v != "All": fuel_df = fuel_df[fuel_df["Entity"] == sel_v]
    
    st.metric(f"Total Fuel for {sel_v}", f"{fuel_df['Fuel_Ltr'].sum():,.2f} Liters")
    st.dataframe(fuel_df[["Date", "Entity", "Fuel_Ltr", "Amount", "Note"]], use_container_width=True)

# --- 5. FLEET & WORK ENTRY ---
elif choice == "🚜 Fleet & Work Entry":
    st.subheader("Record Fuel & Machine Work")
    with st.form("fleet_f", clear_on_submit=True):
        d = st.date_input("Date")
        v_no = st.selectbox("Vehicle/Machine No", ve_db["No"].tolist())
        cat = st.selectbox("Record Type", ["Fuel Entry", "Work Entry", "Maintenance"])
        fl = st.number_input("Fuel Liters", min_value=0.0)
        hrs = st.number_input("Hours Worked (Excavator)", min_value=0.0)
        cbs = st.number_input("Cubes Transported (Lorry)", min_value=0.0)
        amt = st.number_input("Cost / Amount (Rs.)", min_value=0.0)
        if st.form_submit_button("Save Record"):
            new_r = pd.DataFrame([[len(df)+1, d, "Expense", cat, v_no, "", amt, cbs, fl, hrs, "Paid"]], columns=df.columns)
            df = pd.concat([df, new_r], ignore_index=True)
            df.to_csv(DATA_FILE, index=False)
            st.success("Record Saved!")

# --- 6. EXPENSES & ADVANCES (FIXED SECTION) ---
elif choice == "💸 Expenses & Advances":
    st.subheader("Payments & General Expenses")
    with st.form("exp_f", clear_on_submit=True):
        d = st.date_input("Date")
        cat = st.selectbox("Category", ["Soil Purchase", "Salary", "Advance", "Food", "Office", "Repair", "Other"])
        ent = st.text_input("Name/Entity (Paid To)")
        
        # Quantity condition - highlight only if Soil Purchase
        qty = 0.0
        if cat == "Soil Purchase":
            qty = st.number_input("Quantity (Cubes)", min_value=0.0, help="Stock එකට එකතු වෙන්න මෙතන කියුබ් ගණන දාන්න.")
        
        amt = st.number_input("Total Amount (Rs.)", min_value=0.0)
        note = st.text_area("Note (Optional)")
        
        if st.form_submit_button("Save Expense"):
            new_r = pd.DataFrame([[len(df)+1, d, "Expense", cat, ent, note, amt, qty, 0, 0, "Paid"]], columns=df.columns)
            df = pd.concat([df, new_r], ignore_index=True)
            df.to_csv(DATA_FILE, index=False)
            st.success(f"Record added: {cat}")

# --- 7. REPORTS ---
elif choice == "📑 Full Reports":
    st.subheader("Master Data Log")
    st.dataframe(df, use_container_width=True)
    st.download_button("Download CSV Backup", df.to_csv(index=False), "KSD_Full_Backup.csv")

# --- 8. SETUP ---
elif choice == "🛠️ System Setup":
    st.subheader("Vehicle & Machine Registration")
    with st.form("v_reg", clear_on_submit=True):
        v_no = st.text_input("No")
        v_ty = st.selectbox("Type", ["Lorry", "Excavator", "Machine"])
        v_ow = st.text_input("Owner Name")
        if st.form_submit_button("Register"):
            new_v = pd.DataFrame([[v_no, v_ty, v_ow]], columns=ve_db.columns)
            ve_db = pd.concat([ve_db, new_v], ignore_index=True)
            ve_db.to_csv(VE_FILE, index=False)
            st.rerun()
    st.table(ve_db)
