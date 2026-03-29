import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
from fpdf import FPDF
from streamlit_gsheets import GSheetsConnection # අලුතින් එක් කළා

# --- 1. LOGIN CREDENTIALS ---
USERS = {
    "ksdadmin": {"password": "ksd7979", "role": "admin"},
    "ksd": {"password": "ksd123", "role": "user"}
}

# --- 1. CONFIG & GOOGLE SHEETS SETUP ---
SHOP_NAME = "K. SIRIWARDHANA SAND CONSTRUCTION PRO"
# ඔයාගේ Google Sheet URL එක මෙතනට පසුව ඇතුළත් කරන්න
SHEET_URL = "https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID_HERE/edit?usp=sharing"

# Google Sheets Connection එක හදනවා
conn = st.connection("gsheets", type=GSheetsConnection)

# --- 2. DATA ENGINE (Google Sheets අනුව සකස් කළා) ---

def save_to_gsheets(dataframe, worksheet_name):
    """ඕනෑම DataFrame එකක් අදාළ Worksheet එකට Save කරයි"""
    try:
        conn.update(spreadsheet=SHEET_URL, worksheet=worksheet_name, data=dataframe)
        st.cache_data.clear() # පරණ Cache දත්ත අයින් කරයි
    except Exception as e:
        st.error(f"Error saving to {worksheet_name}: {e}")

def load_from_gsheets(worksheet_name, expected_cols):
    """Google Sheet එකෙන් දත්ත Load කරයි, ටැබ් එක නැත්නම් හිස් DataFrame එකක් දෙයි"""
    try:
        data = conn.read(spreadsheet=SHEET_URL, worksheet=worksheet_name)
        # දින වකවානු හරියට සකස් කිරීම
        if 'Date' in data.columns:
            data['Date'] = pd.to_datetime(data['Date']).dt.date
        return data
    except:
        return pd.DataFrame(columns=expected_cols)

# පරණ save_all() එක වෙනුවට අපි දැන් save_to_gsheets() එක තැනින් තැන පාවිච්චි කරනවා.
# නමුත් පරණ කෝඩ් වලට හානියක් නොවෙන්න හිස් function එකක් මෙලෙස තියමු.
def save_all():
    pass

# --- 3. SESSION STATE INITIALIZATION ---
# Column names ටික පරණ විදිහටම තියෙනවා
cols_master = ["ID", "Date", "Time", "Type", "Category", "Entity", "Note", "Amount", "Qty_Cubes", "Fuel_Ltr", "Hours", "Rate_At_Time", "Status"]
cols_ve = ["No", "Type", "Owner", "Rate_Per_Unit"]
cols_dr = ["Name", "Phone", "Daily_Salary"]
cols_staff = ["Name", "Position", "Daily_Rate"]
cols_lo = ["Name", "Address", "Contact", "Rate_Per_Cube"]

# --- දත්ත Google Sheets වලින් Load කිරීම ---
# පළමු වතාවට ඇප් එක රන් වෙද්දී පමණක් දත්ත ලෝඩ් වේ
if 'data_loaded' not in st.session_state:
    st.session_state.df = load_from_gsheets("Master_DF", cols_master)
    st.session_state.ve_db = load_from_gsheets("Vehicles", cols_ve)
    st.session_state.dr_db = load_from_gsheets("Drivers", cols_dr)
    st.session_state.staff_db = load_from_gsheets("Staff", cols_staff)
    st.session_state.lo_db = load_from_gsheets("Landowners", cols_lo)
    st.session_state.data_loaded = True

# පරණ landowners ලිස්ට් එක (Dictionary එකක් ලෙස) පවත්වා ගැනීම
if 'landowners' not in st.session_state:
    if not st.session_state.lo_db.empty:
        st.session_state.landowners = st.session_state.lo_db.to_dict('records')
    else:
        st.session_state.landowners = []
# --- 4. PDF ENGINE (Google Sheets දත්ත වලට ගැලපෙන සේ) ---
class PDF(FPDF):
    def header(self):
        # ආයතනයේ නම (Title)
        self.set_font('Arial', 'B', 15)
        self.set_text_color(230, 126, 34) 
        self.cell(0, 10, "K. SIRIWARDHANA SAND CONSTRUCTION PROJECT", 0, 1, 'C')
        self.ln(5)

def create_pdf(title, data_df, summary_dict):
    pdf = PDF()
    pdf.add_page()
    
    def safe_text(text):
        if text is None or str(text) == "nan": return ""
        # Latin-1 වලට සපෝට් නොකරන අකුරු අයින් කරයි (Sinahala අකුරු PDF එකේ පෙන්වීමට වෙනම Font එකක් අවශ්‍යයි)
        return str(text).encode("latin-1", "ignore").decode("latin-1")

    # Title Section
    pdf.set_font("Arial", 'B', 12)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 10, safe_text(f"STATEMENT: {title.upper()}"), 1, 1, 'L', fill=True)
    pdf.ln(2)
    
    # Summary Section (Landowner හෝ Driver විස්තර මෙතනට එනවා)
    pdf.set_font("Arial", 'B', 10)
    for k, v in summary_dict.items():
        if k != "Rate_Breakdown":
            pdf.cell(50, 8, safe_text(k) + ":", 1)
            pdf.set_font("Arial", '', 10)
            pdf.cell(0, 8, " " + safe_text(v), 1, 1)
            pdf.set_font("Arial", 'B', 10)

    # Table Header
    pdf.ln(8)
    pdf.set_font("Arial", 'B', 9)
    # වගුවේ පේළි වල පළල: Date, Category, Description, Qty, Rate, Amount
    w = [22, 35, 50, 15, 25, 43]
    headers = ["Date", "Category", "Description", "Qty/Hr", "Rate", "Amount"]
    
    pdf.set_fill_color(220, 220, 220)
    for i, h in enumerate(headers):
        pdf.cell(w[i], 8, safe_text(h), 1, 0, 'C', fill=True)
    pdf.ln()
    
    pdf.set_font("Arial", '', 8)
    total_earn = 0
    total_exp = 0
    total_qty_hrs = 0 
    
    for _, row in data_df.iterrows():
        # දත්ත පිරිසිදු කිරීමේ Function එක
        def clean_val(v):
            try:
                if v is None or str(v).lower() == 'nan' or str(v).strip() == '': return 0.0
                if isinstance(v, (int, float)): return float(v)
                v_str = str(v).replace(',', '').replace('Rs.', '').replace('LKR', '').replace(' ', '').strip()
                return float(v_str) if v_str else 0.0
            except: return 0.0

        # Google Sheets වල ඇති Columns අනුව අගයන් ලබාගැනීම
        q_cubes = clean_val(row.get('Qty_Cubes', 0))
        w_hrs = clean_val(row.get('Hours', row.get('Work_Hours', 0))) # 'Hours' හෝ 'Work_Hours' පරීක්ෂා කරයි
        qty = q_cubes if q_cubes > 0 else w_hrs
        
        rate = clean_val(row.get('Rate_At_Time', 0))
        amt = clean_val(row.get('Amount', 0))
        
        # දත්ත පේළිය පිරවීම
        date_val = safe_text(str(row.get('Date', '-')))
        category = str(row.get('Category', 'N/A'))
        note_val = safe_text(str(row.get('Note', '')))[:30] # Note එක දිග වැඩි නම් කපනවා

        pdf.cell(w[0], 7, date_val, 1)
        pdf.cell(w[1], 7, safe_text(category), 1)
        pdf.cell(w[2], 7, note_val, 1)
        pdf.cell(w[3], 7, f"{qty:,.2f}" if qty > 0 else "-", 1, 0, 'C')
        
        # Earnings සහ Expenses වෙන් කිරීම (Logic එක එලෙසමයි)
        is_expense = any(exp in category for exp in ["Fuel", "Repair", "Advance", "Payroll", "Salary", "Expense"])
        
        if is_expense:
            total_exp += amt
            pdf.set_text_color(200, 0, 0) # රතු පාටින් පෙන්වයි
            pdf.cell(w[4], 7, "EXPENSE", 1, 0, 'C')
            pdf.cell(w[5], 7, f"({amt:,.2f})", 1, 1, 'R')
            pdf.set_text_color(0, 0, 0) # නැවත කළු පාටට හැරවීම
        else:
            total_earn += amt
            total_qty_hrs += qty # ආදායමක් ලැබුණු දත්ත වල පමණක් Qty එකතු කරයි
            pdf.cell(w[4], 7, f"{rate:,.2f}" if rate > 0 else "-", 1, 0, 'R')
            pdf.cell(w[5], 7, f"{amt:,.2f}", 1, 1, 'R')

    # Final Totals Section
    pdf.ln(2)
    if pdf.get_y() > 250: pdf.add_page() # පිටුවේ අවසානය නම් අලුත් පිටුවක් ගනී

    pdf.set_font("Arial", 'B', 9)
    
    # 1. TOTAL QUANTITY / HOURS
    pdf.set_fill_color(245, 245, 245)
    pdf.cell(sum(w[:3]), 8, "TOTAL QUANTITY / HOURS", 1, 0, 'R', fill=True)
    pdf.cell(w[3], 8, f"{total_qty_hrs:,.2f}", 1, 0, 'C', fill=True)
    pdf.cell(w[4] + w[5], 8, "", 1, 1, 'R', fill=True)
    
    # 2. Gross Earnings
    pdf.cell(sum(w[:5]), 8, "GROSS EARNINGS (LKR)", 1, 0, 'R')
    pdf.cell(w[5], 8, f"{total_earn:,.2f}", 1, 1, 'R')
    
    # 3. Total Expenses
    pdf.cell(sum(w[:5]), 8, "TOTAL EXPENSES (LKR)", 1, 0, 'R')
    pdf.cell(w[5], 8, f"{total_exp:,.2f}", 1, 1, 'R')
    
    # 4. Net Balance (අවසාන ගෙවිය යුතු මුදල)
    pdf.set_fill_color(230, 126, 34); pdf.set_text_color(255, 255, 255)
    pdf.cell(sum(w[:5]), 10, "NET SETTLEMENT BALANCE (LKR)", 1, 0, 'R', fill=True)
    pdf.cell(w[5], 10, f"{(total_earn - total_exp):,.2f}", 1, 1, 'R', fill=True)
    
    # PDF එක File එකක් ලෙස Save කිරීම
    fn = f"Statement_{datetime.now().strftime('%H%M%S')}.pdf"
    pdf.output(fn)
    return fn

def create_staff_pdf(staff_name, data_df):
    pdf = PDF() # අපේ ප්‍රධාන PDF class එක පාවිච්චි කරයි
    pdf.add_page()
    
    def safe_text(text):
        if text is None or str(text) == "nan": return ""
        return str(text).encode("latin-1", "ignore").decode("latin-1")

    # Header Section
    pdf.set_font("Arial", 'B', 14)
    pdf.set_fill_color(230, 126, 34); pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 12, f"STAFF SETTLEMENT: {staff_name.upper()}", 1, 1, 'C', fill=True)
    pdf.set_text_color(0, 0, 0) # කළු පාටට මාරු කිරීම
    pdf.ln(5)

    # Table Header
    pdf.set_font("Arial", 'B', 10)
    # Date, Type, Note, Days, Amount
    w = [30, 40, 60, 20, 40]
    headers = ["Date", "Type", "Note", "Days", "Amount (LKR)"]
    
    pdf.set_fill_color(200, 200, 200)
    for i, h in enumerate(headers):
        pdf.cell(w[i], 8, h, 1, 0, 'C', fill=True)
    pdf.ln()

    pdf.set_font("Arial", '', 9)
    total_days = 0
    total_pay = 0
    total_adv = 0

    for _, row in data_df.iterrows():
        # දත්ත සුරක්ෂිතව ලබා ගැනීම
        def clean_num(v):
            try: return float(str(v).replace(',', '').strip()) if v and str(v) != 'nan' else 0.0
            except: return 0.0

        date = safe_text(str(row.get('Date', '-')))
        cat = safe_text(str(row.get('Category', 'Staff')))
        note = safe_text(str(row.get('Note', '')))
        amt = clean_num(row.get('Amount', 0))
        # අපි Staff Payroll වලදී 'Hours' column එක තමයි දවස් ගණනට පාවිච්චි කරන්නේ
        days = clean_num(row.get('Hours', 0)) 

        pdf.cell(w[0], 7, date, 1)
        pdf.cell(w[1], 7, cat, 1)
        pdf.cell(w[2], 7, note[:35], 1) # Note එකේ පළමු අකුරු 35 පෙන්වයි
        pdf.cell(w[3], 7, f"{days:,.1f}" if days > 0 else "-", 1, 0, 'C')
        
        # අත්තිකාරම් (Advance) රතු පාටින් පෙන්වීමට
        if "Advance" in cat or "Food" in cat:
            total_adv += amt
            pdf.set_text_color(200, 0, 0)
            pdf.cell(w[4], 7, f"({amt:,.2f})", 1, 1, 'R')
            pdf.set_text_color(0, 0, 0)
        else:
            total_pay += amt
            total_days += days
            pdf.cell(w[4], 7, f"{amt:,.2f}", 1, 1, 'R')

    # Totals Section
    pdf.ln(5)
    if pdf.get_y() > 250: pdf.add_page()

    pdf.set_font("Arial", 'B', 10)
    
    # 1. පඩිය (Salary)
    pdf.cell(sum(w[:4]), 8, "GROSS EARNINGS", 1, 0, 'R')
    pdf.cell(w[4], 8, f"{total_pay:,.2f}", 1, 1, 'R')
    
    # 2. අත්තිකාරම් (Advances)
    pdf.cell(sum(w[:4]), 8, "TOTAL ADVANCES / DEDUCTIONS", 1, 0, 'R')
    pdf.cell(w[4], 8, f"{total_adv:,.2f}", 1, 1, 'R')
    
    # 3. ශුද්ධ වැටුප (Net Payable)
    pdf.set_fill_color(46, 134, 193); pdf.set_text_color(255, 255, 255)
    pdf.cell(sum(w[:4]), 10, "NET PAYABLE BALANCE", 1, 0, 'R', fill=True)
    pdf.cell(w[4], 10, f"{(total_pay - total_adv):,.2f}", 1, 1, 'R', fill=True)

    # ගොනුවේ නම සෑදීම
    fn = f"Staff_Report_{staff_name}_{datetime.now().strftime('%H%M%S')}.pdf"
    pdf.output(fn)
    return fn
    
def create_driver_pdf(title, data_df, summary_dict):
    pdf = PDF() # අපේ ප්‍රධාන PDF class එක පාවිච්චි කරයි
    pdf.add_page()
    
    def safe_text(text):
        if text is None or str(text) == "nan": return ""
        return str(text).encode("latin-1", "ignore").decode("latin-1")

    # Title Section
    pdf.set_font("Arial", 'B', 12)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 10, safe_text(f"DRIVER PAYMENT STATEMENT: {title.upper()}"), 1, 1, 'L', fill=True)
    pdf.ln(2)
    
    # Summary Section (Driver ගේ නම, වාහන අංකය වැනි විස්තර)
    pdf.set_font("Arial", 'B', 10)
    for k, v in summary_dict.items():
        pdf.cell(50, 8, safe_text(k) + ":", 1)
        pdf.set_font("Arial", '', 10)
        pdf.cell(0, 8, " " + safe_text(v), 1, 1)
        pdf.set_font("Arial", 'B', 10)

    # Table Header
    pdf.ln(8)
    pdf.set_font("Arial", 'B', 9)
    # Headers: Date, Category, Description, Amount
    w = [30, 45, 75, 40]
    headers = ["Date", "Category", "Description", "Amount (LKR)"]
    
    pdf.set_fill_color(220, 220, 220)
    for i, h in enumerate(headers):
        pdf.cell(w[i], 8, safe_text(h), 1, 0, 'C', fill=True)
    pdf.ln()
    
    pdf.set_font("Arial", '', 9)
    total_paid = 0
    
    # --- Filter & Row Logic ---
    for _, row in data_df.iterrows():
        cat_str = str(row.get('Category', ''))
        
        # Salary, Advance, Payroll වැනි වචන තියෙන ගනුදෙනු විතරක් තෝරා ගනී
        is_salary_or_advance = any(word in cat_str for word in ["Salary", "Advance", "Payroll", "D.Advance"])
        
        if is_salary_or_advance:
            date_val = safe_text(str(row.get('Date', '-')))
            # Note එකේ පළමු අකුරු 45 පෙන්වයි
            note_val = safe_text(str(row.get('Note', '')))[:45]
            
            # Amount එක ආරක්ෂිතව Number එකක් කරගැනීම
            def clean_num(v):
                try:
                    if v is None or str(v).lower() == 'nan': return 0.0
                    return float(str(v).replace(',', '').replace('Rs.', '').strip())
                except: return 0.0
            
            amt = clean_num(row.get('Amount', 0))
            total_paid += amt

            # PDF එකට දත්ත පේළිය එකතු කිරීම
            pdf.cell(w[0], 7, date_val, 1)
            pdf.cell(w[1], 7, safe_text(cat_str), 1)
            pdf.cell(w[2], 7, note_val, 1)
            pdf.cell(w[3], 7, f"{amt:,.2f}", 1, 1, 'R')

    # Final Total Section
    pdf.ln(2)
    if pdf.get_y() > 250: pdf.add_page() # පිටුව ඉවර නම් අලුත් පිටුවක් ගනී

    pdf.set_font("Arial", 'B', 10)
    pdf.set_fill_color(230, 126, 34); pdf.set_text_color(255, 255, 255)
    pdf.cell(sum(w[:3]), 10, "TOTAL PAYMENTS TO DRIVER (LKR)", 1, 0, 'R', fill=True)
    pdf.cell(w[3], 10, f"{total_paid:,.2f}", 1, 1, 'R', fill=True)
    
    # PDF එක Output කිරීම
    fn = f"Driver_Settlement_{datetime.now().strftime('%H%M%S')}.pdf"
    pdf.output(fn)
    return fn
    
# --- Landowner PDF Engine (Google Sheets Compatible) ---
def create_landowner_pdf(title, data_df, summary_dict):
    pdf = PDF() # අපේ ප්‍රධාන PDF class එක පාවිච්චි කරයි
    pdf.add_page()
    
    def safe_text(text):
        if text is None or str(text) == "nan": return ""
        return str(text).encode("latin-1", "ignore").decode("latin-1")

    # Title Section
    pdf.set_font("Arial", 'B', 12)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 10, safe_text(f"LANDOWNER STATEMENT: {title.upper()}"), 1, 1, 'L', fill=True)
    pdf.ln(2)
    
    # Summary Section (Landowner නම, ඉඩමේ විස්තර වැනි දේ)
    pdf.set_font("Arial", 'B', 10)
    for k, v in summary_dict.items():
        pdf.cell(50, 8, safe_text(k) + ":", 1)
        pdf.set_font("Arial", '', 10)
        pdf.cell(0, 8, " " + safe_text(v), 1, 1)
        pdf.set_font("Arial", 'B', 10)

    # Table Header
    pdf.ln(8)
    pdf.set_font("Arial", 'B', 9)
    # Headers: Date, Category, Note, Cubes, Rate, Amount
    w = [22, 35, 50, 15, 25, 43]
    headers = ["Date", "Category", "Note", "Cubes", "Rate", "Amount"]
    
    pdf.set_fill_color(220, 220, 220)
    for i, h in enumerate(headers):
        pdf.cell(w[i], 8, safe_text(h), 1, 0, 'C', fill=True)
    pdf.ln()
    
    pdf.set_font("Arial", '', 8)
    total_payable = 0
    total_paid = 0
    
    for _, row in data_df.iterrows():
        # අංක පිරිසිදු කරගැනීමේ function එක
        def clean_num(v):
            try: return float(str(v).replace(',', '').strip()) if v and str(v) != 'nan' else 0.0
            except: return 0.0

        pdf.cell(w[0], 7, safe_text(str(row.get('Date', '-'))), 1)
        category = str(row.get('Category', 'N/A'))
        pdf.cell(w[1], 7, safe_text(category), 1)
        pdf.cell(w[2], 7, safe_text(str(row.get('Note', '')))[:30], 1)
        
        cubes = clean_num(row.get('Qty_Cubes', 0))
        pdf.cell(w[3], 7, f"{cubes}" if cubes > 0 else "-", 1, 0, 'C')
        
        rate = clean_num(row.get('Rate_At_Time', 0))
        pdf.cell(w[4], 7, f"{rate:,.2f}" if rate > 0 else "-", 1, 0, 'R')
        
        amt = clean_num(row.get('Amount', 0))
        
        # Stock Inward (වැලි ගත්ත ඒවා) Payable එකට එකතු කරනවා
        if "Inward" in category or "Stock" in category:
            total_payable += amt
            pdf.cell(w[5], 7, f"{amt:,.2f}", 1, 0, 'R')
        # Advances හෝ Payments (සල්ලි ගෙවපු ඒවා) Paid එකට එකතු කරනවා
        elif any(x in category for x in ["Advance", "Payment", "Paid"]):
            total_paid += amt
            pdf.set_text_color(200, 0, 0) # රතු පාටින් පෙන්වයි
            pdf.cell(w[5], 7, f"({amt:,.2f})", 1, 0, 'R')
            pdf.set_text_color(0, 0, 0)
        else:
            pdf.cell(w[5], 7, "-", 1, 0, 'R')
        pdf.ln()
    
    # Final Summary Section
    pdf.ln(2)
    if pdf.get_y() > 250: pdf.add_page()
    
    pdf.set_font("Arial", 'B', 9)
    # 1. මුළු වැලි වටිනාකම
    pdf.cell(sum(w[:5]), 8, "TOTAL PAYABLE FOR CUBES (LKR)", 1, 0, 'R')
    pdf.cell(w[5], 8, f"{total_payable:,.2f}", 1, 1, 'R')
    
    # 2. දීපු අත්තිකාරම්
    pdf.cell(sum(w[:5]), 8, "TOTAL ADVANCES PAID (LKR)", 1, 0, 'R')
    pdf.cell(w[5], 8, f"{total_paid:,.2f}", 1, 1, 'R')
    
    # 3. ඉතිරි ශුද්ධ හිඟ මුදල
    pdf.set_fill_color(39, 174, 96); pdf.set_text_color(255, 255, 255) # කොළ පාට (Success)
    pdf.cell(sum(w[:5]), 10, "NET BALANCE TO BE PAID (LKR)", 1, 0, 'R', fill=True)
    pdf.cell(w[5], 10, f"{(total_payable - total_paid):,.2f}", 1, 1, 'R', fill=True)
    
    fn = f"Landowner_Settlement_{datetime.now().strftime('%H%M%S')}.pdf"
    pdf.output(fn)
    return fn

# --- 1. LOGIN STATUS & DATA INITIALIZATION ---
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

# --- 2. LOGIN UI ---
if not st.session_state["logged_in"]:
    st.markdown("<h2 style='text-align: center; color: #8E44AD;'>🔐 KSD Sand & Soil System</h2>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        with st.form("login_panel"):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Login to System"):
                # කලින් අපි හදාගත්ත USERS dictionary එක මෙතනදී පාවිච්චි වෙනවා
                if u in USERS and USERS[u]["password"] == p:
                    st.session_state["logged_in"] = True
                    st.session_state["user_name"] = u
                    st.session_state["role"] = USERS[u]["role"]
                    
                    # 📥 ලොග් වුණු ගමන්ම Google Sheets වලින් දත්ත ඇදලා ගන්නවා
                    # (අපි මුලින්ම හදාගත්ත load_from_gsheets functions මෙතනදී ක්‍රියාත්මක වේ)
                    with st.spinner("Connecting to Google Sheets..."):
                        # මෙතනදී st.session_state.data_loaded = True කියලා පස්සේ සෙට් වෙනවා
                        st.success(f"Welcome {u}!")
                        st.rerun()
                else:
                    st.error("Invalid Username or Password")
    st.stop()

# --- 3. POST-LOGIN SIDEBAR & LOGOUT ---
st.sidebar.markdown(f"### 👤 User: {st.session_state.get('user_name', 'Admin')}")
st.sidebar.markdown(f"**Role:** {st.session_state.get('role', 'user').capitalize()}")

if st.sidebar.button("Logout 🔓", use_container_width=True):
    # Logout වෙද්දී Session එක ක්ලියර් කරනවා
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

st.sidebar.divider()
st.sidebar.title("SyntaxCore Panel")
# ... ඔයාගේ පරණ Menu එක සහ අනෙකුත් කොටස් ...
    
# --- 5. UI LAYOUT & LOGIN CHECK ---
st.set_page_config(page_title=SHOP_NAME, layout="wide")

# 2. LOGIN STATUS පරීක්ෂාව
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["role"] = None

# 3. ලොග් වෙලා නැත්නම් විතරක් Login Form එක පෙන්වන්න
if not st.session_state["logged_in"]:
    st.markdown("<h2 style='text-align: center; color: #2E86C1;'>🔐 KSD ERP - Security Portal</h2>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        with st.form("login_panel"):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            
            if st.form_submit_button("Access System"):
                if u in USERS and USERS[u]["password"] == p:
                    st.session_state["logged_in"] = True
                    st.session_state["role"] = USERS[u]["role"]
                    st.session_state["user_name"] = u
                    
                    # 📥 ලොග් වුණු විගස Google Sheets වලින් දත්ත ලබා ගැනීම
                    with st.spinner("🔄 Synchronizing with Cloud Database..."):
                        # මෙතනදී පරණ load_data functions වෙනුවට අපේ අලුත් load_from_gsheets රන් වේ
                        st.success("Login Successful!")
                        st.rerun()
                else:
                    st.error("Invalid Username or Password!")
    st.stop() 

# --- 🔓 4. ලොග් වුණාට පස්සේ පේන කොටස ---

# Sidebar එකේ පෙනුම සකස් කිරීම
st.sidebar.markdown(f"### 🏗️ {SHOP_NAME}")
role_display = st.session_state["role"].upper()
st.sidebar.info(f"👤 User: **{st.session_state['user_name']}**\n\n🛡️ Role: **{role_display}**")

# 👮 ROLE එක අනුව MENU එක තෝරා ගැනීම
if st.session_state["role"] == "admin":
    menu_options = [
        "📊 Dashboard", 
        "🏗️ Site Operations", 
        "👤 Manage Landowners", 
        "👷 Staff Payroll", 
        "💰 Finance & Shed", 
        "⚙️ System Setup", 
        "📑 Reports Center", 
        "⚙️ Data Manager"
    ]
else:
    # සාමාන්‍ය USER (Staff) ට පේන්නේ Operations විතරයි
    menu_options = ["🏗️ Site Operations"]

menu = st.sidebar.selectbox("MAIN MENU", menu_options)

# Sidebar අඩියට Logout සහ Refresh බටන් දාමු
st.sidebar.markdown("---")
if st.sidebar.button("🔄 Refresh Data", use_container_width=True):
    st.cache_data.clear() # Cache එක මකලා අලුත්ම ඩේටා Sheets වලින් ගනී
    st.rerun()

if st.sidebar.button("Logout 🔓", use_container_width=True, key="sidebar_logout_unique"):
    # Logout වෙද්දී සියලුම Session දත්ත මකා දමයි
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# --- මෙතනින් පස්සේ ඔයාගේ පරණ කෝඩ් එකේ 'if menu == ...' කොටස් ආරම්භ කරන්න ---

# --- 1. DASHBOARD SECTION (Google Sheets Compatible) ---
if menu == "📊 Dashboard":
    st.markdown("<h2 style='color: #2E86C1;'>📊 Business Overview</h2>", unsafe_allow_html=True)
    
    # 📥 Google Sheets දත්ත Copy එකක් ලබා ගැනීම
    df = st.session_state.df.copy()
    
    if not df.empty:
        # --- DATE FILTER ---
        st.subheader("📅 Filter Transactions")
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            start_date = st.date_input("From Date", datetime.now().date() - timedelta(days=7))
        with col_f2:
            end_date = st.date_input("To Date", datetime.now().date())
        
        # දින වකවානු නිවැරදි Format එකට හැරවීම
        df['Date'] = pd.to_datetime(df['Date']).dt.date
        mask = (df['Date'] >= start_date) & (df['Date'] <= end_date)
        filtered_df = df.loc[mask].copy()

        if not filtered_df.empty:
            # --- FINANCIAL METRICS ---
            # Numeric වලට හරවා ගැනීම (Error වැලැක්වීමට)
            filtered_df['Qty_Cubes'] = pd.to_numeric(filtered_df['Qty_Cubes'], errors='coerce').fillna(0)
            filtered_df['Rate_At_Time'] = pd.to_numeric(filtered_df['Rate_At_Time'], errors='coerce').fillna(0)
            filtered_df['Amount'] = pd.to_numeric(filtered_df['Amount'], errors='coerce').fillna(0)

            # Sales Income ගණනය කිරීම
            sales_mask = filtered_df["Category"].str.contains("Sales Out", na=False)
            real_income = (filtered_df.loc[sales_mask, 'Qty_Cubes'] * filtered_df.loc[sales_mask, 'Rate_At_Time']).sum()
            
            # Expenses ගණනය කිරීම
            total_expenses = filtered_df[filtered_df["Type"] == "Expense"]["Amount"].sum()

            # Metrics පෙන්වීම
            m1, m2, m3 = st.columns(3)
            m1.metric("Net Sales Income", f"Rs. {real_income:,.2f}")
            m2.metric("Total Expenses", f"Rs. {total_expenses:,.2f}")
            m3.metric("Net Cashflow", f"Rs. {real_income - total_expenses:,.2f}")

            st.divider()

            # ==========================================
            # 📦 STOCK BALANCE (Cloud Sync Logic)
            # ==========================================
            st.subheader("📦 Plant Stock Balance (Current)")
            s_col1, s_col2 = st.columns(2)
            
            # මුළු ඉතිහාසයම පරීක්ෂා කිරීම සඳහා ප්‍රධාන DF එක භාවිතා කරයි
            full_df = st.session_state.df.copy()
            full_df['Qty_Cubes'] = pd.to_numeric(full_df['Qty_Cubes'], errors='coerce').fillna(0)
            
            # Sand Calculation (වැලි)
            s_in = full_df[full_df["Category"].str.contains("Stock Inward", na=False) & 
                           full_df["Category"].str.contains("Sand", na=False)]["Qty_Cubes"].sum()
            s_out = full_df[full_df["Category"].str.contains("Sales Out", na=False) & 
                            full_df["Category"].str.contains("Sand", na=False)]["Qty_Cubes"].sum()
            
            # Soil Calculation (පස්)
            so_in = full_df[full_df["Category"].str.contains("Stock Inward", na=False) & 
                            full_df["Category"].str.contains("Soil", na=False)]["Qty_Cubes"].sum()
            so_out = full_df[full_df["Category"].str.contains("Sales Out", na=False) & 
                             full_df["Category"].str.contains("Soil", na=False)]["Qty_Cubes"].sum()

            s_col1.metric("Sand Remaining", f"{s_in - s_out:.2f} Cubes", delta=f"In: {s_in} | Out: {s_out}")
            s_col2.metric("Soil Remaining", f"{so_in - so_out:.2f} Cubes", delta=f"In: {so_in} | Out: {so_out}")
            # ==========================================

            st.divider()
            st.subheader("Daily Income Trend")
            # Trend Chart එක සඳහා Income එක වෙනම Column එකක් ලෙස හදා ගැනීම
            filtered_df['Income_Val'] = 0.0
            filtered_df.loc[sales_mask, 'Income_Val'] = filtered_df['Qty_Cubes'] * filtered_df['Rate_At_Time']
            st.line_chart(filtered_df.groupby('Date')['Income_Val'].sum())
            
        else:
            st.warning("තෝරාගත් දින පරාසය තුළ දත්ත නැත.")
    else:
        st.info("පද්ධතියේ දත්ත කිසිවක් නැත.")

# --- 2. SITE OPERATIONS SECTION ---
# මේ 'elif' එක පටන් ගන්න ඕනේ උඩ තියෙන 'if menu == "📊 Dashboard":' එකට කෙළින්ම පල්ලෙහායින්
# --- කලින් තිබුණු Site Operations එක අයින් කරලා මේක දාන්න ---
elif menu == "🏗️ Site Operations":
    st.markdown(f"<h2 style='color: #E67E22;'>🏗️ Site Operations & Stock Manager</h2>", unsafe_allow_html=True)
    
    op = st.radio("Select Activity Type", ["🚜 Excavator Work Log", "💰 Sales Out", "📥 Stock Inward (To Plant)"], horizontal=True)
    
    # 1. දත්ත මූලාශ්‍ර ලබා ගැනීම (Lists)
    v_list = st.session_state.ve_db["No"].tolist() if not st.session_state.ve_db.empty else ["N/A"]
    d_list = st.session_state.dr_db["Name"].tolist() if not st.session_state.dr_db.empty else ["No Drivers"]
    # Landowners ලා DataFrame එකක් ලෙස ඇත්නම්:
    l_list = st.session_state.lo_db["Name"].tolist() if not st.session_state.lo_db.empty else ["No Owners"]

    with st.form("site_f", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            v = st.selectbox("Select Vehicle / Machine", v_list if op != "📥 Stock Inward (To Plant)" else ["Third Party Truck"])
            d = st.date_input("Date", datetime.now().date())
            material = st.selectbox("Material Type", ["Sand", "Soil", "Other"]) if op != "🚜 Excavator Work Log" else ""
            
            # Stock Inward එකේදී Landowner සහ Driver විස්තර Note එකට කලින්ම ගන්නවා
            src_owner = ""
            src_driver = ""
            if op == "📥 Stock Inward (To Plant)":
                src_owner = st.selectbox("Source (Landowner)", l_list)
                src_driver = st.selectbox("Driver/Operator", d_list)
        
        with col2:
            # පේළියේ ලේබල් එක තෝරාගත් ක්‍රියාකාරකම අනුව වෙනස් වේ
            is_excavator = "Excavator" in op
            val_label = "Work Hours" if is_excavator else "Qty (Cubes)"
            unit = "Hrs" if is_excavator else "Cubes"
            
            val = st.number_input(f"Enter {val_label}", min_value=0.0, step=0.5, format="%.2f")
            r = st.number_input(f"Rate per {unit} (LKR)", min_value=0.0, step=100.0, format="%.2f")
            
            # Auto-Calculation පෙන්වීම (Visual Confirmation)
            total_preview = val * r
            st.markdown(f"**Total Amount: Rs. {total_preview:,.2f}**")
            
        n = st.text_input("Additional Note / Location")
        
        if st.form_submit_button("📥 Save Record to Cloud"):
            if val <= 0:
                st.error(f"Please enter a valid {val_label}!")
            elif r <= 0:
                st.error("Please enter a valid Rate!")
            else:
                # --- දත්ත සකස් කිරීම (Data Preparation) ---
                calculated_amount = val * r
                q = 0.0 if is_excavator else val
                h = val if is_excavator else 0.0
                
                # Note එකට අමතර විස්තර එකතු කිරීම
                final_note = n
                if op == "📥 Stock Inward (To Plant)":
                    final_note = f"{n} | Owner: {src_owner} | Drv: {src_driver}".strip(" | ")

                # Google Sheets Column Structure එකට ගැලපෙන Dictionary එක
                new_entry = {
                    "Date": str(d),
                    "Type": "Income" if op == "💰 Sales Out" else "Process",
                    "Category": f"{op} ({material})" if material else op,
                    "Entity": v,
                    "Note": final_note,
                    "Qty_Cubes": q,
                    "Hours": h,  # Google Sheets හි 'Hours' column එකට යයි
                    "Rate_At_Time": r,
                    "Amount": calculated_amount,
                    "Status": "Verified"
                }
                
                # 📥 Cloud එකට Save කිරීම
                with st.spinner("Saving to Google Sheets..."):
                    success = save_to_gsheets(MASTER_SHEET, new_entry)
                    
                    if success:
                        # Local session state එකත් update කරනවා (වහාම පෙන්වීමට)
                        new_row = pd.DataFrame([new_entry])
                        st.session_state.df = pd.concat([st.session_state.df, new_row], ignore_index=True)
                        st.success(f"✅ Recorded! Total: Rs.{calculated_amount:,.2f}")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error("Cloud Save Failed! Please check your internet.")

    # --- Today's Logs Display ---
    st.divider()
    st.subheader("📅 Today's Operations")
    
    if not st.session_state.df.empty:
        temp_df = st.session_state.df.copy()
        # දින අනුව Filter කිරීම
        temp_df['Date'] = pd.to_datetime(temp_df['Date']).dt.date
        today_data = temp_df[temp_df["Date"] == datetime.now().date()].sort_index(ascending=False)
        
        if not today_data.empty:
            st.dataframe(today_data[["Date", "Category", "Entity", "Qty_Cubes", "Hours", "Amount", "Note"]], 
                         use_container_width=True)
        else:
            st.info("No records found for today.")
    
# --- 8. FINANCE & SHED (v56 FULL) ---
elif menu == "💰 Finance & Shed":
    st.markdown("<h2 style='color: #27AE60;'>💰 Finance & Expenditure Manager</h2>", unsafe_allow_html=True)
    
    fin = st.radio("Finance Category", ["⛽ Fuel & Shed", "🔧 Repairs", "💸 Payroll", "🏦 Owner Advances", "🧾 Others"], horizontal=True)
    
    # වාහන ලැයිස්තුව ලබා ගැනීම
    v_list = st.session_state.ve_db["No"].tolist() if not st.session_state.ve_db.empty else ["N/A"]
    
    if fin == "⛽ Fuel & Shed":
        f1, f2 = st.tabs(["⛽ Log Fuel Bill (Credit)", "💳 Settle Shed Payments"])
        
        # --- TAB 1: තෙල් ගැසූ බිල්පත ඇතුළත් කිරීම ---
        with f1:
            st.info("ෂෙඩ් එකෙන් ණයට (Credit) තෙල් ගැසූ විට මෙහි ඇතුළත් කරන්න.")
            with st.form("fuel", clear_on_submit=True):
                col_a, col_b = st.columns(2)
                with col_a:
                    d = st.date_input("Date", datetime.now().date())
                    v = st.selectbox("Vehicle", v_list)
                with col_b:
                    l = st.number_input("Liters (Qty)", min_value=0.0, step=1.0)
                    c = st.number_input("Total Bill Cost (LKR)", min_value=0.0, step=100.0)
                
                n = st.text_input("Meter Reading / Pump No (Optional)")
                
                if st.form_submit_button("Save Fuel Bill"):
                    if c <= 0:
                        st.error("Please enter a valid bill cost!")
                    else:
                        # Google Sheets එකට ගැලපෙන දත්ත පෙළ
                        new_fuel_entry = {
                            "Date": str(d),
                            "Type": "Expense",
                            "Category": "Fuel Entry",
                            "Entity": v,
                            "Note": f"Ltrs: {l} | {n}".strip(" | "),
                            "Amount": c,
                            "Qty_Cubes": 0, "Hours": 0, "Rate_At_Time": 0, # Placeholder values
                            "Status": "Pending" # ෂෙඩ් එකට තවම ගෙවා නැති බව
                        }
                        
                        with st.spinner("Uploading to Cloud..."):
                            if save_to_gsheets(MASTER_SHEET, new_fuel_entry):
                                # Local DF එකට එකතු කිරීම
                                st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_fuel_entry])], ignore_index=True)
                                st.success(f"Fuel bill for {v} (Rs.{c:,.2f}) recorded!")
                                st.rerun()

        # --- TAB 2: ෂෙඩ් එකට මුදල් ගෙවීම ---
        with f2:
            st.warning("ෂෙඩ් එකට ගනුදෙනු බේරීමට (Settlements) මුදල් ගෙවූ විට මෙහි ඇතුළත් කරන්න.")
            with st.form("shed_pay", clear_on_submit=True):
                pay_date = st.date_input("Payment Date", datetime.now().date())
                am = st.number_input("Amount Paid (LKR)", min_value=0.0, step=500.0)
                ref = st.text_input("Cheque No / Cash Reference")
                
                if st.form_submit_button("Record Payment"):
                    if am <= 0:
                        st.error("Enter a valid payment amount!")
                    else:
                        new_payment = {
                            "Date": str(pay_date),
                            "Type": "Expense",
                            "Category": "Shed Payment",
                            "Entity": "Shed",
                            "Note": ref,
                            "Amount": am,
                            "Qty_Cubes": 0, "Hours": 0, "Rate_At_Time": 0,
                            "Status": "Paid"
                        }
                        
                        with st.spinner("Recording Payment..."):
                            if save_to_gsheets(MASTER_SHEET, new_payment):
                                st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_payment])], ignore_index=True)
                                st.success(f"Payment of Rs.{am:,.2f} recorded on {pay_date}")
                                st.rerun()

    # --- මෑතකදී කළ වියදම් පෙන්වීම ---
    st.divider()
    st.subheader("Recent Finance Records")
    if not st.session_state.df.empty:
        fin_df = st.session_state.df[st.session_state.df["Type"] == "Expense"].tail(10)
        st.dataframe(fin_df[["Date", "Category", "Entity", "Amount", "Note", "Status"]], use_container_width=True)
                    
    elif fin == "🔧 Repairs":
        st.info("වාහන හෝ මැෂින් අලුත්වැඩියාවන් (Maintenance) මෙහි ඇතුළත් කරන්න.")
        with st.form("rep", clear_on_submit=True):
            col_a, col_b = st.columns(2)
            with col_a:
                d = st.date_input("Date", datetime.now().date())
                v = st.selectbox("Select Vehicle / Machine", v_list)
            with col_b:
                am = st.number_input("Repair Cost (LKR)", min_value=0.0, step=500.0)
                garage = st.text_input("Garage / Technician Name")
            
            nt = st.text_area("Detail of Repair (මොනවද කළේ?)", placeholder="उदा: Engine oil change, Bucket teeth replacement...")
            
            if st.form_submit_button("💾 Save Repair Record"):
                if am <= 0:
                    st.error("Please enter the repair cost!")
                elif not nt:
                    st.error("Please enter the repair details!")
                else:
                    # Google Sheets එකට ගැලපෙන දත්ත සැකසීම
                    new_repair_entry = {
                        "Date": str(d),
                        "Type": "Expense",
                        "Category": "Repair",
                        "Entity": v,
                        "Note": f"{nt} | Garage: {garage}".strip(" | "),
                        "Amount": am,
                        "Qty_Cubes": 0, "Hours": 0, "Rate_At_Time": 0,
                        "Status": "Paid"
                    }
                    
                    with st.spinner("Saving Repair Record to Cloud..."):
                        if save_to_gsheets(MASTER_SHEET, new_repair_entry):
                            # Local DataFrame එක Update කිරීම
                            st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_repair_entry])], ignore_index=True)
                            st.success(f"✅ Repair of {v} (Rs.{am:,.2f}) recorded successfully!")
                            st.rerun()
                        else:
                            st.error("Cloud Save Failed! Check Connection.")

    # කලින් තිබුණ if/elif පේළියට කෙලින්ම යටින් මෙය තිබිය යුතුය
    elif fin == "💸 Payroll":
        st.info("සේවක වැටුප් (Salary) සහ අත්තිකාරම් (Advance) මෙහි ඇතුළත් කරන්න.")
        
        # ඩ්‍රයිවර්ලා සහ අනෙකුත් ස්ටාෆ් ලැයිස්තුව ලබා ගැනීම
        dr_names = st.session_state.dr_db["Name"].tolist() if not st.session_state.dr_db.empty else ["No Drivers"]
        
        with st.form("pay", clear_on_submit=True):
            col_a, col_b = st.columns(2)
            
            with col_a:
                dr = st.selectbox("Select Employee / Driver", dr_names)
                pay_date = st.date_input("Payment Date", datetime.now().date())
                v_rel = st.selectbox("Related Vehicle (Optional)", ["None"] + v_list)
            
            with col_b:
                ty = st.selectbox("Payment Type", ["Driver Advance", "Salary", "Staff Advance", "Bonus"])
                am = st.number_input("Amount Paid (LKR)", min_value=0.0, step=500.0)
                method = st.selectbox("Payment Method", ["Cash", "Online Transfer", "Cheque"])

            nt = st.text_input("Additional Note (වැඩිපුර විස්තර)")

            if st.form_submit_button("💰 Save to Payroll"):
                if am <= 0:
                    st.error("Please enter a valid amount!")
                else:
                    # Google Sheets එකට යන දත්ත Structure එක
                    # අපි කලින් හදාගත්ත Driver PDF එකට මේ Category එක කෙලින්ම බලපානවා
                    new_payroll_entry = {
                        "Date": str(pay_date),
                        "Type": "Expense",
                        "Category": ty,
                        "Entity": v_rel if v_rel != "None" else "General",
                        "Note": f"Emp: {dr} | {nt} | {method}".strip(" | "),
                        "Amount": am,
                        "Qty_Cubes": 0, "Hours": 0, "Rate_At_Time": 0,
                        "Status": "Paid"
                    }
                    
                    with st.spinner("Syncing Payroll with Cloud..."):
                        if save_to_gsheets(MASTER_SHEET, new_payroll_entry):
                            # Local session state update කිරීම
                            st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_payroll_entry])], ignore_index=True)
                            st.success(f"✅ {ty} of Rs.{am:,.2f} for {dr} recorded!")
                            st.rerun()
                        else:
                            st.error("Cloud Connection Error!")
                            
    elif fin == "🏦 Owner Advances":
        st.info("වැලි නිධි අයිතිකරුවන්ට (Landowners) ලබාදෙන අත්තිකාරම් මුදල් මෙහි ඇතුළත් කරන්න.")
        
        # Landowners ලාගේ නම් ලැයිස්තුව ලබා ගැනීම
        l_list = st.session_state.lo_db["Name"].tolist() if not st.session_state.lo_db.empty else ["No Owners Registered"]

        with st.form("own_adv", clear_on_submit=True):
            col_a, col_b = st.columns(2)
            
            with col_a:
                # මෙතනදී Entity එක විදිහට Landowner ව තෝරා ගනී
                owner = st.selectbox("Select Landowner", l_list)
                d = st.date_input("Date", datetime.now().date())
            
            with col_b:
                am = st.number_input("Advance Amount (LKR)", min_value=0.0, step=1000.0)
                v_rel = st.selectbox("Related Machine (Optional)", ["None"] + v_list)

            nt = st.text_input("Note / Reference (उदा: Cheque No, Bank Transfer Ref)")

            if st.form_submit_button("💰 Save Owner Advance"):
                if am <= 0:
                    st.error("Please enter a valid amount!")
                elif owner == "No Owners Registered":
                    st.error("Please register a Landowner first!")
                else:
                    # Google Sheets එකට යන දත්ත Structure එක
                    # Category එක 'Owner Advance' ලෙස තැබීමෙන් PDF එකේ Payment එකක් ලෙස අඳුනා ගනී
                    new_adv_entry = {
                        "Date": str(d),
                        "Type": "Expense",
                        "Category": "Owner Advance",
                        "Entity": owner, # අයිතිකරුගේ නම මෙතනට වැටේ
                        "Note": f"{nt} | Machine: {v_rel}".strip(" | "),
                        "Amount": am,
                        "Qty_Cubes": 0, "Hours": 0, "Rate_At_Time": 0,
                        "Status": "Paid"
                    }
                    
                    with st.spinner("Syncing with Cloud Database..."):
                        if save_to_gsheets(MASTER_SHEET, new_adv_entry):
                            # Local session state update කිරීම
                            st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_adv_entry])], ignore_index=True)
                            st.success(f"✅ Advance of Rs.{am:,.2f} for {owner} recorded!")
                            st.rerun()
                        else:
                            st.error("Cloud Connection Error! Please check your internet.")
                            
    elif fin == "🧾 Others":
        st.info("ඉහත ප්‍රධාන ගණයන්ට අයත් නොවන අනෙකුත් සියලුම වියදම් මෙහි ඇතුළත් කරන්න.")
        with st.form("oth", clear_on_submit=True):
            col_a, col_b = st.columns(2)
            
            with col_a:
                d = st.date_input("Date", datetime.now().date())
                cat = st.selectbox("Expense Category", ["Food & Beverage", "Office Rent", "Electricity & Water", "Internet & Mobile", "Tools & Stationary", "Misc"])
            
            with col_b:
                am = st.number_input("Amount (LKR)", min_value=0.0, step=100.0)
                pay_method = st.selectbox("Paid By", ["Cash", "Petty Cash", "Owner's Fund"])

            nt = st.text_input("Note / Purpose (වැඩිපුර විස්තර)")

            if st.form_submit_button("💾 Save Expense"):
                if am <= 0:
                    st.error("Please enter a valid amount!")
                else:
                    # Google Sheets එකට යන දත්ත Structure එක
                    new_other_entry = {
                        "Date": str(d),
                        "Type": "Expense",
                        "Category": cat,
                        "Entity": "Admin / General",
                        "Note": f"{nt} | Paid via: {pay_method}".strip(" | "),
                        "Amount": am,
                        "Qty_Cubes": 0, "Hours": 0, "Rate_At_Time": 0,
                        "Status": "Paid"
                    }
                    
                    with st.spinner("Uploading to Google Sheets..."):
                        if save_to_gsheets(MASTER_SHEET, new_other_entry):
                            # Local session state එක update කිරීම
                            st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_other_entry])], ignore_index=True)
                            st.success(f"✅ {cat} expense of Rs.{am:,.2f} recorded!")
                            st.rerun()
                        else:
                            st.error("Cloud Save Failed!")
                            
# --- 9. REPORTS CENTER SECTION ---
elif menu == "📑 Reports Center":
    st.markdown("<h2 style='color: #8E44AD;'>📑 Business Reports Center</h2>", unsafe_allow_html=True)
    
    # --- STEP 1: DATA CLEANUP (Google Sheets වලට ගැලපෙන විදිහට) ---
    df_raw = st.session_state.df.copy()
    
    # 1. Column names වල තියෙන හිස්තැන් (Extra spaces) අයින් කිරීම
    df_raw.columns = [str(c).strip() for c in df_raw.columns]
    
    # 2. වැදගත්ම දේ: Numeric columns හරියටම numbers වලට හරවා ගැනීම (Sheets වලින් එද්දී එන errors වැලැක්වීමට)
    num_cols = ['Amount', 'Qty_Cubes', 'Hours', 'Rate_At_Time']
    for col in num_cols:
        if col in df_raw.columns:
            df_raw[col] = pd.to_numeric(df_raw[col], errors='coerce').fillna(0)

    # 3. Vehicle/Entity column එක හරියටම සෙට් කරගැනීම
    if 'Entity' in df_raw.columns:
        df_raw['Vehicle'] = df_raw['Entity'] 
    elif 'Vehicle No' in df_raw.columns:
        df_raw['Vehicle'] = df_raw['Vehicle No']

    # --- STEP 2: TABS SETTING ---
    # ඔයාගේ අලුත් පිළිවෙළට Tabs ටික මෙතන තියෙනවා
    tabs = st.tabs([
        "💰 Daily Income Report", 
        "📊 Profit/Loss Analysis",
        "📈 Material Gross Earnings",
        "👷 Staff Settlement", 
        "🚜 Vehicle Settlement", 
        "👤 Driver Summary", 
        "📑 Daily Log", 
        "⛽ Shed Report"
    ])
    
    # Tabs variables වලට Assign කිරීම (පිළිවෙළට)
    r_inc, r_prof, r_gross, r_staff, r_veh, r_drv, r_log, r_shed = tabs
    
    # --- STEP 3: DATE FILTER ---
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        f_d = st.date_input("From Date", datetime.now().date() - timedelta(days=30), key="r_from")
    with col_d2:
        t_d = st.date_input("To Date", datetime.now().date(), key="r_to")

    # Date column එක නිවැරදි Format එකට හැරවීම සහ Filter කිරීම
    df_raw['Date'] = pd.to_datetime(df_raw['Date']).dt.date
    df_f = df_raw[(df_raw["Date"] >= f_d) & (df_raw["Date"] <= t_d)].copy()

    # -----------------------------------------------------------------
    # දැන් මෙතනින් පල්ලෙහාට එක එක Tab එක ඇතුළේ ලොජික් එක ලියන්න පුළුවන්
    # -----------------------------------------------------------------
    
   # --- TAB: DAILY INCOME REPORT (ENHANCED) ---
    with r_inc:
        st.subheader("💰 Daily Sales & Income Statement")
        
        # 1. Sales Out records විතරක් පෙරා ගැනීම (Category එකේ 'Sales Out' ඇති ඒවා)
        daily_sales = df_f[df_f["Category"].str.contains("Sales Out", na=False)].copy()
        
        if not daily_sales.empty:
            # 2. Column Safety Check
            available_cols = daily_sales.columns.tolist()
            required_cols = ['Date', 'Category', 'Entity', 'Qty_Cubes', 'Rate_At_Time', 'Amount']
            final_cols = [c for c in required_cols if c in available_cols]
            
            display_sales = daily_sales[final_cols].copy()
            
            # 3. Rename columns for better UI
            rename_dict = {
                'Category': 'Material', 'Entity': 'Vehicle/Client', 
                'Qty_Cubes': 'Qty', 'Rate_At_Time': 'Rate', 'Amount': 'Total Amount'
            }
            display_sales.rename(columns=rename_dict, inplace=True)

            # --- ANALYTICS CARDS ---
            total_income = display_sales['Total Amount'].sum() if 'Total Amount' in display_sales.columns else 0
            total_qty = display_sales['Qty'].sum() if 'Qty' in display_sales.columns else 0
            
            c1, c2 = st.columns(2)
            c1.metric("Total Period Income", f"LKR {total_income:,.2f}")
            c2.metric("Total Cubes Sold", f"{total_qty:,.1f} Cubes")

            # --- CHART: DAILY INCOME TREND ---
            st.markdown("#### 📈 Income Trend")
            chart_data = display_sales.groupby('Date')['Total Amount'].sum().reset_index()
            st.line_chart(chart_data.set_index('Date'))

            # --- DATA TABLE ---
            st.markdown("#### 📄 Transaction Breakdown")
            st.dataframe(display_sales.sort_values(by='Date', ascending=False), use_container_width=True)
            
            # --- PDF GENERATION ---
            if st.button("📥 Download Daily Income PDF"):
                with st.spinner("Generating PDF..."):
                    inc_summary = {
                        "Report Type": "Daily Income Statement",
                        "Period": f"{f_d} to {t_d}",
                        "Total Items": len(display_sales),
                        "Total Gross Income": f"LKR {total_income:,.2f}"
                    }
                    pdf_fn = create_pdf(f"Daily_Income", display_sales, inc_summary)
                    with open(pdf_fn, "rb") as f:
                        st.download_button("📩 Click to Download PDF", f, file_name=f"Income_Report_{f_d}.pdf")
        else:
            st.warning("තෝරාගත් දින පරාසය තුළ Sales records කිසිවක් නැත.")
            
   # --- TAB: PROFIT/LOSS ANALYSIS (ENHANCED) ---
    with r_prof:
        st.subheader("📊 Profit & Loss Performance Analysis")
        
        if not df_f.empty:
            # 1. Income (Sales Out) වෙන් කරගැනීම
            inc_data = df_f[df_f["Category"].str.contains("Sales Out", na=False)].copy()
            inc_data['Val'] = pd.to_numeric(inc_data['Amount'], errors='coerce').fillna(0)
            
            # 2. Expenses (Repairs, Fuel, Payroll, Others) වෙන් කරගැනීම
            # මෙතනදී Type එක 'Expense' වන සියලුම දේ ගනී
            exp_data = df_f[df_f["Type"] == "Expense"].copy()
            exp_data['Val'] = pd.to_numeric(exp_data['Amount'], errors='coerce').fillna(0)

            # 3. දින අනුව ගොනු කිරීම (Grouping)
            d_inc = inc_data.groupby('Date')['Val'].sum()
            d_exp = exp_data.groupby('Date')['Val'].sum()
            
            # 4. එකම Table එකකට ගෙන ඒම
            profit_df = pd.concat([d_inc, d_exp], axis=1).fillna(0)
            profit_df.columns = ['Income', 'Expense']
            profit_df['Net Profit'] = profit_df['Income'] - profit_df['Expense']
            
            # --- SUMMARY METRICS ---
            t_i = profit_df['Income'].sum()
            t_e = profit_df['Expense'].sum()
            net_p = t_i - t_e
            margin = (net_p / t_i * 100) if t_i > 0 else 0

            col1, col2, col3 = st.columns(3)
            col1.metric("Total Period Income", f"LKR {t_i:,.2f}")
            col2.metric("Total Period Expenses", f"LKR {t_e:,.2f}", delta=f"-{t_e:,.0f}", delta_color="inverse")
            col3.metric("Net Profit / Loss", f"LKR {net_p:,.2f}", delta=f"{margin:.1f}% Margin")

            st.divider()

            # --- VISUALS ---
            c_left, c_right = st.columns([2, 1])
            
            with c_left:
                st.markdown("#### 📈 Income vs Expense Trend")
                st.bar_chart(profit_df[['Income', 'Expense']])
            
            with c_right:
                st.markdown("#### 🍕 Expense Breakdown")
                # වියදම් මොනවා සඳහාද ගියේ කියලා Pie Chart එකකින් පෙන්වීම
                exp_breakdown = exp_data.groupby('Category')['Val'].sum()
                if not exp_breakdown.empty:
                    st.write(exp_breakdown) # මෙතනට පස්සේ ලස්සන Pie chart එකක් දාන්න පුළුවන්

            # --- DATA TABLE ---
            st.markdown("#### 📄 Detailed Daily Breakdown")
            st.dataframe(profit_df.sort_index(ascending=False).style.format("{:,.2f}"), use_container_width=True)
            
            # --- PDF DOWNLOAD ---
            if st.button("📥 Download P&L Report"):
                with st.spinner("Preparing Finance Report..."):
                    # මෙතනදී ඔයාගේ PDF Logic එක සම්බන්ධ කරන්න පුළුවන්
                    st.success("Finance Report Logic Connected!")
        else:
            st.info("තෝරාගත් දින පරාසය තුළ ගනුදෙනු සිදු වී නැත.")

   # --- TAB: MATERIAL GROSS EARNINGS (ENHANCED) ---
    with r_gross:
        st.subheader("📈 Material-wise Revenue Analysis")
        
        # 1. Sales records පමණක් පෙරා ගැනීම
        gross_df = df_f[df_f["Category"].str.contains("Sales Out", na=False)].copy()
        
        if not gross_df.empty:
            # 2. Material Type එක වෙන් කරගැනීම (Sand, Soil, Other)
            gross_df['Material_Type'] = gross_df['Category'].apply(
                lambda x: "Sand" if "Sand" in x else ("Soil" if "Soil" in x else "Other")
            )
            
            # 3. Numeric Conversion (Sheets වලින් එන දත්ත වල ආරක්ෂාවට)
            gross_df['Amount'] = pd.to_numeric(gross_df['Amount'], errors='coerce').fillna(0)
            gross_df['Qty_Cubes'] = pd.to_numeric(gross_df['Qty_Cubes'], errors='coerce').fillna(0)

            # 4. Grouping logic - මුදල සහ කියුබ් ගණන යන දෙකම ගමු
            summary_gross = gross_df.groupby('Material_Type').agg({
                'Amount': 'sum',
                'Qty_Cubes': 'sum'
            }).reset_index()
            
            summary_gross.columns = ['Material', 'Total Revenue (LKR)', 'Total Cubes']
            
            # --- TOP METRICS ---
            total_rev = summary_gross['Total Revenue (LKR)'].sum()
            total_vol = summary_gross['Total Cubes'].sum()
            
            c1, c2 = st.columns(2)
            c1.metric("Total Material Revenue", f"LKR {total_rev:,.2f}")
            c2.metric("Total Volume Sold", f"{total_vol:,.1f} Cubes")

            st.divider()

            # --- VISUAL ANALYSIS ---
            col_v1, col_v2 = st.columns([1, 1])
            
            with col_v1:
                st.markdown("**💰 Revenue by Material**")
                # ආදායම පෙන්වන Bar Chart එක
                st.bar_chart(data=summary_gross, x='Material', y='Total Revenue (LKR)', color="#27AE60")
                
            with col_v2:
                st.markdown("**📦 Volume by Material (Cubes)**")
                # කියුබ් ගණන පෙන්වන Bar Chart එක
                st.bar_chart(data=summary_gross, x='Material', y='Total Cubes', color="#F39C12")

            # --- DATA SUMMARY TABLE ---
            st.markdown("#### 📊 Summary Table")
            st.dataframe(summary_gross.style.format({
                "Total Revenue (LKR)": "{:,.2f}",
                "Total Cubes": "{:,.1f}"
            }), use_container_width=True)
            
            # --- DETAILED LOG ---
            with st.expander("🔍 View Detailed Sales Log"):
                req_cols = ['Date', 'Entity', 'Category', 'Qty_Cubes', 'Amount']
                available_cols = [c for c in req_cols if c in gross_df.columns]
                st.dataframe(gross_df[available_cols].sort_values('Date', ascending=False), use_container_width=True)
                
        else:
            st.info("තෝරාගත් දින පරාසය තුළ විකුණුම් (Sales) වාර්තා වී නැත.")
            
    # --- TAB: STAFF SETTLEMENT (ENHANCED) ---
    with r_staff:
        st.subheader("👷 Staff Payment & Settlement Report")
        
        # 1. Staff ලිස්ට් එක Database එකෙන් ලබා ගැනීම
        if not st.session_state.staff_db.empty:
            s_list = st.session_state.staff_db["Name"].tolist()
            sel_staff = st.selectbox("Select Staff Member", s_list, key="staff_rep_sel")
            
            # 2. Filter data (Note එකේ නම ඇති සහ Date පරාසය ඇතුළත ඇති දත්ත)
            staff_mask = df_f['Note'].str.contains(sel_staff, na=False)
            staff_rep_data = df_f[staff_mask].copy()
            
            if not staff_rep_data.empty:
                # --- SUMMARY CALCULATIONS ---
                # සේවකයාට අදාළ මුළු පැය ගණන සහ මුළු මුදල (Advances/Salary)
                t_hours = staff_rep_data["Hours"].sum() if "Hours" in staff_rep_data.columns else 0
                t_paid = staff_rep_data["Amount"].sum()
                
                c1, c2 = st.columns(2)
                c1.metric(f"Total Hours (Period)", f"{t_hours:,.1f} Hrs")
                c2.metric(f"Total Paid/Advance", f"LKR {t_paid:,.2f}")

                st.divider()

                # --- PDF & DATA DISPLAY ---
                col_btn, col_blank = st.columns([1, 2])
                with col_btn:
                    if st.button("Generate Staff Report 📄", key="gen_staff_btn", use_container_width=True):
                        with st.spinner(f"Preparing {sel_staff}'s Report..."):
                            # PDF Engine එක සම්බන්ධ කිරීම
                            fn = create_staff_pdf(sel_staff, staff_rep_data)
                            with open(fn, "rb") as f:
                                st.download_button("📥 Click to Download PDF", f, file_name=f"Staff_{sel_staff}_{f_d}.pdf")
                            st.success(f"Report for {sel_staff} is ready!")

                st.markdown(f"**Detailed Logs for {sel_staff}:**")
                # ටේබල් එකේ පෙන්විය යුතු Columns ටික විතරක් තෝරා ගැනීම
                disp_cols = ["Date", "Category", "Note", "Hours", "Amount"]
                valid_disp = [c for c in disp_cols if c in staff_rep_data.columns]
                
                st.dataframe(staff_rep_data[valid_disp].sort_values("Date", ascending=False), use_container_width=True)

            else:
                st.info(f"තෝරාගත් දින පරාසය තුළ {sel_staff} සඳහා ගනුදෙනු වාර්තා වී නැත.")
        else:
            st.warning("කරුණාකර ප්‍රථමයෙන් 'System Setup' හරහා සේවක මණ්ඩලය (Staff) ඇතුළත් කරන්න.")
            
    # --- TAB 1: VEHICLE SETTLEMENT ---
   # --- 1. වාහන ලැයිස්තුව ලබා ගනිමු ---
v_list = st.session_state.ve_db["No"].tolist() if not st.session_state.ve_db.empty else ["N/A"]

# පේජ් එක කොටස් දෙකකට බෙදා ගනිමු
r1, r2 = st.columns(2) 

with r1:
    st.subheader("🚜 Vehicle & Machine Performance Settlement")
    # වාහනය තෝරාගැනීම
    selected_ve = st.selectbox("Select Vehicle to Review", v_list, key="settle_ve")

# වාහනයක් තෝරාගෙන තිබේ නම් පමණක් දත්ත පෙන්වමු
if selected_ve and selected_ve != "N/A":
    # ඩේටාබේස් එකේ අදාළ Column එක සොයාගැනීම
    col_options = ['Entity', 'Vehicle', 'Vehicle_No', 'Machine', 'No']
    target_col = next((c for c in col_options if c in df_f.columns), None)
    
    if target_col:
        # තෝරාගත් වාහනයට අදාළ දත්ත පෙරීම
        ve_records = df_f[df_f[target_col] == selected_ve].copy()
        
        if not ve_records.empty:
            # දත්ත පිරිසිදු කිරීම (Numeric conversion)
            ve_records.columns = [c.strip() for c in ve_records.columns]
            num_fields = ['Amount', 'Qty_Cubes', 'Hours']
            for f in num_fields:
                if f in ve_records.columns:
                    ve_records[f] = pd.to_numeric(ve_records[f], errors='coerce').fillna(0)

            # ගණනය කිරීම්
            is_excavator = any(x in selected_ve.upper() for x in ["EX", "PC", "EXCAVATOR"])
            total_hours = ve_records['Hours'].sum() if 'Hours' in ve_records.columns else ve_records['Qty_Cubes'].sum()
            gross_earning = ve_records[ve_records["Type"] != "Expense"]['Amount'].sum() if is_excavator else 0.0
            fuel_exp = ve_records[ve_records["Category"].str.contains("Fuel", na=False)]["Amount"].sum()
            total_exp = ve_records[ve_records["Type"] == "Expense"]["Amount"].sum()
            net_balance = gross_earning - total_exp

            # --- දකුණු පැත්තේ Summary එක පෙන්වීම ---
            with r2:
                st.subheader("📊 Summary View")
                m1, m2 = st.columns(2)
                if is_excavator:
                    m1.metric("Total Usage", f"{total_hours:,.1f} Hrs")
                    m2.metric("Gross Revenue", f"Rs. {gross_earning:,.2f}")
                else:
                    m1.metric("Type", "Truck/Lorry")
                    m2.metric("Net Performance", f"Rs. {net_balance:,.2f}")
                
                m3, m4 = st.columns(2)
                m3.metric("Total Expenses", f"Rs. {total_exp:,.2f}", delta=f"Fuel: {fuel_exp:,.0f}")
                m4.metric("Net Balance", f"Rs. {net_balance:,.2f}")

            st.divider()

            # --- PDF සහ Detailed Table කොටස ---
            col_pdf, col_table = st.columns([1, 2])
            
            with col_pdf:
                if st.button("📥 Generate Settlement PDF", use_container_width=True):
                    with st.spinner("Generating Report..."):
                        summary_data = {
                            "Vehicle": selected_ve,
                            "Usage/Hours": f"{total_hours:,.2f}",
                            "Gross Earnings": f"Rs. {gross_earning:,.2f}",
                            "Fuel Cost": f"Rs. {fuel_exp:,.2f}",
                            "Total Expenses": f"Rs. {total_exp:,.2f}",
                            "Net Balance": f"Rs. {net_balance:,.2f}",
                            "Period": f"{f_d} to {t_d}"
                        }
                        pdf_path = create_pdf("Vehicle_Settlement", ve_records, summary_data)
                        with open(pdf_path, "rb") as f:
                            st.download_button("📩 Download PDF File", f, file_name=f"{selected_ve}_Report.pdf")

            with col_table:
                st.write(f"**Logs for {selected_ve}:**")
                disp_cols = ['Date', 'Category', 'Note', 'Amount']
                valid_cols = [c for c in disp_cols if c in ve_records.columns]
                st.dataframe(ve_records[valid_cols].sort_values("Date", ascending=False), use_container_width=True)
                
        else:
            st.info(f"තෝරාගත් කාල සීමාව තුළ {selected_ve} සඳහා දත්ත නැත.")
    else:
        st.error("Database Error: Column mapping failed.")
                # --- මෙන්න මෙතනින් පටන් ගන්න (Landowner Settlement Section) ---
        
      # --- Landowner Settlement Section ---
        st.divider()
        st.subheader("⛰️ Landowner Settlement")

        # 1. ලියාපදිංචි landowner ලා හෝ දැනට data වල ඉන්න අයව තෝරාගැනීම
        reg_landowners = []
        if 'landowners' in st.session_state and st.session_state.landowners:
            reg_landowners = [owner.get('Name') for owner in st.session_state.landowners if owner.get('Name')]
        
        # ලැයිස්තුව හිස්නම් දැනට තියෙන Data වලින් අරගන්නවා
        if not reg_landowners and not st.session_state.df.empty:
            reg_landowners = [name for name in st.session_state.df['Entity'].unique().tolist() if name and str(name).lower() != 'nan']

        if not reg_landowners: reg_landowners = ["N/A"]

        # 2. Dropdown Selector
        selected_lo = st.selectbox("Select Landowner", options=reg_landowners, key="lo_settle_final")

        if selected_lo and selected_lo != "N/A":
            search_name = str(selected_lo).strip()
            
            # --- FILTERING LOGIC ---
            # Entity එකේ නම තිබීම හෝ Note එකේ නම සඳහන් වීම (ඔයාගේ mask logic එක)
            mask_ent = df_f['Entity'].astype(str).str.strip().str.lower() == search_name.lower()
            mask_nt = df_f['Note'].fillna("").astype(str).str.contains(search_name, case=False)
            
            lo_records = df_f[mask_ent | mask_nt].copy()
            
            if not lo_records.empty:
                # Amount පිරිසිදු කිරීම (Comma සහ Rs. අයින් කර numeric කිරීම)
                lo_records['Amount'] = pd.to_numeric(
                    lo_records['Amount'].astype(str).str.replace(',', '').str.replace('Rs.', ''), 
                    errors='coerce'
                ).fillna(0)
                
                # ගණනය කිරීම්: අපිට ලැබුණු බඩු (Payable) vs අපි දුන්න සල්ලි (Paid)
                # 'Inward' හෝ 'Stock In' කියන්නේ අපි බඩු ගත්ත ඒවා (අපි ගෙවිය යුතුයි)
                # 'Advance' හෝ 'Payment' කියන්නේ අපි දුන්න සල්ලි
                total_payable = lo_records[lo_records['Category'].str.contains('Inward|Stock In', case=False, na=False)]['Amount'].sum()
                total_paid = lo_records[lo_records['Category'].str.contains('Advance|Payment|Salary', case=False, na=False)]['Amount'].sum()
                lo_balance = total_payable - total_paid

                # Summary Metrics
                m1, m2, m3 = st.columns(3)
                m1.metric("Total Payable (බඩු සඳහා)", f"Rs. {total_payable:,.2f}")
                m2.metric("Total Paid (ගෙවූ මුදල)", f"Rs. {total_paid:,.2f}")
                m3.metric("Balance to Pay", f"Rs. {lo_balance:,.2f}", delta_color="inverse")

                st.divider()

                # --- PDF GENERATION ---
                if st.button("📄 Generate Landowner Report"):
                    with st.spinner("Preparing Report..."):
                        lo_summary = {
                            "Landowner": search_name,
                            "Total Payable": f"Rs. {total_payable:,.2f}",
                            "Total Paid": f"Rs. {total_paid:,.2f}",
                            "Current Balance": f"Rs. {lo_balance:,.2f}",
                            "Period": f"{f_d} to {t_d}"
                        }
                        
                        try:
                            # Universal create_pdf function එක call කිරීම
                            pdf_path = create_pdf(f"Landowner_{search_name}", lo_records, lo_summary)
                            with open(pdf_path, "rb") as f:
                                st.download_button(
                                    label="⬇️ Download Settlement PDF",
                                    data=f,
                                    file_name=f"Settlement_{search_name}.pdf",
                                    mime="application/pdf"
                                )
                        except Exception as e:
                            st.error(f"PDF Error: {e}")

                # Detailed Table පෙන්වීම
                st.write(f"**Transaction Breakdown for {search_name}:**")
                disp_cols = ['Date', 'Category', 'Entity', 'Qty_Cubes', 'Amount', 'Note']
                valid_cols = [c for c in disp_cols if c in lo_records.columns]
                st.dataframe(lo_records[valid_cols].sort_values("Date", ascending=False), use_container_width=True)
                
            else:
                st.info(f"'{search_name}' නම යටතේ කිසිදු ගනුදෙනුවක් හමු නොවීය.")
                        
   # --- TAB 2: DRIVER SUMMARY (ENHANCED) ---
    with r2:
        st.subheader("👤 Driver Salary & Advance Statement")
        
        # 1. Driver list එක Database එකෙන් ලබා ගැනීම
        dr_list = st.session_state.dr_db["Name"].tolist() if not st.session_state.dr_db.empty else []
        sel_dr = st.selectbox("Select Driver", dr_list, key="dr_report_selector")
        
        if sel_dr:
            # නම පාවිච්චි කරලා Filter කිරීම (Case insensitive)
            search_dr = str(sel_dr).strip()
            # මුලින්ම Date filter කරපු df_f එකෙන් ගන්නවා
            dr_rep = df_f[df_f["Note"].fillna("").astype(str).str.contains(search_dr, case=False)].copy()
            
            if not dr_rep.empty:
                # 2. වැදගත්ම දේ: පඩි සහ ඇඩ්වාන්ස් විතරක් වෙන් කිරීම
                # Category එකේ 'Salary', 'Advance', 'Payroll', 'D.Advance' තියෙන ඒවා විතරක් ගනී
                dr_rep = dr_rep[dr_rep['Category'].str.contains('Salary|Advance|Payroll|D.Advance', case=False, na=False)].copy()
                
                # 3. Amount එක පිරිසිදු කර ගණනය කිරීම
                dr_rep['Clean_Amount'] = pd.to_numeric(dr_rep['Amount'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
                total_paid = dr_rep['Clean_Amount'].sum()
                
                # Metric display
                st.metric(f"Total Paid to {search_dr}", f"LKR {total_paid:,.2f}")
                
                if not dr_rep.empty:
                    # Table එක පෙන්වීම
                    cols_to_show = ['Date', 'Category', 'Note', 'Amount']
                    existing_cols = [c for c in cols_to_show if c in dr_rep.columns]
                    st.dataframe(dr_rep[existing_cols].sort_values("Date", ascending=False), use_container_width=True)
                    
                    # --- PDF GENERATION ---
                    if st.button("📄 Generate Driver Statement PDF"):
                        with st.spinner("Preparing PDF Report..."):
                            summary_data = {
                                "Driver Name": search_dr,
                                "Period": f"{f_d} to {t_d}", # උඩින් date_input වල තියෙන variables
                                "Total Paid": f"Rs. {total_paid:,.2f}",
                                "Status": "Salary & Advance Only"
                            }
                            
                            # PDF හදන function එක call කිරීම
                            try:
                                # create_pdf හෝ create_driver_pdf (ඔයාගේ function නම අනුව)
                                pdf_fn = create_pdf(f"Driver_Settlement_{search_dr}", dr_rep, summary_data)
                                with open(pdf_fn, "rb") as f:
                                    st.download_button("⬇️ Download PDF Report", f, file_name=f"Driver_{search_dr}.pdf")
                            except Exception as e:
                                st.error(f"PDF Error: {e}")
                else:
                    st.info(f"තෝරාගත් කාල සීමාව තුළ {search_dr} සඳහා පඩි හෝ ඇඩ්වාන්ස් වාර්තා වී නැත.")
            else:
                st.warning(f"{search_dr} සම්බන්ධ කිසිදු දත්තයක් හමු නොවීය.")

    # --- TAB 3: DAILY LOG (ENHANCED) ---
    with r3:
        st.subheader("📑 Master Daily Transaction Log")
        
        if not df_f.empty:
            # 1. අලුත්ම දත්ත උඩින්ම පේන විදිහට දින අනුව පිළිවෙළට සකස් කිරීම
            log_display = df_f.sort_values(by='Date', ascending=False).copy()
            
            # 2. අවශ්‍ය Column ටික විතරක් පිළිවෙළකට තෝරා ගැනීම
            all_cols = ['Date', 'Type', 'Category', 'Entity', 'Qty_Cubes', 'Amount', 'Note']
            existing_log_cols = [c for c in all_cols if c in log_display.columns]
            
            # 3. Numeric Columns ලස්සනට පෙන්වීම (Formatting)
            # Amount එකට කොමා (Comma) දාලා රුපියල් විදිහට පෙන්වමු
            styled_log = log_display[existing_log_cols].style.format({
                'Amount': "{:,.2f}",
                'Qty_Cubes': "{:,.1f}"
            })

            # 4. Table එක Display කිරීම
            st.dataframe(styled_log, use_container_width=True, height=500)
            
            # --- SEARCH & EXPORT ---
            st.divider()
            c1, c2 = st.columns([2, 1])
            
            with c1:
                st.info(f"Showing {len(log_display)} records from {f_d} to {t_d}")
            
            with c2:
                # සම්පූර්ණ Filter කරපු දත්ත ටික Excel එකකට ගන්න පුළුවන් විදිහට (CSV)
                csv = log_display.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Export Log to CSV",
                    data=csv,
                    file_name=f"Daily_Log_{f_d}_to_{t_d}.csv",
                    mime='text/csv',
                    use_container_width=True
                )
        else:
            st.warning("තෝරාගත් කාල සීමාව තුළ කිසිදු ගනුදෙනුවක් වාර්තා වී නැත.")
            
# --- TAB 4: SHED REPORT (ENHANCED) ---
    with r4:
        st.subheader("⛽ Fuel & Shed Settlement Report")
        
        # 1. Fuel සහ Shed වලට අදාළ දත්ත පමණක් වෙන් කරගැනීම
        # Category එකේ 'Fuel' හෝ 'Shed' ඇති ඒවා පෙරමු
        shed_f = df_f[df_f["Category"].str.contains("Fuel|Shed", na=False, case=False)].copy()
        
        if not shed_f.empty:
            # Numeric conversion (ගණනය කිරීම් වලට පෙර)
            shed_f['Amount'] = pd.to_numeric(shed_f['Amount'], errors='coerce').fillna(0)
            # සමහර විට Qty_Cubes එකේ තමයි තෙල් ලීටර් ගණන ලියන්නේ
            shed_f['Qty_Cubes'] = pd.to_numeric(shed_f['Qty_Cubes'], errors='coerce').fillna(0)
            
            # 2. ගණනය කිරීම්
            # තෙල් ගහපු මුළු බිල (Fuel Entry / Fuel Out)
            f_bill = shed_f[shed_f["Category"].str.contains("Fuel", case=False)]["Amount"].sum()
            # ෂෙඩ් එකට ගෙවපු මුළු සල්ලි (Shed Payment)
            p_paid = shed_f[shed_f["Category"].str.contains("Shed Payment", case=False)]["Amount"].sum()
            # මුළු තෙල් ලීටර් ගණන
            total_liters = shed_f[shed_f["Category"].str.contains("Fuel", case=False)]["Qty_Cubes"].sum()
            
            # 3. UI Metrics පෙන්වීම
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Fuel Bill", f"Rs. {f_bill:,.2f}")
            c2.metric("Total Paid to Shed", f"Rs. {p_paid:,.2f}", delta=f"-{p_paid:,.0f}")
            c3.metric("Outstanding Debt", f"Rs. {f_bill - p_paid:,.2f}", delta_color="inverse")
            
            st.info(f"⛽ Total Fuel Consumption: **{total_liters:,.1f} Liters**")
            st.divider()

            # 4. Shed-wise Summary (සමහර විට Entity එකේ ෂෙඩ් එකේ නම තිබුණොත්)
            if 'Entity' in shed_f.columns:
                st.markdown("#### 🏢 Summary by Shed / Fuel Station")
                shed_summary = shed_f.groupby('Entity')['Amount'].sum().reset_index()
                st.dataframe(shed_summary.style.format({'Amount': "{:,.2f}"}), use_container_width=True)

            # 5. Detailed Transaction Log
            st.markdown("#### 📄 Detailed Fuel Log")
            disp_cols = ['Date', 'Category', 'Entity', 'Qty_Cubes', 'Amount', 'Note']
            existing_cols = [c for c in disp_cols if c in shed_f.columns]
            st.dataframe(shed_f[existing_cols].sort_values("Date", ascending=False), use_container_width=True)
            
            # 6. PDF Button
            if st.button("📥 Download Shed Report PDF"):
                summary_data = {
                    "Report Type": "Fuel & Shed Settlement",
                    "Total Fuel Bill": f"Rs. {f_bill:,.2f}",
                    "Total Paid": f"Rs. {p_paid:,.2f}",
                    "Balance Due": f"Rs. {f_bill - p_paid:,.2f}",
                    "Total Liters": f"{total_liters:,.1f} L"
                }
                pdf_fn = create_pdf("Shed_Report", shed_f, summary_data)
                with open(pdf_fn, "rb") as f:
                    st.download_button("📩 Download PDF", f, file_name=f"Shed_Report_{f_d}.pdf")
        else:
            st.info("තෝරාගත් කාල සීමාව තුළ තෙල් වලට අදාළ ගනුදෙනු කිසිවක් නැත.")

# --- 10. SYSTEM SETUP (මේ කොටස අලුතින් ඇතුළත් කරන්න) ---
elif menu == "⚙️ System Setup":
        st.markdown("<h2 style='color: #2E86C1;'>⚙️ System Configuration</h2>", unsafe_allow_html=True)
        
        # ටැබ් තුනක් සාදමු - වාහන, ඩ්‍රයිවර්ස්ලා සහ අනෙකුත් සේවකයෝ
        setup_tab1, setup_tab2, setup_tab3 = st.tabs(["🚜 Vehicles", "👷 Drivers", "👥 Staff Management"])

        # --- TAB 1: VEHICLES ---
        with setup_tab1:
            st.subheader("🚜 Add New Vehicle / Machine")
            with st.form("v_setup_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    v_no = st.text_input("Vehicle Number")
                    v_type = st.selectbox("Vehicle Type", ["Tipper", "Excavator", "JCB", "Tractor", "Other"])
                with col2:
                    v_owner = st.text_input("Owner Name")
                    v_rate = st.number_input("Rate per Unit", min_value=0.0)
                
                if st.form_submit_button("✅ Register Vehicle"):
                    if v_no:
                        new_v = pd.DataFrame([[v_no, v_type, v_owner, v_rate]], columns=["No", "Type", "Owner", "Rate_Per_Unit"])
                        st.session_state.ve_db = pd.concat([st.session_state.ve_db, new_v], ignore_index=True)
                        save_all(); st.success(f"Vehicle {v_no} registered!"); st.rerun()

            if not st.session_state.ve_db.empty:
                st.divider()
                ve_to_manage = st.selectbox("Select Vehicle to Manage", st.session_state.ve_db["No"].tolist())
                if st.button("Delete Vehicle ❌", key="del_ve"):
                    st.session_state.ve_db = st.session_state.ve_db[st.session_state.ve_db["No"] != ve_to_manage]
                    save_all(); st.rerun()

        # --- TAB 2: DRIVERS ---
        with setup_tab2:
            st.subheader("👷 Register New Driver / Operator")
            
            with st.form("d_setup_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    d_name = st.text_input("Full Name").strip()
                    d_phone = st.text_input("Contact Number (e.g. 0771234567)")
                with col2:
                    d_salary = st.number_input("Standard Daily Salary (LKR)", min_value=0.0, step=500.0)
                
                submitted_d = st.form_submit_button("✅ Register Driver")
                
                if submitted_d:
                    if d_name:
                        # 1. Duplicate check (නම අනුව)
                        if not st.session_state.dr_db.empty and d_name.lower() in st.session_state.dr_db["Name"].str.lower().values:
                            st.error(f"'{d_name}' නම දැනටමත් පද්ධතියේ පවතී!")
                        else:
                            # 2. අලුත් ඩ්‍රයිවර් එකතු කිරීම
                            new_d = pd.DataFrame([[d_name, d_phone, d_salary]], 
                                               columns=["Name", "Phone", "Daily_Salary"])
                            st.session_state.dr_db = pd.concat([st.session_state.dr_db, new_d], ignore_index=True)
                            
                            save_all()
                            st.success(f"Driver {d_name} registered successfully!")
                            st.rerun()
                    else:
                        st.warning("කරුණාකර ඩ්‍රයිවර්ගේ නම ඇතුළත් කරන්න.")

            # --- TAB 2: DRIVERS (As it was) ---
        with setup_tab2:
            st.subheader("👷 Register New Driver / Operator")
            
            with st.form("d_setup_form_new", clear_on_submit=True): # මෙතන නම පොඩ්ඩක් වෙනස් කළා
                col1, col2 = st.columns(2)
                with col1:
                    d_name = st.text_input("Driver Name").strip()
                    d_phone = st.text_input("Contact Number")
                with col2:
                    d_salary = st.number_input("Daily Salary (LKR)", min_value=0.0, step=100.0)
                
                if st.form_submit_button("✅ Register Driver"):
                    if d_name:
                        # Duplicate check
                        if not st.session_state.dr_db.empty and d_name in st.session_state.dr_db["Name"].values:
                            st.error(f"'{d_name}' දැනටමත් ඇතුළත් කර ඇත.")
                        else:
                            new_d = pd.DataFrame([[d_name, d_phone, d_salary]], columns=["Name", "Phone", "Daily_Salary"])
                            st.session_state.dr_db = pd.concat([st.session_state.dr_db, new_d], ignore_index=True)
                            save_all()
                            st.success(f"Driver {d_name} registered!")
                            st.rerun()

            # දැනට ඉන්න අයව බලාගන්න සහ Delete කරන්න
            if not st.session_state.dr_db.empty:
                st.divider()
                st.dataframe(st.session_state.dr_db, use_container_width=True)
                
                with st.expander("🗑️ Manage Drivers"):
                    dr_to_manage = st.selectbox("Select Driver to Remove", st.session_state.dr_db["Name"].tolist(), key="del_dr_sel")
                    if st.button("Delete Driver ❌"):
                        st.session_state.dr_db = st.session_state.dr_db[st.session_state.dr_db["Name"] != dr_to_manage]
                        save_all(); st.rerun()
                        
        # --- TAB 3: STAFF MANAGEMENT ---
        with setup_tab3:
            st.subheader("👷 Register Plant Staff Members")
            with st.form("staff_setup_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    s_name = st.text_input("Staff Member Name").strip()
                    s_pos = st.selectbox("Position", ["Helper", "Operator", "Supervisor", "Security", "Other"])
                with col2:
                    s_rate = st.number_input("Daily Rate (LKR)", min_value=0.0, step=100.0)
                
                if st.form_submit_button("✅ Register Staff Member"):
                    if s_name:
                        # Duplicate check
                        if not st.session_state.staff_db.empty and s_name in st.session_state.staff_db["Name"].values:
                            st.error(f"'{s_name}' දැනටමත් ලියාපදිංචි කර ඇත.")
                        else:
                            new_s = pd.DataFrame([{"Name": s_name, "Position": s_pos, "Daily_Rate": s_rate}])
                            st.session_state.staff_db = pd.concat([st.session_state.staff_db, new_s], ignore_index=True)
                            save_all()
                            st.success(f"Staff member {s_name} registered!")
                            st.rerun()
                    else:
                        st.error("කරුණාකර නමක් ඇතුළත් කරන්න.")

            # දැනට ඉන්න Staff ලිස්ට් එක කළමනාකරණය
            if not st.session_state.staff_db.empty:
                st.divider()
                st.write("### 📋 Current Staff List")
                st.dataframe(st.session_state.staff_db, use_container_width=True)
                
                # පද්ධතියෙන් ඉවත් කිරීමේ කොටස (Expander එකක් දැම්මා ආරක්ෂාවට)
                with st.expander("🗑️ Remove Staff Member"):
                    s_to_del = st.selectbox("Select Member to Remove", st.session_state.staff_db["Name"].tolist(), key="staff_del_sel")
                    if st.button("Confirm Removal ❌", key="del_staff_btn"):
                        st.session_state.staff_db = st.session_state.staff_db[st.session_state.staff_db["Name"] != s_to_del]
                        save_all()
                        st.warning(f"Staff member {s_to_del} removed.")
                        st.rerun()
                    
# --- මේක වෙනම Menu එකක් විදිහට පල්ලෙහායින් දාන්න ---
elif menu == "👤 Manage Landowners":
        st.markdown("<h2 style='color: #1E8449;'>👤 Landowner Management</h2>", unsafe_allow_html=True)
        
        # Tabs තුනක් හදමු - Register, Advance සහ View
        l_tab1, l_tab2, l_tab3 = st.tabs(["🆕 Register Landowner", "💰 Give Advance", "📋 View All"])

        # --- TAB 1: Register New Landowner ---
        with l_tab1:
            st.subheader("Add a New Landowner to System")
            with st.form("landowner_reg_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    l_name = st.text_input("Full Name").strip()
                    l_addr = st.text_input("Land Location / Address")
                with col2:
                    l_cont = st.text_input("Contact Number")
                    l_rate = st.number_input("Rate Per Cube (LKR)", min_value=0.0, step=100.0)
                
                if st.form_submit_button("✅ Register Landowner"):
                    if l_name:
                        # 1. Duplicate check (නම දැනටමත් තියෙනවද බලමු)
                        if not st.session_state.lo_db.empty and l_name.lower() in st.session_state.lo_db["Name"].str.lower().values:
                            st.error(f"Landowner '{l_name}' දැනටමත් පද්ධතියේ පවතී!")
                        else:
                            # 2. අලුත් row එකක් හදනවා
                            new_lo = pd.DataFrame([{
                                "Name": l_name, 
                                "Address": l_addr, 
                                "Contact": l_cont, 
                                "Rate_Per_Cube": l_rate
                            }])
                            
                            st.session_state.lo_db = pd.concat([st.session_state.lo_db, new_lo], ignore_index=True)
                            
                            # File එකට සේව් කිරීම
                            st.session_state.lo_db.to_csv(LANDOWNER_FILE, index=False)
                            st.success(f"Registered {l_name} with Rate: LKR {l_rate:,.2f} per Cube!")
                            st.rerun()
                    else:
                        st.error("Landowner Name is required!")

        # --- TAB 2: Give Advance ---
        with l_tab2:
            st.subheader("Record Advance Payment")
            if not st.session_state.lo_db.empty:
                with st.form("lo_advance_form", clear_on_submit=True):
                    lo_names = st.session_state.lo_db["Name"].tolist()
                    selected_lo = st.selectbox("Select Landowner", lo_names)
                    adv_date = st.date_input("Date", datetime.now().date())
                    adv_amount = st.number_input("Advance Amount (LKR)", min_value=0.0, step=1000.0)
                    adv_note = st.text_input("Reference Note (Cheque No / Cash)")

                    if st.form_submit_button("✅ Save Advance Payment"):
                        if adv_amount > 0:
                            # Main DataFrame (Master Ledger) එකට Entry එක එකතු කිරීම
                            new_entry = {
                                "ID": str(int(time.time())), # Unique ID එකක්
                                "Date": adv_date.strftime("%Y-%m-%d"),
                                "Type": "Expense",
                                "Category": "Landowner Advance",
                                "Entity": selected_lo,
                                "Note": adv_note,
                                "Amount": adv_amount,
                                "Qty_Cubes": 0,
                                "Status": "Paid"
                            }
                            # df එකට එකතු කර සේව් කිරීම
                            st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_entry])], ignore_index=True)
                            save_all()
                            st.success(f"LKR {adv_amount:,.2f} advance paid to {selected_lo} recorded!")
                            st.rerun()
            else:
                st.info("කරුණාකර ප්‍රථමයෙන් Landowner කෙනෙකු රෙජිස්ටර් කරන්න.")

        # --- TAB 3: View & Manage ---
        with l_tab3:
            st.subheader("Registered Landowners List")
            if not st.session_state.lo_db.empty:
                # රේට් එක ලස්සනට පේන්න Format කරපු table එකක් පෙන්වමු
                st.dataframe(st.session_state.lo_db.style.format({"Rate_Per_Cube": "{:,.2f}"}), use_container_width=True)
                
                st.divider()
                with st.expander("🗑️ Danger Zone: Remove Landowner"):
                    lo_to_del = st.selectbox("Select Landowner to Remove", st.session_state.lo_db["Name"].tolist(), key="del_lo_box")
                    if st.button("Confirm Delete ❌", key="del_lo_btn"):
                        st.session_state.lo_db = st.session_state.lo_db[st.session_state.lo_db["Name"] != lo_to_del]
                        st.session_state.lo_db.to_csv(LANDOWNER_FILE, index=False)
                        st.warning(f"Landowner {lo_to_del} removed from the system.")
                        st.rerun()
                        
# --- 12. staff payroll (මේ කොටස අලුතින් ඇතුළත් කරන්න) ---
elif menu == "👷 Staff Payroll":
        st.markdown("<h2 style='color: #2E86C1;'>👷 Staff Salary & Advance Management</h2>", unsafe_allow_html=True)
        
        # සේවකයන්ගේ නම් ලිස්ට් එක ගැනීම
        if not st.session_state.staff_db.empty:
            s_names = st.session_state.staff_db["Name"].tolist()
            
            with st.form("staff_pay", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    member = st.selectbox("Select Staff Member", s_names)
                    pay_date = st.date_input("Date", datetime.now().date())
                    
                    # සේවකයාගේ Daily Rate එක Staff Database එකෙන් හොයා ගැනීම
                    current_rate = st.session_state.staff_db[st.session_state.staff_db["Name"] == member]["Daily_Rate"].values[0]
                    st.info(f"Registered Rate: LKR {current_rate:,.2f} per day")
                    
                with col2:
                    pay_type = st.selectbox("Payment Type", ["Salary", "Advance", "Food/Other"])
                    days = st.number_input("Work Days (Enter 0 if Advance/Food)", min_value=0, step=1)
                    
                    # පඩිය (Salary) නම් පමණක් auto calculate කිරීම, අනිත් ඒවට manual amount එකක් දිය හැක
                    suggested_amt = float(days * current_rate) if pay_type == "Salary" else 0.0
                    amount = st.number_input("Amount (LKR)", min_value=0.0, value=suggested_amt)
                
                note = st.text_input("Additional Note (Reference / Remarks)")
                
                if st.form_submit_button("✅ Save Staff Payment"):
                    if amount > 0:
                        new_staff_data = {
                            "ID": str(int(time.time())), 
                            "Date": pay_date.strftime("%Y-%m-%d"), 
                            "Time": datetime.now().strftime("%H:%M:%S"), 
                            "Type": "Expense",
                            "Category": f"Staff {pay_type}", 
                            "Entity": member, # "Plant General" වෙනුවට මෙතනට සේවකයාගේ නම දාමු
                            "Note": f"Days: {days} | {note}", 
                            "Amount": amount,
                            "Qty_Cubes": 0, "Fuel_Ltr": 0, 
                            "Hours": days, 
                            "Rate_At_Time": current_rate, 
                            "Status": "Paid"
                        }
                        
                        st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_staff_data])], ignore_index=True)
                        save_all()
                        st.success(f"LKR {amount:,.2f} {pay_type} payment saved for {member}")
                        st.rerun()
                    else:
                        st.error("කරුණාකර මුදල (Amount) ඇතුළත් කරන්න.")
        else:
            st.warning("කරුණාකර ප්‍රථමයෙන් System Setup එකේ Staff Members ලියාපදිංචි කරන්න.")

# --- 11. DATA MANAGER (EDIT / DELETE) ---
elif menu == "⚙️ Data Manager":
    st.markdown(f"<h2 style='color: #E67E22;'>⚙️ Master Data Manager</h2>", unsafe_allow_html=True)
    st.info("මෙහිදී ඔබට වැරදිලාවත් ඇතුළත් කළ දත්ත Edit කිරීමට හෝ Delete කිරීමට හැකියාව ඇත.")
    
    if st.session_state.df.empty:
        st.warning("පද්ධතියේ දත්ත කිසිවක් හමු නොවීය.")
    else:
        # 1. සෙවුම් කොටස
        col_s1, col_s2 = st.columns([1, 2])
        with col_s1:
            search_id = st.text_input("Enter Record ID to Search", placeholder="Ex: 171165...")
        
        # DataFrame එකේ ID column එක string හෝ numeric විය හැක, ඒ නිසා දෙකම check කරමු
        record_idx = st.session_state.df.index[st.session_state.df["ID"].astype(str) == str(search_id)].tolist()
        
        if search_id and record_idx:
            idx = record_idx[0]
            record = st.session_state.df.loc[idx]
            
            st.success(f"Record Found for ID: {search_id}")
            
            # පවතින දත්ත පෙන්වීම
            st.markdown("#### 📋 Current Record Details")
            st.dataframe(pd.DataFrame([record]), use_container_width=True)
            
            st.divider()
            
            edit_col, del_col = st.columns(2)
            
            # --- EDIT SECTION ---
            with edit_col:
                st.subheader("📝 Edit Record")
                with st.form("edit_record_form", clear_on_submit=False):
                    # Date එක string එකක් නම් එය date object එකක් බවට පත් කිරීම
                    try:
                        current_date = pd.to_datetime(record["Date"]).date()
                    except:
                        current_date = datetime.now().date()

                    u_date = st.date_input("Update Date", value=current_date)
                    u_entity = st.text_input("Update Vehicle / Entity", value=str(record["Entity"]))
                    u_note = st.text_input("Update Note", value=str(record["Note"]))
                    
                    c1, c2 = st.columns(2)
                    with c1:
                        u_amount = st.number_input("Amount (LKR)", value=float(record.get("Amount", 0)))
                        u_qty = st.number_input("Qty (Cubes)", value=float(record.get("Qty_Cubes", 0)))
                    with c2:
                        u_hours = st.number_input("Hours / Days", value=float(record.get("Hours", 0)))
                        u_rate = st.number_input("Rate Used", value=float(record.get("Rate_At_Time", 0)))
                    
                    if st.form_submit_button("💾 Save Changes"):
                        st.session_state.df.at[idx, "Date"] = u_date.strftime("%Y-%m-%d")
                        st.session_state.df.at[idx, "Entity"] = u_entity
                        st.session_state.df.at[idx, "Note"] = u_note
                        st.session_state.df.at[idx, "Amount"] = u_amount
                        st.session_state.df.at[idx, "Qty_Cubes"] = u_qty
                        st.session_state.df.at[idx, "Hours"] = u_hours
                        st.session_state.df.at[idx, "Rate_At_Time"] = u_rate
                        
                        save_all() # CSV/Sheets වලට save කිරීම
                        st.balloons()
                        st.success("Record updated successfully!")
                        st.rerun()

            # --- DELETE SECTION ---
            with del_col:
                st.subheader("🗑️ Delete Record")
                st.warning("ප්‍රවේසමෙන්! මෙය මැකූ පසු නැවත ලබාගත නොහැක.")
                
                # Delete කරන්න කලින් තව පාරක් අහන එක ආරක්ෂිතයි
                confirm_del = st.checkbox("I want to delete this record permanently.")
                if st.button("🔥 Confirm Permanent Delete", disabled=not confirm_del):
                    st.session_state.df = st.session_state.df.drop(idx).reset_index(drop=True)
                    save_all()
                    st.success(f"Record {search_id} deleted successfully!")
                    st.rerun()
        
        elif search_id:
            st.error("නොගැලපෙන ID එකකි. කරුණාකර පහත වගුවෙන් නිවැරදි ID එක පරීක්ෂා කරන්න.")

        # --- VIEW TABLE ---
        st.divider()
        st.write("🔍 All Recent Transactions (Use ID column to Edit/Delete):")
        # ID, Date, Entity, Amount වගේ වැදගත් දේවල් මුලට පේන්න හදමු
        display_df = st.session_state.df.sort_values(by="Date", ascending=False)
        st.dataframe(display_df, use_container_width=True, height=400)
