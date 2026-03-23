import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
from fpdf import FPDF

# --- CONFIG & FILENAMES ---
DATA_FILE = "ksd_master_v28.csv"
VE_FILE = "ksd_vehicles_v28.csv"
DR_FILE = "ksd_drivers_v28.csv"
SHOP_NAME = "K. SIRIWARDHANA SAND CONSTRUCTION PRO"

# --- HELPER FUNCTIONS ---
def load_data(file, cols):
    if os.path.exists(file): 
        d = pd.read_csv(file)
        if 'Date' in d.columns:
            d['Date'] = pd.to_datetime(d['Date']).dt.date
        return d
    return pd.DataFrame(columns=cols)

def save_all():
    st.session_state.df.to_csv(DATA_FILE, index=False)
    st.session_state.ve_db.to_csv(VE_FILE, index=False)
    st.session_state.dr_db.to_csv(DR_FILE, index=False)

# --- INITIALIZE SESSION STATE ---
if 'df' not in st.session_state:
    st.session_state.df = load_data(DATA_FILE, ["ID", "Date", "Time", "Type", "Category", "Entity", "Note", "Amount", "Qty_Cubes", "Fuel_Ltr", "Hours", "Status"])
if 've_db' not in st.session_state:
    st.session_state.ve_db = load_data(VE_FILE, ["No", "Type", "Owner", "Current_Driver"])
if 'dr_db' not in st.session_state:
    st.session_state.dr_db = load_data(DR_FILE, ["Name", "Phone", "Daily_Salary"])

# --- UI SETUP ---
st.set_page_config(page_title=SHOP_NAME, layout="wide")
st.sidebar.title("🛠️ KSD ERP PRO v2.8")

main_sector = st.sidebar.selectbox("MAIN MENU", [
    "📊 Dashboard & Data Manager", 
    "🏗️ Site Operations", 
    "💰 Finance & Shed", 
    "⚙️ System Setup", 
    "📑 Reports Center"
])

# --- 1. DASHBOARD & DATA MANAGER ---
if main_sector == "📊 Dashboard & Data Manager":
    t1, t2 = st.tabs(["📈 Dashboard Analytics", "🛠️ Edit/Delete Transactions"])
    
    with t1:
        df = st.session_state.df
        ti = df[df["Type"] == "Income"]["Amount"].sum()
        te = df[df["Type"] == "Expense"]["Amount"].sum()
        f_bills = df[df["Category"] == "Fuel Entry"]["Amount"].sum()
        f_paid = df[df["Category"] == "Shed Payment"]["Amount"].sum()
        fuel_debt = f_bills - f_paid

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Income", f"Rs. {ti:,.2f}")
        m2.metric("Total Expenses", f"Rs. {te:,.2f}")
        m3.metric("Net Profit", f"Rs. {ti-te:,.2f}")
        m4.metric("Shed Debt (Naya)", f"Rs. {fuel_debt:,.2f}", delta_color="inverse")
        
        st.divider()
        if not df.empty:
            daily = df.groupby(['Date', 'Type'])['Amount'].sum().unstack().fillna(0)
            st.line_chart(daily)

    with t2:
        st.subheader("Recent Transactions (Delete/Manage)")
        if not st.session_state.df.empty:
            # Pennanne anthimata dapu items 20
            temp_df = st.session_state.df.iloc[::-1].head(20)
            for i, row in temp_df.iterrows():
                c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
                c1.write(f"**{row['Date']}** | {row['Category']} ({row['Entity']})")
                c2.write(f"Rs. {row['Amount']:,.2f}")
                c3.write(f"Status: {row['Status']}")
                if c4.button("🗑️", key=f"del_{i}"):
                    st.session_state.df = st.session_state.df.drop(i)
                    save_all(); st.rerun()
        else: st.info("No data available.")

# --- 2. SITE OPERATIONS ---
elif main_sector == "🏗️ Site Operations":
    op = st.sidebar.radio("Activity", ["🚚 Stock In (Soil)", "💰 Sales Out (Sand/Soil)", "🚜 Machine Performance"])
    
    if op == "🚜 Machine Performance":
        with st.form("mach_f", clear_on_submit=True):
            v = st.selectbox("Select Vehicle", st.session_state.ve_db["No"].tolist() if not st.session_state.ve_db.empty else ["None"])
            h = st.number_input("Hours / Cubes", min_value=0.0)
            a = st.number_input("Amount (Income/Cost)", min_value=0.0)
            n = st.text_input("Job/Trip Details")
            if st.form_submit_button("Save Operation Entry"):
                new = pd.DataFrame([[len(st.session_state.df)+1, datetime.now().date(), "", "Expense", "Work", v, n, a, 0, 0, h, "Done"]], columns=st.session_state.df.columns)
                st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.success("Logged!"); st.rerun()

    elif op == "💰 Sales Out (Sand/Soil)":
        with st.form("sale_f"):
            it = st.selectbox("Item", ["Sand Sale", "Soil Sale"]); q = st.number_input("Cubes"); a = st.number_input("Amount")
            if st.form_submit_button("Record Sale"):
                new = pd.DataFrame([[len(st.session_state.df)+1, datetime.now().date(), "", "Income", it, "Cash", "Sale", a, q, 0, 0, "Paid"]], columns=st.session_state.df.columns)
                st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()

# --- 3. FINANCE & SHED ---
elif main_sector == "💰 Finance & Shed":
    fin = st.sidebar.radio("Finance Category", ["⛽ Fuel & Shed Payments", "🔧 Vehicle Repairs", "💸 Driver Payroll", "🧾 Other Expenses"])
    
    if fin == "⛽ Fuel & Shed Payments":
        t1, t2 = st.tabs(["Log Fuel Bill", "Settle Shed Balance"])
        with t1:
            with st.form("f_f", clear_on_submit=True):
                v = st.selectbox("Vehicle", st.session_state.ve_db["No"].tolist()); l = st.number_input("Liters"); c = st.number_input("Cost")
                if st.form_submit_button("Save Credit Bill"):
                    new = pd.DataFrame([[len(st.session_state.df)+1, datetime.now().date(), "", "Expense", "Fuel Entry", v, "Fuel Bill", c, 0, l, 0, "Pending"]], columns=st.session_state.df.columns)
                    st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True); save_all(); st.rerun()
        with t2:
            st.subheader("Shed Settlement")
            p_amt = st.number_input("Amount Paying to Shed", min_value=0.0)
            if st.button("Confirm Payment"):
                new = pd.DataFrame([[len(st.session_state.df)+1, datetime.now().date(), "", "Expense", "Shed Payment", "Shed", "Payment", p_amt, 0, 0, 0, "Paid"]],
