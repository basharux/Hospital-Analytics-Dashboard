import os
import streamlit as st
import pandas as pd
import pymysql
import plotly.express as px
import plotly.graph_objects as go
from auth import login_gate, allowed_menu, logout_button, manage_users

# python -m streamlit run hospitall.py

st.set_page_config(
    page_title="Hospital Analytics",
    page_icon="🏥",
    layout="wide"
)

# ---------------- VISUAL THEME ----------------
BRAND_COLORS = ["#6C5CE7", "#00CEC9", "#FD79A8", "#FDCB6E", "#55EFC4", "#74B9FF", "#E17055"]
ACCENT_SCALE = ["#2D1B69", "#6C5CE7", "#A29BFE", "#00CEC9", "#55EFC4"]
CHART_FONT = "Segoe UI, Helvetica, Arial, sans-serif"

def style_chart(fig, title=None, height=400):
    """Apply consistent branding to every Plotly figure."""
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=CHART_FONT, size=13, color="#E8E8E8"),
        title=dict(text=title, x=0.02, xanchor="left", font=dict(size=18, weight="bold")) if title else None,
        height=height,
        margin=dict(t=60 if title else 20, b=30, l=30, r=30),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
        hoverlabel=dict(bgcolor="#1E1E2E", font_size=13, font_family=CHART_FONT),
    )
    fig.update_xaxes(gridcolor="rgba(255,255,255,0.08)", zeroline=False)
    fig.update_yaxes(gridcolor="rgba(255,255,255,0.08)", zeroline=False)
    return fig

# ---------------- DATABASE CONNECTION ----------------
# Credentials come ONLY from .streamlit/secrets.toml or environment variables.
def get_connection():
    def cfg(key, default=None):
        try:
            return st.secrets[key]
        except Exception:
            return os.getenv(key, default)

    keys = ["DB_HOST", "DB_USER", "DB_PASSWORD", "DB_NAME"]
    values = {k: cfg(k) for k in keys}
    missing = [k for k, v in values.items() if v is None]
    if missing:
        raise RuntimeError(f"Missing settings: {', '.join(missing)}")

    # SSL is only switched on when DB_SSL = "true" (needed for TiDB Cloud)
    extra = {}
    if str(cfg("DB_SSL", "false")).lower() == "true":
        import certifi
        extra = dict(
            ssl={"ca": certifi.where()},
            ssl_verify_cert=True,
            ssl_verify_identity=True,
        )

    return pymysql.connect(
        host=values["DB_HOST"],
        port=int(cfg("DB_PORT", 3306)),
        user=values["DB_USER"],
        password=values["DB_PASSWORD"],
        database=values["DB_NAME"],
        autocommit=True,
        **extra
    )


try:
    conn = get_connection()
    cursor = conn.cursor()
except Exception as e:
    st.error(f"Database Connection Failed: {e}")
    st.stop()

# ---------------- LOGIN ----------------
user = login_gate(conn)   # app stops here until the user logs in

# ---------------- SIDEBAR ----------------
st.sidebar.title("🏥 Hospital Business Analytics")
st.sidebar.caption("Executive Decision Support System")

menu = [
    "Executive Dashboard",
    "Add Patient",
    "View Patients",
    "Add Doctor",
    "View Doctors",
    "Book Appointment",
    "View Appointments",
    "Billing",
    "Medicine"
]

menu = allowed_menu(user["role"], menu)
choice = st.sidebar.selectbox("Menu", menu)
logout_button(user)

# ================================================================
# ---------------- DASHBOARD ----------------
# ================================================================
if choice == "Executive Dashboard":

    st.title("🏥 Hospital Business Analytics Dashboard")
    st.write("Executive Decision Support Dashboard | Python • SQL • Streamlit • Plotly")

    # ---------------- FILTERS ----------------
    st.subheader("🎯 Dashboard Filters")

    col1, col2, col3 = st.columns(3)

    with col1:
        selected_gender = st.selectbox(
            "Gender",
            ["All", "Male", "Female", "Other"]
        )

    ward_list = pd.read_sql(
        "SELECT DISTINCT ward_type FROM patients ORDER BY ward_type",
        conn
    )["ward_type"].dropna().tolist()

    with col2:
        selected_ward = st.selectbox(
            "Ward Type",
            ["All"] + ward_list
        )

    disease_list = pd.read_sql(
        "SELECT DISTINCT disease FROM patients ORDER BY disease",
        conn
    )["disease"].dropna().tolist()

    with col3:
        selected_disease = st.selectbox(
            "Disease",
            ["All"] + disease_list
        )

    # ---------------- FILTER QUERY ----------------
    query = "SELECT * FROM patients WHERE 1=1"
    params = []

    if selected_gender != "All":
        query += " AND gender=%s"
        params.append(selected_gender)

    if selected_ward != "All":
        query += " AND ward_type=%s"
        params.append(selected_ward)

    if selected_disease != "All":
        query += " AND disease=%s"
        params.append(selected_disease)

    filtered_df = pd.read_sql(query, conn, params=params)

    st.divider()

    # ---------------- KPI DATA ----------------
    total_patients = len(filtered_df)

    cursor.execute("SELECT COUNT(*) FROM doctors")
    total_doctors = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM appointments")
    total_appointments = cursor.fetchone()[0]

    cursor.execute("SELECT IFNULL(SUM(amount),0) FROM billing")
    total_revenue = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM medicines")
    total_medicines = cursor.fetchone()[0]

    admitted_patients = len(
        filtered_df[filtered_df["admit_status"] == "Admitted"]
    ) if not filtered_df.empty else 0

    # ================= EXECUTIVE INSIGHTS DATA =================

    # Most Common Disease
    cursor.execute("""
    SELECT disease, COUNT(*) AS total
    FROM patients
    GROUP BY disease
    ORDER BY total DESC
    LIMIT 1
    """)
    top_disease = cursor.fetchone()

    # Highest Occupied Ward
    cursor.execute("""
    SELECT ward_type, COUNT(*) AS total
    FROM patients
    GROUP BY ward_type
    ORDER BY total DESC
    LIMIT 1
    """)
    top_ward = cursor.fetchone()

    # Top Doctor by Appointments
    cursor.execute("""
    SELECT d.name, COUNT(a.appointment_id) AS total
    FROM appointments a
    JOIN doctors d ON a.doctor_id = d.doctor_id
    GROUP BY d.name
    ORDER BY total DESC
    LIMIT 1
    """)
    top_doctor = cursor.fetchone()

    # Pending Revenue
    cursor.execute("""
    SELECT IFNULL(SUM(amount),0)
    FROM billing
    WHERE payment_status='Pending'
    """)
    pending_amount = cursor.fetchone()[0]

    # ---------------- KPI CARDS ----------------
    c1, c2, c3 = st.columns(3)
    c1.metric("👥 Total Patients", f"{total_patients:,}")
    c2.metric("👨‍⚕️ Doctors", f"{total_doctors:,}")
    c3.metric("📅 Appointments", f"{total_appointments:,}")

    c4, c5, c6 = st.columns(3)
    c4.metric("💰 Revenue", f"₹ {total_revenue:,.0f}")
    c5.metric("🛏 Admitted", f"{admitted_patients:,}")
    c6.metric("💊 Medicines", f"{total_medicines:,}")

    st.divider()

    # ---------------- EXECUTIVE INSIGHTS ----------------
    st.subheader("📌 Executive Business Insights")

    col1, col2 = st.columns(2)

    with col1:
        st.success(f"""
### 📈 Operational Summary

- 👥 **Total Patients:** {total_patients:,}
- 🛏 **Admitted Patients:** {admitted_patients:,}
- 👨‍⚕️ **Doctors Available:** {total_doctors:,}
""")

    with col2:
        st.info(f"""
### 💰 Business Summary

- 💵 **Total Revenue:** ₹ {total_revenue:,.0f}
- 📅 **Appointments:** {total_appointments:,}
- 💊 **Medicine Inventory:** {total_medicines:,}
""")

    st.divider()

    # ---------------- TOP CHARTS ----------------
    left, right = st.columns(2)

    # Disease Analysis
    disease_df = pd.read_sql(
        """
        SELECT disease, COUNT(*) AS total
        FROM patients
        GROUP BY disease
        ORDER BY total DESC
        """,
        conn
    )

    with left:
        st.subheader("🦠 Disease Analysis")

        if not disease_df.empty:
            fig = px.treemap(
                disease_df,
                path=["disease"],
                values="total",
                color="total",
                color_continuous_scale=ACCENT_SCALE,
            )
            fig.update_traces(
                textinfo="label+value",
                textfont=dict(size=14, family=CHART_FONT),
                hovertemplate="<b>%{label}</b><br>Patients: %{value}<extra></extra>",
                marker=dict(line=dict(width=1, color="#0E0E1A"))
            )
            style_chart(fig, title="Top Diseases by Patient Count", height=420)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No disease data available yet.")

    # Gender Distribution
    gender_df = pd.read_sql(
        """
        SELECT gender, COUNT(*) AS total
        FROM patients
        GROUP BY gender
        """,
        conn
    )

    with right:
        st.subheader("👥 Gender Distribution")

        if not gender_df.empty:
            fig = px.pie(
                gender_df,
                names="gender",
                values="total",
                hole=0.6,
                color_discrete_sequence=BRAND_COLORS,
            )
            fig.update_traces(
                textposition="outside",
                textinfo="percent+label",
                textfont=dict(size=13, family=CHART_FONT),
                marker=dict(line=dict(color="#0E0E1A", width=2)),
                hovertemplate="<b>%{label}</b><br>Patients: %{value}<br>Share: %{percent}<extra></extra>"
            )
            style_chart(fig, title="Gender Distribution", height=420)
            fig.update_layout(showlegend=True, legend_title_text="")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No gender data available yet.")

    # ---------------- SECOND ROW ----------------
    left2, right2 = st.columns(2)

    # Appointment Trend
    appointment_df = pd.read_sql(
        """
        SELECT date, COUNT(*) AS total
        FROM appointments
        GROUP BY date
        ORDER BY date
        """,
        conn
    )

    with left2:
        st.subheader("📈 Appointment Trend")

        if not appointment_df.empty:
            fig = px.area(
                appointment_df,
                x="date",
                y="total",
                markers=False,
            )
            fig.update_traces(
                line=dict(width=3, color=BRAND_COLORS[0]),
                fillcolor="rgba(108,92,231,0.15)",
                hovertemplate="<b>%{x|%d %b %Y}</b><br>Appointments: %{y}<extra></extra>"
            )
            style_chart(fig, title="Appointments Over Time", height=400)
            fig.update_xaxes(title="")
            fig.update_yaxes(title="Appointments")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No appointment data available yet.")

    # Medicine Stock
    medicine_df = pd.read_sql(
        """
        SELECT medicine_name, quantity
        FROM medicines
        ORDER BY quantity DESC
        """,
        conn
    )

    with right2:
        st.subheader("💊 Medicine Stock")

        if not medicine_df.empty:
            top_medicine_df = medicine_df.nlargest(10, "quantity")
            fig = px.bar(
                top_medicine_df,
                x="quantity",
                y="medicine_name",
                orientation="h",
                color="quantity",
                text="quantity",
                color_continuous_scale=ACCENT_SCALE,
            )
            fig.update_traces(
                textposition="outside",
                hovertemplate="<b>%{y}</b><br>Quantity: %{x}<extra></extra>",
                marker=dict(line=dict(width=0))
            )
            style_chart(fig, title="Top 10 Medicines by Stock", height=400)
            fig.update_layout(yaxis=dict(categoryorder="total ascending", title=""))
            fig.update_xaxes(title="Quantity")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No medicine data available yet.")

    st.divider()

    # ---------------- WARD + AGE ANALYTICS ----------------
    left3, right3 = st.columns(2)

    ward_df = pd.read_sql(
        """
        SELECT ward_type, COUNT(*) AS total
        FROM patients
        WHERE ward_type IS NOT NULL
        GROUP BY ward_type
        """,
        conn
    )

    with left3:
        st.subheader("🏥 Ward Occupancy")

        if not ward_df.empty:
            fig = px.pie(
                ward_df,
                names="ward_type",
                values="total",
                hole=0.65,
                color_discrete_sequence=BRAND_COLORS,
            )
            fig.update_traces(
                textposition="outside",
                textinfo="percent+label",
                textfont=dict(size=13, family=CHART_FONT),
                marker=dict(line=dict(color="#0E0E1A", width=2)),
                hovertemplate="<b>%{label}</b><br>Patients: %{value}<br>Share: %{percent}<extra></extra>"
            )
            style_chart(fig, title="Patients by Ward Type", height=380)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No ward data available yet.")

    # Age Distribution
    age_df = pd.read_sql(
        "SELECT age FROM patients WHERE age IS NOT NULL",
        conn
    )

    with right3:
        st.subheader("📊 Age Distribution")

        if not age_df.empty:
            bins = [0, 12, 18, 30, 45, 60, 120]
            labels = ["0-12", "13-18", "19-30", "31-45", "46-60", "60+"]
            age_df["age_group"] = pd.cut(age_df["age"], bins=bins, labels=labels, right=True)
            age_group_df = (
                age_df["age_group"].value_counts().reindex(labels).reset_index()
            )
            age_group_df.columns = ["age_group", "total"]

            fig = px.bar(
                age_group_df,
                x="age_group",
                y="total",
                color="total",
                text="total",
                color_continuous_scale=ACCENT_SCALE,
            )
            fig.update_traces(
                textposition="outside",
                hovertemplate="<b>Age %{x}</b><br>Patients: %{y}<extra></extra>",
                marker=dict(line=dict(width=0))
            )
            style_chart(fig, title="Patients by Age Group", height=380)
            fig.update_xaxes(title="")
            fig.update_yaxes(title="Patients")
            fig.update_layout(coloraxis_showscale=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No age data available yet.")

    st.divider()

    # ---------------- DOCTORS + REVENUE ANALYTICS ----------------
    left4, right4 = st.columns(2)

    # Doctor Specialization Mix
    specialization_df = pd.read_sql(
        """
        SELECT specialization, COUNT(*) AS total
        FROM doctors
        WHERE specialization IS NOT NULL
        GROUP BY specialization
        ORDER BY total DESC
        """,
        conn
    )

    with left4:
        st.subheader("🩺 Doctor Specializations")

        if not specialization_df.empty:
            fig = px.bar(
                specialization_df,
                x="total",
                y="specialization",
                orientation="h",
                color="total",
                text="total",
                color_continuous_scale=ACCENT_SCALE,
            )
            fig.update_traces(
                textposition="outside",
                hovertemplate="<b>%{y}</b><br>Doctors: %{x}<extra></extra>",
                marker=dict(line=dict(width=0))
            )
            style_chart(fig, title="Doctors by Specialization", height=400)
            fig.update_layout(
                yaxis=dict(categoryorder="total ascending", title=""),
                coloraxis_showscale=False
            )
            fig.update_xaxes(title="Number of Doctors")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No doctor data available yet.")

    # Revenue by Payment Status
    payment_df = pd.read_sql(
        """
        SELECT payment_status, SUM(amount) AS total
        FROM billing
        WHERE payment_status IS NOT NULL
        GROUP BY payment_status
        """,
        conn
    )

    with right4:
        st.subheader("💰 Revenue by Payment Status")

        if not payment_df.empty:
            fig = px.pie(
                payment_df,
                names="payment_status",
                values="total",
                hole=0.6,
                color="payment_status",
                color_discrete_map={"Paid": "#00CEC9", "Pending": "#FD79A8", "Partial": "#FDCB6E"},
            )
            fig.update_traces(
                textposition="outside",
                textinfo="percent+label",
                textfont=dict(size=13, family=CHART_FONT),
                marker=dict(line=dict(color="#0E0E1A", width=2)),
                hovertemplate="<b>%{label}</b><br>₹%{value:,.0f}<br>Share: %{percent}<extra></extra>"
            )
            style_chart(fig, title="Collected vs Pending Revenue", height=400)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No billing data available yet.")

    st.divider()

    # ---------------- TOP DOCTORS BY APPOINTMENTS (full width) ----------------
    st.subheader("🏆 Top 10 Doctors by Appointment Volume")

    top_doctors_df = pd.read_sql(
        """
        SELECT d.name AS doctor, d.specialization, COUNT(a.appointment_id) AS total
        FROM appointments a
        JOIN doctors d ON a.doctor_id = d.doctor_id
        GROUP BY d.doctor_id, d.name, d.specialization
        ORDER BY total DESC
        LIMIT 10
        """,
        conn
    )

    if not top_doctors_df.empty:
        top_doctors_df["label"] = top_doctors_df["doctor"] + " (" + top_doctors_df["specialization"] + ")"
        fig = px.bar(
            top_doctors_df,
            x="total",
            y="label",
            orientation="h",
            color="total",
            text="total",
            color_continuous_scale=ACCENT_SCALE,
        )
        fig.update_traces(
            textposition="outside",
            hovertemplate="<b>%{y}</b><br>Appointments: %{x}<extra></extra>",
            marker=dict(line=dict(width=0))
        )
        style_chart(fig, title=None, height=420)
        fig.update_layout(
            yaxis=dict(categoryorder="total ascending", title=""),
            coloraxis_showscale=False
        )
        fig.update_xaxes(title="Appointments")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No appointment data available yet.")

# ================================================================
# ---------------- ADD PATIENT ----------------
# ================================================================
elif choice == "Add Patient":

    st.title("➕ Add Patient")

    name = st.text_input("Patient Name")
    age = st.number_input("Age", min_value=0, max_value=120, value=25)
    gender = st.selectbox("Gender", ["Male", "Female", "Other"])
    phone = st.text_input("Phone Number")
    disease = st.text_input("Disease")
    room_no = st.text_input("Room Number")
    ward_type = st.selectbox("Ward Type", ["General", "Private", "ICU", "Emergency"])
    admit_status = st.selectbox("Admit Status", ["Admitted", "Discharged"])

    if st.button("Add Patient"):
        if name and phone:
            try:
                cursor.execute(
                    """
                    INSERT INTO patients
                    (name, age, gender, phone, disease, room_no, ward_type, admit_status)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                    """,
                    (name, age, gender, phone, disease, room_no, ward_type, admit_status)
                )
                st.success("✅ Patient Added Successfully")
            except Exception as e:
                st.error(f"Failed to add patient: {e}")
        else:
            st.error("Please fill details")

# ================================================================
# ---------------- VIEW PATIENTS ----------------
# ================================================================
elif choice == "View Patients":

    st.title("👥 Patients List")

    patient_df = pd.read_sql(
        """
        SELECT patient_id, name, age, gender, disease, room_no, ward_type, admit_status
        FROM patients
        """,
        conn
    )

    st.dataframe(patient_df, use_container_width=True)

    csv = patient_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Download Patients CSV",
        data=csv,
        file_name="patients_data.csv",
        mime="text/csv"
    )

    # Only Admin can delete patients, and only after confirming
    if user["role"] == "Admin":
        st.markdown("---")
        st.subheader("🗑 Delete Patient")

        delete_id = st.number_input("Patient ID to Delete", min_value=1, step=1)
        confirm_delete = st.checkbox(
            f"Yes, I want to permanently delete patient {delete_id}"
        )

        if st.button("Delete Patient"):
            if not confirm_delete:
                st.warning("Please tick the confirmation box first.")
            else:
                try:
                    cursor.execute("DELETE FROM patients WHERE patient_id=%s", (delete_id,))
                    st.warning(f"Patient {delete_id} deleted")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to delete patient: {e}")

# ================================================================
# ---------------- ADD DOCTOR ----------------
# ================================================================
elif choice == "Add Doctor":

    st.title("👨‍⚕️ Add Doctor")

    doctor_name = st.text_input("Doctor Name")
    specialization = st.text_input("Specialization")
    fees = st.number_input("Fees", min_value=0.0, step=100.0)
    room_no = st.text_input("Doctor Room Number")

    if st.button("Add Doctor"):
        try:
            cursor.execute(
                """
                INSERT INTO doctors (name, specialization, fees, room_no)
                VALUES (%s,%s,%s,%s)
                """,
                (doctor_name, specialization, fees, room_no)
            )
            st.success("✅ Doctor Added")
        except Exception as e:
            st.error(f"Failed to add doctor: {e}")

# ================================================================
# ---------------- VIEW DOCTORS ----------------
# ================================================================
elif choice == "View Doctors":

    st.title("👨‍⚕️ Doctors List")

    doctor_df = pd.read_sql(
        "SELECT doctor_id, name, specialization, fees, room_no FROM doctors",
        conn
    )

    st.dataframe(doctor_df, use_container_width=True)

    csv = doctor_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Download Doctors CSV",
        data=csv,
        file_name="doctors_data.csv",
        mime="text/csv"
    )

# ================================================================
# ---------------- BOOK APPOINTMENT ----------------
# ================================================================
elif choice == "Book Appointment":

    st.title("📅 Book Appointment")

    patients_df = pd.read_sql("SELECT * FROM patients", conn)
    doctors_df = pd.read_sql("SELECT * FROM doctors", conn)

    if not patients_df.empty and not doctors_df.empty:

        patient_options = {
            row["patient_id"]: f"{row['name']} (ID:{row['patient_id']})"
            for _, row in patients_df.iterrows()
        }

        doctor_options = {
            row["doctor_id"]: f"{row['name']} - {row['specialization']}"
            for _, row in doctors_df.iterrows()
        }

        patient_id = st.selectbox(
            "Select Patient",
            list(patient_options.keys()),
            format_func=lambda x: patient_options[x]
        )

        doctor_id = st.selectbox(
            "Select Doctor",
            list(doctor_options.keys()),
            format_func=lambda x: doctor_options[x]
        )

        appointment_date = st.date_input("Appointment Date")

        if st.button("Book Appointment"):
            try:
                cursor.execute(
                    """
                    INSERT INTO appointments (patient_id, doctor_id, date, status)
                    VALUES (%s,%s,%s,%s)
                    """,
                    (patient_id, doctor_id, str(appointment_date), "Scheduled")
                )
                st.success("✅ Appointment Booked")
            except Exception as e:
                st.error(f"Failed to book appointment: {e}")
    else:
        st.info("Add at least one patient and one doctor first.")

# ================================================================
# ---------------- VIEW APPOINTMENTS ----------------
# ================================================================
elif choice == "View Appointments":

    st.title("📅 Appointment List")

    appointment_df = pd.read_sql(
        """
        SELECT
            a.appointment_id,
            p.name AS patient,
            d.name AS doctor,
            d.specialization,
            a.date,
            a.status
        FROM appointments a
        LEFT JOIN patients p ON a.patient_id = p.patient_id
        LEFT JOIN doctors d ON a.doctor_id = d.doctor_id
        """,
        conn
    )

    st.dataframe(appointment_df, use_container_width=True)

    appointment_csv = appointment_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Download Appointments CSV",
        data=appointment_csv,
        file_name="appointments.csv",
        mime="text/csv"
    )

# ================================================================
# ---------------- BILLING ----------------
# ================================================================
elif choice == "Billing":

    st.title("💳 Billing System")

    patients_df = pd.read_sql("SELECT * FROM patients", conn)

    if not patients_df.empty:

        patient_options = {
            row["patient_id"]: f"{row['name']} (ID:{row['patient_id']})"
            for _, row in patients_df.iterrows()
        }

        patient_id = st.selectbox(
            "Select Patient",
            list(patient_options.keys()),
            format_func=lambda x: patient_options[x]
        )

        amount = st.number_input("Bill Amount", min_value=0.0, step=100.0)
        payment_status = st.selectbox("Payment Status", ["Paid", "Pending", "Partial"])

        if st.button("Generate Bill"):
            try:
                cursor.execute(
                    """
                    INSERT INTO billing (patient_id, amount, payment_status)
                    VALUES (%s,%s,%s)
                    """,
                    (patient_id, amount, payment_status)
                )
                st.success("✅ Bill Generated")
            except Exception as e:
                st.error(f"Failed to generate bill: {e}")

    st.subheader("🧾 Billing Records")

    billing_df = pd.read_sql(
        """
        SELECT b.bill_id, p.name, b.amount, b.payment_status
        FROM billing b
        JOIN patients p ON b.patient_id = p.patient_id
        """,
        conn
    )

    st.dataframe(billing_df, use_container_width=True)

    csv = billing_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Download Billing CSV",
        data=csv,
        file_name="billing.csv",
        mime="text/csv"
    )

# ================================================================
# ---------------- MEDICINE ----------------
# ================================================================
elif choice == "Medicine":

    st.title("💊 Medicine Inventory")

    medicine_name = st.text_input("Medicine Name")
    quantity = st.number_input("Quantity", min_value=1)
    price = st.number_input("Price", min_value=0.0)
    expiry_date = st.date_input("Expiry Date")
    supplier = st.text_input("Supplier")

    if st.button("Add Medicine"):
        try:
            cursor.execute(
                """
                INSERT INTO medicines (medicine_name, quantity, price, expiry_date, supplier)
                VALUES (%s,%s,%s,%s,%s)
                """,
                (medicine_name, quantity, price, str(expiry_date), supplier)
            )
            st.success("✅ Medicine Added")
        except Exception as e:
            st.error(f"Failed to add medicine: {e}")

    st.subheader("📦 Medicine Stock")

    medicine_df = pd.read_sql("SELECT * FROM medicines", conn)
    st.dataframe(medicine_df, use_container_width=True)

    csv = medicine_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Download Medicine CSV",
        data=csv,
        file_name="medicine_stock.csv",
        mime="text/csv"
    )

# ================================================================
# ---------------- MANAGE USERS (Admin only) ----------------
# ================================================================
elif choice == "Manage Users":
    manage_users(conn, user)

# ---------------- FOOTER ----------------
st.markdown("---")
st.caption("🏥 Hospital Analytics Dashboard | Python + SQL + Streamlit + Plotly")

# ---------------- CLOSE CONNECTION ----------------
cursor.close()
conn.close()