import pymongo as mg
import pandas as pd
from datetime import datetime
from datetime import date
from bson.objectid import ObjectId # Import ObjectId for user lookup

# --- Configuration ---
MONGO_URI = "mongodb://localhost:27017/"
CLIENT = mg.MongoClient(MONGO_URI)
DB = CLIENT["Expense"]
USERS_COLLECTION = DB["users"]
EXPENSES_COLLECTION = DB["My_bill"]
CATEGORIES = ["Food", "Transport", "Shopping", "Others", "Utilities", "Entertainment"]

# --- User Management Functions (for Authentication) ---

def add_user(username, password_hash):
    """Inserts a new user into the database."""
    if USERS_COLLECTION.find_one({"username": username}):
        raise ValueError("Username already exists.")
    
    user_data = {
        "username": username,
        "password_hash": password_hash,
    }
    result = USERS_COLLECTION.insert_one(user_data)
    return str(result.inserted_id)

def get_user_by_username(username):
    """Finds a user by username."""
    user = USERS_COLLECTION.find_one({"username": username})
    return user

def get_user_by_id(user_id):
    """Finds a user by MongoDB ObjectId string."""
    try:
        # Use ObjectId to query by the primary key
        user = USERS_COLLECTION.find_one({"_id": ObjectId(user_id)})
        return user
    except Exception:
        return None

# --- Expense Management Functions (all require user_id) ---

def add_expenses(user_id, amount, category, date_str, notes):
    """Adds a new expense for a specific user."""
    try:
        # Convert web form date string (YYYY-MM-DD) to datetime object
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        
        record = {
            # Ensure user_id is stored as a string or ObjectId depending on how you want to query later
            'user_id': user_id, 
            'Amount': float(amount),
            'category': category,
            'date': date_obj,
            'notes': notes if notes else "No notes"
        }
        EXPENSES_COLLECTION.insert_one(record)
        return True
    except ValueError as e:
        print(f"Error converting data: {e}")
        return False
    except Exception as e:
        print(f"Database error during add: {e}")
        return False

def get_user_expenses_df(user_id):
    """Fetches all expenses for a user and returns them as a clean DataFrame."""
    try:
        # Filter expenses only for the current user
        expense_list = list(EXPENSES_COLLECTION.find({"user_id": user_id}).sort("date", 1))
        
        if not expense_list:
            return pd.DataFrame() 

        df = pd.DataFrame(expense_list)
        df = df.drop(columns=["_id", "user_id"], errors='ignore')
        
        # Ensure date column is datetime and format for display
        df["date"] = pd.to_datetime(df["date"])
        # Add a column for display formatting
        df["display_date"] = df["date"].dt.strftime("%d/%m/%y") 
        
        # Ensure amount is numeric for calculations
        df['Amount'] = pd.to_numeric(df['Amount'], errors='coerce')
        df.dropna(subset=['Amount'], inplace=True)

        return df.sort_values(by="date", ascending=False)
    except Exception as e:
        print(f"Error fetching data for user {user_id}: {e}")
        return pd.DataFrame()

def get_summary_data(user_id, group_by='category'):
    """Returns summarized totals grouped by category, month, or week, filtered by user."""
    df = get_user_expenses_df(user_id)
    if df.empty:
        return pd.DataFrame(columns=['Group', 'Total'])

    if group_by == 'month':
        df['Group'] = df['date'].dt.strftime('%Y-%m') # Year-Month
    elif group_by == 'week':
        # ISO week numbering for grouping
        df['Group'] = df['date'].dt.strftime('%Y-W%W') 
    else:  # category is default
        df['Group'] = df['category']

    # Aggregate and clean up
    grouped = df.groupby('Group')['Amount'].sum().reset_index()
    grouped.rename(columns={'Amount': 'Total'}, inplace=True)
    grouped['Total'] = grouped['Total'].round(2)
    
    return grouped
    
def get_dashboard_stats(user_id):
    """Calculates key statistics for the dashboard."""
    df = get_user_expenses_df(user_id)
    
    if df.empty:
        return {
            "total_expenses": 0.00,
            "month_expenses": 0.00,
            "week_expenses": 0.00,
            "total_records": 0,
            "category_breakdown": {}
        }
        
    # --- 1. Total Expenses and Records ---
    total = df['Amount'].sum().round(2)
    total_records = len(df)
    
    # --- 2. Current Month and Week Totals ---
    
    # Filter for the current month
    today = datetime.now()
    current_month = df['date'].dt.to_period('M') == pd.Period(today, freq='M')
    month_expenses = df[current_month]['Amount'].sum().round(2)
    
    # Filter for the current week (ISO Week)
    current_year_week = today.strftime('%Y-%W')
    df['YearWeek'] = df['date'].dt.strftime('%Y-%W')
    current_week = df['YearWeek'] == current_year_week
    week_expenses = df[current_week]['Amount'].sum().round(2)

    # --- 3. Category Breakdown (for dashboard) ---
    category_breakdown = df.groupby('category')['Amount'].sum().sort_values(ascending=False).to_dict()
    
    return {
        "total_expenses": total,
        "month_expenses": month_expenses,
        "week_expenses": week_expenses,
        "total_records": total_records,
        "category_breakdown": category_breakdown
    }
