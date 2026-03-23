import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from fpdf import FPDF
from streamlit_gsheets import GSheetsConnection

# --- CONFIG ---
SHOP_NAME = "K. SIRIWARDHANA SAND CONSTRUCTION PRO"
# Secrets wala spreadsheet_url kiyala link eka danna puluwan. 
# Nathnam meke ' ' athulata link eka danna.
SHEET_URL = "https://docs.google.com/spreadsheets/d/1fXwWem_GNXEmvPwzmRifCDNLRg6w-rYsrWZ0GpemN_U/edit?usp=sharing" 

# --- FIXED HEADERS (Fix for ValueError) ---
TX_COLS = ["ID", "Date", "Time", "Type", "Category", "Entity", "Note", "Amount", "Qty_Cubes", "Fuel_Ltr", "Hours", "Status"]
VE_COLS = ["No", "Type", "Owner", "Current_Driver"]
DR_COLS = ["Name", "Phone", "Daily_Salary"]

# --- INITIALIZE CONNECTION ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_gsheet_data(worksheet_name, default_cols):
    try:
        # Spreadsheet eka kiyawanna try karanawa
        df = conn.read(spreadsheet=SHEET_URL, worksheet=worksheet_name)
        df = df.dropna(how='all')
        if df is None or df.empty:
            return pd.DataFrame(columns=default_cols)
        return df
    except Exception as e:
        # Connection eke error ekak thiyenam meke pennanawa
        st.error(f"Error connecting to {worksheet_name}: {e}")
        return pd.DataFrame(columns=default_cols)

# --- LOAD DATA INTO SESSION STATE ---
if 'df' not in st.session_state:
    st.session_state.df = load_gsheet_data("Transactions", TX_COLS)
if 've_db' not in st.session_state:
    st.session_state.ve_db = load_gsheet_data("Vehicles", VE_COLS)
if 'dr_db' not in st.session_state:
    st.session_state.dr_db = load_gsheet_data("Drivers", DR_COLS)

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
        val = float(row['Amount']) if row['Amount'] else 0.0
        pdf.cell(47, 7, f"{val:,.2f}", 1, 0, 'R'); pdf.ln()
    fname = f"Report_{datetime.now().strftime('%H%M%S')}.pdf"
    pdf.output(fname); return fname

# --- UI SETUP ---
st.set_page_config(page_title=SHOP_NAME, layout="wide")
st.sidebar.title("🛠️ KSD CLOUD ERP v5.5")
main_sector = st.sidebar.selectbox("MAIN MENU", ["📊 Dashboard", "🏗️ Site Operations", "💰 Finance & Shed", "⚙️ System Setup", "📑 Reports Center"])

st.markdown(f"<h1 style='text-align: center; color: #E67E22;'>{main_sector}</h1>", unsafe_allow_html=True)

# --- 1. DASHBOARD ---
if main_sector == "📊 Dashboard":
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
        st.subheader("Manage Recent Transactions")
        for i, row in df.iloc[::-1].head(15).iterrows():
            c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
            c1.write(f"**{row['Date']}** | {row['Category']}")
            c2.write(f"Rs. {float(row['Amount']):,.2f}")
            c3.write(f"Note: {row['Note']}")
            if c4.button("🗑️", key=f"del_{i}"):
                st.session_state.df = st.session_state.df.drop(i)
                save_to_gsheet(st.session_state.df, "Transactions"); st.rerun()
    else:
        st.info("No transactions found. Connect your Google Sheet correctly.")

# --- 2. SITE OPERATIONS ---
elif main_sector == "🏗️ Site Operations":
    op = st.sidebar.radio("Activity", ["🚚 Stock In", "💰 Sales Out", "🚜 Machine Work"])
    with st.form("site_form", clear_on_submit=True):
        d = st.date_input("Date")
        if op == "🚚 Stock In":
            v = st.text_input("Supplier/Lorry No"); q = st.number_input("Cubes")
            if st.form_submit_button("Log Inbound"):
                new = pd.DataFrame([[len(st.session_state.df)+1, str(d), "", "Process", "Soil In", v, "Inbound", 0, q, 0, 0, "Done"]], columns=TX_COLS)
                st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True)
                save_to_gsheet(st.session_state.df, "Transactions"); st.rerun()
        elif op == "💰 Sales Out":
            it = st.selectbox("Item", ["Sand Sale", "Soil Sale"]); q = st.number_input("Cubes"); a = st.number_input("Amount")
            if st.form_submit_button("Record Sale"):
                new = pd.DataFrame([[len(st.session_state.df)+1, str(d), "", "Income", it, "Cash", "Sale", a, q, 0, 0, "Paid"]], columns=TX_COLS)
                st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True)
                save_to_gsheet(st.session_state.df, "Transactions"); st.rerun()
        elif op == "🚜 Machine Work":
            ve_list = st.session_state.ve_db["No"].tolist() if not st.session_state.ve_db.empty else ["Add Vehicles"]
            sel = st.selectbox("Machine", ve_list); h = st.number_input("Hours"); am = st.number_input("Cost"); nt = st.text_input("Note")
            if st.form_submit_button("Log Machine Work"):
                new = pd.DataFrame([[len(st.session_state.df)+1, str(d), "", "Expense", "Machine Work", sel, nt, am, 0, 0, h, "Done"]], columns=TX_COLS)
                st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True)
                save_to_gsheet(st.session_state.df, "Transactions"); st.rerun()

# --- 3. FINANCE & SHED ---
elif main_sector == "💰 Finance & Shed":
    fin = st.sidebar.radio("Category", ["⛽ Fuel & Shed", "🔧 Repairs", "💸 Payroll", "🧾 Other Expenses"])
    with st.form("fin_form", clear_on_submit=True):
        d = st.date_input("Date")
        if fin == "⛽ Fuel & Shed":
            v = st.selectbox("Vehicle", st.session_state.ve_db["No"].tolist() if not st.session_state.ve_db.empty else ["None"])
            l = st.number_input("Liters"); c = st.number_input("Bill Cost"); s = st.text_input("Shed Name")
            if st.form_submit_button("Save Fuel Bill"):
                new = pd.DataFrame([[len(st.session_state.df)+1, str(d), "", "Expense", "Fuel Entry", v, f"Shed: {s}", c, 0, l, 0, "Pending"]], columns=TX_COLS)
                st.session_state.df = pd.concat([st.session_state.df, new], ignore_index=True)
                save
