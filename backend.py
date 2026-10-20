import json
import os
from datetime import date
from typing import Literal, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

DATA_FILE = "expenses.json"

app = FastAPI(title="Expense Tracker API")

Category = Literal["Food", "Transport", "Shopping", "Bills", "Health", "Entertainment", "Other"]


# ---------- Models ----------
class Expense(BaseModel):
    title: str = Field(..., min_length=1, max_length=100)
    amount: float = Field(..., gt=0, description="Amount must be greater than 0")
    category: Category
    date: date
    note: Optional[str] = None


class ExpenseUpdate(BaseModel):
    title: Optional[str] = None
    amount: Optional[float] = Field(None, gt=0)
    category: Optional[Category] = None
    date: Optional[date] = None
    note: Optional[str] = None


# ---------- Helpers ----------
def load_data() -> dict:
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r") as f:
        return json.load(f)


def save_data(data: dict) -> None:
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def next_id(data: dict) -> str:
    if not data:                              # no expenses yet
        return "1"
    biggest = max(int(k) for k in data)       # highest existing ID
    return str(biggest + 1)


# ---------- Routes ----------
@app.get("/")
def home():
    return {"message": "Expense Tracker API is running"}


@app.post("/expenses", status_code=201)
def add_expense(expense: Expense):
    data = load_data()
    new_id = next_id(data)
    data[new_id] = expense.model_dump(mode="json")
    save_data(data)
    return {"message": "Expense added", "id": new_id}


@app.get("/expenses")
def get_expenses(category: Optional[Category] = None):
    data = load_data()
    items = [{"id": k, **v} for k, v in data.items()]
    if category:
        items = [e for e in items if e["category"] == category]
    return items


@app.get("/expenses/{expense_id}")
def get_expense(expense_id: str):
    data = load_data()
    if expense_id not in data:
        raise HTTPException(status_code=404, detail="Expense not found")
    return {"id": expense_id, **data[expense_id]}


@app.put("/expenses/{expense_id}")
def update_expense(expense_id: str, update: ExpenseUpdate):
    data = load_data()
    if expense_id not in data:
        raise HTTPException(status_code=404, detail="Expense not found")
    changes = update.model_dump(mode="json", exclude_unset=True)
    data[expense_id].update(changes)
    save_data(data)
    return {"message": "Expense updated"}


@app.delete("/expenses/{expense_id}")
def delete_expense(expense_id: str):
    data = load_data()
    if expense_id not in data:
        raise HTTPException(status_code=404, detail="Expense not found")
    del data[expense_id]
    save_data(data)
    return {"message": "Expense deleted"}


@app.get("/summary")
def summary():
    data = load_data()
    total = sum(e["amount"] for e in data.values())
    by_category: dict = {}
    for e in data.values():
        by_category[e["category"]] = by_category.get(e["category"], 0) + e["amount"]
    return {
        "total_spent": round(total, 2),
        "count": len(data),
        "by_category": {k: round(v, 2) for k, v in by_category.items()},
    }