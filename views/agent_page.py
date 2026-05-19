import streamlit as st
import requests

from config import SERVER


def _get_agent_state(username: str):
    try:
        return requests.get(SERVER + "/user_state", params={"username": username}).json()
    except Exception:
        return {
            "regular_wallet": 0,
            "escrow_wallet": 0,
            "service_fee_wallet": 0,
            "penalties": 0,
            "rep": 10.0,
        }


def _order_status_count(orders, status_value):
    return len([o for o in orders if str(o.get("status", "")).upper() == status_value])


def _render_order_card(order):
    product = order.get("product", {})
    st.markdown(f"### Order #{order['id']} - {product.get('name', 'Item')}")
    st.caption(f"Buyer: {order.get('buyer', '-')}")
    st.caption(f"Seller: {order.get('seller', '-')}")
    st.caption(f"Status: {order.get('status', 'NOT YET DISPATCHED')}")

    if str(order.get("status", "")).upper() == "RETURN_REQUESTED":
        review_col1, review_col2 = st.columns(2)
        with review_col1:
            if st.button("REASONABLE", key=f"agent_reasonable_{order['id']}"):
                response = requests.post(
                    SERVER + "/agent_review_return",
                    params={"order_id": order["id"], "decision": "REASONABLE"}
                )
                if response.ok:
                    st.success("Return marked REASONABLE")
                    st.rerun()
                else:
                    st.error(response.json().get("detail", "Unable to review return"))
        with review_col2:
            if st.button("NOT REASONABLE", key=f"agent_not_reasonable_{order['id']}"):
                response = requests.post(
                    SERVER + "/agent_review_return",
                    params={"order_id": order["id"], "decision": "NOT REASONABLE"}
                )
                if response.ok:
                    st.success("Return marked NOT REASONABLE")
                    st.rerun()
                else:
                    st.error(response.json().get("detail", "Unable to review return"))
    else:
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Mark IN TRANSIT", key=f"agent_transit_{order['id']}"):
                response = requests.post(SERVER + "/mark_in_transit", params={"order_id": order["id"]})
                if response.ok:
                    st.success("Order marked IN TRANSIT")
                    st.rerun()
                else:
                    st.error(response.json().get("detail", "Unable to update status"))
        with col2:
            if st.button("Mark DELIVERED", key=f"agent_delivered_{order['id']}"):
                response = requests.post(SERVER + "/mark_delivered", params={"order_id": order["id"]})
                if response.ok:
                    st.success("Order marked DELIVERED and payout settled")
                    st.rerun()
                else:
                    st.error(response.json().get("detail", "Unable to update status"))


def render_agent_page(username: str):
    st.header("Agent Panel")

    menu_option = st.sidebar.radio(
        "Browse",
        ["Dashboard", "Agent Orders", "Escrow Wallet", "Track Order"]
    )

    agent_state = _get_agent_state(username)
    top_left, top_right = st.columns([4, 1])
    with top_left:
        st.text_input("Search Bar", placeholder="Search orders/items", key="agent_search", disabled=True)
    with top_right:
        st.metric("Reputation Score", f"{float(agent_state.get('rep', 10.0)):.1f}")

    if menu_option == "Dashboard":
        st.subheader("Agent Dashboard")
        notifications = requests.get(SERVER + "/agent_notifications").json()
        orders = requests.get(SERVER + "/orders").json()

        pending = len(notifications)
        in_transit = _order_status_count(orders, "IN TRANSIT")
        delivered = _order_status_count(orders, "DELIVERED")
        return_requests = _order_status_count(orders, "RETURN_REQUESTED")

        stats_col1, stats_col2 = st.columns(2)
        with stats_col1:
            st.metric("Notifications", f"{pending}")
            st.metric("In Transit", f"{in_transit}")
        with stats_col2:
            st.metric("Delivered", f"{delivered}")
            st.metric("Return Requests", f"{return_requests}")

        st.metric("Service Fee Wallet", f"₹ {int(agent_state.get('service_fee_wallet', 0))}")
        st.caption("All agent service fees are transferred here and not spendable.")

        if pending:
            st.info("You have orders waiting for action. Click Agent Orders to review them.")
        else:
            st.info("No active delivery orders or return requests at the moment.")

    elif menu_option == "Agent Orders":
        st.subheader("Agent Orders")
        notifications = requests.get(SERVER + "/agent_notifications").json()
        if not notifications:
            st.info("No orders ready for agent action")
            return

        for order in notifications:
            _render_order_card(order)

    elif menu_option == "Escrow Wallet":
        st.subheader("Service Fee Wallet")
        st.metric("Service Fee Wallet", f"₹ {int(agent_state.get('service_fee_wallet', 0))}")
        st.caption("All agent service fees are transferred here and not spendable.")

    elif menu_option == "Track Order":
        st.subheader("Track Order")
        orders = requests.get(SERVER + "/orders").json()
        track_id = st.number_input("Track by number", min_value=1, step=1, key="agent_track")
        if st.button("Track", key="agent_track_btn"):
            matched = [order for order in orders if int(order.get("id", 0)) == int(track_id)]
            if matched:
                st.success(matched[0].get("status", "NOT YET DISPATCHED"))
            else:
                st.error("Order number not found")
