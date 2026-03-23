import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from fpdf import FPDF
from streamlit_gsheets import GSheetsConnection

# --- CONFIG ---
SHOP_NAME = "K. SIRIWARDHANA SAND CONSTRUCTION PRO"
# Meka Secrets wala danna puluwan, nathnam meke ' ' athulata sheet link eka danna.
SHEET_URL = "https://docs.google.com/spreadsheets/d/1fXwWem_GNXEmvPwzmRifCDNLRg6w-rYsrWZ0GpemN_U/edit?usp=sharing" 

# --- INITIALIZE CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- HELPER FUNCTIONS ---
def load_gsheet_data(worksheet_name):
    try:
        df = conn.read(spreadsheet=SHEET_URL, worksheet=worksheet_name)
        return df.dropna(how='all')
    except:
        return pd.DataFrame()

def save_to_gsheet(df, worksheet_name):
    conn.update(spreadsheet=SHEET_URL, worksheet=worksheet_name, data=df)
    st.cache_data.clear()

# --- LOAD DATA INTO SESSION STATE ---
if 'df' not in st.session_state:
    st.session_state.df = load_gsheet_data("Transactions")
if 've_db' not in st.session_state:
    st.session_state.ve_db = load_gsheet_data("Vehicles")
if 'dr_db' not in st.session_state:
    st.session_state.dr_db = load_gsheet_data("Drivers")

# --- PDF GENERATOR ---
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
        pdf.cell(47, 7, str(row['Note'])[:20], 1); 
        amt = float(row['Amount']) if row['Amount'] else 0.0
        pdf.cell(47, 7, f"{amt:,.2f}", 1, 0, 'R'); pdf.ln()
    fname = f"Report_{datetime.now().strftime('%H%M%S')}.pdf"
    pdf.output(fname); return fname

# --- UI SETUP ---
st.set_page_config(page_title=SHOP_NAME, layout="wide")
st.sidebar.title("🛠️ KSD CLOUD ERP v5.0")
main_sector = st.sidebar.selectbox("MAIN MENU", ["📊 Dashboard & Data Manager", "🏗️ Site Operations", "💰 Finance & Shed", "⚙️ System Setup", "📑 Reports Center"])

st.markdown(f"<h1 style='text-align: center; color: #E67E22;'>{main_sector}</h1>", unsafe_allow_html=True)

# --- 1. DASHBOARD ---
if main_sector == "📊 Dashboard & Data Manager":
    t1, t2 = st.tabs(["📈 Business Analytics", "🛠️ Manage Transactions"])
    with t1:
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
            if len(df) > 1:
                st.write("### Monthly Cashflow Trend")
                st.line_chart(df.groupby('Date')['Amount'].sum())

    with t2:
        st.subheader("Cloud Transaction History (Recent 20)")
        if not st.session_state.df.empty:
            for i, row in st.session_state.df.iloc[::-1].head(20).iterrows():
                c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
                c1.write(f"**{row['Date']}** | {row['Category']}")
                c2.write(f"Rs. {float(row['Amount']):,.2f}")
                c3.write(f"Note: {row['Note']}")
                if c4.button("🗑️", key=f"del_{i}"):
                    st.session_state.df = st.session_state.df.drop(i)
                    save_to_gsheet(st.session_state.df, "Transactions"); st.rerun()

# --- 2. SITE OPERATIONS ---
elif main_sector == "🏗️ Site Operations":
    op = st.sidebar.radio("Activity", ["🚚 Stock In (Soil)", "💰 Sales Out (Sand/Soil)", "🚜 Machine Work Logs"])
    with st.form("site_form", clear_on_submit=True):
        d = st.date_input("Date")
        if op == "🚚 Stock In (Soil)":
            v = st.text_input("Supplier/Vehicle No"); q = st.number_input("Quantity (Cubes)")
            if st.form_submit_button("Record Inbound Stock"):
                new_row = pd.DataFrame([[len(st.session_state.df)+1, str(d), "", "Process", "Soil In", v, "Inbound", 0, q, 0, 0, "Done"]], columns=st.session_state.df.columns)
                st.session_state.df = pd.concat([st.session_state.df, new_row], ignore_index=True)
                save_to_gsheet(st.session_state.df, "Transactions"); st.success("Synced to Cloud!"); st.rerun()

        elif op == "💰 Sales Out (Sand/Soil)":
            it = st.selectbox("Item Type", ["Sand Sale", "Soil Sale"]); q = st.number_input("Cubes Sold"); a = st.number_input("Total Amount (Rs.)")
            if st.form_submit_button("Record Sale"):
                new_row = pd.DataFrame([[len(st.session_state.df)+1, str(d), "", "Income", it, "Cash Sale", "Sold", a, q, 0, 0, "Paid"]], columns=st.session_state.df.columns)
                st.session_state.df = pd.concat([st.session_state.df, new_row], ignore_index=True)
                save_to_gsheet(st.session_state.df, "Transactions"); st.success("Sale Recorded!"); st.rerun()

        elif op == "🚜 Machine Work Logs":
            ve_list = st.session_state.ve_db["No"].tolist() if not st.session_state.ve_db.empty else ["None"]
            sel = st.selectbox("Select Machine/Lorry", ve_list); h = st.number_input("Work Hours / Cubes"); am = st.number_input("Operational Cost"); nt = st.text_input("Project Details")
            if st.form_submit_button("Log Machine Performance"):
                new_row = pd.DataFrame([[len(st.session_state.df)+1, str(d), "", "Expense", "Machine Work", sel, nt, am, 0, 0, h, "Done"]], columns=st.session_state.df.columns)
                st.session_state.df = pd.concat([st.session_state.df, new_row], ignore_index=True)
                save_to_gsheet(st.session_state.df, "Transactions"); st.success("Log Saved!"); st.rerun()

# --- 3. FINANCE & SHED ---
elif main_sector == "💰 Finance & Shed":
    fin = st.sidebar.radio("Finance Category", ["⛽ Fuel & Shed", "🔧 Vehicle Repairs", "💸 Driver Payroll", "🧾 Other Expenses"])
    with st.form("fin_form", clear_on_submit=True):
        d = st.date_input("Date")
        if fin == "⛽ Fuel & Shed":
            v = st.selectbox("Vehicle", st.session_state.ve_db["No"].tolist() if not st.session_state.ve_db.empty else ["None"])
            l = st.number_input("Liters"); c = st.number_input("Bill Cost (Credit)"); s = st.text_input("Shed Name")
            if st.form_submit_button("Save Fuel Entry"):
                new_row = pd.DataFrame([[len(st.session_state.df)+1, str(d), "", "Expense", "Fuel Entry", v, f"Shed: {s}", c, 0, l, 0, "Pending"]], columns=st.session_state.df.columns)
                st.session_state.df = pd.concat([st.session_state.df, new_row], ignore_index=True)
                save_to_gsheet(st.session_state.df, "Transactions"); st.rerun()

        elif fin == "🔧 Vehicle Repairs":
            v = st.selectbox("Vehicle", st.session_state.ve_db["No"].tolist() if not st.session_state.ve_db.empty else ["None"])
            n = st.text_input("Repair Detail (e.g., Tyre Change)"); a = st.number_input("Repair Cost")
            if st.form_submit_button("Save Repair"):
                new_row = pd.DataFrame([[len(st.session_state.df)+1, str(d), "", "Expense", "Repair", v, n, a, 0, 0, 0, "Paid"]], columns=st.session_state.df.columns)
                st.session_state.df = pd.concat([st.session_state.df, new_row], ignore_index=True)
                save_to_gsheet(st.session_state.df, "Transactions"); st.rerun()

        elif fin == "💸 Driver Payroll":
            dr = st.selectbox("Driver", st.session_state.dr_db["Name"].tolist() if not st.session_state.dr_db.empty else ["None"])
            ty = st.selectbox("Type", ["Salary", "Advance"]); am = st.number_input("Amount")
            if st.form_submit_button("Save Payroll"):
                new_row = pd.DataFrame([[len(st.session_state.df)+1, str(d), "", "Expense", ty, dr, "Payroll", am, 0, 0, 0, "Paid"]], columns=st.session_state.df.columns)
                st.session_state.df = pd.concat([st.session_state.df, new_row], ignore_index=True)
                save_to_gsheet(st.session_state.df, "Transactions"); st.rerun()

        elif fin == "🧾 Other Expenses":
            cat = st.selectbox("Expense Category", ["Food", "Rent", "Utility", "Maintenance", "Misc"]); n = st.text_area("Note"); a = st.number_input("Amount")
            if st.form_submit_button("Record General Expense"):
                new_row = pd.DataFrame([[len(st.session_state.df)+1, str(d), "", "Expense", cat, "Admin", n, a, 0, 0, 0, "Paid"]], columns=st.session_state.df.columns)
                st.session_state.df = pd.concat([st.session_state.df, new_row], ignore_index=True)
                save_to_gsheet(st.session_state.df, "Transactions"); st.rerun()

# --- 4. SYSTEM SETUP ---
elif main_sector == "⚙️ System Setup":
    s1, s2 = st.tabs(["👷 Drivers Manager", "🚜 Fleet Manager"])
    with s1:
        with st.form("dr_add", clear_on_submit=True):
            n = st.text_input("Name"); p = st.text_input("Phone"); sl = st.number_input("Daily Salary Rate")
            if st.form_submit_button("Register Driver"):
                new_dr = pd.DataFrame([[n, p, sl]], columns=st.session_state.dr_db.columns)
                st.session_state.dr_db = pd.concat([st.session_state.dr_db, new_dr], ignore_index=True)
                save_to_gsheet(st.session_state.dr_db, "Drivers"); st.rerun()
        st.write("### Active Drivers")
        st.table(st.session_state.dr_db)
        for i, r in st.session_state.dr_db.iterrows():
            if st.button(f"🗑️ Delete {r['Name']}", key=f"drdel_{i}"):
                st.session_state.dr_db = st.session_state.dr_db.drop(i)
                save_to_gsheet(st.session_state.dr_db, "Drivers"); st.rerun()

    with s2:
        with st.form("ve_add", clear_on_submit=True):
            no = st.text_input("Vehicle Plate No"); ty = st.selectbox("Category", ["Lorry", "Excavator", "JCB", "Other"]); ow = st.text_input("Owner Name")
            if st.form_submit_button("Register Vehicle"):
                new_ve = pd.DataFrame([[no, ty, ow, ""]], columns=st.session_state.ve_db.columns)
                st.session_state.ve_db = pd.concat([st.session_state.ve_db, new_ve], ignore_index=True)
                save_to_gsheet(st.session_state.ve_db, "Vehicles"); st.rerun()
        st.write("### Registered Vehicles")
        st.table(st.session_state.ve_db)
        for i, r in st.session_state.ve_db.iterrows():
            if st.button(f"🗑️ Delete {r['No']}", key=f"vedel_{i}"):
                st.session_state.ve_db = st.session_state.ve_db.drop(i)
                save_to_gsheet(st.session_state.ve_db, "Vehicles"); st.rerun()

# --- 5. REPORTS CENTER ---
elif main_sector == "📑 Reports Center":
    st.subheader("Generate Statements")
    f = st.date_input("Start Date", datetime.now().date()-timedelta(days=30)); t = st.date_input("End Date")
    filtered = st.session_state.df[(st.session_state.df['Date'] >= str(f)) & (st.session_state.df['Date'] <= str(t))]
    st.dataframe(filtered, use_container_width=True)
    if st.button("Download PDF Detailed Report"):
        fn = create_pdf("Detailed_Report", filtered, {"Status": "Live Cloud Sync", "Range": f"{f} to {t}"})
        with open(fn, "rb") as fl: st.download_button("📩 Download PDF Now", fl, file_name=fn)
