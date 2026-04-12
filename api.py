from fastapi import FastAPI, HTTPException

app = FastAPI()

users = {
    "Blessy_buyer": {
        "role": "Buyer",
        "regular_wallet": 30000,
        "escrow_wallet": 0,
        "penalties": 0,
        "rep": 10.0,
    },
    "Blessy_seller": {
        "role": "Seller",
        "regular_wallet": 30000,
        "escrow_wallet": 0,
        "penalties": 0,
        "rep": 10.0,
    },
    "Blessy_agent": {
        "role": "Agent",
        "regular_wallet": 30000,
        "escrow_wallet": 0,
        "penalties": 0,
    },
}

products = []
orders = []


def _get_user(username: str):
    user = users.get(username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def _get_order(order_id: int):
    matching = [order for order in orders if order["id"] == order_id]
    if not matching:
        raise HTTPException(status_code=404, detail="Order not found")
    return matching[0]


def _decrease_reputation(username: str, amount: float = 0.1):
    user = _get_user(username)
    if "rep" in user:
        user["rep"] = max(0.0, round(float(user["rep"]) - amount, 1))


@app.get("/products")
def get_products():
    return products


@app.post("/add_product")
def add_product(name: str, price: int, image: str = "", seller: str = ""):
    if seller:
        _get_user(seller)

    product = {
        "name": name,
        "price": price,
        "image": image,
        "seller": seller,
    }
    products.append(product)
    return {"status": "product added"}


@app.post("/order")
def place_order(product_index: int, buyer: str, payment_mode: str = "PREPAID"):
    if not (0 <= product_index < len(products)):
        raise HTTPException(status_code=400, detail="Invalid product index")

    buyer_user = _get_user(buyer)
    product = products[product_index]
    price = int(product["price"])
    normalized_mode = payment_mode.strip().upper()
    if normalized_mode not in {"PREPAID", "COD"}:
        raise HTTPException(status_code=400, detail="payment_mode must be PREPAID or COD")

    locked_amount = price if normalized_mode == "PREPAID" else int(price * 0.10)

    if buyer_user["regular_wallet"] < locked_amount:
        raise HTTPException(status_code=400, detail="Insufficient buyer regular wallet")

    buyer_user["regular_wallet"] -= locked_amount
    buyer_user["escrow_wallet"] += locked_amount

    order = {
        "id": len(orders) + 1,
        "buyer": buyer,
        "seller": product.get("seller", ""),
        "product": product,
        "payment_mode": normalized_mode,
        "buyer_locked_amount": locked_amount,
        "status": "NOT YET DISPATCHED",
        "buyer_deal_done": True,
        "seller_agree": False,
        "agent_notified": False,
        "seller_security_deposit": int(product["price"] * 0.10),
        "return_requested": False,
        "return_decision": "",
    }
    orders.append(order)
    return {
        "status": "order placed",
        "order_id": order["id"],
        "payment_mode": normalized_mode,
        "locked_amount": locked_amount,
    }


@app.get("/orders_for_buyer")
def get_orders_for_buyer(buyer: str):
    return [o for o in orders if o.get("buyer") == buyer]


@app.get("/orders_for_seller")
def get_orders_for_seller(seller: str):
    return [o for o in orders if o.get("seller") == seller]


@app.post("/buyer_deal_done")
def buyer_deal_done(order_id: int, buyer: str):
    buyer_user = _get_user(buyer)
    matching = [o for o in orders if o["id"] == order_id and o.get("buyer") == buyer]
    if not matching:
        raise HTTPException(status_code=404, detail="Order not found for buyer")

    order = matching[0]
    if order["buyer_deal_done"]:
        return {"status": "already_done"}

    price = int(order["product"]["price"])
    if buyer_user["regular_wallet"] < price:
        raise HTTPException(status_code=400, detail="Insufficient buyer regular wallet")

    buyer_user["regular_wallet"] -= price
    buyer_user["escrow_wallet"] += price
    order["buyer_deal_done"] = True

    if order["seller_agree"]:
        order["agent_notified"] = True

    return {"status": "buyer_deal_done"}


@app.post("/seller_agree")
def seller_agree(order_id: int, seller: str):
    seller_user = _get_user(seller)
    order = _get_order(order_id)
    if order.get("seller") != seller:
        raise HTTPException(status_code=404, detail="Order not found for seller")
    if order.get("status") in {"CANCELLED_BY_BUYER", "CANCELLED_BY_SELLER", "DELIVERED"}:
        raise HTTPException(status_code=400, detail="Order is already closed")
    if order["seller_agree"]:
        return {"status": "already_agreed"}

    deposit = int(order["seller_security_deposit"])
    if seller_user["regular_wallet"] < deposit:
        raise HTTPException(status_code=400, detail="Insufficient seller regular wallet")

    seller_user["regular_wallet"] -= deposit
    seller_user["escrow_wallet"] += deposit
    order["seller_agree"] = True
    order["agent_notified"] = True

    return {"status": "seller_agreed"}


@app.post("/seller_cancel")
def seller_cancel(order_id: int, seller: str, reason: str = "OUT OF STOCK"):
    order = _get_order(order_id)
    if order.get("seller") != seller:
        raise HTTPException(status_code=404, detail="Order not found for seller")
    if order.get("status") in {
        "CANCELLED_BY_BUYER",
        "CANCELLED_BY_SELLER",
        "DELIVERED",
        "RETURN_REQUESTED",
        "RETURN_APPROVED",
        "RETURN_REJECTED",
    }:
        raise HTTPException(status_code=400, detail="Order is already closed")

    buyer_user = _get_user(order["buyer"])
    seller_user = _get_user(seller)
    agent_user = _get_user("Blessy_agent")
    price = int(order["product"]["price"])
    locked_amount = int(order.get("buyer_locked_amount", price))
    deposit = int(order.get("seller_security_deposit", 0))

    if buyer_user["escrow_wallet"] >= locked_amount:
        buyer_user["escrow_wallet"] -= locked_amount
        buyer_user["regular_wallet"] += locked_amount

    if order.get("seller_agree") and seller_user["escrow_wallet"] >= deposit:
        seller_user["escrow_wallet"] -= deposit
        seller_share = int(deposit * 0.70)
        agent_share = deposit - seller_share
        buyer_user["escrow_wallet"] += seller_share
        agent_user["escrow_wallet"] += agent_share

    _decrease_reputation(seller, 0.1)

    order["status"] = "CANCELLED_BY_SELLER"
    order["agent_notified"] = False
    return {"status": "seller_cancelled", "reason": reason}


@app.post("/buyer_cancel")
def buyer_cancel(order_id: int, buyer: str):
    order = _get_order(order_id)
    if order.get("buyer") != buyer:
        raise HTTPException(status_code=404, detail="Order not found for buyer")
    if order.get("status") in {
        "CANCELLED_BY_BUYER",
        "CANCELLED_BY_SELLER",
        "DELIVERED",
        "RETURN_REQUESTED",
        "RETURN_APPROVED",
        "RETURN_REJECTED",
    }:
        raise HTTPException(status_code=400, detail="Order is already closed")

    buyer_user = _get_user(buyer)
    seller_user = _get_user(order.get("seller", ""))
    agent_user = _get_user("Blessy_agent")
    product_price = int(order["product"].get("price", 0))
    payment_mode = str(order.get("payment_mode", "PREPAID")).upper()
    locked_amount = int(order.get("buyer_locked_amount", product_price))

    if buyer_user["escrow_wallet"] < locked_amount:
        raise HTTPException(status_code=400, detail="No sufficient amount in buyer escrow")

    penalty_amount = int(product_price * 0.10)
    buyer_refund = locked_amount - penalty_amount if payment_mode == "COD" else product_price - penalty_amount
    buyer_refund = max(0, buyer_refund)
    seller_share = int(product_price * 0.07)
    agent_share = penalty_amount - seller_share

    buyer_user["escrow_wallet"] -= locked_amount
    buyer_user["regular_wallet"] += buyer_refund
    seller_user["escrow_wallet"] += seller_share
    agent_user["escrow_wallet"] += agent_share
    buyer_user["penalties"] += penalty_amount

    if order.get("seller_agree"):
        seller_deposit = int(order.get("seller_security_deposit", 0))
        if seller_user["escrow_wallet"] >= seller_deposit:
            seller_user["escrow_wallet"] -= seller_deposit
            seller_user["regular_wallet"] += seller_deposit

    _decrease_reputation(buyer, 0.1)

    order["status"] = "CANCELLED_BY_BUYER"
    order["agent_notified"] = False

    return {
        "status": "buyer_cancelled",
        "penalty": penalty_amount,
        "refund_to_buyer": buyer_refund,
        "seller_escrow_credit": seller_share,
        "agent_escrow_credit": agent_share,
    }


@app.post("/mark_in_transit")
def mark_in_transit(order_id: int):
    order = _get_order(order_id)
    if not order["seller_agree"]:
        raise HTTPException(status_code=400, detail="Agreement not complete")

    order["status"] = "IN TRANSIT"
    return {"status": "updated"}


@app.post("/mark_delivered")
def mark_delivered(order_id: int):
    order = _get_order(order_id)
    if not order["seller_agree"]:
        raise HTTPException(status_code=400, detail="Agreement not complete")

    buyer_user = _get_user(order["buyer"])
    seller_user = _get_user(order["seller"])
    price = int(order["product"]["price"])
    deposit = int(order["seller_security_deposit"])
    payment_mode = str(order.get("payment_mode", "PREPAID")).upper()
    locked_amount = int(order.get("buyer_locked_amount", price))

    if payment_mode == "PREPAID":
        if buyer_user["escrow_wallet"] >= price:
            buyer_user["escrow_wallet"] -= price
            seller_user["regular_wallet"] += price
    else:
        if buyer_user["escrow_wallet"] >= locked_amount:
            buyer_user["escrow_wallet"] -= locked_amount
            buyer_user["regular_wallet"] += locked_amount

    if seller_user["escrow_wallet"] >= deposit:
        seller_user["escrow_wallet"] -= deposit
        seller_user["regular_wallet"] += deposit

    order["status"] = "DELIVERED"
    order["agent_notified"] = False
    return {"status": "updated"}


@app.post("/buyer_return_request")
def buyer_return_request(order_id: int, buyer: str):
    order = _get_order(order_id)
    if order.get("buyer") != buyer:
        raise HTTPException(status_code=404, detail="Order not found for buyer")
    if order.get("status") != "DELIVERED":
        raise HTTPException(status_code=400, detail="Return request allowed only after delivery")

    order["return_requested"] = True
    order["return_decision"] = "PENDING"
    order["status"] = "RETURN_REQUESTED"
    order["agent_notified"] = True
    return {"status": "return_requested"}


@app.post("/agent_review_return")
def agent_review_return(order_id: int, decision: str):
    order = _get_order(order_id)
    if not order.get("return_requested"):
        raise HTTPException(status_code=400, detail="No return request found for this order")

    normalized_decision = decision.strip().upper()
    if normalized_decision not in {"REASONABLE", "NOT REASONABLE"}:
        raise HTTPException(status_code=400, detail="Decision must be REASONABLE or NOT REASONABLE")

    buyer_user = _get_user(order.get("buyer", ""))
    seller_user = _get_user(order.get("seller", ""))

    if normalized_decision == "REASONABLE":
        _decrease_reputation(order.get("seller", ""), 0.1)
        order["status"] = "RETURN_APPROVED"
    else:
        _decrease_reputation(order.get("buyer", ""), 0.1)
        order["status"] = "RETURN_REJECTED"

    order["return_decision"] = normalized_decision
    order["agent_notified"] = False

    return {
        "status": "return_reviewed",
        "decision": normalized_decision,
        "buyer_rep": buyer_user.get("rep", 0),
        "seller_rep": seller_user.get("rep", 0),
    }


@app.get("/agent_notifications")
def get_agent_notifications():
    return [
        o for o in orders
        if o.get("agent_notified") and o.get("status") not in {
            "DELIVERED",
            "CANCELLED_BY_BUYER",
            "CANCELLED_BY_SELLER",
            "RETURN_APPROVED",
            "RETURN_REJECTED",
        }
    ]


@app.get("/orders")
def get_orders():
    return orders


@app.get("/user_state")
def get_user_state(username: str):
    user = _get_user(username)
    return {
        "username": username,
        "role": user.get("role"),
        "regular_wallet": user.get("regular_wallet", 0),
        "escrow_wallet": user.get("escrow_wallet", 0),
        "penalties": user.get("penalties", 0),
        "rep": user.get("rep", 0),
    }


@app.post("/add_money")
def add_money(username: str, amount: int):
    user = _get_user(username)
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    user["regular_wallet"] += amount
    return {"status": "added", "regular_wallet": user["regular_wallet"]}