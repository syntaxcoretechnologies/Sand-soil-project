# --- 5. ADVANCED REPORTS (FILTERED BY DRIVER/VEHICLE) ---
elif choice == "Advanced Reports":
    st.subheader("Filter & Generate Statements")
    
    report_type = st.radio("Select Report Type", ["Driver Summary", "Vehicle/Machine Summary", "Full Transaction Log"], horizontal=True)
    
    col1, col2 = st.columns(2)
    f_date = col1.date_input("From Date", datetime.now().date() - timedelta(days=30))
    t_date = col2.date_input("To Date", datetime.now().date())

    # --- DRIVER SUMMARY ---
    if report_type == "Driver Summary":
        if not dr_db.empty:
            sel_dr = st.selectbox("Select Driver", dr_db["Name"].tolist())
            # Driver ge data filter kirima
            dr_data = df[(df["Entity"] == sel_dr) & (df["Date"] >= f_date) & (df["Date"] <= t_date)]
            
            # Calculations
            advances = dr_data[dr_data["Category"] == "Advance"]["Amount"].sum()
            salary_paid = dr_data[dr_data["Category"] == "Salary Payment"]["Amount"].sum()
            days_worked = len(dr_data[dr_data["Category"] == "Work Entry"]["Date"].unique())
            
            st.info(f"Summary for {sel_dr} from {f_date} to {t_date}")
            c1, c2, c3 = st.columns(3)
            c1.metric("Days Worked", f"{days_worked} Days")
            c2.metric("Total Advances", f"Rs. {advances:,.2f}")
            c3.metric("Salary Paid", f"Rs. {salary_paid:,.2f}")
            
            st.dataframe(dr_data[["Date", "Category", "Note", "Amount"]], use_container_width=True)
            
            if st.button("Generate Driver PDF"):
                fn = create_pdf(f"Driver_{sel_dr}", dr_data, {"Driver": sel_dr, "Period": f"{f_date} to {t_date}", "Work Days": days_worked})
                with open(fn, "rb") as f: st.download_button("📩 Download PDF", f, file_name=fn)
        else: st.warning("No drivers found.")

    # --- VEHICLE SUMMARY ---
    elif report_type == "Vehicle/Machine Summary":
        if not ve_db.empty:
            sel_ve = st.selectbox("Select Vehicle/Machine", ve_db["No"].tolist())
            ve_data = df[(df["Entity"] == sel_ve) & (df["Date"] >= f_date) & (df["Date"] <= t_date)]
            
            # Calculations
            total_fuel = ve_data[ve_data["Category"] == "Fuel Entry"]["Amount"].sum()
            total_work_cost = ve_data[ve_data["Category"].isin(["Machine Work", "Lorry Trip"])]["Amount"].sum()
            total_hrs = ve_data["Hours"].sum()
            total_cubes = ve_data["Qty_Cubes"].sum()
            
            st.info(f"Performance for {sel_ve}")
            v1, v2, v3, v4 = st.columns(4)
            v1.metric("Total Fuel Cost", f"Rs. {total_fuel:,.2f}")
            v2.metric("Operation Cost", f"Rs. {total_work_cost:,.2f}")
            if total_hrs > 0: v3.metric("Total Hours", f"{total_hrs} Hrs")
            if total_cubes > 0: v4.metric("Total Cubes", f"{total_cubes} Cubes")
            
            st.dataframe(ve_data[["Date", "Category", "Note", "Hours", "Qty_Cubes", "Amount"]], use_container_width=True)
            
            if st.button("Generate Vehicle PDF"):
                fn = create_pdf(f"Vehicle_{sel_ve}", ve_data, {"Vehicle": sel_ve, "Total Fuel": total_fuel, "Work Cost": total_work_cost})
                with open(fn, "rb") as f: st.download_button("📩 Download PDF", f, file_name=fn)
        else: st.warning("No vehicles found.")

    # --- FULL LOG ---
    else:
        full_view = df[(df["Date"] >= f_date) & (df["Date"] <= t_date)]
        st.dataframe(full_view, use_container_width=True)
