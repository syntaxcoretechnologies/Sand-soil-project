import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
from fpdf import FPDF

# --- 1. LOGIN CREDENTIALS ---
USERS = {
    "ksdadmin": {"password": "ksd7979", "role": "admin"},
    "ksd": {"password": "ksd123", "role": "user"}
}
# --- 2. SUPABASE CONNECTION ---
# Streamlit Secrets (Settings > Secrets) වල ඔයාගේ URL සහ KEY එක තියෙන්න ඕනේ.
try:
    from st_supabase_connection import SupabaseConnection
    conn = st.connection("supabase", type=SupabaseConnection)
except Exception as e:
    st.error("Supabase Connection Error! Please check your Streamlit Secrets.")
    
# --- 2. CONFIG & TABLE NAMES (CSV වෙනුවට දැන් තියෙන්නේ Cloud Tables) ---
SHOP_NAME = "K. SIRIWARDHANA SAND CONSTRUCTION PRO"

# මේවා තමයි අපි Supabase එකේ හදපු Table Names
TABLE_MASTER = "master_log"
TABLE_VEHICLES = "vehicles"
TABLE_DRIVERS = "drivers"
TABLE_LANDOWNERS = "landowners"

# --- 2. DATA ENGINE (Cloud Updated) ---
def load_data(table_name, cols):
    """CSV වෙනුවට Cloud Table එකෙන් දත්ත load කරයි"""
    try:
        # Supabase එකෙන් table එකේ තියෙන ඔක්කොම දත්ත ගන්නවා
        response = conn.table(table_name).select("*").execute()
        d = pd.DataFrame(response.data)
        
        # Table එක හිස් නම් (මුලින්ම දත්ත දාද්දී) හිස් DataFrame එකක් හදනවා
        if d.empty:
            return pd.DataFrame(columns=cols)
            
        # ඔයාගේ පරණ Date logic එකමයි: String එකක් විදිහට එන Date එක Python Date එකක් කරනවා
        if 'Date' in d.columns:
            d['Date'] = pd.to_datetime(d['Date']).dt.date
            
        # පරණ කෝඩ් එකේ තිබ්බ විදිහටම අඩුවෙන Columns තිබුණොත් ඒවාට 0 දානවා
        for col in cols:
            if col not in d.columns: 
                d[col] = 0
                
        return d
    except Exception as e:
        # මොකක් හරි Error එකක් ආවොත් පරණ විදිහටම හිස් DataFrame එකක් දෙනවා
        return pd.DataFrame(columns=cols)
        
# --- 3. SAVE ENGINE (Cloud Updated) ---
# --- පරණ save_all වෙනුවට මේක දාන්න ---
def save_master_record(record_dict):
    """අලුත් Master Log Record එකක් සේව් කරලා Local List එකටත් එකතු කරයි"""
    try:
        data_to_save = record_dict.copy()
        if 'id' in data_to_save: del data_to_save['id']
        
        # Date එක string එකක් කරන එක වඩාත් ආරක්ෂිතයි
        if 'Date' in data_to_save: 
            data_to_save['Date'] = str(data_to_save['Date'])
        
        # 1. Supabase එකට දත්ත යවනවා
        conn.table("master_log").insert(data_to_save).execute()
        
        # 2. Local DataFrame එකටත් අලුත් පේළිය එකතු කරනවා (එතකොටයි එසැණින් පේන්නේ)
        new_row = pd.DataFrame([data_to_save])
        st.session_state.df = pd.concat([st.session_state.df, new_row], ignore_index=True)
        
        st.success("✅ Cloud Synced Successfully!")
        st.rerun() 
    except Exception as e:
        st.error(f"❌ Cloud Save Error: {e}")

def save_setup_item(table_name, item_dict):
    """Setup (Vehicles/Drivers/Landowners) දත්ත සේව් කරලා Local DB එකත් අප්ඩේට් කරයි"""
    try:
        data_to_save = item_dict.copy()
        if 'id' in data_to_save: del data_to_save['id']
        
        # 1. Supabase එකට දත්ත යැවීම
        conn.table(table_name).insert(data_to_save).execute()
        
        # 2. අදාළ Local Database එක අප්ඩේට් කිරීම
        new_row = pd.DataFrame([data_to_save])
        
        if table_name == "vehicles":
            st.session_state.ve_db = pd.concat([st.session_state.ve_db, new_row], ignore_index=True)
        elif table_name == "drivers":
            st.session_state.dr_db = pd.concat([st.session_state.dr_db, new_row], ignore_index=True)
        elif table_name == "landowners":
            st.session_state.lo_db = pd.concat([st.session_state.lo_db, new_row], ignore_index=True)
        elif table_name == "staff":
            st.session_state.staff_db = pd.concat([st.session_state.staff_db, new_row], ignore_index=True)

        st.success(f"✅ {table_name} Added!")
        st.rerun()
    except Exception as e:
        st.error(f"❌ Setup Save Error: {e}")

# --- 4. SESSION STATE (Cloud Initialization) ---

# Master Log එකේ තියෙන්න ඕනේ Columns ටික (SQL Table එකේ තියෙන විදිහටම)
cols_master = ["id", "Date", "Time", "Type", "Category", "Entity", "Note", "Amount", "Qty_Cubes", "Fuel_Ltr", "Hours", "Rate_At_Time", "Status"]

# --- දත්ත Cloud එකෙන් ලෝඩ් කිරීම ---

# 1. Master Log එක ලෝඩ් කිරීම
if 'df' not in st.session_state:
    # TABLE_MASTER කියන්නේ "master_log" කියන එක (අපි කලින් හදපු variable එක)
    st.session_state.df = load_data("master_log", cols_master)

# 2. Vehicles දත්ත ලෝඩ් කිරීම
if 've_db' not in st.session_state:
    st.session_state.ve_db = load_data("vehicles", ["No", "Type", "Owner", "Rate_Per_Unit"])

# 3. Drivers දත්ත ලෝඩ් කිරීම
if 'dr_db' not in st.session_state:
    st.session_state.dr_db = load_data("drivers", ["Name", "Phone", "Daily_Salary"])

# 4. Staff දත්ත ලෝඩ් කිරීම
if 'staff_db' not in st.session_state:
    # "*" පාවිච්චි කිරීමෙන් table එකේ තියෙන ඔක්කොම columns ටික load වෙනවා
    st.session_state.staff_db = load_data("staff", ["*"])
    # පෙන්වන්න කලින් columns තියෙනවාද කියලා check කරනවා
    if st.session_state.staff_db.empty:
        st.session_state.staff_db = pd.DataFrame(columns=["Name", "Position", "Daily_Rate"])

# 5. Landowners දත්ත ලෝඩ් කිරීම (Site Owners)
if 'lo_db' not in st.session_state:
    st.session_state.lo_db = load_data("landowners", ["*"])

# 5.5 Vehicle Owners දත්ත ලෝඩ් කිරීම (🚛 Owner Advance වැඩ කරන්න මේක ඕනේ)
if 'vo_db' not in st.session_state:
    # ඔයාගේ Supabase එකේ vehicle owners ඉන්න table එකේ නම 'vehicle_owners' නම් ඒක දෙන්න
    # නැතිනම් 'vo_db' එක 've_db' එකෙන්ම filter කරලත් ගන්න පුළුවන්
    try:
        st.session_state.vo_db = load_data("vehicle_owners", ["*"])
    except:
        # Table එක නැතිනම් හිස් එකක් හදනවා error නොවී ඉන්න
        st.session_state.vo_db = pd.DataFrame(columns=["Name", "Phone"])

# 6. පරණ landowners ලිස්ට් එක (Dictionary එකක් ලෙස තියාගැනීම)
if 'landowners' not in st.session_state:
    if not st.session_state.lo_db.empty:
        st.session_state.landowners = st.session_state.lo_db.to_dict('records')
    else:
        st.session_state.landowners = []
        
# --- 5. PDF ENGINE (Cloud Data වලට ගැලපෙන විදිහට) ---
class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.set_text_color(230, 126, 34) 
        self.cell(0, 10, "K. SIRIWARDHANA SAND CONSTRUCTION PROJECT", 0, 1, 'C')
        self.ln(5)

def create_pdf(title, data_df, summary_dict):
    pdf = PDF()
    pdf.add_page()
    
    def safe_text(text):
        if text is None or str(text) == "nan": return ""
        return str(text).encode("latin-1", "ignore").decode("latin-1")

    def clean_val(v):
        try:
            if v is None or str(v).lower() == 'nan' or str(v).strip() == '': return 0.0
            if isinstance(v, (int, float)): return float(v)
            v_str = str(v).replace(',', '').replace('Rs.', '').replace('LKR', '').replace(' ', '').strip()
            return float(v_str) if v_str else 0.0
        except: return 0.0

    # --- 1. සාරාංශය සඳහා මුළු එකතුව කලින්ම ගණනය කරමු ---
    actual_total_units = 0.0
    for _, row in data_df.iterrows():
        q_cubes = clean_val(row.get('Qty_Cubes', row.get('qty_cubes', 0)))
        w_hrs = clean_val(row.get('Hours', row.get('hours', row.get('Work_Hours', row.get('work_hours', 0)))))
        q_qty = clean_val(row.get('Qty', row.get('qty', 0)))
        row_qty = q_cubes if q_cubes > 0 else (w_hrs if w_hrs > 0 else q_qty)
        category_str = str(row.get('Category', row.get('category', ''))).lower()
        if "work log" in category_str:
            actual_total_units += row_qty

    summary_dict["Total Units/Hours"] = f"{actual_total_units:,.2f}"

    # --- 2. PDF Header & Summary Section ---
    pdf.set_font("Arial", 'B', 12)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 10, safe_text(f"STATEMENT: {title.upper()}"), 1, 1, 'L', fill=True)
    pdf.ln(2)
    
    pdf.set_font("Arial", 'B', 10)
    for k, v in summary_dict.items():
        if k != "Rate_Breakdown":
            display_val = safe_text(v)
            pdf.cell(50, 8, safe_text(k) + ":", 1)
            pdf.set_font("Arial", '', 10)
            pdf.cell(0, 8, " " + display_val, 1, 1)
            pdf.set_font("Arial", 'B', 10)

    pdf.ln(8)
    headers = ["Date", "Category", "Description", "Qty/Hr", "Rate", "Amount"]
    w = [22, 35, 50, 15, 25, 43]
    pdf.set_fill_color(220, 220, 220)
    for i, h in enumerate(headers):
        pdf.cell(w[i], 8, safe_text(h), 1, 0, 'C', fill=True)
    pdf.ln()
    
    # --- 3. Table Data Section ---
    pdf.set_font("Arial", '', 8)
    total_earn = 0
    total_exp = 0
    current_total_qty = 0 
    
    for _, row in data_df.iterrows():
        q_cubes = clean_val(row.get('Qty_Cubes', row.get('qty_cubes', 0)))
        w_hrs = clean_val(row.get('Hours', row.get('hours', row.get('Work_Hours', row.get('work_hours', 0)))))
        q_qty = clean_val(row.get('Qty', row.get('qty', 0)))
        row_qty = q_cubes if q_cubes > 0 else (w_hrs if w_hrs > 0 else q_qty)
        
        category = row.get('Category', row.get('category', 'N/A'))
        cat_str = str(category)
        
        if "work log" in cat_str.lower():
            current_total_qty += row_qty
        
        rate = clean_val(row.get('Rate_At_Time', row.get('rate_at_time', 0)))
        amt = clean_val(row.get('Amount', row.get('amount', 0)))
        
        if amt == 0 and row_qty > 0 and rate > 0:
            amt = row_qty * rate

        date_val = safe_text(str(row.get('Date', row.get('date', '-'))))
        note_val = safe_text(str(row.get('Note', row.get('note', ''))))[:30]

        pdf.cell(w[0], 7, date_val, 1)
        pdf.cell(w[1], 7, safe_text(cat_str), 1)
        pdf.cell(w[2], 7, note_val, 1)
        pdf.cell(w[3], 7, f"{row_qty:,.2f}" if row_qty > 0 else "-", 1, 0, 'C')
        
        # --- FIXED EXPENSE LOGIC ---
        # Category එකේ වියදම් වචනයක් තියෙනවා නම් හෝ Amount එක 0 ට වඩා අඩු නම් එය වියදමකි
        is_expense = any(exp in cat_str for exp in ["Fuel", "Repair", "Advance", "Payroll", "Salary", "Expense", "Staff", "Food", "Rent", "Utility", "Office", "Misc"]) or (amt < 0)

        if is_expense:
            # සෘණ අගය ධන කර වරහන් ඇතුළේ පෙන්වා, මුළු වියදමට එකතු කරයි
            display_amt_val = abs(amt)
            total_exp += display_amt_val
            
            pdf.set_text_color(200, 0, 0)
            pdf.cell(w[4], 7, "EXPENSE", 1, 0, 'C')
            pdf.cell(w[5], 7, f"({display_amt_val:,.2f})", 1, 1, 'R')
            pdf.set_text_color(0, 0, 0)
        else:
            # ධන අගයන් පමණක් ආදායමට එකතු කරයි
            total_earn += amt
            pdf.cell(w[4], 7, f"{rate:,.2f}" if rate > 0 else "-", 1, 0, 'R')
            pdf.cell(w[5], 7, f"{amt:,.2f}", 1, 1, 'R')

    # --- 4. Totals Footer Section ---
    if pdf.get_y() > 250: pdf.add_page()
    pdf.set_font("Arial", 'B', 9)
    pdf.set_fill_color(245, 245, 245)
    pdf.cell(sum(w[:3]), 8, "TOTAL QUANTITY / HOURS", 1, 0, 'R', fill=True)
    pdf.cell(w[3], 8, f"{current_total_qty:,.2f}", 1, 0, 'C', fill=True)
    pdf.cell(w[4] + w[5], 8, "", 1, 1, 'R', fill=True)
    
    # පහළ summary එකේදී වැරදි අගයන් නොපෙන්වීමට total_earn සහ total_exp පාවිච්චි කරයි
    pdf.cell(sum(w[:5]), 8, "GROSS EARNINGS (LKR)", 1, 0, 'R')
    pdf.cell(w[5], 8, f"{total_earn:,.2f}", 1, 1, 'R')
    
    pdf.cell(sum(w[:5]), 8, "TOTAL EXPENSES (LKR)", 1, 0, 'R')
    pdf.cell(w[5], 8, f"{total_exp:,.2f}", 1, 1, 'R')
    
    pdf.set_fill_color(230, 126, 34); pdf.set_text_color(255, 255, 255)
    pdf.cell(sum(w[:5]), 10, "NET SETTLEMENT BALANCE (LKR)", 1, 0, 'R', fill=True)
    pdf.cell(w[5], 10, f"{(total_earn - total_exp):,.2f}", 1, 1, 'R', fill=True)
    
    fn = f"Statement_{datetime.now().strftime('%H%M%S')}.pdf"
    pdf.output(fn)
    return fn
    
# --- 6. STAFF PDF ENGINE (Cloud-Ready) ---
def create_staff_pdf(staff_name, data_df):
    pdf = PDF()
    pdf.add_page()
    
    def safe_text(text):
        if text is None or str(text) == "nan": return ""
        return str(text).encode("latin-1", "ignore").decode("latin-1")

    # Header
    pdf.set_font("Arial", 'B', 14)
    pdf.set_fill_color(46, 134, 193); pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 12, f"STAFF SETTLEMENT: {staff_name.upper()}", 1, 1, 'C', fill=True)
    pdf.ln(5); pdf.set_text_color(0, 0, 0)

    # Table Header
    pdf.set_font("Arial", 'B', 10)
    headers = ["Date", "Type", "Note", "Days", "Amount (LKR)"]
    w = [30, 40, 60, 20, 40]
    
    pdf.set_fill_color(200, 200, 200)
    for i, h in enumerate(headers):
        pdf.cell(w[i], 8, h, 1, 0, 'C', fill=True)
    pdf.ln()

    pdf.set_font("Arial", '', 9)
    total_days = 0
    total_pay = 0
    total_adv = 0

    for _, row in data_df.iterrows():
        # Row එකෙන් දත්ත ගන්නකොට Column name එක Case-insensitive (පොඩි/මහ අකුරු) බලන්න get() පාවිච්චි කරයි
        date = safe_text(str(row.get('Date', row.get('date', '-'))))
        cat = safe_text(str(row.get('Category', row.get('category', 'N/A'))))
        note = safe_text(str(row.get('Note', row.get('note', ''))))
        
        try:
            amt = float(row.get('Amount', row.get('amount', 0)))
            days = float(row.get('Hours', row.get('hours', 0)))
        except:
            amt = 0; days = 0

        pdf.cell(w[0], 7, date, 1)
        pdf.cell(w[1], 7, cat, 1)
        pdf.cell(w[2], 7, note[:35], 1)
        pdf.cell(w[3], 7, f"{days:,.1f}" if days > 0 else "-", 1, 0, 'C')
        
        # Advance එකක්ද කියලා බලන logic එක (ඔයාගේ පරණ විදිහටම)
        if "Advance" in cat:
            total_adv += amt
            pdf.set_text_color(200, 0, 0) # Advance නම් රතු පාටින්
            pdf.cell(w[4], 7, f"({amt:,.2f})", 1, 1, 'R')
            pdf.set_text_color(0, 0, 0)
        else:
            total_pay += amt
            total_days += days
            pdf.cell(w[4], 7, f"{amt:,.2f}", 1, 1, 'R')

    # Totals Section
    if pdf.get_y() > 250: pdf.add_page()
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 10)
    
    pdf.cell(sum(w[:4]), 8, "GROSS EARNINGS", 1, 0, 'R')
    pdf.cell(w[4], 8, f"{total_pay:,.2f}", 1, 1, 'R')
    
    pdf.cell(sum(w[:4]), 8, "TOTAL ADVANCES", 1, 0, 'R')
    pdf.cell(w[4], 8, f"{total_adv:,.2f}", 1, 1, 'R')
    
    pdf.set_fill_color(46, 134, 193); pdf.set_text_color(255, 255, 255)
    pdf.cell(sum(w[:4]), 10, "NET PAYABLE BALANCE", 1, 0, 'R', fill=True)
    pdf.cell(w[4], 10, f"{(total_pay - total_adv):,.2f}", 1, 1, 'R', fill=True)

    fn = f"Staff_Report_{staff_name}_{datetime.now().strftime('%H%M%S')}.pdf"
    pdf.output(fn)
    return fn
    
# --- 7. DRIVER PDF ENGINE (Cloud-Ready) ---
def create_driver_pdf(title, data_df, summary_dict):
    pdf = PDF()
    pdf.add_page()
    
    def safe_text(text):
        if text is None or str(text) == "nan": return ""
        return str(text).encode("latin-1", "ignore").decode("latin-1")

    # Title Section
    pdf.set_font("Arial", 'B', 12)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 10, safe_text(f"DRIVER PAYMENT STATEMENT: {title.upper()}"), 1, 1, 'L', fill=True)
    pdf.ln(2)
    
    # Summary Section
    pdf.set_font("Arial", 'B', 10)
    for k, v in summary_dict.items():
        pdf.cell(50, 8, safe_text(k) + ":", 1)
        pdf.set_font("Arial", '', 10)
        pdf.cell(0, 8, " " + safe_text(v), 1, 1)
        pdf.set_font("Arial", 'B', 10)

    # Table Header
    pdf.ln(8)
    pdf.set_font("Arial", 'B', 9)
    headers = ["Date", "Category", "Description", "Amount (LKR)"]
    w = [30, 45, 75, 40]
    pdf.set_fill_color(220, 220, 220)
    for i, h in enumerate(headers):
        pdf.cell(w[i], 8, safe_text(h), 1, 0, 'C', fill=True)
    pdf.ln()
    
    pdf.set_font("Arial", '', 9)
    total_paid = 0
    
    # --- Filter Logic ---
    for _, row in data_df.iterrows():
        # Cloud Table එකේ Category හෝ category ලෙස තිබිය හැක
        cat_str = str(row.get('Category', row.get('category', '')))
        
        # ඔයාගේ Logic එක: Salary/Advance වචන තියෙන ඒවා විතරක් පෙරීම
        is_salary_or_advance = any(word in cat_str for word in ["Salary", "Advance", "Payroll", "D.Advance"])
        
        if is_salary_or_advance:
            date_val = safe_text(str(row.get('Date', row.get('date', '-'))))
            note_val = safe_text(str(row.get('Note', row.get('note', ''))))[:45]
            
            # Amount එක clean කරගැනීම
            val = row.get('Amount', row.get('amount', 0))
            if isinstance(val, str): 
                val = val.replace(',', '').replace('Rs.', '').replace(' ', '').strip()
            
            try:
                amt = float(val) if val else 0.0
            except:
                amt = 0.0
                
            total_paid += amt

            # Row එක print කිරීම
            pdf.cell(w[0], 7, date_val, 1)
            pdf.cell(w[1], 7, safe_text(cat_str), 1)
            pdf.cell(w[2], 7, note_val, 1)
            pdf.cell(w[3], 7, f"{amt:,.2f}", 1, 1, 'R')

    # Final Total Section
    if pdf.get_y() > 250: pdf.add_page()
    pdf.ln(2)
    pdf.set_font("Arial", 'B', 10)
    pdf.set_fill_color(230, 126, 34); pdf.set_text_color(255, 255, 255)
    pdf.cell(sum(w[:3]), 10, "TOTAL PAYMENTS TO DRIVER (LKR)", 1, 0, 'R', fill=True)
    pdf.cell(w[3], 10, f"{total_paid:,.2f}", 1, 1, 'R', fill=True)
    
    fn = f"Driver_Settlement_{datetime.now().strftime('%H%M%S')}.pdf"
    pdf.output(fn)
    return fn
    
# --- 8. LANDOWNER PDF ENGINE (Fixed for Total Cubes) ---
def create_landowner_pdf(title, data_df, summary_dict):
    pdf = PDF() 
    pdf.add_page()
    
    def safe_text(text):
        if text is None or str(text) == "nan": return ""
        return str(text).encode("latin-1", "ignore").decode("latin-1")

    # --- 1. සාරාංශයට කලින් Cube ගණන හරියටම ගණන් කරමු ---
    actual_total_units = 0.0
    for _, row in data_df.iterrows():
        # ඔයාගේ PDF එකේ තියෙන විදිහට Qty/Hr, Qty_Cubes හෝ qty කියන ඕනෑම නමකින් data ගන්නවා
        q_val = float(row.get('Qty/Hr', row.get('Qty_Cubes', row.get('qty', 0))))
        
        cat_str = str(row.get('Category', '')).lower()
        # Inward හෝ Stock In තියෙන ඒවා විතරක් එකතු කරනවා
        if "inward" in cat_str or "stock in" in cat_str:
            actual_total_units += q_val

    # සාරාංශයේ 'Total Units/Hours' එකට අපි හොයාගත්ත අගය බලෙන්ම දානවා
    summary_dict["Total Units/Hours"] = f"{actual_total_units:,.2f}"

    # --- 2. Header & Summary Section ---
    pdf.set_font("Arial", 'B', 12)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 10, safe_text(f"LANDOWNER STATEMENT: {title.upper()}"), 1, 1, 'L', fill=True)
    pdf.ln(2)
    
    pdf.set_font("Arial", 'B', 10)
    for k, v in summary_dict.items():
        pdf.cell(50, 8, safe_text(k) + ":", 1)
        pdf.set_font("Arial", '', 10)
        pdf.cell(0, 8, " " + safe_text(v), 1, 1)
        pdf.set_font("Arial", 'B', 10)

    # --- 3. Table Header ---
    pdf.ln(8)
    headers = ["Date", "Category", "Note", "Qty/Hr", "Rate", "Amount"]
    w = [22, 35, 50, 15, 25, 43]
    pdf.set_fill_color(220, 220, 220)
    for i, h in enumerate(headers):
        pdf.cell(w[i], 8, safe_text(h), 1, 0, 'C', fill=True)
    pdf.ln()

    # --- 4. Table Body ---
    pdf.set_font("Arial", '', 8)
    total_payable = 0
    total_paid = 0
    
    for _, row in data_df.iterrows():
        date_val = safe_text(str(row.get('Date', '-')))
        cat_val = safe_text(str(row.get('Category', 'General')))
        note_val = safe_text(str(row.get('Note', ''))[:30])
        
        # Table එක ඇතුළත දත්ත පෙන්වීම
        cubes = float(row.get('Qty/Hr', row.get('Qty_Cubes', 0)))
        rate = float(row.get('Rate_At_Time', row.get('Rate', 0)))
        amt = float(row.get('Amount', 0))

        pdf.cell(w[0], 7, date_val, 1)
        pdf.cell(w[1], 7, cat_val, 1)
        pdf.cell(w[2], 7, note_val, 1)
        pdf.cell(w[3], 7, f"{cubes:,.2f}" if cubes > 0 else "-", 1, 0, 'C')
        pdf.cell(w[4], 7, f"{rate:,.2f}" if rate > 0 else "-", 1, 0, 'R')
        
        category_str = cat_val.lower()
        if "inward" in category_str or "stock in" in category_str:
            total_payable += amt
            pdf.cell(w[5], 7, f"{amt:,.2f}", 1, 1, 'R')
        elif any(x in category_str for x in ["advance", "payment", "paid"]):
            total_paid += amt
            pdf.set_text_color(200, 0, 0)
            pdf.cell(w[5], 7, f"({amt:,.2f})", 1, 1, 'R')
            pdf.set_text_color(0, 0, 0)
        else:
            pdf.cell(w[5], 7, f"{amt:,.2f}" if amt != 0 else "-", 1, 1, 'R')

    # --- 5. Table Bottom (අවසාන එකතුව) ---
    pdf.set_font("Arial", 'B', 9)
    pdf.cell(sum(w[:3]), 8, "TOTAL QUANTITY / HOURS", 1, 0, 'R')
    pdf.cell(w[3], 8, f"{actual_total_units:,.2f}", 1, 0, 'C') # මෙතන දැන් 25.00 හරියට වැටෙනවා
    pdf.cell(w[4]+w[5], 8, "", 1, 1)

    from datetime import datetime
    fn = f"LO_Settlement_{datetime.now().strftime('%H%M%S')}.pdf"
    pdf.output(fn)
    return fn

def create_others_report(df_others, start_date, end_date):
    pdf = PDF() # ඔයා පාවිච්චි කරන PDF class එක
    pdf.add_page()
    
    def safe_text(text):
        if text is None or str(text) == "nan": return ""
        return str(text).encode("latin-1", "ignore").decode("latin-1")

    # Header
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, "OTHER EXPENSES REPORT", 1, 1, 'C')
    pdf.set_font("Arial", '', 10)
    pdf.cell(0, 10, f"Period: {start_date} to {end_date}", 0, 1, 'C')
    pdf.ln(5)

    # Table Header
    headers = ["Date", "Category", "Description", "Amount (LKR)"]
    w = [30, 40, 80, 40]
    pdf.set_font("Arial", 'B', 10)
    pdf.set_fill_color(220, 220, 220)
    for i, h in enumerate(headers):
        pdf.cell(w[i], 8, h, 1, 0, 'C', fill=True)
    pdf.ln()

    # Table Body
    pdf.set_font("Arial", '', 9)
    total_amount = 0
    for _, row in df_others.iterrows():
        amt = float(row.get('Amount', 0))
        total_amount += amt
        
        pdf.cell(w[0], 7, safe_text(str(row.get('Date', ''))), 1)
        pdf.cell(w[1], 7, safe_text(str(row.get('Category', ''))), 1)
        pdf.cell(w[2], 7, safe_text(str(row.get('Note', ''))[:50]), 1)
        pdf.cell(w[3], 7, f"{amt:,.2f}", 1, 1, 'R')

    # Total Row
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(sum(w[:2]), 10, "TOTAL EXPENDITURE", 1, 0, 'R')
    pdf.cell(w[2]+w[3], 10, f"LKR {total_amount:,.2f}  ", 1, 1, 'R')

    from datetime import datetime
    fn = f"Other_Expenses_{datetime.now().strftime('%H%M%S')}.pdf"
    pdf.output(fn)
    return fn
    
# --- 9. SECURITY & LOGIN UI ---

# 1. මුලින්ම Login Status එක පරීක්ෂා කරනවා (Session State එකේ නැත්නම් False කරනවා)
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

# 2. Login වෙලා නැත්නම් විතරක් මේ පෝරමය (Form) පෙන්වනවා
if not st.session_state["logged_in"]:
    # මැදට වෙන්න ලස්සන Header එකක්
    st.markdown("<h2 style='text-align: center; color: #2E86C1;'>🏗️ KSD CONSTRUCTION - ERP LOGIN</h2>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        with st.form("login_panel", clear_on_submit=False):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            
            if st.form_submit_button("Access System 🔐", use_container_width=True):
                # අපි උඩින්ම හදපු USERS list එකේ මේ Username/Password තියෙනවාද බලනවා
                if u in USERS and USERS[u]["password"] == p:
                    st.session_state["logged_in"] = True
                    st.session_state["role"] = USERS[u]["role"]
                    st.success(f"Welcome {u}! Redirecting...")
                    st.rerun() # සාර්ථක නම් App එක Refresh කරලා ඇතුළට ගන්නවා
                else:
                    st.error("Invalid Username or Password! Please try again.")
    
    # Login පෝරමය පෙන්වන වෙලාවේ App එකේ අනිත් කොටස් පේන්නේ නැති වෙන්න මෙතනින් නවත්වනවා
    st.stop()
    
# --- 2. Login වෙලා නැත්නම් Login Form එක පෙන්වනවා ---
if not st.session_state["logged_in"]:
    st.markdown("<h2 style='text-align: center; color: #8E44AD;'>🔐 KSD Sand & Soil System</h2>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        with st.form("login_panel"):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Login to System"):
                # ✅ අලුත් විදිහ: USER_CONF වෙනුවට USERS dictionary එක පාවිච්චි කරනවා
                if u in USERS and USERS[u]["password"] == p:
                    st.session_state["logged_in"] = True
                    st.session_state["role"] = USERS[u]["role"] # Role එකත් සේව් කරගන්නවා
                    st.success(f"Welcome {u}!")
                    st.rerun()
                else:
                    st.error("Invalid Username or Password")
    st.stop()
    
# 3. Login වුණාට පස්සේ විතරයි මෙතනින් පල්ලෙහාට යන්නේ
# --- මෙතැන් සිට ඔයාගේ පරණ කෝඩ් එක පටන් ගන්නවා ---

st.sidebar.title("Syntaxcore Panel")
if st.sidebar.button("Logout 🔓"):
    st.session_state["logged_in"] = False
    st.rerun()

# ... ඔයාගේ පරණ Menu එක සහ අනෙකුත් කොටස් ...
    
# --- 10. UI CONFIG & SECURITY HANDLER ---

# 1. Page Configuration (Wide Layout එක Tables වලට හොඳයි)
st.set_page_config(page_title=SHOP_NAME, layout="wide", page_icon="🏗️")

# 2. Supabase Cloud Connection Initialize කිරීම
# (මේක කරන්නේ secrets.toml එකේ දත්ත පාවිච්චි කරලා)
try:
    conn = st.connection("supabase", type=SupabaseConnection)
except Exception:
    st.error("Cloud Database එකට සම්බන්ධ වීමට නොහැක. කරුණාකර Connection එක පරීක්ෂා කරන්න.")

# 3. Session State එක ලෑස්ති කරගන්නවා
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["role"] = None

# 4. Login Status එක පරීක්ෂා කිරීම (Login වෙලා නැත්නම් විතරක් Login පෝරමය පෙන්වයි)
if not st.session_state["logged_in"]:
    # (මෙතනට ඔයා කලින් එවපු Login Form එකේ කෝඩ් එක එනවා)
    pass
    

# 2. ලොග් වෙලා නැත්නම් විතරක් මේ ටික පෙන්වන්න
if not st.session_state["logged_in"]:
    st.markdown("<h2 style='text-align: center; color: #2E86C1;'>🔐 KSD ERP - Security Portal</h2>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        with st.form("login_panel"):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            
            if st.form_submit_button("Access System"):
                # USERS dictionary එක ඔයා කෝඩ් එකේ උඩම Define කරලා තියෙන්න ඕනේ
                if u in USERS and USERS[u]["password"] == p:
                    st.session_state["logged_in"] = True
                    st.session_state["role"] = USERS[u]["role"]
                    st.success("Login Successful!")
                    st.rerun()
                else:
                    st.error("Invalid Username or Password!")
    st.stop() # මේක හරිම වැදගත්! ලොග් වෙනකම් පල්ලෙහා ටික නවත්වනවා.

# --- 🔓 3. ලොග් වුණාට පස්සේ පේන කොටස ---

# --- 11. DYNAMIC SIDEBAR & ROLE ACCESS CONTROL ---

# 1. Role එක ලස්සනට පෙන්වීමට සකස් කිරීම
role_val = st.session_state.get("role", "user")
role_display = "ADMINISTRATOR" if role_val == "admin" else "STAFF USER"

st.sidebar.title(f"🏗️ KSD ERP v5.6")
st.sidebar.info(f"Logged in as: **{role_display}**")

# 2. 👮 ROLE එක අනුව පෙන්වන MENU එක තීරණය කිරීම
if st.session_state.get("role") == "admin":
    # ඇඩ්මින්ට පද්ධතියේ සියලුම පාලන බලතල තියෙනවා
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
    # සාමාන්‍ය USER (Staff) ට පේන්නේ දත්ත ඇතුළත් කරන කොටස විතරයි
    # එතකොට එයාලට Dashboard එකේ තියෙන ලාභ-අලාභ බලන්න බැහැ
    menu_options = ["🏗️ Site Operations","💰 Finance & Shed"]

# 3. Sidebar එකේ මෙනු එක පෙන්වීම
menu = st.sidebar.selectbox("MAIN MENU", menu_options)

# 4. Logout බටන් එක (Sidebar එකේ පල්ලෙහාටම)
st.sidebar.markdown("---")
if st.sidebar.button("Logout 🔓", use_container_width=True, type="secondary"):
    st.session_state["logged_in"] = False
    st.session_state["role"] = None
    st.success("Logged out successfully!")
    st.rerun()
    
# --- මෙතනින් පස්සේ ඔයාගේ පරණ කෝඩ් එකේ 'if menu == ...' කොටස් ආරම්භ කරන්න ---

# --- 1. DASHBOARD SECTION (සම්පූර්ණ එකම මෙතන තියෙනවා) ---
# --- 6. DASHBOARD ---
elif menu == "📊 Dashboard":
            st.markdown("<h2 style='color: #2E86C1;'>📊 Business Overview</h2>", unsafe_allow_html=True)
            
            if not st.session_state.df.empty:
                df = st.session_state.df.copy()
                st.subheader("📅 Filter Transactions")
                col_f1, col_f2 = st.columns(2)
                
                with col_f1:
                    from datetime import timedelta, datetime
                    start_date = st.date_input("From Date", datetime.now().date() - timedelta(days=7))
                with col_f2:
                    end_date = st.date_input("To Date", datetime.now().date())
                
                # --- 1. DATE FILTERING (4-6 දත්ත අහු නොවන ප්‍රශ්නයට විසඳුම) ---
                df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
                df = df.dropna(subset=['Date'])
                mask = (df['Date'].dt.date >= start_date) & (df['Date'].dt.date <= end_date)
                filtered_df = df.loc[mask].copy()

                if not filtered_df.empty:
                    # --- 2. INCOME (ආදායම - Sales Out පමණි) ---
                    income_mask = filtered_df["Category"].str.contains("Sales Out", case=False, na=False)
                    temp_sales_df = filtered_df[income_mask].copy()
                    
                    if not temp_sales_df.empty:
                        temp_sales_df['Income_Val'] = pd.to_numeric(temp_sales_df['Amount'], errors='coerce').fillna(0)
                        real_income = temp_sales_df['Income_Val'].sum()
                    else:
                        real_income = 0

                    # --- 3. TOTAL EXPENSES (INWARD + EXCAVATOR + OTHER) ---
                    expense_categories = [
                        "Food", "Fuel", "Repair", "Advance", "Rent", "Office", 
                        "Misc", "Utility", "Payroll", "Wage", "Salary", 
                        "Staff", "Owner Advance", "Driver", "Shed",
                        "Inward", "Stock In", "Excavator"
                    ]
                    exp_pattern = "|".join(expense_categories)

                    expense_mask = (
                        (filtered_df["Amount"] < 0) |
                        (filtered_df["Type"].str.strip().str.capitalize() == "Expense") |
                        (filtered_df["Category"].str.contains(exp_pattern, case=False, na=False))
                    )

                    all_exp_df = filtered_df[expense_mask].copy()

                    if not all_exp_df.empty:
                        all_exp_df["Note"] = all_exp_df["Note"].astype(str).fillna("")
                        # Actual Expenses (Payments නොවන ඒවා)
                        actual_exp_mask = ~all_exp_df["Note"].str.contains("Payment|Settle", case=False, na=False)
                        raw_expenses = pd.to_numeric(all_exp_df[actual_exp_mask]["Amount"], errors='coerce').abs().fillna(0).sum()
                        
                        # Shed Payments (වියදමෙන් අඩු විය යුතු ඒවා)
                        shed_payment_mask = (all_exp_df["Category"].str.contains("Shed", case=False, na=False)) & \
                                           (all_exp_df["Note"].str.contains("Payment|Settle", case=False, na=False))
                        
                        total_shed_payments = pd.to_numeric(all_exp_df[shed_payment_mask]["Amount"], errors='coerce').abs().fillna(0).sum()
                        total_expenses = raw_expenses - total_shed_payments
                    else:
                        total_expenses = 0

                    # --- 4. METRICS DISPLAY ---
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Net Sales Income", f"Rs. {real_income:,.2f}")
                    m2.metric("Total Expenses", f"Rs. {total_expenses:,.2f}")
                    
                    cashflow = real_income - total_expenses
                    margin = (cashflow / real_income * 100) if real_income > 0 else 0
                    m3.metric("Net Cashflow", f"Rs. {cashflow:,.2f}", delta=f"{margin:.1f}% Margin")

                    st.divider()

                    # --- 5. STOCK BALANCE SECTION ---
                    st.subheader("📦 Plant Stock Balance (Main Stock)")
                    try:
                        in_mask = (filtered_df["Category"].str.contains("Inward|Stock In", case=False, na=False))
                        total_in = pd.to_numeric(filtered_df[in_mask]["Qty_Cubes"], errors='coerce').fillna(0).sum()

                        sand_out_mask = (filtered_df["Category"].str.contains("Sales Out|Outward", case=False, na=False)) & \
                                        (filtered_df["Category"].str.contains("Sand", case=False, na=False))
                        sand_out = pd.to_numeric(filtered_df[sand_out_mask]["Qty_Cubes"], errors='coerce').fillna(0).sum()

                        soil_out_mask = (filtered_df["Category"].str.contains("Sales Out|Outward", case=False, na=False)) & \
                                        (filtered_df["Category"].str.contains("Soil", case=False, na=False))
                        soil_out = pd.to_numeric(filtered_df[soil_out_mask]["Qty_Cubes"], errors='coerce').fillna(0).sum()

                        remaining_balance = total_in - (sand_out + soil_out)

                        s_col1, s_col2 = st.columns(2)
                        s_col1.metric("Sand Stats", f"{remaining_balance:.2f} Cubes Left", delta=f"Sold: {sand_out} Cubes", delta_color="inverse")
                        s_col2.metric("Inward Total", f"{total_in:.2f} Cubes", delta=f"Soil Sold: {soil_out}", delta_color="normal")

                        # --- Income Trend Chart ---
                        st.divider()
                        st.subheader("Daily Income Trend")
                        if not temp_sales_df.empty:
                            trend_data = temp_sales_df.groupby(temp_sales_df['Date'].dt.date)['Income_Val'].sum()
                            st.line_chart(trend_data)
                    except Exception as e:
                        st.error(f"Stock Logic Error: {e}")
                else:
                    st.warning("තෝරාගත් දින පරාසය තුළ දත්ත නැත.")
            else:
                st.info("පද්ධතියේ දත්ත කිසිවක් නැත.")
            
# --- 2. SITE OPERATIONS SECTION ---
# මේ 'elif' එක පටන් ගන්න ඕනේ උඩ තියෙන 'if menu == "📊 Dashboard":' එකට කෙළින්ම පල්ලෙහායින්
# --- කලින් තිබුණු Site Operations එක අයින් කරලා මේක දාන්න ---
# --- 7. SITE OPERATIONS ---
elif menu == "🏗️ Site Operations":
        st.markdown(f"<h2 style='color: #E67E22;'>🏗️ Site Operations & Stock Manager</h2>", unsafe_allow_html=True)
        
        op = st.radio("Select Activity Type", ["🚜 Excavator Work Log", "💰 Sales Out", "📥 Stock Inward (To Plant)"], horizontal=True)
        
        # දත්ත ලබා ගැනීම
        v_list = st.session_state.ve_db["No"].tolist() if not st.session_state.ve_db.empty else ["N/A"]
        d_list = st.session_state.dr_db["Name"].tolist() if not st.session_state.dr_db.empty else ["No Drivers Registered"]
        l_list = st.session_state.lo_db["Name"].tolist() if not st.session_state.lo_db.empty else ["No Owners Registered"]

        with st.form("site_f", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                v = st.selectbox("Select Vehicle / Machine", v_list if op != "📥 Stock Inward (To Plant)" else ["Internal / Third Party"])
                d = st.date_input("Date", datetime.now().date())
                material = st.selectbox("Material Type", ["Sand", "Soil", "Other"]) if (op != "🚜 Excavator Work Log") else ""
                
                if op == "📥 Stock Inward (To Plant)":
                    src_owner = st.selectbox("Source (Landowner)", l_list)
                    src_driver = st.selectbox("Driver/Operator", d_list)
            
            with col2:
                val_label = "Work Hours" if "Excavator" in op else "Qty (Cubes)"
                unit = "Hrs" if "Excavator" in op else "Cubes"
                val = st.number_input(val_label, min_value=0.0, step=0.5, value=0.0)
                r = st.number_input(f"Enter Rate per {unit} (LKR)", min_value=0.0, step=100.0, value=0.0)
            
            n = st.text_input("Additional Note")
            
            if st.form_submit_button("📥 Save Record & Sync to Cloud"):
                if val <= 0 or r <= 0: 
                    st.error("Please enter valid Qty/Hours and Rate!")
                else:
                    cat = f"{op} ({material})" if material else op
                    calculated_amount = val * r
                    q = val if "Cubes" in val_label else 0
                    h = val if "Hours" in val_label else 0
                    
                    final_note = n
                    if op == "📥 Stock Inward (To Plant)":
                        final_note = f"{n} | Owner: {src_owner} | Drv: {src_driver}"
                    
                    # 1. Cloud එකට යවන්න ඕන දත්ත ටික ලෑස්ති කරගන්නවා
                    new_data = {
                        "Date": str(d),
                        "Type": "Income" if op == "💰 Sales Out" else "Process",
                        "Category": cat,
                        "Entity": v,
                        "Note": final_note,
                        "Amount": calculated_amount,
                        "Qty_Cubes": q,
                        "Hours": h,
                        "Fuel_Ltr": 0,
                        "Rate_At_Time": r,
                        "Status": "Done"
                    }
                    
                    try:
                        # 2. Cloud (Supabase) එකට සේව් කරනවා
                        conn.table("master_log").insert(new_data).execute()
                        
                        # 3. Local එකටත් දත්ත එකතු කරනවා (Refresh වෙනකම් පෙන්වන්න)
                        st.session_state.df = pd.concat([st.session_state.df, pd.DataFrame([new_data])], ignore_index=True)
                        
                        st.success(f"Successfully Recorded! Total: Rs.{calculated_amount:,.2f}")
                        st.balloons()
                        
                        # 4. වැදගත්ම දේ: පේජ් එක Refresh කරනවා Duplicate නොවී ඉන්න
                        st.rerun() 
                        
                    except Exception as e:
                        st.error(f"Error syncing with Cloud: {e}")
                    
    # --- 8. FINANCE & SHED ---
elif menu == "💰 Finance & Shed":
        st.markdown(f"<h2 style='color: #2E86C1;'>💰 Finance & Shed Management</h2>", unsafe_allow_html=True)
        fin = st.radio("Finance Category", ["⛽ Fuel & Shed", "🔧 Repairs", "💸 Payroll", "🏦 Owner Advances", "🧾 Others"], horizontal=True)
        
        v_list = st.session_state.ve_db["No"].tolist() if not st.session_state.ve_db.empty else ["N/A"]
        
        if fin == "⛽ Fuel & Shed":
            f1, f2 = st.tabs(["⛽ Log Fuel Bill", "💳 Settle Shed Payments"])
            with f1:
                st.subheader("⛽ Log Fuel Bill")
                with st.form("fuel", clear_on_submit=True):
                    col1, col2 = st.columns(2)
                    with col1:
                        d = st.date_input("Date", datetime.now().date())
                        v = st.selectbox("Vehicle", v_list)
                    with col2:
                        l = st.number_input("Liters", min_value=0.0, step=1.0)
                        c = st.number_input("Cost (LKR)", min_value=0.0, step=100.0)
                    
                    if st.form_submit_button("Save Fuel Entry"):
                        if c > 0:
                            fuel_data = {
                                "Date": str(d), "Type": "Expense", "Category": "Fuel Entry",
                                "Entity": v, "Note": "Shed Bill Entry", "Amount": c,
                                "Fuel_Ltr": l, "Qty_Cubes": 0, "Hours": 0, "Rate_At_Time": 0, "Status": "Pending"
                            }
                            try:
                                conn.table("master_log").insert(fuel_data).execute()
                                st.session_state.df = load_data("master_log", cols_master)
                                st.success("Fuel Saved!"); st.rerun()
                            except Exception as e: st.error(f"Error: {e}")
            with f2:
                st.subheader("💳 Settle Shed Payments")
                with st.form("shed_pay", clear_on_submit=True):
                    pay_date = st.date_input("Payment Date", datetime.now().date())
                    am = st.number_input("Amount Paid (LKR)", min_value=0.0)
                    ref = st.text_input("Reference (Cheque No/Cash/Slip)")
                    if st.form_submit_button("Record Payment"):
                        if am > 0:
                            pay_data = {
                                "Date": str(pay_date), "Type": "Expense", "Category": "Shed Payment",
                                "Entity": "Shed", "Note": ref, "Amount": am,
                                "Qty_Cubes": 0, "Fuel_Ltr": 0, "Hours": 0, "Rate_At_Time": 0, "Status": "Paid"
                            }
                            try:
                                conn.table("master_log").insert(pay_data).execute()
                                st.session_state.df = load_data("master_log", cols_master)
                                st.success("Payment recorded!"); st.rerun()
                            except Exception as e: st.error(f"Error: {e}")

        elif fin == "🔧 Repairs":
            st.subheader("🔧 Log Vehicle Repair")
            with st.form("rep", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    d = st.date_input("Date", datetime.now().date())
                    v = st.selectbox("Vehicle / Machine", v_list)
                with col2:
                    am = st.number_input("Repair Cost (LKR)", min_value=0.0)
                    nt = st.text_input("Repair Detail")
                if st.form_submit_button("Save Repair Record"):
                    if am > 0:
                        rep_data = {
                            "Date": str(d), "Type": "Expense", "Category": "Repair",
                            "Entity": v, "Note": nt, "Amount": am,
                            "Qty_Cubes": 0, "Fuel_Ltr": 0, "Hours": 0, "Rate_At_Time": 0, "Status": "Paid"
                        }
                        try:
                            conn.table("master_log").insert(rep_data).execute()
                            st.session_state.df = load_data("master_log", cols_master)
                            st.success("Saved!"); st.rerun()
                        except Exception as e: st.error(f"Error: {e}")

        elif fin == "💸 Payroll":
            st.subheader("💸 Staff Payroll & Advances")
            dr_names = st.session_state.dr_db["Name"].tolist() if not st.session_state.dr_db.empty else ["N/A"]
            with st.form("pay", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    dr = st.selectbox("Select Staff", dr_names)
                    pay_date = st.date_input("Date", datetime.now().date())
                with col2:
                    am = st.number_input("Amount (LKR)", min_value=0.0)
                    ty = st.selectbox("Type", ["Driver Advance", "Salary", "Bonus"])
                    v_rel = st.selectbox("Related Vehicle", v_list)
                if st.form_submit_button("Save Payroll Entry"):
                    if am > 0:
                        p_data = {
                            "Date": str(pay_date), "Type": "Expense", "Category": ty,
                            "Entity": v_rel, "Note": f"Driver: {dr}", "Amount": am,
                            "Qty_Cubes": 0, "Fuel_Ltr": 0, "Hours": 0, "Rate_At_Time": 0, "Status": "Paid"
                        }
                        try:
                            conn.table("master_log").insert(p_data).execute()
                            st.session_state.df = load_data("master_log", cols_master)
                            st.success("Paid!"); st.rerun()
                        except Exception as e: st.error(f"Error: {e}")

        elif fin == "🏦 Owner Advances":
            st.subheader("🚛 Vehicle Owner Advances")
        
            # 1. වාහන අයිතිකරුවන්ගේ ලැයිස්තුව (ve_db එකෙන් ගන්නවා)
            vo_names = []
            if not st.session_state.ve_db.empty:
                # 'Owner' column එකේ තියෙන unique නම් ටික ගන්නවා
                vo_names = st.session_state.ve_db["Owner"].dropna().unique().tolist()
            
            vo_names = sorted([str(x) for x in vo_names if x])
            if not vo_names: vo_names = ["N/A"]
    
            with st.form("own_adv", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    d = st.date_input("Date", datetime.now().date())
                    owner = st.selectbox("Vehicle Owner", vo_names)
                with col2:
                    am = st.number_input("Amount (LKR)", min_value=0.0)
                    # v_list කියන්නේ වාහන අංක ටික තියෙන list එක විය යුතුයි
                    v_rel = st.selectbox("Related Vehicle", v_list if 'v_list' in locals() else ["N/A"])
                
                nt = st.text_input("Note")
                
                if st.form_submit_button("Save Advance"):
                    if am > 0 and owner != "N/A":
                        adv_data = {
                            "Date": str(d), 
                            "Type": "Expense", 
                            "Category": "Vehicle Owner Advance",
                            "Entity": v_rel, 
                            "Note": f"Owner: {owner} | {nt}", 
                            "Amount": am,
                            "Qty_Cubes": 0, "Fuel_Ltr": 0, "Hours": 0, "Rate_At_Time": 0, 
                            "Status": "Paid"
                        }
                        try:
                            # Cloud Save
                            conn.table("master_log").insert(adv_data).execute()
                            
                            # Local State Update (Refresh කරන්න ඕන වෙන්නේ නැහැ එතකොට)
                            new_row = pd.DataFrame([adv_data])
                            st.session_state.df = pd.concat([st.session_state.df, new_row], ignore_index=True)
                            
                            st.success(f"✅ Advance of Rs.{am:,.2f} recorded for {owner}")
                            st.rerun()
                        except Exception as e: 
                            st.error(f"Error: {e}")
                    else:
                        st.warning("කරුණාකර අයිතිකරුවෙකු තෝරා මුදල ඇතුළත් කරන්න.")

        elif fin == "🧾 Others":
            st.subheader("🧾 Other Expenses")
            
            # --- 1. දත්ත ඇතුළත් කරන Form එක ---
            with st.form("oth", clear_on_submit=True):
                ex_date = st.date_input("Date", value=datetime.now().date())
                cat = st.selectbox("Category", ["Food", "Rent", "Utility", "Office", "Misc"])
                am = st.number_input("Amount (LKR)", min_value=0.0)
                nt = st.text_input("Description")
                
                if st.form_submit_button("Save Expense"):
                    if am > 0:
                        # වියදමක් නිසා Amount එක සෘණ (-) කරමු
                        final_amount = -abs(am)
                        
                        oth_data = {
                            "Date": str(ex_date), 
                            "Type": "Expense", 
                            "Category": cat,
                            "Entity": "Admin", 
                            "Note": nt, 
                            "Amount": final_amount, 
                            "Qty_Cubes": 0, 
                            "Fuel_Ltr": 0, 
                            "Hours": 0, 
                            "Rate_At_Time": 0, 
                            "Status": "Paid"
                        }
                        try:
                            conn.table("master_log").insert(oth_data).execute()
                            st.session_state.df = load_data("master_log", cols_master)
                            st.success(f"Saved! Record added for {ex_date}")
                            st.rerun()
                        except Exception as e: 
                            st.error(f"Error: {e}")
                    else:
                        st.warning("Please enter an amount greater than 0.")
        
            # --- 2. Report එක Generate කරන කොටස ---
            st.write("---")
            st.subheader("📊 Generate Others Report")
            
            col1, col2 = st.columns(2)
            d_start = col1.date_input("Start Date", value=datetime.now().date().replace(day=1))
            d_end = col2.date_input("End Date", value=datetime.now().date())
        
            if st.button("📥 Download Others PDF Report"):
                # filter කිරීමේදී Category එක වගේම Type එකත් බැලීම වඩා හොඳයි
                mask = (st.session_state.df['Category'].isin(["Food", "Rent", "Utility", "Office", "Misc"])) & \
                       (st.session_state.df['Date'].astype(str).between(str(d_start), str(d_end)))
                
                report_df = st.session_state.df[mask].copy()
                
                if not report_df.empty:
                    try:
                        # මෙතනදී create_others_report එකට යවන report_df එකේ 
                        # Amount එක ධන කරලා (Positive) යැවීමෙන් PDF එකේ Minus ප්‍රශ්නය විසඳෙනවා
                        report_df['Amount'] = report_df['Amount'].abs() 
                        
                        file_path = create_others_report(report_df, d_start, d_end)
                        with open(file_path, "rb") as f:
                            st.download_button("⬇️ Click here to Download", f, file_name=f"Expenses_{d_start}_to_{d_end}.pdf")
                        st.success(f"Report for {len(report_df)} records generated!")
                    except Exception as e:
                        st.error(f"Report Error: {e}")
                else:
                    st.warning("No records found for the selected period.")
                            
# --- 9. SYSTEM SETUP ---
elif menu == "📑 Reports Center":
    st.markdown("<h2 style='color: #8E44AD;'>📑 Business Reports Center</h2>", unsafe_allow_html=True)
    
    # 1. Column Fixes (Variables වෙනස් නොකර)
    df_raw = st.session_state.df.copy()
    df_raw.columns = [str(c).strip() for c in df_raw.columns]
    df_raw.rename(columns={'Vehicle No': 'Vehicle', 'Vehicle_No': 'Vehicle', 'Entity': 'Vehicle'}, inplace=True)

    # 2. Tabs (ඔයා දුන්න Variables ටික ඒ විදිහටම)
    r_inc, r_prof, r_gross, r_staff, r1, r2, r3, r4 = st.tabs([
        "💰 Daily Income Report", 
        "📊 Profit/Loss Analysis",
        "📈 Material Gross Earnings",
        "👷 Staff Settlement",
        "🚜 Vehicle Settlement", 
        "👤 Driver Summary", 
        "📑 Daily Log", 
        "⛽ Shed Report"
    ])
    
    # 3. Date Selection
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        # timedelta පාවිච්චියට උඩින්ම 'from datetime import timedelta' තියෙන්න ඕනේ
        f_d = st.date_input("From Date", datetime.now().date() - timedelta(days=30), key="r_from")
    with col_d2:
        t_d = st.date_input("To Date", datetime.now().date(), key="r_to")

    # 4. Filtering Logic
    df_raw['Date'] = pd.to_datetime(df_raw['Date'], errors='coerce')
    df_raw['Date_Only'] = df_raw['Date'].dt.date
    
    # Filter කිරීම (Date objects දෙකක් සසඳන නිසා දැන් 100% නිවැරදිව අද දවස අහු වෙනවා)
    df_f = df_raw[(df_raw["Date_Only"] >= f_d) & (df_raw["Date_Only"] <= t_d)].copy()
    df_f['Date'] = df_f['Date_Only']
    # df_f = df_f.drop(columns=['Date_Only']) # මේ පේළිය දැනට තියන්න, පල්ලෙහාට ඕන වෙනවා

    with r_inc:
        st.subheader("Daily Sales & Income Statement")
        
        # 1. Clean columns
        df_f.columns = [str(c).strip() for c in df_f.columns]
        
        # Expense keywords list - ඔයාගේ 'Fuel Entry' කියන නම මෙතනට දැම්මා
        exp_keywords = r"Food|Fuel Entry|Repair|Advance|Rent|Office|Misc|Utility|Excavator|Work|Inward|Stock In"
        
        # 2. Filtering for All Relevant Records (Table එකේ පෙන්නන්න Shed Payment records ගන්නවා)
        daily_report_data = df_f[
            (df_f["Category"].str.contains(r"Sales Out|Outward|r_inc", case=False, na=False, regex=True)) | 
            (df_f["Type"].str.strip().str.capitalize() == "Expense") |
            (df_f["Type"].str.contains(r"r_inc", case=False, na=False, regex=True)) |
            (df_f["Category"].str.contains(exp_keywords + r"|Shed Payment", case=False, na=False, regex=True))
        ].copy()
        
        if not daily_report_data.empty:
            for col in ['Amount', 'Qty_Cubes', 'Rate_At_Time']:
                if col in daily_report_data.columns:
                    daily_report_data[col] = pd.to_numeric(daily_report_data[col], errors='coerce').fillna(0)

            pdf_ready_df = daily_report_data.copy()
            display_combined = daily_report_data.copy()
            
            # --- SUMMARY LOGIC (FIXED FOR FUEL ENTRY & SHED PAYMENT) ---
            
            # 1. Gross Sales
            sales_mask = (
                (daily_report_data["Amount"] > 0) &
                (daily_report_data["Category"].str.contains(r"Sales Out|Outward", case=False, na=False, regex=True)) & 
                (daily_report_data["Type"].str.strip().str.capitalize() != "Expense") &
                (~daily_report_data["Category"].str.contains(exp_keywords + r"|Shed Payment|r_inc", case=False, na=False, regex=True))
            )
            total_sales = daily_report_data[sales_mask]['Amount'].sum()

            # 2. Retention Income (r_inc)
            r_inc_mask = (
                (daily_report_data["Category"].str.contains(r"r_inc", case=False, na=False, regex=True)) |
                (daily_report_data["Type"].str.contains(r"r_inc", case=False, na=False, regex=True))
            )
            total_r_inc = daily_report_data[r_inc_mask]['Amount'].sum()

            # 3. Total Expenses (Fuel Entry ඇතුළත්, Shed Payment ඉවත් කර ඇත)
            # මචං මෙතනින් තමයි Double counting නවත්තන්නේ
            expense_mask = (
                ((daily_report_data["Amount"] < 0) | 
                 (daily_report_data["Type"].str.strip().str.capitalize() == "Expense") |
                 (daily_report_data["Category"].str.contains(exp_keywords, case=False, na=False, regex=True))) &
                (~daily_report_data["Category"].str.contains(r"Shed Payment", case=False, na=False, regex=True))
            )
            total_expenses = daily_report_data[expense_mask]['Amount'].abs().sum()
            
            # Net Balance Calculation
            net_bal = (total_sales + total_r_inc) - total_expenses

            # Summary Metrics
            col_s1, col_s2, col_s3, col_s4 = st.columns(4)
            col_s1.metric("Gross Sales", f"LKR {total_sales:,.2f}")
            col_s2.metric("Retention (r_inc)", f"LKR {total_r_inc:,.2f}")
            col_s3.metric("Total Expenses", f"LKR {total_expenses:,.2f}", delta_color="inverse")
            col_s4.metric("Net Settlement", f"LKR {net_bal:,.2f}")

            # UI Table
            if not display_combined.empty:
                table_display_df = display_combined.copy()
                if 'Amount' in table_display_df.columns:
                    table_display_df['Amount'] = table_display_df['Amount'].abs()
                
                rename_dict = {
                    'Date': 'Date', 'Type': 'Type', 'Category': 'Material/Category', 
                    'Entity': 'Vehicle/Client/Entity', 'Qty_Cubes': 'Qty', 
                    'Rate_At_Time': 'Rate', 'Amount': 'Total Amount'
                }
                cols_to_show = [c for c in rename_dict.keys() if c in table_display_df.columns]
                
                st.dataframe(
                    table_display_df[cols_to_show].rename(columns=rename_dict), 
                    use_container_width=True
                )
            else:
                st.info("දත්ත වාර්තා වී නැත.")

            # PDF Download Button
            if st.button("📥 Download Daily Settlement PDF"):
                inc_summary = {
                    "Report Type": "Daily Settlement Statement",
                    "Period": f"{f_d} to {t_d}",
                    "Total Records": len(pdf_ready_df),
                    "Gross Earnings": f"LKR {total_sales:,.2f}",
                    "Retention Inc": f"LKR {total_r_inc:,.2f}",
                    "Total Expenses": f"LKR {total_expenses:,.2f}",
                    "Net Balance": f"LKR {net_bal:,.2f}"
                }
                pdf_fn = create_pdf(f"Daily_Settlement", pdf_ready_df, inc_summary)
                with open(pdf_fn, "rb") as f:
                    st.download_button("📩 Click to Download PDF", f, file_name=f"Settlement_Report_{f_d}.pdf")

        else:
            st.warning("තෝරාගත් දින පරාසය තුළ දත්ත (Sales, Expenses හෝ r_inc) කිසිවක් නැත.")
            
    # --- TAB: PROFIT/LOSS ANALYSIS ---
    with r_prof:
        st.subheader("📊 Daily Profit & Loss Analysis")
        
        if not df_f.empty:
            # 1. Income (Sales) - Case-insensitive search
            inc_data = df_f[df_f["Category"].str.contains("Sales Out", case=False, na=False)].copy()
            inc_data['Val'] = pd.to_numeric(inc_data['Amount'], errors='coerce').fillna(0)
            
            # 2. Expense (All Expenses)
            # 'Type' එක 'Expense' තියෙන හෝ Category එකේ 'Advance/Salary/Fuel/Repair/Shed' තියෙන ඒවා සලකමු
            exp_data = df_f[(df_f["Type"] == "Expense") | 
                            (df_f["Category"].str.contains("Advance|Salary|Fuel|Repair|Shed", case=False, na=False))].copy()
            exp_data['Val'] = pd.to_numeric(exp_data['Amount'], errors='coerce').fillna(0)

            # 3. දින අනුව Group කිරීම
            d_inc = inc_data.groupby('Date')['Val'].sum()
            d_exp = exp_data.groupby('Date')['Val'].sum()
            
            # 4. Profit Table එක සෑදීම (ඔයාගේ variables ඒ විදිහටම)
            profit_df = pd.concat([d_inc, d_exp], axis=1).fillna(0)
            profit_df.columns = ['Income', 'Expense']
            
            # ශුද්ධ ලාභය ගණනය කිරීම
            profit_df['Net Profit'] = profit_df['Income'] - profit_df['Expense']
            
            # 5. Visualizations (Chart & Table)
            st.bar_chart(profit_df[['Income', 'Expense']])
            
            # Table එක පෙන්වීම (Formatting සමඟ)
            st.dataframe(profit_df.style.format("{:,.2f}"), use_container_width=True)
            
            # 6. Totals Summary
            t_i = profit_df['Income'].sum()
            t_e = profit_df['Expense'].sum()
            net_p = t_i - t_e
            
            # ලාභය හෝ අලාභය අනුව පාට වෙනස් කර පෙන්වීම
            if net_p >= 0:
                st.success(f"✅ Summary: Total Income: LKR {t_i:,.2f} | Total Expense: LKR {t_e:,.2f} | Net Profit: LKR {net_p:,.2f}")
            else:
                st.error(f"⚠️ Summary: Total Income: LKR {t_i:,.2f} | Total Expense: LKR {t_e:,.2f} | Net Loss: LKR {net_p:,.2f}")
        else:
            st.info("දත්ත පද්ධතියේ නැත.")

    # --- TAB: MATERIAL GROSS EARNINGS (FIXED) ---
    with r_gross:
        st.subheader("📈 Material Gross Earnings (Sales Revenue)")
        
        # 1. Column names clean කරමු (Variable names වෙනස් නොකර)
        df_f.columns = [str(c).strip() for c in df_f.columns]
        
        # 2. Sales records පමණක් පෙරමු (case-insensitive search)
        gross_df = df_f[df_f["Category"].str.contains("Sales Out", case=False, na=False)].copy()
        
        if not gross_df.empty:
            # 3. Material Type එක වෙන් කරගමු (Sand / Soil / Other)
            gross_df['Material_Type'] = gross_df['Category'].apply(
                lambda x: "Sand" if "Sand" in str(x) else ("Soil" if "Soil" in str(x) else "Other")
            )
            
            # 4. Amount column එක number එකක් බව ෂුවර් කරගමු
            if 'Amount' in gross_df.columns:
                gross_df['Amount'] = pd.to_numeric(gross_df['Amount'], errors='coerce').fillna(0)
                
                # Summary Table එක සෑදීම
                summary_gross = gross_df.groupby('Material_Type')['Amount'].sum().reset_index()
                summary_gross.columns = ['Material', 'Total Gross Earning (LKR)']
                
                # Visual Layout
                col_g1, col_g2 = st.columns([1, 2])
                with col_g1:
                    st.write("**Earnings Summary:**")
                    st.dataframe(
                        summary_gross.style.format({"Total Gross Earning (LKR)": "{:,.2f}"}), 
                        use_container_width=True,
                        hide_index=True
                    )
                
                with col_g2:
                    # Chart එකේ Material එක x axis එකටත් Earning එක y axis එකටත් ගනිමු
                    st.bar_chart(data=summary_gross.set_index('Material'))
            
            st.divider()
            st.write("**Detailed Sales Log (Period Wise):**")
            
            # 5. Column check - KeyError වැළැක්වීමට (ඔයාගේ logic එකමයි)
            req_cols = ['Date', 'Entity', 'Category', 'Qty_Cubes', 'Amount']
            available_cols = [c for c in req_cols if c in gross_df.columns]
            
            # තියෙන Column ටික විතරක් ලස්සනට පෙන්වමු
            st.dataframe(
                gross_df[available_cols].sort_values(by='Date', ascending=False), 
                use_container_width=True
            )
        else:
            st.info("තෝරාගත් දින පරාසය තුළ විකුණුම් දත්ත (Sales records) කිසිවක් නැත.")

    # --- TAB: STAFF SETTLEMENT (FIXED) ---
    with r_staff:
        st.subheader("👷 Staff Salary & Advance Settlement")
        
        # --- Variables කලින්ම Define කරනවා (NameError එක නොවෙන්න) ---
        ent_col = "Vehicle"  # ඔයාගේ Master Table එකේ Entity/Vehicle column එක
        note_col = "Note"

        # 1. Staff ලැයිස්තුව විතරක් හදාගැනීම (Drivers නැතුව)
        only_staff = []
        if 'staff_db' in st.session_state and not st.session_state.staff_db.empty:
            if "Name" in st.session_state.staff_db.columns:
                only_staff = st.session_state.staff_db["Name"].tolist()
        
        # නම් පිරිසිදු කිරීම (Unique & Sorted)
        only_staff = sorted(list(set([str(x).strip() for x in only_staff if x and str(x).lower() != 'nan'])))

        if only_staff:
            sel_staff = st.selectbox("Select Staff Member", ["-- Select --"] + only_staff, key="staff_only_settle_sel")
            
            if sel_staff != "-- Select --":
                # 2. Filtering - මේ ස්ටාෆ් කෙනාට අදාළ Salary & Advance විතරක් ගැනීම
                staff_mask = (df_f[ent_col].astype(str).str.contains(str(sel_staff), case=False, na=False)) | \
                             (df_f[note_col].astype(str).str.contains(str(sel_staff), case=False, na=False))
                
                staff_rep_raw = df_f[staff_mask].copy()
                
                # Category එකෙන් මූල්‍ය දත්ත විතරක් වෙන් කිරීම
                staff_rep_data = staff_rep_raw[
                    staff_rep_raw['Category'].str.contains('Salary|Advance|Payment|Payroll', case=False, na=False)
                ].copy()
                
                if not staff_rep_data.empty:
                    # Date සහ Amount පිරිසිදු කිරීම
                    staff_rep_data['Date'] = pd.to_datetime(staff_rep_data['Date'], errors='coerce')
                    staff_rep_data['Amount'] = pd.to_numeric(
                        staff_rep_data['Amount'].astype(str).str.replace(',', '').str.replace('Rs.', '').str.strip(), 
                        errors='coerce'
                    ).fillna(0)
        
                    # 3. පඩිය සහ ඇඩ්වාන්ස් ගණනය කිරීම
                    total_salary = staff_rep_data[staff_rep_data['Category'].str.contains('Salary', case=False)]['Amount'].sum()
                    total_advances = staff_rep_data[staff_rep_data['Category'].str.contains('Advance|Payment', case=False)]['Amount'].sum()
                    balance_due = total_salary - total_advances
        
                    # Metrics පෙන්වීම
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Total Salary", f"LKR {total_salary:,.2f}")
                    m2.metric("Total Advances", f"LKR {total_advances:,.2f}")
                    m3.metric("Balance to Pay", f"LKR {balance_due:,.2f}", delta=f"{-balance_due:,.2f}")
        
                    # 4. Table එක පෙන්වීම
                    st.dataframe(
                        staff_rep_data[['Date', 'Category', 'Amount', 'Note']].sort_values(by="Date", ascending=False), 
                        use_container_width=True,
                        hide_index=True
                    )
        
                    # 5. PDF Button
                    if st.button("Generate Staff Report 📄", key="gen_staff_only_btn"):
                        try:
                            fn = create_staff_pdf(sel_staff, staff_rep_data)
                            with open(fn, "rb") as f:
                                st.download_button("Download Report 📥", f, file_name=f"Staff_Report_{sel_staff}.pdf")
                        except Exception as e:
                            st.error(f"PDF Error: {e}")
                else:
                    st.warning(f"No Salary or Advance records found for {sel_staff}")
        else:
            st.info("Staff database එකේ කිසිම කෙනෙක්ව register කරලා නැහැ.")    

            
    # 1. වාහන ලැයිස්තුව ලබා ගනිමු
    v_list = st.session_state.ve_db["No"].tolist() if not st.session_state.ve_db.empty else ["N/A"]
    
    # --- TAB: VEHICLE / MACHINE SETTLEMENT (STRICT FIX) ---
    # --- TAB: VEHICLE / MACHINE SETTLEMENT (STRICT FIX) ---
    with r1:
        st.subheader("🚜 Vehicle / Machine Settlement & Profitability")
        
        dr_list = v_list 
        selected_ve = st.selectbox("Select Vehicle to Settle", dr_list, key="settle_ve")
        
        if selected_ve and selected_ve != "N/A":
            col_options = ['Entity', 'Vehicle', 'Vehicle_No', 'Machine', 'No']
            target_col = next((c for c in col_options if c in df_f.columns), None)
            
            if target_col:
                ve_records = df_f[df_f[target_col] == selected_ve].copy()
                
                if not ve_records.empty:
                    # 1. මැෂින් වර්ගය හඳුනාගැනීම
                    is_excavator = any(x in str(selected_ve).upper() for x in ["EX", "PC", "SK", "EXCAVATOR", "JCB"])
                    ve_records.columns = [str(c).strip() for c in ve_records.columns]
                    
                    # 2. මුලින්ම variables ටික clear කරමු
                    final_units = 0.0
                    final_gross = 0.0
                    final_exp = 0.0

                    # 3. පැය ගණන (Units) ගණනය කිරීම - Strict Check
                    unit_col = next((c for c in ['Qty/Hr', 'Work_Hours', 'Qty_Cubes', 'Qty'] if c in ve_records.columns), None)
                    
                    if unit_col:
                        ve_records[unit_col] = pd.to_numeric(ve_records[unit_col], errors='coerce').fillna(0)
                        # Income හෝ Work Log වලට අදාළ දත්ත පමණක් ගමු
                        unit_filter = (ve_records["Type"] == "Income") | (ve_records["Category"].str.contains("Work Log", case=False, na=False))
                        final_units = float(ve_records[unit_filter][unit_col].sum())
                    
                    # 4. මුදල් ගණනය කිරීම්
                    ve_records['Amount'] = pd.to_numeric(ve_records['Amount'], errors='coerce').fillna(0)
                    
                    # ආදායම
                    income_filter = (ve_records["Type"] == "Income") | (ve_records["Category"].str.contains("Work Log", case=False, na=False))
                    final_gross = float(ve_records[income_filter]["Amount"].sum())
                    
                    # වියදම
                    final_exp = float(ve_records[ve_records["Type"] == "Expense"]["Amount"].sum())
                    
                    # ශේෂය
                    final_net = final_gross - final_exp
                    
                    # 5. Metrics Display (UI එකේ පෙන්වන කොටස)
                    c1, c2, c3, c4 = st.columns(4)
                    if is_excavator:
                        c1.metric("Total Work Hours", f"{final_units:,.2f} hrs")
                    else:
                        c1.metric("Total Qty", f"{final_units:,.2f} Units")
                    
                    c2.metric("Gross Earning", f"Rs. {final_gross:,.2f}")
                    c3.metric("Total Expenses", f"Rs. {final_exp:,.2f}")
                    c4.metric("Net Settlement", f"Rs. {final_net:,.2f}", delta=f"{final_net:,.2f}")
                    
                    st.divider()

                    # 6. PDF එකට දත්ත යවන තැන (මෙහිදී අගයන් string වලට හරවා යවමු)
                    # --- PDF Download Button එක තියෙන කොටස මෙන්න මේ විදිහට update කරන්න ---

                    if st.button("📥 Download Settlement PDF"):
                        # 1. පල්ලෙහා table එකේ පෙන්වන අගයම මෙතනදීත් ගණනය කරගන්නවා
                        unit_col = next((c for c in ['Qty/Hr', 'Work_Hours', 'Qty_Cubes', 'Qty'] if c in ve_records.columns), None)
                        
                        # පල්ලෙහා table එකේ එකතුව ගන්න පාවිච්චි කරන logic එකමයි
                        if unit_col:
                            u_filter = (ve_records["Type"] == "Income") | (ve_records["Category"].str.contains("Work Log", case=False, na=False))
                            calc_units = float(pd.to_numeric(ve_records[u_filter][unit_col], errors='coerce').fillna(0).sum())
                        else:
                            calc_units = 0.0
                    
                        # 2. දැන් මේ දත්ත ටික summary_data එකට දානවා
                        summary_data = {
                            "Vehicle/Machine": str(selected_ve),
                            "Type": "Excavator/Own" if is_excavator else "Lorry/Rented",
                            "Total Units/Hours": f"{calc_units:,.2f}",  # <-- මෙතන තමයි 0.00 වෙන එක නවත්තන්නේ
                            "Gross Earnings": f"Rs. {final_gross:,.2f}",
                            "Total Expenses": f"Rs. {final_exp:,.2f}",
                            "Net Balance": f"Rs. {final_net:,.2f}",
                            "Period": f"{f_d} to {t_d}"
                        }
                    
                        # 3. PDF එක generate කරනවා
                        pdf_path = create_pdf("Settlement_Report", ve_records, summary_data)
                        with open(pdf_path, "rb") as f:
                            st.download_button("📩 Download PDF Now", f, file_name=f"{selected_ve}_Settlement.pdf")
                            
                    # 7. Detailed Log Table
                    st.write(f"**Detailed Transaction Log for {selected_ve}:**")
                    display_cols = ['Date', 'Category', 'Qty_Cubes', 'Work_Hours', 'Qty/Hr', 'Amount', 'Type', 'Note']
                    safe_cols = [c for c in display_cols if c in ve_records.columns]
                    st.dataframe(ve_records[safe_cols].sort_values(by='Date', ascending=False), use_container_width=True)
                    
                else:
                    st.info(f"No records found for {selected_ve} in the selected period.")
            else:
                st.error("System Error: Could not find identification columns.")
                
                # --- මෙන්න මෙතනින් පටන් ගන්න (Landowner Settlement Section) ---
        
      # --- Landowner Settlement Section ---
        st.divider()
        st.subheader("Landowner Settlement")

        # 1. නම් ලැයිස්තුව ලබා ගැනීම (ඔයාගේ logic එකමයි)
        registered_landowners = []
        if 'lo_db' in st.session_state and not st.session_state.lo_db.empty:
            registered_landowners = st.session_state.lo_db["Name"].tolist()
        elif 'df' in st.session_state and not st.session_state.df.empty:
            registered_landowners = [name for name in st.session_state.df['Entity'].unique().tolist() if name and str(name).lower() != 'nan']

        if not registered_landowners:
            registered_landowners = ["N/A"]

        # 2. Selectbox
        selected_landowner = st.selectbox("Select Landowner", options=registered_landowners, key="settle_lo_final_v5")

        if selected_landowner and selected_landowner != "N/A":
            df_f_copy = st.session_state.df.copy() # variable නම පොඩ්ඩක් වෙනස් කළා filter වෙච්ච df එක නිසා
            search_name = str(selected_landowner).strip()
            
            # --- Filtering Logic (ඔයාගේ සුපිරි filter එක) ---
            mask_entity = df_f_copy['Entity'].astype(str).str.strip().str.lower() == search_name.lower()
            mask_note = df_f_copy['Note'].fillna("").astype(str).str.contains(search_name, case=False)
            
            lo_records = df_f_copy[mask_entity | mask_note].copy()
            
            if not lo_records.empty:
                # Amount Cleaning
                lo_records['Amount'] = pd.to_numeric(
                    lo_records['Amount'].astype(str).str.replace(',', '').str.replace('Rs.', '').str.strip(), 
                    errors='coerce'
                ).fillna(0)
                
                # ගණනය කිරීම් (Inward = ආපු වැලි / Advance = දීපු සල්ලි)
                total_payable = lo_records[lo_records['Category'].str.contains('Inward|Stock In', case=False, na=False)]['Amount'].sum()
                total_paid = lo_records[lo_records['Category'].str.contains('Advance|Payment', case=False, na=False)]['Amount'].sum()
                lo_balance = total_payable - total_paid

                # 3. Metrics (Display)
                m1, m2, m3 = st.columns(3)
                m1.metric("Total Payable (Stock)", f"Rs. {total_payable:,.2f}")
                m2.metric("Total Paid (Advances)", f"Rs. {total_paid:,.2f}")
                m3.metric("Balance Due", f"Rs. {lo_balance:,.2f}", delta=f"{-lo_balance:,.2f}", delta_color="inverse")

                # 4. PDF Generation
                # 4. PDF Generation
                if st.button("📄 Generate Landowner Report"):
            
                    # --- මචං මෙතන තමයි Fix එක තියෙන්නේ ---
                    inward_rows = lo_records[lo_records['Category'].str.contains('Inward|Stock In', case=False, na=False)]
                    
                    # Qty_Cubes පේළියේ අගයක් නැත්නම් Qty/Hr පේළිය බලන්න කියලා අපි මෙතන කියනවා
                    # මේ පේළියෙන් column දෙකම චෙක් කරනවා
                    total_cubes_val = pd.to_numeric(inward_rows['Qty_Cubes'], errors='coerce').fillna(0).sum()
                    if total_cubes_val == 0:
                        total_cubes_val = pd.to_numeric(inward_rows['Qty/Hr'], errors='coerce').fillna(0).sum()
                    # ---------------------------------------

                    lo_summary = {
                        "Landowner Name": search_name,
                        "Report Date": datetime.now().strftime("%Y-%m-%d"),
                        "Total Units/Hours": f"{total_cubes_val:,.2f}", 
                        "Total Stock Value": f"Rs. {total_payable:,.2f}",
                        "Total Advances Paid": f"Rs. {total_paid:,.2f}",
                        "Net Balance Payable": f"Rs. {lo_balance:,.2f}"
                    }
                    
                    try:
                        # වැදගත්: ඔයා උඩින් හැදුවේ create_landowner_pdf නම නම් මෙතනත් ඒ නමම දෙන්න
                        lo_pdf_path = create_landowner_pdf(f"LO_Settlement_{search_name}", lo_records, lo_summary)
                        with open(lo_pdf_path, "rb") as f:
                            st.download_button("⬇️ Download Settlement PDF", f, file_name=f"LO_{search_name}.pdf")
                        st.success("Report generated successfully!")
                    except Exception as e:
                        st.error(f"PDF error: {e}")
                
                # 5. Table
                st.write(f"**Detailed History for {search_name}:**")
                display_cols = ['Date', 'Category', 'Entity', 'Qty_Cubes', 'Amount', 'Note']
                existing_cols = [c for c in display_cols if c in lo_records.columns]
                
                # --- මෙන්න මෙතන තමයි Fix එක තියෙන්නේ ---
                if not lo_records.empty:
                    # 1. Date එක හරියටම දින වකවානු බවට හරවනවා (Sort කරන්න කලින්)
                    lo_records['Date'] = pd.to_datetime(lo_records['Date'], errors='coerce')
                    
                    # 2. Sort කරලා DataFrame එක පෙන්වනවා
                    st.dataframe(
                        lo_records[existing_cols].sort_values(by='Date', ascending=False), 
                        use_container_width=True,
                        hide_index=True
                    )
                # ---------------------------------------
                
            else:
                st.warning(f"No records linked to '{search_name}' found.")
                
    # --- TAB 2: DRIVER SUMMARY (FIXED) ---
    with r2:
        st.subheader("👤 Driver Salary & Advance Summary")
        
        # 1. ඩ්‍රයිවර්ලාගේ ලැයිස්තුව ලබා ගැනීම
        dr_list = st.session_state.dr_db["Name"].tolist() if not st.session_state.dr_db.empty else []
        sel_dr = st.selectbox("Select Driver", dr_list, key="dr_sum_select")
        
        if sel_dr:
            # 2. Driver filter කිරීම (Note එකේ නම තිබේදැයි බැලීම)
            dr_rep = df_f[df_f["Note"].fillna("").astype(str).str.contains(str(sel_dr), case=False)].copy()
            
            if not dr_rep.empty:
                # 3. වැදගත්ම කොටස: Salary සහ Advance විතරක් පෙරීම (Trips/Hours මෙතනට එන්නේ නැහැ)
                dr_rep = dr_rep[dr_rep['Category'].str.contains('Salary|Advance|Payroll|D.Advance|Payment', case=False, na=False)].copy()
            
            if not dr_rep.empty:
                # 4. දත්ත පිරිසිදු කිරීම (Amount සහ Date)
                dr_rep['Clean_Amount'] = pd.to_numeric(
                    dr_rep['Amount'].astype(str).str.replace(',', '').str.replace('Rs.', '').str.strip(), 
                    errors='coerce'
                ).fillna(0)
                
                # Date එක sort කරන්න කලින් datetime වලට හරවනවා (Error එක වැලැක්වීමට)
                dr_rep['Date'] = pd.to_datetime(dr_rep['Date'], errors='coerce')
                
                # ගණනය කිරීම්
                total_earned = dr_rep[dr_rep['Category'].str.contains('Salary', case=False)]['Clean_Amount'].sum()
                total_advances = dr_rep[dr_rep['Category'].str.contains('Advance|Payment|D.Advance', case=False)]['Clean_Amount'].sum()
                net_balance = total_earned - total_advances
                
                # Metrics පෙන්වීම
                m1, m2, m3 = st.columns(3)
                m1.metric("Total Salary", f"Rs. {total_earned:,.2f}")
                m2.metric("Total Advances", f"Rs. {total_advances:,.2f}")
                m3.metric("Net Balance", f"Rs. {net_balance:,.2f}", delta=f"{-net_balance:,.2f}")
                
                # 5. Table එක පෙන්වීම
                cols_to_show = ['Date', 'Category', 'Amount', 'Note']
                existing_cols = [c for c in cols_to_show if c in dr_rep.columns]
                
                st.dataframe(
                    dr_rep[existing_cols].sort_values(by='Date', ascending=False), 
                    use_container_width=True,
                    hide_index=True
                )
                
                # 6. PDF Report Button
                if st.button("📄 Download Driver Settlement PDF", key="btn_dr_pdf"):
                    summary_data = {
                        "Driver Name": str(sel_dr),
                        "Total Salary": f"Rs. {total_earned:,.2f}",
                        "Total Advances": f"Rs. {total_advances:,.2f}",
                        "Net Balance": f"Rs. {net_balance:,.2f}",
                        "Report Period": f"{f_d} to {t_d}"
                    }
                    try:
                        pdf_fn = create_driver_pdf(f"Settlement_{sel_dr}", dr_rep, summary_data)
                        with open(pdf_fn, "rb") as f:
                            st.download_button("⬇️ Click to Download PDF", f, file_name=f"Driver_Report_{sel_dr}.pdf")
                    except Exception as e:
                        st.error(f"Error generating PDF: {e}")
            else:
                st.info(f"No Salary or Advance records found for {sel_dr}.")
                
    # --- TAB 3: DAILY LOG (FULL AUDIT TRAIL) ---
    with r3:
    st.subheader("📋 Detailed Transaction Log")
    
    if not df_f.empty:
        # 1. පෙන්විය යුතු තීරු (Fuel_Ltr එකත් මම ඇතුළත් කළා තෙල් විස්තර පේන්න ඕන නිසා)
        log_cols = ['Date', 'Type', 'Category', 'Entity', 'Qty_Cubes', 'Fuel_Ltr', 'Hours', 'Amount', 'Note']
        
        # 2. Database එකේ තියෙන තීරු විතරක් තෝරාගන්නවා
        available_log_cols = [c for c in log_cols if c in df_f.columns]
        
        # 3. දත්ත Sort කිරීම (අලුත්ම ඒක උඩට)
        display_log = df_f[available_log_cols].sort_values(by='Date', ascending=False).copy()
        
        # 4. Numeric දත්ත වලට format එක දීම (Errors එන එක නවත්තන්න fillna(0) කළා)
        format_dict = {}
        if "Amount" in display_log.columns: 
            display_log["Amount"] = pd.to_numeric(display_log["Amount"], errors='coerce').fillna(0)
            format_dict["Amount"] = "{:,.2f}"
        if "Qty_Cubes" in display_log.columns: 
            display_log["Qty_Cubes"] = pd.to_numeric(display_log["Qty_Cubes"], errors='coerce').fillna(0)
            format_dict["Qty_Cubes"] = "{:,.2f}"
        if "Fuel_Ltr" in display_log.columns:
            display_log["Fuel_Ltr"] = pd.to_numeric(display_log["Fuel_Ltr"], errors='coerce').fillna(0)
            format_dict["Fuel_Ltr"] = "{:,.2f}"
        if "Hours" in display_log.columns: 
            display_log["Hours"] = pd.to_numeric(display_log["Hours"], errors='coerce').fillna(0)
            format_dict["Hours"] = "{:,.2f}"

        # 5. Table එක පෙන්වීම
        st.dataframe(
            display_log.style.format(format_dict), 
            use_container_width=True,
            height=500,
            hide_index=True
        )
        
        # CSV Download Button
        csv = display_log.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Export Full Log as CSV",
            data=csv,
            file_name=f"Detailed_Log.csv",
            mime='text/csv',
        )
    else:
        st.info("දත්ත කිසිවක් වාර්තා වී නැත.")
        
    # --- TAB 4: SHED REPORT (FUEL & PAYMENTS) ---
    with r4:
        st.subheader("⛽ Fuel & Shed Settlement Analysis")
        
        # 1. දත්ත පෙරීම (තව ටිකක් විශ්වාසවන්ත විදියට)
        # Category එකේ තියෙන spaces අයින් කරලා චෙක් කරනවා
        if not df_f.empty:
            # Category column එක string එකක් විදියට අරන් දෙපැත්තේ spaces අයින් කරනවා
            temp_df = df_f.copy()
            temp_df["Category_Clean"] = temp_df["Category"].astype(str).str.strip()
            
            # 'Fuel' හෝ 'Shed' අඩංගු දත්ත විතරක් ගන්නවා
            shed_f = temp_df[temp_df["Category_Clean"].str.contains(r"Fuel|Shed", case=False, na=False)].copy()
            
            if not shed_f.empty:
                # Amount එක numeric වලට හරවනවා
                if 'Amount' in shed_f.columns:
                    shed_f['Amount'] = pd.to_numeric(shed_f['Amount'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
        
                # 2. Fuel Bill සහ Paid Amount වෙන් කරගැනීම
                # "Fuel Entry" කියන Category එකට අදාළ ඒවා Bill එකට ගන්නවා
                f_bill = shed_f[shed_f["Category_Clean"].str.contains("Fuel", case=False, na=False)]["Amount"].sum()
                
                # "Shed Payment" කියන Category එකට අදාළ ඒවා Paid එකට ගන්නවා
                p_paid = shed_f[shed_f["Category_Clean"].str.contains("Shed", case=False, na=False)]["Amount"].sum()
                
                # 3. Metrics පෙන්වීම
                c1, c2, c3 = st.columns(3)
                c1.metric("Total Fuel Bill", f"Rs. {f_bill:,.2f}")
                c2.metric("Total Paid to Shed", f"Rs. {p_paid:,.2f}")
                
                debt = f_bill - p_paid
                # ණය තියෙනවා නම් රතු පාටින් පෙන්වන්න (delta_color="normal" and delta is negative)
                c3.metric("Shed Debt (Balance)", f"Rs. {debt:,.2f}", delta=f"{-debt:,.2f}", delta_color="inverse")
                
                st.divider()
                
                # 4. Table එක
                st.write("**Fuel & Payment History:**")
                # මෙතන 'Fuel_Ltr' එකත් තිබුණොත් පෙන්වන්න දාන්නම්
                display_cols = ['Date', 'Category', 'Entity', 'Qty_Cubes', 'Fuel_Ltr', 'Amount', 'Note']
                actual_cols = [c for c in display_cols if c in shed_f.columns]
                
                st.dataframe(
                    shed_f[actual_cols].sort_values(by='Date', ascending=False), 
                    use_container_width=True,
                    hide_index=True
                )
                
                # 5. Shed PDF එක
                if st.button("📄 Download Shed Statement"):
                    try:
                        summary = {
                            "Report Type": "Fuel & Shed Settlement Analysis",
                            "Total Fuel Bill": f"Rs. {f_bill:,.2f}",
                            "Total Paid": f"Rs. {p_paid:,.2f}",
                            "Outstanding Debt": f"Rs. {debt:,.2f}"
                        }
                        fn = create_pdf("Shed_Report", shed_f[actual_cols], summary)
                        with open(fn, "rb") as f:
                            st.download_button("⬇️ Download PDF", f, file_name=f"Shed_Statement.pdf")
                    except Exception as e:
                        st.error(f"Error generating PDF: {e}")
            else:
                st.info("තෝරාගත් දින පරාසය තුළ ඉන්ධන (Fuel) හෝ ෂෙඩ් (Shed) ගෙවීම් වාර්තා වී නැත.")
        else:
            st.info("දත්ත කිසිවක් වාර්තා වී නැත.")
        
# --- 10. SYSTEM SETUP (මේ කොටස අලුතින් ඇතුළත් කරන්න) ---
elif menu == "⚙️ System Setup":
        st.markdown("<h2 style='color: #2E86C1;'>⚙️ System Configuration</h2>", unsafe_allow_html=True)
        
        # ටැබ් තුනක් සාදමු - වාහන, ඩ්‍රයිවර්ස්ලා සහ අනෙකුත් සේවකයෝ
        setup_tab1, setup_tab2, setup_tab3 = st.tabs(["🚜 Vehicles", "👷 Drivers", "👥 Staff Management"])

        # --- TAB 1: VEHICLES (SYSTEM SETUP) ---
        with setup_tab1:
            st.subheader("🚜 Add New Vehicle / Machine")
            
            # 1. වාහන ලියාපදිංචි කිරීමේ Form එක
            with st.form("v_setup_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    v_no = st.text_input("Vehicle Number (Ex: WP CP-1234)")
                    v_type = st.selectbox("Vehicle Type", ["Tipper", "Excavator", "JCB", "Tractor", "Lorry", "Other"])
                with col2:
                    v_owner = st.text_input("Owner Name")
                    v_rate = st.number_input("Rate per Unit (LKR)", min_value=0.0, step=100.0)
                
                if st.form_submit_button("✅ Register Vehicle"):
                    if v_no:
                        is_duplicate = False
                        if not st.session_state.ve_db.empty:
                            if v_no in st.session_state.ve_db["No"].values:
                                is_duplicate = True
                        
                        if not is_duplicate:
                            new_v_data = {
                                "No": v_no,
                                "Type": v_type,
                                "Owner": v_owner,
                                "Rate_Per_Unit": v_rate
                            }
                            save_setup_item("vehicles", new_v_data)
                            st.success(f"Vehicle {v_no} registered successfully!")
                        else:
                            st.error(f"Vehicle {v_no} is already registered!")
                    else:
                        st.warning("Please enter a Vehicle Number.")
            
            # 2. ලියාපදිංචි වාහන ලැයිස්තුව (මේ පේළිය line 1589 විය යුතුයි)
            if not st.session_state.ve_db.empty:
                st.divider()
                st.subheader("📋 Registered Vehicles List")
                st.dataframe(st.session_state.ve_db, use_container_width=True, hide_index=True)
                
                col_m1, col_m2 = st.columns([2, 1])
                with col_m1:
                    ve_to_manage = st.selectbox("Select Vehicle", st.session_state.ve_db["No"].tolist(), key="manage_ve_sel")
                
                with col_m2:
                    st.write(" ") 
                    if st.button("Delete Vehicle ❌", key="del_ve", use_container_width=True):
                        try:
                            conn.table("vehicles").delete().eq("No", ve_to_manage).execute()
                            st.session_state.ve_db = st.session_state.ve_db[st.session_state.ve_db["No"] != ve_to_manage]
                            st.warning(f"Vehicle {ve_to_manage} removed.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")

        # --- TAB 2: DRIVERS / OPERATORS ---
        with setup_tab2:
            st.subheader("👷 Add New Driver / Operator")
            
            # 1. ඩ්‍රයිවර් ලියාපදිංචි කිරීමේ Form එක
            with st.form("d_setup_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    d_name = st.text_input("Full Name")
                    d_phone = st.text_input("Contact Number", placeholder="07x-xxxxxxx")
                with col2:
                    d_salary = st.number_input("Daily Salary (Rs.)", min_value=0.0, step=100.0)
                
                if st.form_submit_button("✅ Register Driver"):
                    if d_name:
                        if d_name not in st.session_state.dr_db["Name"].values:
                            try:
                                new_driver_data = {
                                    "Name": d_name,
                                    "Phone": d_phone,
                                    "Daily_Salary": d_salary
                                }
                                conn.table("drivers").insert(new_driver_data).execute()
                                
                                new_d = pd.DataFrame([[d_name, d_phone, d_salary]], 
                                                     columns=["Name", "Phone", "Daily_Salary"])
                                st.session_state.dr_db = pd.concat([st.session_state.dr_db, new_d], ignore_index=True)
                                st.success(f"Driver {d_name} registered successfully in Supabase!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Supabase Error: {e}")
                        else:
                            st.error(f"Driver {d_name} is already in the system!")
                    else:
                        st.warning("Please enter the Driver's Name.")
        
            # 2. ලියාපදිංචි ඩ්‍රයිවර්ලා කළමනාකරණය (List & Delete)
            if not st.session_state.dr_db.empty:
                st.divider()
                st.subheader("📋 Registered Driver List")
                st.dataframe(st.session_state.dr_db, use_container_width=True, hide_index=True)
                
                col_dr1, col_dr2 = st.columns([2, 1])
                with col_dr1:
                    dr_to_manage = st.selectbox("Select Driver to Manage", 
                                               st.session_state.dr_db["Name"].tolist(), key="sel_dr_manage")
                with col_dr2:
                    st.write(" ") 
                    if st.button("Delete Driver ❌", key="del_dr", use_container_width=True):
                        try:
                            conn.table("drivers").delete().eq("Name", dr_to_manage).execute()
                            st.session_state.dr_db = st.session_state.dr_db[st.session_state.dr_db["Name"] != dr_to_manage]
                            st.warning(f"Driver {dr_to_manage} removed from Database.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Delete Error: {e}")
                    
       # --- TAB 3: STAFF MANAGEMENT (Syntaxcore ERP Standard) ---
        # --- TAB: STAFF REGISTRATION (SETUP) ---
        with setup_tab3:
            st.subheader("👷 Add New Staff Member")
            
            # --- අලුත් Staff කෙනෙක්ව ඇතුළත් කරන Form එක ---
            with st.form("staff_reg_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    s_name = st.text_input("Staff Name")
                    s_pos = st.text_input("Position (Ex: Helper, Supervisor)")
                with col2:
                    s_rate = st.number_input("Daily Rate (Rs.)", min_value=0.0, step=100.0)
                    
                if st.form_submit_button("✅ Register Staff"):
                    if s_name:
                        # දැනට ඉන්නවද කියලා Check කිරීම
                        if s_name not in st.session_state.staff_db["Name"].values:
                            try:
                                new_staff = {
                                    "Name": s_name,
                                    "Position": s_pos,
                                    "Daily_Rate": s_rate
                                }
                                # Supabase එකට Insert කිරීම
                                conn.table("staff").insert(new_staff).execute()
                                
                                # Local List එක Update කිරීම
                                new_s_df = pd.DataFrame([new_staff])
                                st.session_state.staff_db = pd.concat([st.session_state.staff_db, new_s_df], ignore_index=True)
                                
                                st.success(f"Staff member {s_name} registered successfully!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Cloud Error: {e}")
                        else:
                            st.error("This member is already registered!")
                    else:
                        st.warning("Please enter the Staff Name.")
            
            # --- ලියාපදිංචි අයගේ ලැයිස්තුව සහ Edit/Delete පහසුකම ---
            if not st.session_state.staff_db.empty:
                st.divider()
                st.subheader("📝 Manage Registered Staff")
                
                # Manage කරන්න ඕන කෙනාව තෝරගන්න Dropdown එක
                staff_names = st.session_state.staff_db["Name"].tolist()
                selected_staff = st.selectbox("Select Member to Edit or Delete", ["-- Select Member --"] + staff_names)
                
                if selected_staff != "-- Select Member --":
                    # තෝරාගත් කෙනාගේ දත්ත වෙනම පෙන්වීම
                    staff_info = st.session_state.staff_db[st.session_state.staff_db["Name"] == selected_staff].iloc[0]
                    
                    with st.expander(f"⚙️ Edit Details: {selected_staff}", expanded=True):
                        e_col1, e_col2 = st.columns(2)
                        with e_col1:
                            edit_name = st.text_input("Full Name", staff_info["Name"])
                            edit_pos = st.text_input("Position", staff_info["Position"])
                        with e_col2:
                            edit_rate = st.number_input("Daily Rate (Rs.)", value=float(staff_info["Daily_Rate"]))
                        
                        btn_col1, btn_col2, _ = st.columns([1, 1, 2])
                        
                        # --- UPDATE කොටස ---
                        # --- UPDATE කොටස ---
                        if btn_col1.button("💾 Update Details"):
                            try:
                                updated_data = {
                                    "Name": edit_name,
                                    "Position": edit_pos,
                                    "Daily_Rate": edit_rate
                                }
                                # 1. Cloud Update
                                conn.table("staff").update(updated_data).eq("Name", selected_staff).execute()
                                
                                # 2. Local List එකත් එසැණින් Update කිරීම (මේකයි වැදගත්)
                                idx = st.session_state.staff_db[st.session_state.staff_db["Name"] == selected_staff].index[0]
                                for key, value in updated_data.items():
                                    st.session_state.staff_db.at[idx, key] = value

                                st.success(f"✅ {selected_staff} updated successfully!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Update Error: {e}")

                        # --- DELETE කොටස ---
                        if btn_col2.button("🗑️ Delete Staff"):
                            try:
                                # 1. Cloud Delete
                                conn.table("staff").delete().eq("Name", selected_staff).execute()
                                
                                # 2. Local List එකෙන් අයින් කිරීම
                                st.session_state.staff_db = st.session_state.staff_db[st.session_state.staff_db["Name"] != selected_staff]
                                
                                st.warning(f"🚫 {selected_staff} removed from system.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Delete Error: {e}")
                
                # සම්පූර්ණ ලිස්ට් එක Table එකක් විදිහට පහළින් පෙන්වීම
                st.divider()
                st.caption("Current Staff Registry")
                st.dataframe(st.session_state.staff_db, use_container_width=True, hide_index=True)
                    
# --- මේක වෙනම Menu එකක් විදිහට පල්ලෙහායින් දාන්න ---
elif menu == "👤 Manage Landowners":
        st.markdown("<h2 style='color: #1E8449;'>👤 Landowner Management</h2>", unsafe_allow_html=True)
        
        # Tabs තුනක් හදමු
        l_tab1, l_tab2, l_tab3 = st.tabs(["🆕 Register Landowner", "💰 Give Advance", "📋 View All"])

        # --- TAB 1: Register New Landowner ---
        with l_tab1:
            st.subheader("🆕 Add a New Landowner to System")
            with st.form("landowner_reg_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    l_name = st.text_input("Full Name")
                    l_addr = st.text_input("Land Location / Address")
                with col2:
                    l_cont = st.text_input("Contact Number")
                    l_rate = st.number_input("Rate Per Cube (LKR)", min_value=0.0, step=100.0)
                
                if st.form_submit_button("✅ Register Landowner"):
                    if l_name:
                        # 1. ඩියුප්ලිකේට් චෙක් එක වඩාත් ආරක්ෂිතව කරනවා
                        is_duplicate = False
                        if not st.session_state.lo_db.empty and "Name" in st.session_state.lo_db.columns:
                            if l_name in st.session_state.lo_db["Name"].values:
                                is_duplicate = True
                        
                        if not is_duplicate:
                            try:
                                # 2. Supabase එකට දත්ත යවනවා
                                new_entry = {
                                    "Name": l_name, 
                                    "Address": l_addr, 
                                    "Contact": l_cont, 
                                    "Rate_Per_Cube": l_rate
                                }
                                conn.table("landowners").insert(new_entry).execute()
                                
                                # 3. Local Session එකත් Update කරනවා
                                new_lo = pd.DataFrame([new_entry])
                                st.session_state.lo_db = pd.concat([st.session_state.lo_db, new_lo], ignore_index=True)
                                
                                st.success(f"Registered {l_name} and Synced with Cloud!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Cloud Save Error: {e}")
                        else:
                            st.error("This landowner is already registered.")
                    else:
                        st.error("Landowner Name is required!")

        # --- TAB 2: Give Advance ---
        with l_tab2:
            st.subheader("💰 Record Advance Payment")
            if not st.session_state.lo_db.empty:
                with st.form("lo_advance_form", clear_on_submit=True):
                    lo_names = st.session_state.lo_db["Name"].tolist()
                    selected_lo = st.selectbox("Select Landowner", lo_names)
                    adv_date = st.date_input("Date", datetime.now().date())
                    adv_amount = st.number_input("Advance Amount (LKR)", min_value=0.0, step=1000.0)
                    adv_note = st.text_input("Reference Note")

                    if st.form_submit_button("✅ Save Advance Payment"):
                        if adv_amount > 0:
                            new_entry = {
                                "Date": str(adv_date),
                                "Type": "Expense",
                                "Category": "Landowner Advance",
                                "Entity": selected_lo,
                                "Note": adv_note,
                                "Amount": adv_amount,
                                "Qty_Cubes": 0, "Hours": 0, "Rate_At_Time": 0, "Status": "Paid"
                            }
                            try:
                                # කෙලින්ම Master Log එකටත් යවනවා
                                conn.table("master_log").insert(new_entry).execute()
                                # ආපහු Database එකෙන් දත්ත Refresh කරගන්නවා
                                st.session_state.df = load_data("master_log", cols_master)
                                st.success(f"LKR {adv_amount:,.2f} advance paid to {selected_lo} and saved to Cloud!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error Syncing Advance: {e}")
            else:
                st.info("No landowners registered yet.")

        # --- TAB 3: View & Manage ---
        with l_tab3:
            st.subheader("📋 Registered Landowners List")
            if not st.session_state.lo_db.empty:
                st.dataframe(st.session_state.lo_db, use_container_width=True, hide_index=True)
                st.divider()
                lo_to_del = st.selectbox("Select Landowner to Remove", st.session_state.lo_db["Name"].tolist(), key="del_lo_box")
                if st.button("Delete Landowner ❌"):
                    try:
                        # Supabase එකෙනුත් අයින් කරනවා
                        conn.table("landowners").delete().eq("Name", lo_to_del).execute()
                        st.session_state.lo_db = st.session_state.lo_db[st.session_state.lo_db["Name"] != lo_to_del]
                        st.warning(f"{lo_to_del} removed from Cloud.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Delete Error: {e}")

# --- 12. STAFF PAYROLL SECTION (දැන් මේක හරියටම Align වෙලා තියෙන්නේ) ---
elif menu == "👷 Staff Payroll":
        st.subheader("💳 Staff Salary & Advance Management")
        
        if "staff_db" not in st.session_state or st.session_state.staff_db.empty:
            st.warning("Please register staff members first.")
        else:
            s_names = st.session_state.staff_db["Name"].tolist()
            with st.form("staff_pay", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    member = st.selectbox("Select Staff Member", s_names)
                    pay_date = st.date_input("Date", datetime.now().date())
                    days = st.number_input("Work Days / Shift", min_value=0.0, step=0.5)
                with col2:
                    pay_type = st.selectbox("Payment Type", ["Salary", "Advance", "Food/Other"])
                    amount = st.number_input("Amount (LKR)", min_value=0.0, step=500.0)
                
                note = st.text_input("Additional Note")
                
                if st.form_submit_button("✅ Save Staff Payment"):
                    if amount > 0:
                        new_staff_data = {
                            "Date": str(pay_date), 
                            "Type": "Expense",
                            "Category": f"Staff {pay_type}", 
                            "Entity": member, 
                            "Note": f"Days: {days} | {note}", 
                            "Amount": amount,
                            "Qty_Cubes": 0, "Hours": days, "Rate_At_Time": 0, "Status": "Paid"
                        }
                        try:
                            conn.table("master_log").insert(new_staff_data).execute()
                            # load_data function එක සහ cols_master variable එක පාවිච්චි කරලා තියෙනවා
                            st.session_state.df = load_data("master_log", cols_master)
                            st.success(f"Rs. {amount:,.2f} saved for {member}!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Cloud Sync Error: {e}")  
    

# --- DATA MANAGER SECTION ---
elif menu == "⚙️ Data Manager":
        st.markdown(f"<h2 style='color: #E67E22;'>⚙️ Data Manager</h2>", unsafe_allow_html=True)
        st.info("මෙහිදී ඔබට වැරදිලාවත් ඇතුළත් කළ දත්ත Edit කිරීමට හෝ Delete කිරීමට හැකියාව ඇත.")
        
        if st.session_state.df.empty:
            st.warning("No data found in the system to manage.")
        else:
            # 1. ID එකෙන් Record එක සොයා ගැනීම
            search_id = st.number_input("Enter Record ID to Edit/Delete", min_value=1, step=1)
            
            # DataFrame එකේ index එක හරියටම අල්ලගන්නවා (ඔයාගේ logic එක)
            record_idx = st.session_state.df.index[st.session_state.df["id"] == search_id].tolist()
            
            if record_idx:
                idx = record_idx[0]
                record = st.session_state.df.loc[idx]
                
                st.write(f"### 🔍 Managing Record ID: {search_id}")
                # තෝරාගත් row එක ලස්සනට පෙන්වීම
                st.dataframe(pd.DataFrame([record]), use_container_width=True, hide_index=True)
                
                col1, col2 = st.columns(2)
                
                # --- EDIT FORM ---
                with col1:
                    st.subheader("📝 Edit Full Record")
                    with st.form("edit_record_form", clear_on_submit=True):
                        # 1. මූලික විස්තර
                        u_date = st.date_input("Update Date", value=pd.to_datetime(record["Date"]))
                        
                        # Category සහ Type
                        categories = ["💰 Sales Out (Sand)", "💰 Sales Out (Soil)", "🚚 Inward (Sand)", "🚚 Inward (Soil)", "⛽ Fuel", "🔧 Maintenance", "💸 Expense"]
                        u_category = st.selectbox("Category", options=categories, index=categories.index(record["Category"]) if record["Category"] in categories else 0)
                        
                        u_type = st.selectbox("Type", options=["Income", "Expense"], index=0 if record["Type"] == "Income" else 1)
                        
                        u_entity = st.text_input("Vehicle / Entity Name", value=str(record["Entity"]))
                        u_note = st.text_input("Modify Note", value=str(record["Note"]))
                        
                        # 2. සංඛ්‍යාත්මක දත්ත (Metrics)
                        c1, c2 = st.columns(2)
                        with c1:
                            u_amount = st.number_input("Amount (LKR)", value=float(record["Amount"]), step=100.0)
                            u_qty = st.number_input("Quantity (Cubes)", value=float(record["Qty_Cubes"]), step=0.5)
                            u_fuel = st.number_input("Fuel (Ltrs)", value=float(record["Fuel_Ltr"]), step=1.0)
                        with c2:
                            u_hours = st.number_input("Hours / Days", value=float(record["Hours"]), step=0.5)
                            u_rate = st.number_input("Rate Used", value=float(record["Rate_At_Time"]), step=10.0)
                            # Status එක database එකේ තියෙන අගය අනුව index එක තෝරමු
                            status_options = ["Completed", "Pending", "Canceled"]
                            current_status = record.get("Status", "Completed")
                            u_status = st.selectbox("Status", options=status_options, index=status_options.index(current_status) if current_status in status_options else 0)
                
                        # 3. Update Button
                        submit_update = st.form_submit_button("✅ Update Everything Now")
                
                        if submit_update:
                            try:
                                # --- Supabase Update Query ---
                                update_data = {
                                    "Date": u_date.strftime("%Y-%m-%d"),
                                    "Category": u_category,
                                    "Type": u_type,
                                    "Entity": u_entity,
                                    "Note": u_note,
                                    "Amount": u_amount,
                                    "Qty_Cubes": u_qty,
                                    "Fuel_Ltr": u_fuel,
                                    "Hours": u_hours,
                                    "Rate_At_Time": u_rate,
                                    "Status": u_status
                                }
                                
                                # මෙතන table නම 'master_log' විදිහට වෙනස් කළා
                                conn.table("master_log").update(update_data).eq("id", record["id"]).execute()
                
                                # Local Session State එක Update කිරීම
                                for key, value in update_data.items():
                                    st.session_state.df.at[idx, key] = value
                
                                st.success(f"Record {record['id']} updated successfully in Master Log!")
                                st.rerun()
                
                            except Exception as e:
                                st.error(f"Error updating record: {e}")
              
                with col2:
                    st.subheader("🗑️ Delete Record")
                    st.error("❗ Warning: This action cannot be undone.")
                    if st.button("🔥 Confirm Permanent Delete", use_container_width=True):
                        try:
                            # 1. Supabase එකෙන් අදාල ID එක තියෙන Row එක Delete කිරීම
                            # මෙතන "master_log" වෙනුවට ඔයාගේ table එකේ නම දාන්න (උදා: sales, records)
                            conn.table("master_log").delete().eq("id", search_id).execute()
                            
                            # 2. Local session state එකත් update කරනවා (UI එකේ පේන්න)
                            st.session_state.df = st.session_state.df[st.session_state.df["id"] != search_id].reset_index(drop=True)
                            
                            st.success(f"Record {search_id} deleted forever from Database!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error deleting from Supabase: {e}")
                            
           # --- අලුත් ආරක්ෂිත ක්‍රමය (Data Fixes ඇතුළුව) ---
            if not st.session_state.df.empty:
                # 1. පෙන්වන්න කලින් Data ටික Clean කරගමු (Arrow Error එක නැති කරන්න)
                df_to_show = st.session_state.df.copy()

                for col in df_to_show.columns:
                    # ඉලක්කම් තියෙන columns වල අකුරු/None තිබුණොත් ඒවා 0 කරන්න
                    if col in ["Amount", "Qty_Cubes", "Fuel_Ltr", "Hours", "Rate_At_Time"]:
                        df_to_show[col] = pd.to_numeric(df_to_show[col], errors='coerce').fillna(0)
                    else:
                        # අනිත් හැම එකක්ම string බවට පත් කරන්න
                        df_to_show[col] = df_to_show[col].astype(str)

                # 2. දැන් ලස්සනට Table එක පෙන්වමු
                st.dataframe(
                    df_to_show.sort_values(by="id", ascending=False), 
                    width="stretch", 
                    hide_index=True
                )
            else:
                st.info("No records found in the database.")
