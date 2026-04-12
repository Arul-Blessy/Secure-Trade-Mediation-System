import streamlit as st
import requests
from config import VALID_CREDENTIALS
from config import SERVER
from views.agent_page import render_agent_page
from views.buyer_page import render_buyer_page
from views.seller_page import render_seller_page


def init_session_state():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "role" not in st.session_state:
        st.session_state.role = None
    if "username" not in st.session_state:
        st.session_state.username = None

st.title("Secure Trade Demo")

init_session_state()

if not st.session_state.logged_in:
    st.subheader("Login")
    username = st.text_input("User ID")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        user = VALID_CREDENTIALS.get(username)
        if user and user["password"] == password:
            st.session_state.logged_in = True
            st.session_state.role = user["role"]
            st.session_state.username = username
            st.rerun()
        else:
            st.error("Invalid user ID or password")
else:
    st.success(f"Logged in as {st.session_state.username}")

    if st.session_state.role == "Agent":
        try:
            pending = requests.get(SERVER + "/agent_notifications").json()
            if pending:
                st.warning(f"Delivery Alert: {len(pending)} order(s) waiting for agent pickup")
        except Exception:
            pass

    if st.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.role = None
        st.session_state.username = None
        st.rerun()

    active_username = st.session_state.username or ""

    if st.session_state.role == "Seller":
        render_seller_page(active_username)
    elif st.session_state.role == "Buyer":
        render_buyer_page(active_username)
    elif st.session_state.role == "Agent":
        render_agent_page(active_username)