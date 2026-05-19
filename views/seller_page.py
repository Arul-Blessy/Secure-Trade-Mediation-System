import streamlit as st
import requests

from config import SERVER


def _get_user_state(username: str):
    try:
        return requests.get(SERVER + "/user_state", params={"username": username}).json()
    except Exception:
        return {
            "regular_wallet": 0,
            "escrow_wallet": 0,
            "penalties": 0,
            "rep": 10.0,
        }


def render_seller_page(username: str):
    st.header("Seller Portal")

    menu_option = st.sidebar.radio(
        "Browse",
        ["Include Item", "My Product", "Orders Received", "Escrow Wallet", "Regular Wallet", "Accrued Penalties", "Track Order"]
    )

    user_state = _get_user_state(username)

    top_left, top_right = st.columns([4, 1])
    with top_left:
        st.text_input("Search Bar", placeholder="Search orders/items", key="seller_search", disabled=True)
    with top_right:
        st.metric("Reputation Score", f"{float(user_state.get('rep', 10.0)):.1f}")

    if menu_option == "Include Item":
        st.subheader("Include Item")
        item_name = st.text_input("Item Name")
        item_price = st.number_input("Cost per piece", min_value=0, step=1)
        item_image = st.text_input("Image URL (optional)")

        if st.button("Include Item"):
            if not item_name.strip() or item_price <= 0:
                st.error("Item Name and Cost per piece are required")
            else:
                requests.post(
                    SERVER + "/add_product",
                    params={
                        "name": item_name.strip(),
                        "price": int(item_price),
                        "image": item_image.strip(),
                        "seller": username,
                    }
                )
                st.success("Item included and visible for buyer search")

    elif menu_option == "My Product":
        st.subheader("My Product")
        products = requests.get(SERVER + "/products").json()
        my_products = [product for product in products if product.get("seller") == username]

        if not my_products:
            st.info("No products added yet")
        else:
            for index, product in enumerate(my_products, start=1):
                st.markdown(f"### {index}. {product.get('name', 'Item')}")
                st.write(f"Cost per piece: ₹ {int(product.get('price', 0))}")
                if product.get("image"):
                    st.image(product.get("image"), width=220)

    elif menu_option == "Orders Received":
        st.subheader("Orders Received")
        orders = requests.get(SERVER + "/orders_for_seller", params={"seller": username}).json()
        orders = sorted(orders, key=lambda order: int(order.get("id", 0)), reverse=True)
        if not orders:
            st.info("No orders received yet")
            return

        for order in orders:
            product = order.get("product", {})
            st.markdown(f"### Order #{order['id']} - {product.get('name', 'Item')}")
            st.caption(f"Buyer: {order.get('buyer', '-')}")
            st.caption(f"Payment: {order.get('payment_mode', 'PREPAID')}")
            st.caption(f"Status: {order.get('status', 'NOT YET DISPATCHED')}")
            st.caption(f"Seller Agree: {'Yes' if order.get('seller_agree') else 'No'}")

            normalized_status = str(order.get("status", "")).upper()
            cancelled_statuses = {"CANCELLED_BY_BUYER", "CANCELLED_BY_SELLER"}
            closed_statuses = cancelled_statuses | {"DELIVERED", "RETURN_REQUESTED", "RETURN_APPROVED", "RETURN_REJECTED"}

            if normalized_status in cancelled_statuses:
                st.info("Order is cancelled. No further actions available.")
                continue

            action_col1, action_col2 = st.columns(2)
            with action_col1:
                if not order.get("seller_agree") and normalized_status not in closed_statuses:
                    if st.button("AGREE", key=f"seller_agree_{order['id']}"):
                        response = requests.post(
                            SERVER + "/seller_agree",
                            params={"order_id": order["id"], "seller": username}
                        )
                        if response.ok:
                            st.success("Seller agreed. Agent has been notified to take delivery.")
                            st.rerun()
                        else:
                            st.error(response.json().get("detail", "Unable to agree"))
            with action_col2:
                if normalized_status not in closed_statuses:
                    if st.button("CANCEL (OUT OF STOCK)", key=f"seller_cancel_{order['id']}"):
                        response = requests.post(
                            SERVER + "/seller_cancel",
                            params={"order_id": order["id"], "seller": username, "reason": "OUT OF STOCK"}
                        )
                        if response.ok:
                            st.warning("Order cancelled by seller: OUT OF STOCK")
                            st.rerun()
                        else:
                            st.error(response.json().get("detail", "Unable to cancel order"))

    elif menu_option == "Escrow Wallet":
        st.subheader("Escrow Wallet")
        st.metric("Escrow Balance", f"₹ {int(user_state.get('escrow_wallet', 0))}")
        st.info("Escrow wallet is system-managed and cannot be manually edited")

    elif menu_option == "Regular Wallet":
        st.subheader("Regular Wallet")
        st.metric("Regular Balance", f"₹ {int(user_state.get('regular_wallet', 0))}")
        add_amount = st.number_input("Enter amount", min_value=0, step=100, key="seller_add_amount")
        if st.button("ADD MONEY", key="seller_add_money_btn"):
            response = requests.post(
                SERVER + "/add_money",
                params={"username": username, "amount": int(add_amount)}
            )
            if response.ok:
                st.success("Money added to Regular Wallet")
                st.rerun()
            else:
                st.error(response.json().get("detail", "Unable to add money"))

    elif menu_option == "Accrued Penalties":
        st.subheader("Accrued Penalties")
        st.metric("Total Penalties", f"₹ {int(user_state.get('penalties', 0))}")

    elif menu_option == "Track Order":
        st.subheader("Track Order")
        orders = requests.get(SERVER + "/orders_for_seller", params={"seller": username}).json()
        track_id = st.number_input("Track by number", min_value=1, step=1, key="seller_track")
        if st.button("Track", key="seller_track_btn"):
            matched = [order for order in orders if int(order.get("id", 0)) == int(track_id)]
            if matched:
                st.success(matched[0].get("status", "NOT YET DISPATCHED"))
            else:
                st.error("Order number not found")
