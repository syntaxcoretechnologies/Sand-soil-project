import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta

# --- CONFIG & FILENAMES ---
DATA_FILE = "ksd_main_v10.csv"
VE_FILE = "ksd_vehicles_v10.csv"
DR_FILE = "ksd_drivers_v10.csv"
SHOP_NAME = "🏗️ K. SIRIWARDHANA SAND CONSTRUCTION PRO"

def load_data(file, cols):
    if os.path.exists(file): 
        d = pd.read_csv(file)
        if 'Date' in d.columns:
            d['Date'] = pd.to_datetime(d['Date']).dt.date
        return d
    return pd.DataFrame(columns=cols)

# --- UI SETUP ---
st.set_page_config(page_title=SHOP_NAME, layout="wide")
st.markdown(f"<h1 style='text-align: center; color: #E67E22;'>{SHOP_NAME}</h1>", unsafe_allow_html=True)

# Load Databases
df = load_data(DATA_FILE, ["ID", "Date", "Time", "Type", "Category", "Entity", "Note", "Amount", "Qty_Cubes", "Fuel_Ltr", "Hours", "Status"])
ve_db = load_data(VE_FILE, ["No", "Type", "Owner", "Current_Driver"])
dr_db = load_data(DR_FILE, ["Name", "Phone", "Daily_Salary"])

# --- SIDEBAR ---
menu = ["📊 Dashboard", "👷 Driver Setup", "🚜 Vehicle Setup", "⛽ Fuel Tracking", "🚚 Stock In (Soil)", "💰 Sales Out (Sand/Soil)", "💸 Driver Payroll", "🚜 Machine Performance"]
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
    st.write("### Registered Drivers")
    st.table(dr_db)

# --- 2. VEHICLE SETUP ---
elif choice == "🚜 Vehicle Setup":
    st.subheader("Manage Fleet")
    if dr_db.empty:
        st.warning("⚠️ Please add at least one Driver first!")
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
                st.success("Vehicle Registered & Assigned!")
                st.rerun()
        st.write("### Current Fleet")
        st.dataframe(ve_db, use_container_width=True)

# --- 3. FUEL TRACKING ---
elif choice == "⛽ Fuel Tracking":
    st.subheader("Fuel Consumption Analysis")
    if ve_db.empty:
        st.warning("Register vehicles first!")
    else:
        col1, col2, col3 = st.columns(3)
        sel_v = col1.selectbox("Filter Vehicle", ["All"] + ve_db["No"].tolist())
        f_date = col2.date_input("From", datetime.now().date() - timedelta(days=30))
        t_date = col3.date_input("To", datetime.now().date())
        
        fuel_df = df[(df["Category"] == "Fuel Entry") & (df["Date"] >= f_date) & (df["Date"] <= t_date)]
        if sel_v != "All": fuel_df = fuel_df[fuel_df["Entity"] == sel_v]
        
        st.metric("Total Fuel Expense", f"Rs. {fuel_df['Amount'].sum():,.2f}")
        st.dataframe(fuel_df[["Date", "Entity", "Fuel_Ltr", "Amount"]], use_container_width=True)

        with st.expander("Add Fuel"):
            with st.form("fuel_f", clear_on_submit=True):
                d = st.date_input("Date")
                v = st.selectbox("Vehicle", ve_db["No"].tolist())
                ltr = st.number_input("Liters", min_value=0.0)
                cost = st.number_input("Cost (Rs.)", min_value=0.0)
                if st.form_submit_button("Save"):
                    new_r = pd.DataFrame([[len(df)+1, d, "", "Expense", "Fuel Entry", v, "Fuel", cost, 0, ltr, 0, "Paid"]], columns=df.columns)
                    df = pd.concat([df, new_r], ignore_index=True)
                    df.to_csv(DATA_FILE, index=False)
                    st.success("Recorded!")
                    st.rerun()

# --- 4. STOCK IN (SOIL) ---
elif choice == "🚚 Stock In (Soil)":
    st.subheader("Raw Soil (Pas) Plant In")
    col1, col2 = st.columns(2)
    f_date = col1.date_input("From Date", datetime.now().date() - timedelta(days=7))
    t_date = col2.date_input("To Date", datetime.now().date())
    
    soil_in = df[(df["Category"] == "Soil In") & (df["Date"] >= f_date) & (df["Date"] <= t_date)]
    st.metric("Total Cubes In", f"{soil_in['Qty_Cubes'].sum()}")
    st.dataframe(soil_in[["Date", "Entity", "Qty_Cubes"]], use_container_width=True)

    with st.expander("New Soil Entry"):
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
    st.subheader("Sales History & Time Tracking")
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
                st.success("Recorded!")
                st.rerun()

# --- 6. DRIVER PAYROLL ---
elif choice == "💸 Driver Payroll":
    st.subheader("Salary & Advance Tracker")
    if dr_db.empty:
        st.warning("No drivers registered!")
    else:
        sel_dr = st.selectbox("Select Driver", dr_db["Name"].tolist())
        dr_data = df[df["Entity"] == sel_dr]
        
        advances = dr_data[dr_data["Category"] == "Advance"]["Amount"].sum()
        salaries = dr_data[dr_data["Category"] == "Salary Payment"]["Amount"].sum()
        
        c1, c2 = st.columns(2)
        c1.metric("Advances Taken", f"Rs. {advances:,.2f}")
        c2.metric("Salary Paid", f"Rs. {salaries:,.2f}")
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

# --- 7. MACHINE PERFORMANCE ---
# --- 7. MACHINE PERFORMANCE (SPLIT: EXCAVATOR & LORRY) ---
elif choice == "🚜 Machine Performance":
    st.subheader("Vehicle & Machine Performance Tracking")
    
    if ve_db.empty:
        st.warning("⚠️ Please register vehicles in 'Vehicle Setup' first!")
    else:
        # Creating two tabs for better organization
        tab1, tab2 = st.tabs(["🏗️ Excavator Performance", "🚚 Lorry Performance"])

        # --- TAB 1: EXCAVATOR ---
        with tab1:
            ex_list = ve_db[ve_db["Type"] == "Excavator"]["No"].tolist()
            if not ex_list:
                st.info("No Excavators registered yet.")
            else:
                sel_ex = st.selectbox("Select Excavator", ex_list)
                ex_info = ve_db[ve_db["No"] == sel_ex].iloc[0]
                ex_data = df[df["Entity"] == sel_ex]
                
                col1, col2, col3 = st.columns(3)
                col1.metric("Total Hours Worked", f"{ex_data['Hours'].sum()} hrs")
                col2.metric("Total Fuel Consumed", f"{ex_data[ex_data['Category'] == 'Fuel Entry']['Fuel_Ltr'].sum()} Ltr")
                col3.info(f"Driver: {ex_info['Current_Driver']}")
                
                with st.form("ex_work", clear_on_submit=True):
                    st.write("### Log Excavator Hours")
                    d = st.date_input("Date", key="ex_d")
                    hrs = st.number_input("Hours Worked Today", min_value=0.0)
                    note = st.text_input("Work Site / Note")
                    if st.form_submit_button("Save Excavator Log"):
                        new_r = pd.DataFrame([[len(df)+1, d, "", "Work", "Work Entry", sel_ex, note, 0, 0, 0, hrs, "Done"]], columns=df.columns)
                        df = pd.concat([df, new_r], ignore_index=True)
                        df.to_csv(DATA_FILE, index=False)
                        st.success("Excavator work logged!")
                        st.rerun()

        # --- TAB 2: LORRY ---
        with tab2:
            lorry_list = ve_db[ve_db["Type"] == "Lorry"]["No"].tolist()
            if not lorry_list:
                st.info("No Lorries registered yet.")
            else:
                sel_lr = st.selectbox("Select Lorry", lorry_list)
                lr_info = ve_db[ve_db["No"] == sel_lr].iloc[0]
                lr_data = df[df["Entity"] == sel_lr]
                
                col1, col2, col3 = st.columns(3)
                col1.metric("Total Cubes Transported", f"{lr_data['Qty_Cubes'].sum()} Cubes")
                col2.metric("Total Trips", f"{len(lr_data[lr_data['Qty_Cubes'] > 0])}")
                col3.info(f"Driver: {lr_info['Current_Driver']}")
                
                with st.form("lr_work", clear_on_submit=True):
                    st.write("### Log Lorry Cubes")
                    d = st.date_input("Date", key="lr_d")
                    cbs = st.number_input("Cubes Transported Today", min_value=0.0)
                    note = st.text_input("Route / Customer")
                    if st.form_submit_button("Save Lorry Log"):
                        new_r = pd.DataFrame([[len(df)+1, d, "", "Work", "Work Entry", sel_lr, note, 0, cbs, 0, 0, "Done"]], columns=df.columns)
                        df = pd.concat([df, new_r], ignore_index=True)
                        df.to_csv(DATA_FILE, index=False)
                        st.success("Lorry work logged!")
                        st.rerun()

# --- 8. DASHBOARD ---
elif choice == "📊 Dashboard":
    st.subheader("Business Summary")
    inc = df[df["Type"] == "Income"]["Amount"].sum()
    exp = df[df["Type"] == "Expense"]["Amount"].sum()
    st.columns(3)[0].metric("Net Profit", f"Rs. {inc-exp:,.2f}")
    if not df.empty:
        st.bar_chart(df.groupby("Date")["Amount"].sum())
