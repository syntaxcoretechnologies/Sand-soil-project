import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
from fpdf import FPDF

# --- CONFIG & FILENAMES ---
DATA_FILE = "ksd_master_v14.csv"
VE_FILE = "ksd_vehicles_v14.csv"
DR_FILE = "ksd_drivers_v14.csv"
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

# --- 🚀 EXPANDED SIDEBAR MENU ---
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/4300/4300058.png", width=100)
st.sidebar.title("KSD NAVIGATION")

# Step 1: Main Category
main_mode = st.sidebar.radio("SELECT SECTOR", ["📊 Dashboard", "⚙️ Management", "🏗️ Operations", "📑 Reporting"])

# Step 2: Sub Category logic
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
    c3.metric("Net Profit", f"Rs. {inc-exp:,.2f}", delta=f"{inc-exp:,.0f}")
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

# --- 4. FUEL TRACKING ---
elif choice == "⛽ Fuel Tracking":
    with st.form("fuel_f", clear_on_submit=True):
        d = st.date_input("Date"); v = st.selectbox("Vehicle", ve_db["No"].tolist() if not ve_db.empty else ["No Vehicles"])
        l = st.number_input("Liters"); c = st.number_input("Cost")
        if st.form_submit_button("Record Fuel"):
            new = pd.DataFrame([[len(df)+1, d, "", "Expense", "Fuel Entry", v, "Fuel", c, 0, l, 0, "Paid"]], columns=df.columns)
            df = pd.concat([df, new], ignore_index=True); df.to_csv(DATA_FILE, index=False); st.success("Saved!"); st.rerun()

# --- 5. STOCK IN ---
elif choice == "🚚 Stock In (Soil)":
    with
