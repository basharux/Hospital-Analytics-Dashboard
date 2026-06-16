import streamlit as st
import pandas as pd
import pymysql
import plotly.express as px

st.set_page_config(
    page_title="Hospital Analytics",
    page_icon="🏥",
    layout="wide"
)

# ---------------- DATABASE CONNECTION ----------------
def get_connection():
    return pymysql.connect(
        host="localhost",
        user="root",
        password="root",
        database="hospital_db",
        autocommit=True
    )

try:
    conn = get_connection()
    cursor = conn.cursor()
except Exception as e:
    st.error(f"Database Connection Failed: {e}")
    st.stop()

# ---------------- SIDEBAR ----------------
st.sidebar.title("🏥 Hospital System")

menu = [
    "Dashboard",
    "Add Patient",
    "View Patients",
    "Add Doctor",
    "View Doctors",
    "Book Appointment",
    "View Appointments",
    "Billing",
    "Medicine"
]

choice = st.sidebar.selectbox("Menu", menu)

# ---------------- DASHBOARD ----------------
if choice == "Dashboard":

    st.title("🏥 Hospital Analytics Dashboard")
    st.caption(
        "Healthcare Analytics Overview"
    )

    # ---------- KPI DATA ----------
    cursor.execute(
        "SELECT COUNT(*) FROM patients"
    )
    total_patients = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM doctors"
    )
    total_doctors = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM appointments"
    )
    total_appointments = cursor.fetchone()[0]

    cursor.execute(
        "SELECT SUM(amount) FROM billing"
    )
    total_revenue = cursor.fetchone()[0]

    cursor.execute("""
    SELECT COUNT(*) FROM medicines
    """)
    total_medicines = cursor.fetchone()[0]

    cursor.execute("""
    SELECT COUNT(*)
    FROM patients
    WHERE admit_status='Admitted'
    """)
    admitted_patients = (
        cursor.fetchone()[0]
    )

    # ---------- KPI CARDS ----------
    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "👥 Patients",
        total_patients
    )

    c2.metric(
        "👨‍⚕️ Doctors",
        total_doctors
    )

    c3.metric(
        "📅 Appointments",
        total_appointments
    )

    c4.metric(
        "💰 Revenue",
        f"₹{total_revenue or 0}"
    )

    c5, c6 = st.columns(2)

    c5.metric(
        "🛏️ Admitted",
        admitted_patients
    )

    c6.metric(
        "💊 Medicines",
        total_medicines
    )

    st.markdown("---")

    # ---------- TOP CHARTS ----------
    left, right = st.columns(2)

    # Disease Analysis
    disease_df = pd.read_sql(
        """
        SELECT disease,
        COUNT(*) AS total
        FROM patients
        GROUP BY disease
        ORDER BY total DESC
        """,
        conn
    )

    with left:

        st.subheader(
            "🦠 Disease Analysis"
        )

        fig = px.bar(
            disease_df,
            x="disease",
            y="total",
            color="total",
            text="total",
            template="plotly_dark"
        )

        fig.update_layout(
            height=400
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    # Gender Distribution
    gender_df = pd.read_sql(
        """
        SELECT gender,
        COUNT(*) AS total
        FROM patients
        GROUP BY gender
        """,
        conn
    )

    with right:

        st.subheader(
            "👥 Gender Distribution"
        )

        fig = px.pie(
            gender_df,
            names="gender",
            values="total",
            hole=0.6,
            template="plotly_dark"
        )

        fig.update_layout(
            height=400
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    st.markdown("---")

    # ---------- SECOND ROW ----------
    left2, right2 = st.columns(2)

    # Appointment Trend
    appointment_df = pd.read_sql(
        """
        SELECT date,
        COUNT(*) AS total
        FROM appointments
        GROUP BY date
        ORDER BY date
        """,
        conn
    )

    with left2:

        st.subheader(
            "📈 Appointment Trend"
        )

        fig = px.line(
            appointment_df,
            x="date",
            y="total",
            markers=True,
            template="plotly_dark"
        )

        fig.update_traces(
            line=dict(width=5)
        )

        fig.update_layout(
            height=400
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    # Medicine Stock
    medicine_df = pd.read_sql(
        """
        SELECT
        medicine_name,
        quantity
        FROM medicines
        ORDER BY quantity DESC
        """,
        conn
    )

    with right2:

        st.subheader(
            "💊 Medicine Stock"
        )

        fig = px.bar(
            medicine_df,
            x="medicine_name",
            y="quantity",
            color="quantity",
            text="quantity",
            template="plotly_dark"
        )

        fig.update_layout(
            height=400
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    st.markdown("---")

    # ---------- WARD ANALYTICS ----------
    st.subheader(
        "🏥 Ward Occupancy"
    )

    ward_df = pd.read_sql(
        """
        SELECT ward_type,
        COUNT(*) AS total
        FROM patients
        GROUP BY ward_type
        """,
        conn
    )

    fig = px.bar(
        ward_df,
        x="ward_type",
        y="total",
        color="total",
        text="total",
        template="plotly_dark"
    )

    fig.update_layout(
        height=400
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )
        # ---------------- ADD PATIENT ----------------
elif choice == "Add Patient":

    st.title("➕ Add Patient")

    name = st.text_input(
        "Patient Name"
    )

    age = st.number_input(
        "Age",
        min_value=0,
        max_value=120,
        value=25
    )

    gender = st.selectbox(
        "Gender",
        ["Male", "Female", "Other"]
    )

    phone = st.text_input(
        "Phone Number"
    )

    disease = st.text_input(
        "Disease"
    )

    # NEW FIELDS
    room_no = st.text_input(
        "Room Number"
    )

    ward_type = st.selectbox(
        "Ward Type",
        [
            "General",
            "Private",
            "ICU",
            "Emergency"
        ]
    )

    admit_status = st.selectbox(
        "Admit Status",
        [
            "Admitted",
            "Discharged"
        ]
    )

    if st.button(
        "Add Patient"
    ):

        if name and phone:

            cursor.execute(
                """
                INSERT INTO patients
                (
                name,
                age,
                gender,
                phone,
                disease,
                room_no,
                ward_type,
                admit_status
                )

                VALUES
                (%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    name,
                    age,
                    gender,
                    phone,
                    disease,
                    room_no,
                    ward_type,
                    admit_status
                )
            )

            st.success(
                "✅ Patient Added Successfully"
            )

        else:
            st.error(
                "Please fill details"
            )

# ---------------- VIEW PATIENTS ----------------
elif choice == "View Patients":

    st.title("👥 Patients List")

    patient_df = pd.read_sql(
        """
        SELECT
            patient_id,
            name,
            age,
            gender,
            disease,
            room_no,
            ward_type,
            admit_status
        FROM patients
        """,
        conn
    )

    st.dataframe(
        patient_df,
        use_container_width=True
    )

    # CSV DOWNLOAD
    csv = patient_df.to_csv(
        index=False
    ).encode("utf-8")

    st.download_button(
        label="📥 Download Patients CSV",
        data=csv,
        file_name="patients_data.csv",
        mime="text/csv"
    )

    st.markdown("---")

    delete_id = st.number_input(
        "Patient ID to Delete",
        min_value=1,
        step=1
    )

    if st.button("Delete Patient"):

        cursor.execute(
            """
            DELETE FROM patients
            WHERE patient_id=%s
            """,
            (delete_id,)
        )

        st.warning(
            f"Patient {delete_id} deleted"
        )

        st.rerun()



# ---------------- ADD DOCTOR ----------------
elif choice == "Add Doctor":

    st.title("👨‍⚕️ Add Doctor")

    doctor_name = st.text_input(
        "Doctor Name"
    )

    specialization = st.text_input(
        "Specialization"
    )

    fees = st.number_input(
        "Fees",
        min_value=0.0,
        step=100.0
    )

    # NEW FIELD
    room_no = st.text_input(
        "Doctor Room Number"
    )

    if st.button("Add Doctor"):

        cursor.execute(
            """
            INSERT INTO doctors
            (
            name,
            specialization,
            fees,
            room_no
            )
            VALUES
            (%s,%s,%s,%s)
            """,
            (
                doctor_name,
                specialization,
                fees,
                room_no
            )
        )

        st.success(
            "✅ Doctor Added"
        )

# ---------------- VIEW DOCTORS ----------------
elif choice == "View Doctors":

    st.title("👨‍⚕️ Doctors List")

    doctor_df = pd.read_sql(
        """
        SELECT
        doctor_id,
        name,
        specialization,
        fees,
        room_no
        FROM doctors
        """,
        conn
    )

    st.dataframe(
        doctor_df,
        use_container_width=True
    )

    # CSV DOWNLOAD
    csv = doctor_df.to_csv(
        index=False
    ).encode("utf-8")

    st.download_button(
        label="📥 Download Doctors CSV",
        data=csv,
        file_name="doctors_data.csv",
        mime="text/csv"
    )
# ---------------- BOOK APPOINTMENT ----------------
elif choice == "Book Appointment":

    st.title(
        "📅 Book Appointment"
    )

    patients_df = pd.read_sql(
        "SELECT * FROM patients",
        conn
    )

    doctors_df = pd.read_sql(
        "SELECT * FROM doctors",
        conn
    )

    if (
        not patients_df.empty
        and not doctors_df.empty
    ):

        patient_options = {
            row["patient_id"]:
            f"{row['name']} "
            f"(ID:{row['patient_id']})"

            for _, row in
            patients_df.iterrows()
        }

        doctor_options = {
            row["doctor_id"]:
            f"{row['name']} - "
            f"{row['specialization']}"

            for _, row in
            doctors_df.iterrows()
        }

        patient_id = st.selectbox(
            "Select Patient",
            list(
                patient_options.keys()
            ),
            format_func=lambda x:
            patient_options[x]
        )

        doctor_id = st.selectbox(
            "Select Doctor",
            list(
                doctor_options.keys()
            ),
            format_func=lambda x:
            doctor_options[x]
        )

        appointment_date = st.date_input(
            "Appointment Date"
        )

        if st.button(
            "Book Appointment"
        ):

            cursor.execute(
                """
                INSERT INTO appointments
                (
                patient_id,
                doctor_id,
                date,
                status
                )
                VALUES
                (%s,%s,%s,%s)
                """,
                (
                    patient_id,
                    doctor_id,
                    str(
                        appointment_date
                    ),
                    "Scheduled"
                )
            )

            st.success(
                "✅ Appointment Booked"
            )
# ---------------- VIEW APPOINTMENTS ----------------
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

        LEFT JOIN patients p
        ON a.patient_id = p.patient_id

        LEFT JOIN doctors d
        ON a.doctor_id = d.doctor_id
        """,
        conn
    )

    st.dataframe(
        appointment_df,
        use_container_width=True
    )

    # CSV DOWNLOAD
    appointment_csv = appointment_df.to_csv(
        index=False
    ).encode("utf-8")

    st.download_button(
        label="📥 Download Appointments CSV",
        data=appointment_csv,
        file_name="appointments.csv",
        mime="text/csv"
    )

# ---------------- BILLING ----------------
elif choice == "Billing":

    st.title(
        "💳 Billing System"
    )

    patients_df = pd.read_sql(
        "SELECT * FROM patients",
        conn
    )

    if not patients_df.empty:

        patient_options = {
            row["patient_id"]:
            f"{row['name']} "
            f"(ID:{row['patient_id']})"

            for _, row in
            patients_df.iterrows()
        }

        patient_id = st.selectbox(
            "Select Patient",
            list(
                patient_options.keys()
            ),
            format_func=lambda x:
            patient_options[x]
        )

        amount = st.number_input(
            "Bill Amount",
            min_value=0.0,
            step=100.0
        )

        payment_status = st.selectbox(
            "Payment Status",
            ["Paid", "Pending"]
        )

        if st.button(
            "Generate Bill"
        ):

            cursor.execute(
                """
                INSERT INTO billing
                (
                patient_id,
                amount,
                payment_status
                )
                VALUES
                (%s,%s,%s)
                """,
                (
                    patient_id,
                    amount,
                    payment_status
                )
            )

            st.success(
                "✅ Bill Generated"
            )

    st.subheader(
        "🧾 Billing Records"
    )

    billing_df = pd.read_sql(
        """
        SELECT
        b.bill_id,
        p.name,
        b.amount,
        b.payment_status

        FROM billing b

        JOIN patients p
        ON b.patient_id =
        p.patient_id
        """,
        conn
    )

    st.dataframe(
        billing_df,
        use_container_width=True
    )
    csv = billing_df.to_csv(
    index=False
).encode("utf-8")

    st.download_button(
    label="📥 Download Billing CSV",
    data=csv,
    file_name="billing.csv",
    mime="text/csv"
)
    # ---------------- MEDICINE ----------------
elif choice == "Medicine":

    st.title("💊 Medicine Inventory")

    medicine_name = st.text_input(
        "Medicine Name"
    )

    quantity = st.number_input(
        "Quantity",
        min_value=1
    )

    price = st.number_input(
        "Price",
        min_value=0.0
    )

    expiry_date = st.date_input(
        "Expiry Date"
    )

    supplier = st.text_input(
        "Supplier"
    )

    if st.button(
        "Add Medicine"
    ):

        cursor.execute(
            """
            INSERT INTO medicines
            (
            medicine_name,
            quantity,
            price,
            expiry_date,
            supplier
            )

            VALUES
            (%s,%s,%s,%s,%s)
            """,
            (
                medicine_name,
                quantity,
                price,
                str(expiry_date),
                supplier
            )
        )

        st.success(
            "✅ Medicine Added"
        )

    st.subheader(
        "📦 Medicine Stock"
    )

    medicine_df = pd.read_sql(
        "SELECT * FROM medicines",
        conn
    )

    st.dataframe(
        medicine_df,
        use_container_width=True
    ) 
    csv = medicine_df.to_csv(
    index=False
).encode("utf-8")

    st.download_button(
    label="📥 Download Medicine CSV",
    data=csv,
    file_name="medicine_stock.csv",
    mime="text/csv"
)

# ---------------- FOOTER ----------------
st.markdown("---")

st.caption(
    "🏥 Hospital Analytics Dashboard | "
    "Python + SQL + Streamlit + Plotly"
)

# ---------------- CLOSE CONNECTION ----------------
cursor.close()
conn.close()