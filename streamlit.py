from datetime import date

import pandas as pd
import requests
import streamlit as st

API_URL = "http://127.0.0.1:8000"
CATEGORIES = ["Food", "Transport", "Shopping", "Bills", "Health", "Entertainment", "Other"]

st.set_page_config(page_title="Expense Tracker", page_icon="💰", layout="wide")
st.title("💰 Expense Tracker")

page = st.sidebar.radio("Menu", ["Dashboard", "Add Expense", "Manage Expenses"])


def api(method, path, **kwargs):
    """Small wrapper so we handle connection errors in one place."""
    try:
        return requests.request(method, f"{API_URL}{path}", timeout=5, **kwargs)
    except requests.exceptions.ConnectionError:
        st.error("Cannot reach the API. Is FastAPI running on port 8000?")
        st.stop()


# ---------------- Dashboard ----------------
if page == "Dashboard":
    s = api("GET", "/summary").json()
    c1, c2 = st.columns(2)
    c1.metric("Total Spent", f"₹{s['total_spent']:,.2f}")
    c2.metric("No. of Expenses", s["count"])

    if s["by_category"]:
        st.subheader("Spending by Category")
        df = pd.DataFrame(
            {"Category": list(s["by_category"].keys()), "Amount": list(s["by_category"].values())}
        ).set_index("Category")
        st.bar_chart(df)
    else:
        st.info("No expenses yet. Add your first one!")

# ---------------- Add ----------------
elif page == "Add Expense":
    st.subheader("Add a New Expense")
    with st.form("add_form", clear_on_submit=True):
        title = st.text_input("Title")
        amount = st.number_input("Amount", min_value=0.0, step=10.0)
        category = st.selectbox("Category", CATEGORIES)
        exp_date = st.date_input("Date", value=date.today())
        note = st.text_area("Note (optional)")
        submitted = st.form_submit_button("Add Expense")

    if submitted:
        payload = {
            "title": title,
            "amount": amount,
            "category": category,
            "date": str(exp_date),
            "note": note or None,
        }
        r = api("POST", "/expenses", json=payload)
        if r.status_code == 201:
            st.success("Expense added!")
        else:
            st.error(f"Error: {r.json().get('detail', r.text)}")

# ---------------- Manage ----------------
else:
    st.subheader("All Expenses")
    filter_cat = st.selectbox("Filter by category", ["All"] + CATEGORIES)
    params = {} if filter_cat == "All" else {"category": filter_cat}
    expenses = api("GET", "/expenses", params=params).json()

    if not expenses:
        st.info("No expenses found.")
    else:
        st.dataframe(pd.DataFrame(expenses), use_container_width=True, hide_index=True)

        st.divider()
        st.subheader("Edit or Delete")
        ids = [e["id"] for e in expenses]
        selected = st.selectbox(
            "Select expense",
            ids,
            format_func=lambda i: next(f"#{i} - {e['title']}" for e in expenses if e["id"] == i),
        )
        current = next(e for e in expenses if e["id"] == selected)

        new_title = st.text_input("Title", current["title"])
        new_amount = st.number_input("Amount", min_value=0.01, value=float(current["amount"]))
        new_cat = st.selectbox("Category", CATEGORIES, index=CATEGORIES.index(current["category"]))

        col1, col2 = st.columns(2)
        if col1.button("Update"):
            r = api("PUT", f"/expenses/{selected}",
                    json={"title": new_title, "amount": new_amount, "category": new_cat})
            st.success("Updated!") if r.ok else st.error(r.text)
            st.rerun()
        if col2.button("Delete", type="primary"):
            r = api("DELETE", f"/expenses/{selected}")
            st.success("Deleted!") if r.ok else st.error(r.text)
            st.rerun()