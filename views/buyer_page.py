import streamlit as st
import requests

from config import SERVER


def _init_buyer_state():
    if "buyer_regular_wallet" not in st.session_state:
        st.session_state.buyer_regular_wallet = 30000
    if "buyer_escrow_wallet" not in st.session_state:
        st.session_state.buyer_escrow_wallet = 0
    if "buyer_penalties" not in st.session_state:
        st.session_state.buyer_penalties = 0
    if "buyer_reputation" not in st.session_state:
        st.session_state.buyer_reputation = 10.0
    if "buyer_escrow_history" not in st.session_state:
        st.session_state.buyer_escrow_history = []
    if "buyer_penalty_history" not in st.session_state:
        st.session_state.buyer_penalty_history = []
    if "buyer_order_actions" not in st.session_state:
        st.session_state.buyer_order_actions = {}


def _sync_buyer_state(username: str):
    response = requests.get(SERVER + "/user_state", params={"username": username})
    if response.ok:
        data = response.json()
        st.session_state.buyer_regular_wallet = int(data.get("regular_wallet", 0))
        st.session_state.buyer_escrow_wallet = int(data.get("escrow_wallet", 0))
        st.session_state.buyer_penalties = int(data.get("penalties", 0))
        st.session_state.buyer_reputation = float(data.get("rep", 10.0))


def _effective_order_status(index, api_status):
    return str(api_status or "unknown")


def _apply_penalty_action(order, action_name, username: str):
    response = requests.post(
        SERVER + "/buyer_cancel",
        params={"order_id": int(order["id"]), "buyer": username}
    )
    if not response.ok:
        st.error(response.json().get("detail", "Unable to process request"))
        return

    result = response.json()
    product_name = order.get("product", {}).get("name", "Product")
    penalty_amount = int(result.get("penalty", 0))
    refund_amount = int(result.get("refund_to_buyer", 0))

    st.session_state.buyer_escrow_history.append(
        {
            "type": action_name.title(),
            "amount": penalty_amount,
            "direction": "Outflow from Escrow",
            "note": f"Penalty on {product_name}",
        }
    )
    st.session_state.buyer_escrow_history.append(
        {
            "type": action_name.title(),
            "amount": refund_amount,
            "direction": "Outflow from Escrow",
            "note": f"Refund to Regular Wallet for {product_name}",
        }
    )
    st.session_state.buyer_penalty_history.append(
        {
            "order": product_name,
            "reason": "Order Cancelled" if action_name == "cancelled" else "Refund/Return Requested",
            "amount": penalty_amount,
        }
    )
    st.success(
        f"Order {action_name}. Penalty ₹{penalty_amount}, "
        f"refund ₹{refund_amount}."
    )
    _sync_buyer_state(username)


def _request_return(order, username: str):
    response = requests.post(
        SERVER + "/buyer_return_request",
        params={"order_id": int(order["id"]), "buyer": username}
    )
    if not response.ok:
        st.error(response.json().get("detail", "Unable to request return"))
        return

    st.success("Return request sent to Delivery Agent for review")


def _track_status_label(status):
    normalized = str(status or "").lower()
    if normalized in {"delivered", "completed"}:
        return "DELIVERED"
    if normalized in {"in_transit", "picked_up"}:
        return "IN TRANSIT"
    return "NOT YET DISPATCHED"


def render_buyer_page(username: str):
    st.header("Buyer Marketplace")

    _init_buyer_state()
    _sync_buyer_state(username)

    menu_option = st.sidebar.radio(
        "Browse",
        ["Marketplace", "My Orders", "Escrow Wallet", "Regular Wallet", "Accrued Penalties", "Track Order"]
    )

    top_left, top_right = st.columns([4, 1])
    with top_left:
        search_query = st.text_input("Search Bar", placeholder="Search items using keywords")
    with top_right:
        st.metric("Reputation Score", f"{st.session_state.buyer_reputation:.1f}")

    if menu_option == "My Orders":
        st.subheader("My Orders")
        orders = requests.get(SERVER + "/orders_for_buyer", params={"buyer": username}).json()
        orders = sorted(orders, key=lambda order: int(order.get("id", 0)), reverse=True)
        if not orders:
            st.info("No orders yet")
            return

        delivered_statuses = {"delivered", "completed", "return_requested", "return_approved", "return_rejected"}
        yet_to_be_delivered = []
        delivered_packages = []

        for idx, order in enumerate(orders):
            status = _effective_order_status(idx, order.get("status", "unknown")).lower()
            if status in delivered_statuses:
                delivered_packages.append((idx, order))
            else:
                yet_to_be_delivered.append((idx, order))

        with st.container(border=True):
            pending_col, delivered_col = st.columns(2)

            with pending_col:
                st.markdown("### Yet to be Delivered")
                if not yet_to_be_delivered:
                    st.write("No pending packages")
                else:
                    for idx, (original_index, order) in enumerate(yet_to_be_delivered, start=1):
                        product = order.get("product", {})
                        st.write(f"{idx}. {product.get('name', 'Unknown Product')}")
                        st.caption(f"Payment: {order.get('payment_mode', 'PREPAID')}")
                        if product.get("image"):
                            st.image(product["image"], width=140)
                        status = _effective_order_status(original_index, order.get("status", "unknown"))
                        st.caption(f"Status: {status}")

            with delivered_col:
                st.markdown("### Delivered Packages")
                if not delivered_packages:
                    st.write("No delivered packages")
                else:
                    for idx, (original_index, order) in enumerate(delivered_packages, start=1):
                        product = order.get("product", {})
                        st.write(f"{idx}. {product.get('name', 'Unknown Product')}")
                        st.caption(f"Payment: {order.get('payment_mode', 'PREPAID')}")
                        if product.get("image"):
                            st.image(product["image"], width=140)
                        status = _effective_order_status(original_index, order.get("status", "unknown"))
                        st.caption(f"Status: {status}")

        st.markdown("### Order Actions")
        order_options = [
            f"{index + 1}. {order.get('product', {}).get('name', 'Unknown Product')}"
            for index, order in enumerate(orders)
        ]
        selected_order_label = st.selectbox("Select an order", order_options)
        selected_order_index = order_options.index(selected_order_label)
        selected_order = orders[selected_order_index]
        selected_status = _effective_order_status(
            selected_order_index,
            selected_order.get("status", "unknown")
        )
        st.caption(f"Current Status: {selected_status}")

        normalized_status = str(selected_status).upper()
        cancelled_statuses = {"CANCELLED_BY_BUYER", "CANCELLED_BY_SELLER"}
        return_locked_statuses = {"RETURN_REQUESTED", "RETURN_APPROVED", "RETURN_REJECTED"}

        if normalized_status in cancelled_statuses:
            st.info("Order is cancelled. No further actions available.")
            return

        if normalized_status in return_locked_statuses:
            st.info("Return already in process/completed for this order.")
            return

        action_col1, action_col2 = st.columns(2)
        with action_col1:
            if normalized_status != "DELIVERED":
                if st.button("Cancel Order", key="cancel_order_btn"):
                    _apply_penalty_action(selected_order, "cancelled", username)
                    st.rerun()
        with action_col2:
            if normalized_status == "DELIVERED":
                if st.button("Return Order", key="return_order_btn"):
                    _request_return(selected_order, username)
                    _sync_buyer_state(username)
                    st.rerun()

        return
    elif menu_option == "Escrow Wallet":
        st.subheader("Wallet")

        left_labels, right_values = st.columns([2, 3])
        with left_labels:
            st.markdown("### ESCROW BALANCE")
            st.markdown("### REGULAR WALLET")
            st.markdown("### ADD MONEY")
        with right_values:
            st.metric("Escrow Wallet", f"₹ {st.session_state.buyer_escrow_wallet}")
            st.metric("Regular Wallet", f"₹ {st.session_state.buyer_regular_wallet}")
            add_amount = st.number_input("Enter amount", min_value=0, step=100, key="add_money_input")
            if st.button("ADD MONEY", key="add_money_btn"):
                if add_amount > 0:
                    response = requests.post(
                        SERVER + "/add_money",
                        params={"username": username, "amount": int(add_amount)}
                    )
                    if response.ok:
                        st.success(f"₹ {int(add_amount)} added to Regular Wallet")
                        st.rerun()
                    else:
                        st.error(response.json().get("detail", "Unable to add money"))
                else:
                    st.warning("Enter a valid amount")

        st.markdown("### Escrow Inflow / Outflow")
        history = st.session_state.buyer_escrow_history
        if not history:
            st.info("No escrow inflow/outflow records yet")
        else:
            for entry in reversed(history):
                st.write(
                    f"{entry['type']} | ₹ {entry['amount']} | "
                    f"{entry['direction']} | {entry['note']}"
                )
    elif menu_option == "Regular Wallet":
        st.subheader("Regular Wallet")
        st.metric("Available Balance", f"₹ {st.session_state.buyer_regular_wallet}")
    elif menu_option == "Accrued Penalties":
        st.subheader("Accrued Penalties")
        penalty_col, breakup_col = st.columns([2, 3])
        with penalty_col:
            st.metric("Penalty", f"₹ {st.session_state.buyer_penalties}")
        with breakup_col:
            st.markdown("### Breakout")
            if not st.session_state.buyer_penalty_history:
                st.info("No penalties accrued till now")
            else:
                for item in reversed(st.session_state.buyer_penalty_history):
                    st.write(
                        f"{item['reason']} | {item['order']} | ₹ {item['amount']}"
                    )
    elif menu_option == "Track Order":
        st.subheader("Track Order")
        orders = requests.get(SERVER + "/orders_for_buyer", params={"buyer": username}).json()
        track_id = st.number_input("Track by number", min_value=1, step=1)
        if st.button("Track", key="track_order"):
            matching = [order for order in orders if int(order.get("id", 0)) == int(track_id)]
            if matching:
                tracked = matching[0]
                current_status = tracked.get("status", "NOT YET DISPATCHED")
                st.success(_track_status_label(current_status))
            else:
                st.error("Order number not found")

    if menu_option == "Marketplace":
        st.subheader("Available Items")
        products = requests.get(SERVER + "/products").json()
        filtered_products = [
            product for product in products
            if search_query.lower() in product.get("name", "").lower()
        ]

        if not filtered_products:
            st.info("No items found for this keyword")
            return

        for i, p in enumerate(filtered_products):
            if p.get("image"):
                st.image(p["image"], width=220)
            st.write(p["name"])
            st.write("₹", p["price"])
            if p.get("seller"):
                st.caption(f"Seller: {p.get('seller')}")

            selected_mode = st.selectbox(
                "Payment Mode",
                ["PREPAID", "COD"],
                key=f"payment_mode_{i}_{p['name']}"
            )

            if st.button("Buy " + p["name"], key=f"buy_{i}_{p['name']}"):
                original_index = products.index(p)
                response = requests.post(
                    SERVER + "/order",
                    params={
                        "product_index": original_index,
                        "buyer": username,
                        "payment_mode": selected_mode,
                    }
                )
                if response.ok:
                    st.success(f"Deal sent to seller ({selected_mode})")
                    locked_amount = int(response.json().get("locked_amount", 0))
                    st.session_state.buyer_escrow_history.append(
                        {
                            "type": "Deal Sent",
                            "amount": locked_amount,
                            "direction": "Inflow to Escrow",
                            "note": f"{p.get('name', 'Product')} [{selected_mode}]",
                        }
                    )
                    _sync_buyer_state(username)
                else:
                    st.error(response.json().get("detail", "Unable to place order"))
