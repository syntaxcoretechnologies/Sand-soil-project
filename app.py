import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
from fpdf import FPDF

# --- CONFIG & FILENAMES ---
DATA_FILE = "ksd_master_v18.csv"
VE_FILE = "ksd_vehicles_v18.csv"
DR_FILE = "ksd_drivers_v18.csv"
SHOP_NAME = "K. SIRIWARDHANA SAND CONSTRUCTION PRO"

# --- HELPER FUNCTIONS ---
def load_data(file, cols):
    if os.path.exists(file): 
        d = pd.read_csv(file)
        if 'Date' in d.columns:
            d['Date'] = pd.to_datetime(d['Date']).dt.date
        return d
    return pd.DataFrame(columns=cols)

# --- PDF GENERATOR ---
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

# --- NAVIGATION ---
st.sidebar.title("KSD NAVIGATION")
main_mode = st.sidebar.radio("SELECT SECTOR", ["📊 Dashboard & Profit", "🏗️ Operations", "💳 Fuel & Shed Payments", "💸 Other Expenses", "⚙️ Management", "📑 Reporting"])

choice = ""
if main_mode == "📊 Dashboard & Profit": choice = "📊 Dashboard"
elif main_mode == "🏗️ Operations": choice = st.sidebar.selectbox("Sub Menu", ["🚚 Stock In (Soil)", "💰 Sales Out", "🚜 Machine Performance", "💸 Driver Payroll", "⛽ Fuel Intake"])
elif main_mode == "💳 Fuel & Shed Payments": choice = "💳 Fuel Credit & Shed"
elif main_mode == "💸 Other Expenses": choice = "💸 Other Expenses"
elif main_mode == "⚙️ Management": choice = st.sidebar.selectbox("Sub Menu", ["👷 Driver Setup", "🚜 Vehicle Setup", "📝 General Notes"])
elif main_mode == "📑 Reporting": choice = "📑 Advanced Reports"

st.markdown(f"<h1 style='text-align: center; color: #E67E22;'>{choice}</h1>", unsafe_allow_html=True)

# --- 1. DASHBOARD & PROFIT ---
if choice == "📊 Dashboard":
    total_income = df[df["Type"] == "Income"]["Amount"].sum()
    total_expenses = df[df["Type"] == "Expense"]["Amount"].sum()
    net_profit = total_income - total_expenses
    fuel_debt = df[(df["Category"] == "Fuel Entry") & (df["Status"] == "Pending")]["Amount"].sum()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Income", f"Rs. {total_income:,.2f}")
    m2.metric("Total Expenses", f"Rs. {total_expenses:,.2f}", delta_color="inverse")
    m3.metric("Net Profit", f"Rs. {net_profit:,.2f}", delta=f"{net_profit:,.0f}")
    m4.metric("Fuel Debt (Shed)", f"Rs. {fuel_debt:,.2f}", delta_color="inverse")

    st.divider()
    c_l, c_r
