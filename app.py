import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from fpdf import FPDF
from streamlit_gsheets import GSheetsConnection

# --- 1. CONFIGURATION ---
SHOP_NAME = "K. SIRIWARDHANA SAND CONSTRUCTION PRO"
# ඔයාගේ Sheet ID එක මෙතනට දාන්න
SHEET_ID = "1fXwWem_GNXEmvPwzmRifCDNLRg6w-rYsrWZ0GpemN_U"
SHEET_URL = f"https://docs.google.com/spreadsheets/d/1fXwWem_GNXEmvPwzmRifCDNLRg6w-rYsrWZ0GpemN_U/"

# --- FIXED HEADERS (Table Structure) ---
TX_COLS = ["ID", "Date", "Time", "Type", "Category", "Entity", "Note", "Amount", "Qty_Cubes", "Fuel_Ltr", "Hours", "Status"]
VE_COLS = ["No", "Type", "Owner", "Current_Driver"]
DR_COLS = ["Name", "Phone", "Daily_Salary"]

# --- 2. DATA ENGINE (READ/WRITE) ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_gsheet_data(worksheet_name, default_cols):
    try:
        # Stable CSV Read Method (Prevents 400 Errors)
        csv_url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={worksheet_name}"
        df = pd.read_csv(csv_url)
        df = df.dropna(how='all')
        if df.empty:
            return pd.DataFrame(columns=default_cols)
        return df
    except:
        return pd.DataFrame(columns=default_cols)

def save_to_gsheet(df, worksheet_name):
    try:
        conn.update(spreadsheet=SHEET_URL, worksheet=worksheet_name, data=df)
        st.cache_data.clear()
        st.success(f"✅ Data Synced to {worksheet_name}!")
    except Exception as e:
        st.error(f"❌ Cloud Sync Failed: {e}")

# --- 3. SESSION STATE INITIALIZATION ---
if 'df' not in st.session_state:
    st.session_state.df = load_gsheet_data("Transactions", TX_COLS)
if 've_db' not in st.session_state:
    st.session_state.ve_db = load_gsheet_data("Vehicles", VE_COLS)
if 'dr_db' not in st.session_state:
    st.session_state.dr_db = load_gsheet_data("Drivers", DR_COLS)

# --- 4. PDF REPORT GENERATOR ---
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.set_text_color(230, 126, 34) 
        self.cell(0, 10, SHOP_NAME, 0, 1, 'C')
        self.ln(10)

def create_pdf(title, data_df, summary_dict):
    pdf = PDF(); pdf.add_page(); pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, f"STATEMENT: {title.upper()}", 1, 1, 'L')
    for k, v in summary_dict.items():
        pdf.set_font("Arial", 'B', 10); pdf.cell(60, 8, f"{k}:", 1); pdf.set_font("Arial", '', 10); pdf.cell(0, 8, f" {v}", 1, 1)
    pdf.ln(10); pdf.set_font("Arial", 'B', 9)
    cols = ["Date", "Category", "Note", "Amount"]
    for c in cols: pdf.cell(47, 8, c, 1, 0, 'C')
    pdf.ln(); pdf.set_text_color(0, 0, 0); pdf.set_font("Arial", '', 8)
    for _, row in data_df.iterrows():
        pdf.cell(47, 7, str(row['Date']), 1); pdf.cell(47, 7, str(row['Category']), 1); 
        pdf.cell(47, 7, str(row['Note'])[:25], 1); 
        amt = float(row['Amount']) if not pd.isna(row['Amount']) else 0.0
        pdf.cell(47, 7, f"{amt:,.2f}", 1, 0, 'R'); pdf.ln()
    fname = f"Report_{datetime.now().strftime('%H%M%S')}.pdf"
    pdf.output(fname); return fname

# --- 5. UI LAYOUT ---
st.set_page_config(page_title=SHOP_NAME, layout="wide", page_icon="🏗️")
st.sidebar.title("🛠️ KSD CLOUD v6.0")
menu = st.sidebar.selectbox("MAIN MENU", ["📊 Dashboard", "🏗️ Site Operations", "💰 Finance & Shed", "⚙️ System Setup", "📑 Reports Center"])

st.markdown(f"<h1 style='text-align: center; color: #E67E22;'>{menu}</h1>", unsafe_allow_html=True)

# --- 6. SECTOR: DASHBOARD ---
if menu == "📊 Dashboard":
    df = st.session_state.df
    if not df.empty:
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce').fillna(0)
        ti = df[df["Type"] == "Income"]["Amount"].sum()
        te = df[df["Type"] == "Expense"]["Amount"].sum()
        f_debt = df[df["Category"] == "Fuel Entry"]["Amount"].sum() - df[df["Category"] == "Shed Payment"]["Amount"].sum()
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Income", f"Rs. {ti:,.2f}")
        m2.metric("Total Expenses", f"Rs. {te:,.2f}")
        m3.metric("Net Profit", f"Rs. {ti-te:,.2f}")
        m4.metric("Shed Debt", f"Rs. {f_debt:,.2f}", delta_color="inverse")
        
        st.divider()
        st.subheader("Cloud History (Recent 15)")
        for i, row in df.iloc[::-1].head(15).iterrows():
            c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
            c1.write(f"**{row['Date']}** | {row['Category']} ({row['Entity']})")
            c2.write(f"Rs. {float(row['Amount']):,.2f}")
            c3.write(f"*{row['Note']}*")
            if c4.button("🗑️", key=f"del_{i}"):
                st.session_state.df = st.session_state.df.drop(i)
                save_to_gsheet(st.session_state.df, "Transactions"); st.rerun()
    else:
        st.info("No data found in the cloud. Add transactions to see them here.")

# --- 7. SECTOR: SITE OPERATIONS ---
elif menu == "🏗️ Site Operations":
    op = st.sidebar.radio("Activity", ["🚚 Stock In (Soil)", "💰 Sales Out (Sand/Soil)", "🚜 Machine Performance"])
    with st.form("site_form", clear_on_submit=True):
        d = st.date_input("Date")
        if op == "🚚 Stock In (Soil)":
            v = st.text_input("Supplier / Lorry No"); q = st.number_input("Cubes (Qty)")
            if st.form_submit_button("Log Inbound"):
                new = pd.DataFrame([[len(st.session_state.df)+1, str(d), "", "Process", "Soil In", v, "Inbound", 0, q, 0, 0, "Done"]], columns=TX_COLS)
                st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True)
                save_to_gsheet(st.session_state.df, "Transactions"); st.rerun()
        
        elif op == "💰 Sales Out (Sand/Soil)":
            it = st.selectbox("Item Type", ["Sand Sale", "Soil Sale"]); q = st.number_input("Cubes"); a = st.number_input("Total Bill (Rs.)")
            if st.form_submit_button("Record Sale"):
                new = pd.DataFrame([[len(st.session_state.df)+1, str(d), "", "Income", it, "Cash", "Sale Out", a, q, 0, 0, "Paid"]], columns=TX_COLS)
                st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True)
                save_to_gsheet(st.session_state.df, "Transactions"); st.rerun()
        
        elif op == "🚜 Machine Performance":
            ve_list = st.session_state.ve_db["No"].tolist() if not st.session_state.ve_db.empty else ["Add Machines First"]
            sel = st.selectbox("Select Machine", ve_list); h = st.number_input("Hours Worked"); am = st.number_input("Operational Cost"); nt = st.text_input("Project Note")
            if st.form_submit_button("Save Performance Log"):
                new = pd.DataFrame([[len(st.session_state.df)+1, str(d), "", "Expense", "Machine Work", sel, nt, am, 0, 0, h, "Done"]], columns=TX_COLS)
                st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True)
                save_to_gsheet(st.session_state.df, "Transactions"); st.rerun()

# --- 8. SECTOR: FINANCE & SHED ---
elif menu == "💰 Finance & Shed":
    fin = st.sidebar.radio("Finance", ["⛽ Fuel Entry", "🔧 Repair Bills", "💸 Driver Payroll", "🧾 Other Expenses"])
    with st.form("fin_form", clear_on_submit=True):
        d = st.date_input("Date")
        if fin == "⛽ Fuel Entry":
            v = st.selectbox("Vehicle", st.session_state.ve_db["No"].tolist() if not st.session_state.ve_db.empty else ["None"])
            l = st.number_input("Liters"); c = st.number_input("Bill Cost"); s = st.text_input("Shed Name")
            if st.form_submit_button("Save Fuel Ticket"):
                new = pd.DataFrame([[len(st.session_state.df)+1, str(d), "", "Expense", "Fuel Entry", v, f"Shed: {s}", c, 0, l, 0, "Pending"]], columns=TX_COLS)
                st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True)
                save_to_gsheet(st.session_state.df, "Transactions"); st.rerun()

        elif fin == "🔧 Repair Bills":
            v = st.selectbox("Vehicle", st.session_state.ve_db["No"].tolist() if not st.session_state.ve_db.empty else ["None"])
            n = st.text_input("Repair Details"); a = st.number_input("Cost")
            if st.form_submit_button("Save Repair Bill"):
                new = pd.DataFrame([[len(st.session_state.df)+1, str(d), "", "Expense", "Repair", v, n, a, 0, 0, 0, "Paid"]], columns=TX_COLS)
                st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True)
                save_to_gsheet(st.session_state.df, "Transactions"); st.rerun()

        elif fin == "💸 Driver Payroll":
            dr = st.selectbox("Driver", st.session_state.dr_db["Name"].tolist() if not st.session_state.dr_db.empty else ["None"])
            ty = st.selectbox("Payment Type", ["Salary", "Advance", "Food Allowance"]); am = st.number_input("Amount")
            if st.form_submit_button("Save Payroll Entry"):
                new = pd.DataFrame([[len(st.session_state.df)+1, str(d), "", "Expense", ty, dr, "Payroll", am, 0, 0, 0, "Paid"]], columns=TX_COLS)
                st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True)
                save_to_gsheet(st.session_state.df, "Transactions"); st.rerun()

        elif fin == "🧾 Other Expenses":
            cat = st.selectbox("Category", ["Food", "Yard Rent", "Utility", "Misc"]); nt = st.text_area("Note"); am = st.number_input("Amount")
            if st.form_submit_button("Record General Expense"):
                new = pd.DataFrame([[len(st.session_state.df)+1, str(d), "", "Expense", cat, "Yard Admin", nt, am, 0, 0, 0, "Paid"]], columns=TX_COLS)
                st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True)
                save_to_gsheet(st.session_state.df, "Transactions"); st.rerun()

# --- 9. SECTOR: SYSTEM SETUP ---
elif menu == "⚙️ System Setup":
    t1, t2 = st.tabs(["👷 Drivers Manager", "🚜 Fleet Manager"])
    with t1:
        with st.form("dr_add", clear_on_submit=True):
            n = st.text_input("Full Name"); p = st.text_input("Phone Number"); s = st.number_input("Daily Rate")
            if st.form_submit_button("Add Driver"):
                new_dr = pd.DataFrame([[n, p, s]], columns=DR_COLS)
                st.session_state.dr_db = pd.concat([st.session_state.dr_db, new_dr], ignore_index=True)
                save_to_gsheet(st.session_state.dr_db, "Drivers"); st.rerun()
        st.dataframe(st.session_state.dr_db, use_container_width=True)
        for i, r in st.session_state.dr_db.iterrows():
            if st.button(f"🗑️ Delete Driver: {r['Name']}", key=f"dr_{i}"):
                st.session_state.dr_db = st.session_state.dr_db.drop(i)
                save_to_gsheet(st.session_state.dr_db, "Drivers"); st.rerun()

    with t2:
        with st.form("ve_add", clear_on_submit=True):
            no = st.text_input("Vehicle No"); ty = st.selectbox("Type", ["Lorry", "Excavator", "JCB", "Tractor"]); ow = st.text_input("Owner")
            if st.form_submit_button("Add Vehicle"):
                new_ve = pd.DataFrame([[no, ty, ow, ""]], columns=VE_COLS)
                st.session_state.ve_db = pd.concat([st.session_state.ve_db, new_ve], ignore_index=True)
                save_to_gsheet(st.session_state.ve_db, "Vehicles"); st.rerun()
        st.dataframe(st.session_state.ve_db, use_container_width=True)
        for i, r in st.session_state.ve_db.iterrows():
            if st.button(f"🗑️ Delete Vehicle: {r['No']}", key=f"ve_{i}"):
                st.session_state.ve_db = st.session_state.ve_db.drop(i)
                save_to_gsheet(st.session_state.ve_db, "Vehicles"); st.rerun()

# --- 10. SECTOR: REPORTS ---
elif menu == "📑 Reports Center":
    st.subheader("Cloud Data Explorer")
    start = st.date_input("From", datetime.now().date() - timedelta(days=30))
    end = st.date_input("To", datetime.now().date())
    
    # Filter Logic
    filtered = st.session_state.df[(st.session_state.df['Date'] >= str(start)) & (st.session_state.df['Date'] <= str(end))]
    st.dataframe(filtered, use_container_width=True)
    
    if st.button("Generate Detailed PDF"):
        fn = create_pdf("Usage_Report", filtered, {"Status": "Cloud Generated", "Range": f"{start} to {end}"})
        with open(fn, "rb") as fl:
            st.download_button("📩 Download PDF Report", fl, file_name=fn)
