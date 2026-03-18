import streamlit as st
import os
from dotenv import load_dotenv

load_dotenv()

# Ladda användare från miljövariabler eller använd standardlösenord
def _load_users():
    """Ladda användare """
    return {
        "sales": {
            "password": os.getenv("USER_SALES_PASSWORD", "demo123"),
            "name": "Sarah Svensson",
            "title": "Sales Manager",
            "role": "sales"
        },
        "analyst": {
            "password": os.getenv("USER_ANALYST_PASSWORD", "demo123"),
            "name": "Erik Andersson",
            "title": "Analyst",
            "role": "analyst"
        },
        "admin": {
            "password": os.getenv("USER_ADMIN_PASSWORD", "admin123"),
            "name": "Admin",
            "title": "System Administrator",
            "role": "admin"
        }
    }

# Kontrollera inloggningsuppgifter
def check_login(username, password):
    """Kontrollera inloggningsuppgifter mot användare definierade i .env"""
    users = _load_users()
    if username in users and users[username]["password"] == password:
        return users[username]
    return None

# Visa inloggningssidan
def login_page():
    """Visa inloggningssida"""
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.title("Log in")
        st.markdown("---")

        with st.form("login_form"):
            username = st.text_input("Username", placeholder="Enter username")
            password = st.text_input("Password", type="password", placeholder="Enter password")
            submit = st.form_submit_button("Log in", width='stretch')

            if submit:
                user_data = check_login(username, password)
                if user_data:
                    st.session_state.logged_in = True
                    st.session_state.user_name = user_data["name"]
                    st.session_state.user_title = user_data["title"]
                    st.session_state.user_role = user_data["role"]
                    st.session_state.username = username
                    st.session_state.messages = []
                    st.rerun()
                else:
                    st.error("Invalid username or password")

        with st.expander("Test users (click here)"):
            st.markdown("""
            **Username:** sales  
            **Password:** demo123  
            **Role:** Sales Manager

            **Username:** analyst  
            **Password:** demo123  
            **Role:** Analyst

            **Username:** admin  
            **Password:** admin123  
            **Role:** System Administrator
            """)

# Logga ut användaren och rensa sessionen
def logout():
    """Logga ut användaren"""
    st.session_state.logged_in = False
    st.session_state.user_name = None
    st.session_state.user_title = None
    st.session_state.user_role = None
    st.session_state.username = None
    st.session_state.messages = []
    st.rerun()