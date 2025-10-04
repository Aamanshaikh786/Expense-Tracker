import pymongo as mg
import pandas as pd
from datetime import datetime
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash

# --- Configuration ---
MONGO_URI = "mongodb://localhost:27017/"
CLIENT = mg.MongoClient(MONGO_URI)
DB = CLIENT["Expense"]
USERS_COLLECTION = DB["users"]
EXPENSES_COLLECTION = DB["My_bill"]
CATEGORIES = ["Food", "Transport", "Shopping", "Others", "Utilities", "Entertainment"]

# --- User Management Functions ---
def create_user(username, password):
    """Create a new user with hashed password"""
    if USERS_COLLECTION.find_one({"username": username}):
        return False
    # Use proper password hashing
    password_hash = generate_password_hash(password)
    user_data = {
        "username": username, 
        "password_hash": password_hash,
        "created_at": datetime.now()
    }
    result = USERS_COLLECTION.insert_one(user_data)
    return True

def get_user_by_username(username):
    return USERS_COLLECTION.find_one({"username": username})

def get_user_by_id(user_id):
    try:
        return USERS_COLLECTION.find_one({"_id": ObjectId(user_id)})
    except Exception:
        return None

def verify_password(user, password):
    """Verify user password"""
    if user and 'password_hash' in user:
        return check_password_hash(user['password_hash'], password)
    return False

# --- Expense Management Functions ---
def add_expenses(user_id, amount, category, date_str, notes):
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        # FIX: Ensure amount is properly converted to float
        amount_float = float(amount)
        print(f"DEBUG: Adding expense - Amount: {amount_float}, Type: {type(amount_float)}")
        
        record = {
            "user_id": ObjectId(user_id),
            "Amount": amount_float,  # Use the properly converted float
            "category": category,
            "date": date_obj,
            "notes": notes if notes else "No notes"
        }
        result = EXPENSES_COLLECTION.insert_one(record)
        print(f"DEBUG: Expense added with ID: {result.inserted_id}")
        return True
    except Exception as e:
        print(f"Error adding expense: {e}")
        return False

def get_user_expenses_df(user_id):
    try:
        expenses = list(EXPENSES_COLLECTION.find({"user_id": ObjectId(user_id)}).sort("date", 1))
        if not expenses:
            return pd.DataFrame()

        # Debug: Print raw data from MongoDB
        print("=== RAW MONGODB DATA ===")
        for expense in expenses:
            print(f"ID: {expense.get('_id')}, Amount: {expense.get('Amount')} (type: {type(expense.get('Amount'))}), Category: {expense.get('category')}")

        df = pd.DataFrame(expenses)
        df = df.drop(columns=["_id", "user_id"], errors="ignore")

        df["date"] = pd.to_datetime(df["date"])
        df["display_date"] = df["date"].dt.strftime("%d/%m/%y")

        # FIX: Check if Amount column exists and handle it properly
        if 'Amount' in df.columns:
            print(f"DEBUG: Amount column before conversion: {df['Amount'].tolist()}")
            df["Amount"] = pd.to_numeric(df["Amount"], errors='coerce')
            print(f"DEBUG: Amount column after conversion: {df['Amount'].tolist()}")
        else:
            print("ERROR: 'Amount' column not found in DataFrame!")
            print(f"Available columns: {df.columns.tolist()}")
        
        df.dropna(subset=["Amount"], inplace=True)

        return df.sort_values(by="date", ascending=False)
    except Exception as e:
        print(f"Error fetching expenses: {e}")
        return pd.DataFrame()

def get_summary_data(user_id, group_by="category"):
    df = get_user_expenses_df(user_id)
    
    if df.empty:
        print("DEBUG: No expenses found")
        return pd.DataFrame(columns=["Group", "Total"])

    # FIX: Check if we have the right column and data
    print(f"DEBUG: DataFrame columns: {df.columns.tolist()}")
    if 'Amount' not in df.columns:
        print("ERROR: 'Amount' column missing! Available columns:", df.columns.tolist())
        return pd.DataFrame(columns=["Group", "Total"])
    
    print(f"DEBUG: Amount values: {df['Amount'].tolist()}")
    print(f"DEBUG: Amount data type: {df['Amount'].dtype}")

    if group_by == "month":
        df["Group"] = df["date"].dt.strftime("%Y-%m")
    elif group_by == "week":
        df["Group"] = df["date"].dt.strftime("%Y-W%U")
    else:
        df["Group"] = df["category"]

    # FIX: Use the correct column name and ensure it's numeric
    grouped = df.groupby("Group", as_index=False)["Amount"].sum()
    grouped.rename(columns={"Amount": "Total"}, inplace=True)
    grouped["Total"] = pd.to_numeric(grouped["Total"], errors='coerce').round(2)
    
    print(f"DEBUG: Final grouped data for chart:")
    print(grouped)
    
    return grouped

def get_dashboard_stats(user_id):
    df = get_user_expenses_df(user_id)
    if df.empty:
        return {"total_expenses": 0, "month_expenses": 0, "week_expenses": 0, "total_records": 0, "category_breakdown": {}}

    total = df["Amount"].sum().round(2)
    total_records = len(df)

    today = datetime.now()
    df["YearMonth"] = df["date"].dt.to_period("M").astype(str)
    df["YearWeek"] = df["date"].dt.strftime("%Y-%U")

    month_expenses = df[df["YearMonth"] == today.strftime("%Y-%m")]["Amount"].sum().round(2)
    week_expenses = df[df["YearWeek"] == today.strftime("%Y-%U")]["Amount"].sum().round(2)

    category_breakdown = df.groupby("category")["Amount"].sum().sort_values(ascending=False).to_dict()

    return {
        "total_expenses": total,
        "month_expenses": month_expenses,
        "week_expenses": week_expenses,
        "total_records": total_records,
        "category_breakdown": category_breakdown
    }

def get_expense_by_id(expense_id, user_id):
    """Get expense by ID for specific user"""
    try:
        expense = EXPENSES_COLLECTION.find_one({"_id": ObjectId(expense_id), "user_id": ObjectId(user_id)})
        if expense:
            expense["id"] = str(expense["_id"])
        return expense
    except:
        return None

def update_expense(expense_id, user_id, amount, category, date_str, notes):
    """Update an existing expense"""
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        EXPENSES_COLLECTION.update_one(
            {"_id": ObjectId(expense_id), "user_id": ObjectId(user_id)},
            {"$set": {
                "Amount": float(amount),
                "category": category,
                "date": date_obj,
                "notes": notes if notes else "No notes"
            }}
        )
        return True
    except Exception as e:
        print(f"Error updating expense: {e}")
        return False

def delete_expense(expense_id, user_id):
    """Delete an expense"""
    try:
        result = EXPENSES_COLLECTION.delete_one({"_id": ObjectId(expense_id), "user_id": ObjectId(user_id)})
        return result.deleted_count > 0
    except:
        return False

def view_expenses_by_user(user_id):
    """Get expenses for view template"""
    try:
        expenses = list(EXPENSES_COLLECTION.find({"user_id": ObjectId(user_id)}).sort("date", -1))
        for expense in expenses:
            expense["id"] = str(expense["_id"])
            if isinstance(expense["date"], datetime):
                expense["date"] = expense["date"].strftime("%d/%m/%Y")
        return expenses
    except Exception as e:
        print(f"Error fetching expenses: {e}")
        return []