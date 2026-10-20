import hashlib
import hmac
import os

import pandas as pd
import streamlit as st

ROLES = ["Admin", "Doctor", "Receptionist"]

# Which menu items each role can see. Admin sees everything.
ROLE_MENU = {
    "Admin": None,
    "Doctor": [
        "Executive Dashboard",
        "View Patients",
        "View Doctors",
        "View Appointments",
    ],
    "Receptionist": [
        "Add Patient",
        "View Patients",
        "View Doctors",
        "Book Appointment",
        "View Appointments",
        "Billing",
        "Pending Bills",
        "Medicine",
    ],
}

ITERATIONS = 200_000


# ---------------- PASSWORD HASHING (no extra library needed) ----------------
def _hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, ITERATIONS)
    return f"{salt.hex()}${digest.hex()}"


def _check_password(password: str, stored: str) -> bool:
    try:
        salt_hex, digest_hex = stored.split("$")
        digest = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt_hex), ITERATIONS
        )
        return hmac.compare_digest(digest.hex(), digest_hex)
    except Exception:
        return False


# ---------------- DATABASE HELPERS ----------------
def ensure_users_table(conn):
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                role VARCHAR(20) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def _count_users(conn) -> int:
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM users")
        return cur.fetchone()[0]


def _create_user(conn, username: str, password: str, role: str):
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (%s,%s,%s)",
            (username.strip(), _hash_password(password), role),
        )


def _get_user(conn, username: str):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT username, password_hash, role FROM users WHERE username=%s",
            (username.strip(),),
        )
        return cur.fetchone()


# ---------------- LOGIN GATE ----------------
def login_gate(conn):
    """Call right after the DB connection. Stops the app until the user logs in."""
    ensure_users_table(conn)

    if st.session_state.get("user"):
        return st.session_state["user"]

    st.title("🏥 Hospital Analytics")

    # First run: no users yet -> create the admin account
    if _count_users(conn) == 0:
        st.subheader("First-time setup: create Admin account")
        with st.form("setup_form"):
            username = st.text_input("Admin username")
            password = st.text_input("Password (min 8 characters)", type="password")
            confirm = st.text_input("Confirm password", type="password")
            submitted = st.form_submit_button("Create Admin")
        if submitted:
            if not username.strip():
                st.error("Username is required.")
            elif len(password) < 8:
                st.error("Password must be at least 8 characters.")
            elif password != confirm:
                st.error("Passwords do not match.")
            else:
                _create_user(conn, username, password, "Admin")
                st.success("Admin created. Please log in.")
                st.rerun()
        st.stop()

    # Normal login
    st.subheader("🔐 Login")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")

    if submitted:
        row = _get_user(conn, username)
        if row and _check_password(password, row[1]):
            st.session_state["user"] = {"username": row[0], "role": row[2]}
            st.rerun()
        else:
            st.error("Invalid username or password.")
    st.stop()


def allowed_menu(role: str, full_menu: list) -> list:
    allowed = ROLE_MENU.get(role)
    items = full_menu if allowed is None else [m for m in full_menu if m in allowed]
    if role == "Admin":
        items = items + ["Manage Users"]
    return items


def logout_button(user: dict):
    st.sidebar.markdown("---")
    st.sidebar.write(f"👤 **{user['username']}** ({user['role']})")
    if st.sidebar.button("🚪 Logout"):
        st.session_state.pop("user", None)
        st.rerun()


# ---------------- ADMIN: MANAGE USERS PAGE ----------------
def manage_users(conn, current_user: dict):
    st.title("🔑 Manage Users")

    st.subheader("Add new user")
    with st.form("add_user_form", clear_on_submit=True):
        username = st.text_input("Username")
        password = st.text_input("Password (min 8 characters)", type="password")
        role = st.selectbox("Role", ROLES)
        submitted = st.form_submit_button("Create User")

    if submitted:
        if not username.strip() or len(password) < 8:
            st.error("Username required and password must be at least 8 characters.")
        else:
            try:
                _create_user(conn, username, password, role)
                st.success(f"User '{username}' created as {role}.")
            except Exception as e:
                st.error(f"Could not create user (username may already exist): {e}")

    st.subheader("Existing users")
    users_df = pd.read_sql(
        "SELECT user_id, username, role, created_at FROM users", conn
    )
    st.dataframe(users_df, use_container_width=True)

    st.subheader("Delete user")
    del_username = st.selectbox("Select user", users_df["username"].tolist())
    confirm = st.checkbox(f"Yes, delete '{del_username}'")
    if st.button("Delete User"):
        if del_username == current_user["username"]:
            st.error("You cannot delete your own account.")
        elif not confirm:
            st.warning("Please tick the confirmation box first.")
        else:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM users WHERE username=%s", (del_username,))
            st.success(f"User '{del_username}' deleted.")
            st.rerun()