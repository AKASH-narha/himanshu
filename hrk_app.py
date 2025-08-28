import streamlit as st
import sqlite3
import pandas as pd
import datetime
from io import BytesIO

# OPTIONAL: Twilio for SMS/WhatsApp (only if you enable messaging)
# from twilio.rest import Client
# ACCOUNT_SID = "your_twilio_sid"
# AUTH_TOKEN = "your_twilio_token"
# TWILIO_NUMBER = "your_twilio_number"
# client = Client(ACCOUNT_SID, AUTH_TOKEN)

# ------------------ DATABASE SETUP ------------------
def init_db():
    conn = sqlite3.connect("library.db")
    c = conn.cursor()
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                code TEXT PRIMARY KEY,
                name TEXT,
                father TEXT,
                address TEXT,
                contact TEXT,
                admission_date TEXT,
                monthly_fee REAL
                )''')
    # Payments table
    c.execute('''CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT,
                date TEXT,
                amount REAL,
                FOREIGN KEY(code) REFERENCES users(code)
                )''')
    conn.commit()
    conn.close()

def add_user(code, name, father, address, contact, admission_date, monthly_fee):
    try:
        conn = sqlite3.connect("library.db")
        c = conn.cursor()
        c.execute("INSERT INTO users VALUES (?,?,?,?,?,?,?)",
                  (code, name, father, address, contact, admission_date, monthly_fee))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error adding user: {e}")
        return False

def record_payment(code, amount):
    try:
        conn = sqlite3.connect("library.db")
        c = conn.cursor()
        c.execute("INSERT INTO payments (code,date,amount) VALUES (?,?,?)",
                  (code, datetime.date.today().isoformat(), amount))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error recording payment: {e}")
        return False

def get_user(code):
    conn = sqlite3.connect("library.db")
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE code=?", (code,))
    user = c.fetchone()
    conn.close()
    return user

def get_payments(code):
    conn = sqlite3.connect("library.db")
    c = conn.cursor()
    c.execute("SELECT date,amount FROM payments WHERE code=?", (code,))
    rows = c.fetchall()
    conn.close()
    return pd.DataFrame(rows, columns=["Date","Amount"])

def calculate_due(code):
    user = get_user(code)
    if not user:
        return 0
    admission = datetime.date.fromisoformat(user[5])
    today = datetime.date.today()
    months = (today.year - admission.year) * 12 + (today.month - admission.month) + 1
    total_due = months * user[6]
    payments = get_payments(code)
    paid = payments["Amount"].sum() if not payments.empty else 0
    return total_due - paid

def get_all_users():
    conn = sqlite3.connect("library.db")
    df = pd.read_sql_query("SELECT * FROM users", conn)
    conn.close()
    return df

# ------------------ STREAMLIT APP ------------------
st.set_page_config("📚 Library Management System", layout="wide")
init_db()

menu = ["Admin - Add User","Admin - Payments","Admin - Reports","Student Login"]
choice = st.sidebar.radio("Menu",menu)

# Admin - Add User
if choice=="Admin - Add User":
    st.header("➕ Add New User")
    code = st.text_input("Library Code")
    name = st.text_input("Name")
    father = st.text_input("Father's Name")
    address = st.text_area("Address")
    contact = st.text_input("Contact (+91...)")
    admission_date = st.date_input("Admission Date", datetime.date.today())
    fee = st.number_input("Monthly Fee", min_value=100.0, value=200.0)
    if st.button("Add User"):
        if add_user(code,name,father,address,contact,str(admission_date),fee):
            st.success("✅ User Added Successfully")

# Admin - Payments
elif choice=="Admin - Payments":
    st.header("💰 Record Payment")
    code = st.text_input("Enter Library Code")
    amt = st.number_input("Amount", min_value=50.0)
    if st.button("Record Payment"):
        if record_payment(code,amt):
            st.success("✅ Payment Recorded")

# Admin - Reports
elif choice=="Admin - Reports":
    st.header("📊 Reports & Dues")
    users = get_all_users()
    if not users.empty:
        users["Due"] = users["code"].apply(calculate_due)
        st.dataframe(users)

        # Download CSV
        csv = users.to_csv(index=False).encode("utf-8")
        st.download_button("⬇ Download Report (CSV)",csv,"report.csv","text/csv")

        # Download Excel
        excel_buffer = BytesIO()
        with pd.ExcelWriter(excel_buffer, engine="xlsxwriter") as writer:
            users.to_excel(writer, index=False, sheet_name="Report")
        st.download_button("⬇ Download Report (Excel)", excel_buffer.getvalue(),
                           "report.xlsx","application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        dues = users[users["Due"]>0]
        if not dues.empty:
            st.subheader("Users with Pending Dues")
            st.dataframe(dues)
        else:
            st.info("🎉 No Pending Dues")

# Student Login
elif choice=="Student Login":
    st.header("👤 Student Login")
    code = st.text_input("Enter Library Code")
    if st.button("Login"):
        user = get_user(code)
        if user:
            st.write(f"*Name:* {user[1]}") 
            st.write(f"*Father:* {user[2]}")
            st.write(f"*Address:* {user[3]}")
            st.write(f"*Admission Date:* {user[5]}")
            st.write(f"*Monthly Fee:* ₹{user[6]}")
            
            due = calculate_due(code)
            st.write(f"### 📌 Current Due: ₹{due}")

            st.subheader("💳 Payment History")
            df = get_payments(code)
            if df.empty:
                st.info("No payments yet.")
            else:
                st.table(df)
        else:
            st.error("❌ Invalid Library Code")
