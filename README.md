# Secure Trade Mediation System
### Academic Research Project | Published in IJSART

A full-stack prototype designed to eliminate E-commerce fraud (COD and Return scams) using a **Dual-Escrow** mechanism and **Symmetric Penalty-Redistribution**. This project addresses vulnerabilities in modern supply chains by financially binding both parties to a "Handshake" agreement.

## 🚀 Live Link
- **Live Demo Interface:** [Interact with the Frontend](https://secure-trade-mediation-system-2.onrender.com/)

## 🔑 Demo Login Credentials
To test the end-to-end user roles and the symmetric accountability flows on the live link, you can log in using these preset credentials:

| Role | Username | Password | Purpose in Walkthrough |
| :--- | :--- | :--- | :--- |
| **Buyer** | `Blessy_buyer` | `12345678` | Browse items, add funds, place prepaid/COD orders, or request a return. |
| **Seller** | `Blessy_seller` | `12345678` | View received orders, accept deals, or trigger stock-out simulations. |
| **Delivery Agent** | `Blessy_agent` | `12345678` | Act as the mediator to confirm delivery or flag unreasonable return fraud. |

> **💡 Quick Testing Tip:** Open the live link in two separate browser windows ,so you can log in as a Buyer in one and the Seller/Agent in the other to watch the escrow balances update instantly!

## 🧠 System Logic & Penalty Redistribution
The core of this research is a symmetric accountability model. If the system detects a scam via the Delivery Agent (Mediator), the escrow is redistributed as follows:

| Scenario | Trigger | Agent (3%) | Victim (7%) | Instigator Refund | Reputation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Buyer Fraud** | Unreasonable Return | Service Fee | Seller Compensation | 90% of Price | -0.1 (Buyer) |
| **Seller Fraud** | Stock-out / Fake Cancel | Service Fee | Buyer Compensation | 100% Price + 10% | -0.1 (Seller) |
| **Successful** | Product Delivered | - | - | Full Payouts | No Change |

---

## 📸 Project Interface & Walkthrough
*Visual evidence of the prototype workflow and the Dual-Escrow logic.*

| Step | System View |
| :--- | :--- |
| **1. Initial Product List** | <img src="Screenshots/seller list page .png" width="400"> |
| **2. Buyer's Marketplace** | <img src="Screenshots/buyer's page.png" width="400"> |
| **3. Buyer's Order Confirmation** | <img src="Screenshots/amt paid by the buyer .png" width="400"> |
| **4. Orders receieved by the Seller** | <img src="Screenshots/seller agree.png" width="400"> |
| **5. Successful Delivery** | <img src="Screenshots/agent delivered.png" width="400"> |
| **6. Unreasonable Return by the Buyer** | <img src="Screenshots/buyer return.png" width="400"> |
| **7. 10% Penalty to the Buyer** | <img src="Screenshots/penalty to buyer.png" width="400"> |
| **8. 7% redistribution to the Seller** | <img src="Screenshots/seller%207%25%20gain.png" width="400"> |
| **9. 3% redistribution to the Agent** | <img src="Screenshots/3%25%20gain%20by%20agent.png" width="400"> |

---

## 🛠️ Tech Stack
- **Backend:** FastAPI (Python)
- **Frontend:** Streamlit
- **Server:** Uvicorn (ASGI)
- **Data Handling:** Python (Requests, Config-based Auth)

## 🚀 How to Run Locally
This prototype requires two parallel processes to be running. Ensure you have installed the dependencies first: `pip install -r requirements.txt`.

### Step 1: Start the Backend (API)
Run in terminal 1: `uvicorn api:app --reload`

### Step 2: Start the Frontend (UI)
Run in terminal 2: `streamlit run app.py --server.address 0.0.0.0`

### Step 3: Access
Navigate to the URL provided in the Streamlit terminal. Use the credentials provided in `config.py` to test the Buyer, Seller, and Agent roles.

---

## 📄 Documentation & Publication
This project was formally documented and published to contribute to the field of e-commerce security.

- **Paper Title:** Secure Trade Mediation System
- **Journal:** International Journal of Scientific Research and Technology (IJSART)
- **File:** [Download Research Paper (PDF)](./Secure_Trade_Mediation_System_IJSART.pdf)

---

## 💡 Key Contributions
- **Zero-Trust Escrow:** Neither party holds the total funds until the "Mediator" (Delivery Agent) confirms a successful handover.
- **Symmetric Accountability:** Unlike traditional systems that favor one side, this model penalizes both "Stock-out scams" by sellers and "Return scams" by buyers.
- **Dynamic Reputation:** Users with scores below a certain threshold are flagged, increasing safety for all participants.

> **⚠️ Note on Security:** This is a prototype. User credentials and simulated balances are stored in `config.py` for demonstration purposes. In a production environment, these would be managed via hashed databases and encrypted environment variables.
