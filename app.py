import os
import json
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
import plotly.express as px
import plotly.utils
from databases import create_user, get_user_by_username, get_user_by_id, add_expenses, get_user_expenses_df, get_summary_data, get_dashboard_stats, get_expense_by_id, update_expense, delete_expense, view_expenses_by_user, verify_password
from datetime import date as dt_date
import pandas as pd
CURRENCY = "₹"

app = Flask(__name__, template_folder="templates")
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change_this_secret_key")

login_manager = LoginManager(app)
login_manager.login_view = "login"

# Create a User class for Flask-Login
class User(UserMixin):
    def __init__(self, user_data):
        self.user_data = user_data
        self.id = str(user_data['_id'])
        self.username = user_data['username']

@app.route("/test_data_flow")
@login_required
def test_data_flow():
    """Test the complete data flow"""
    from databases import EXPENSES_COLLECTION
    from bson.objectid import ObjectId
    
    # 1. Check raw MongoDB data
    raw_data = list(EXPENSES_COLLECTION.find({"user_id": ObjectId(current_user.id)}))
    
    result = "<h1>Data Flow Test</h1>"
    
    result += "<h2>1. Raw MongoDB Data:</h2>"
    for item in raw_data:
        result += f"<p>ID: {item['_id']}, Amount: {item.get('Amount')} (type: {type(item.get('Amount'))}), Category: {item.get('category')}</p>"
    
    # 2. Check DataFrame
    df = get_user_expenses_df(current_user.id)
    result += "<h2>2. DataFrame Data:</h2>"
    result += f"<p>DataFrame shape: {df.shape}</p>"
    if not df.empty:
        result += f"<p>Columns: {df.columns.tolist()}</p>"
        result += f"<p>Amount values: {df['Amount'].tolist()}</p>"
    
    # 3. Check Summary Data
    summary_df = get_summary_data(current_user.id, "category")
    result += "<h2>3. Summary Data for Chart:</h2>"
    result += f"<p>Summary DataFrame: {summary_df.to_dict('records')}</p>"
    
    return result

@login_manager.user_loader
def load_user(user_id):
    user_data = get_user_by_id(user_id)
    if user_data:
        return User(user_data)
    return None

def render_page(template, **kwargs):
    return render_template(template, currency=CURRENCY, **kwargs)

# ----------------- AUTH -----------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        u = request.form.get("username")
        p = request.form.get("password")
        if not u or not p:
            flash("Username and password required", "danger")
        else:
            success = create_user(u, p)
            if success:
                flash("Account created! Please log in.", "success")
                return redirect(url_for("login"))
            else:
                flash("Username already exists", "danger")
    return render_page("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user_data = get_user_by_username(username)
        
        if user_data and verify_password(user_data, password):
            user_obj = User(user_data)
            login_user(user_obj)
            flash(f"Welcome {username}!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid credentials", "danger")
    return render_page("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out successfully", "info")
    return redirect(url_for("login"))

# ----------------- EXPENSE ROUTES -----------------
@app.route("/")
@app.route("/dashboard")
@login_required
def dashboard():
    stats = get_dashboard_stats(current_user.id)
    return render_page("dashboard.html", stats=stats)

@app.route("/add_expense", methods=["GET", "POST"])
@login_required
def add_expense():
    cats = ["Food", "Transport", "Shopping", "Others"]
    today = dt_date.today().isoformat()
    if request.method == "POST":
        success = add_expenses(
            user_id=current_user.id,
            amount=request.form.get("amount"),
            category=request.form.get("category"),
            date_str=request.form.get("date"),
            notes=request.form.get("notes")
        )
        if success:
            flash("Expense added!", "success")
            return redirect(url_for("view_expenses"))
        else:
            flash("Error adding expense", "danger")
    return render_page("add_expense.html", categories=cats, today=today)

@app.route("/view")
@login_required
def view_expenses():
    expenses = view_expenses_by_user(current_user.id)
    return render_page("view_expenses.html", expenses=expenses)

@app.route("/edit/<expense_id>", methods=["GET", "POST"])
@login_required
def edit_expense(expense_id):
    expense = get_expense_by_id(expense_id, current_user.id)
    cats = ["Food", "Transport", "Shopping", "Others"]
    if not expense:
        flash("Expense not found", "danger")
        return redirect(url_for("view_expenses"))
    if request.method == "POST":
        success = update_expense(
            expense_id, 
            current_user.id,
            request.form.get("amount"),
            request.form.get("category"),
            request.form.get("date"),
            request.form.get("notes")
        )
        if success:
            flash("Expense updated!", "success")
            return redirect(url_for("view_expenses"))
        else:
            flash("Error updating expense", "danger")
    
    if "date" in expense and isinstance(expense["date"], datetime):
        expense["date_formatted"] = expense["date"].strftime("%Y-%m-%d")
    else:
        expense["date_formatted"] = expense["date"]
    
    return render_page("edit_expense.html", expense=expense, categories=cats)

@app.route("/delete/<expense_id>")
@login_required
def delete_expense(expense_id):
    success = delete_expense(expense_id, current_user.id)
    if success:
        flash("Expense deleted!", "success")
    else:
        flash("Delete failed.", "danger")
    return redirect(url_for("view_expenses"))

@app.route("/summary")
@login_required
def summary():
    group_by = request.args.get("group_by", "category")
    df = get_summary_data(current_user.id, group_by)
    
    total = df["Total"].sum() if not df.empty else 0
    graph_json = ""
    
    if not df.empty:
        # FIX: Manual chart creation to avoid any automatic normalization
        if group_by == "category":
            # Create pie chart manually
            import plotly.graph_objects as go
            
            fig = go.Figure(data=[go.Pie(
                labels=df['Group'].tolist(),
                values=df['Total'].tolist(),
                hole=0.3,
                textinfo='label+value+percent',
                texttemplate='%{label}<br>' + CURRENCY + '%{value:.2f}<br>(%{percent})',
                hovertemplate='<b>%{label}</b><br>' + f'Amount: {CURRENCY}%{{value:.2f}}<br>Percentage: %{{percent}}<extra></extra>'
            )])
            
            fig.update_layout(
                title_text=f"Expenses by Category ({CURRENCY})",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#2c3e50", size=12),
                height=500,
                showlegend=True
            )
            
        else:
            # Create bar chart manually
            import plotly.graph_objects as go
            
            fig = go.Figure(data=[go.Bar(
                x=df['Group'].tolist(),
                y=df['Total'].tolist(),
                text=[f'{CURRENCY}{val:.2f}' for val in df['Total']],
                textposition='outside',
                marker_color='#6366f1',
                hovertemplate='<b>%{x}</b><br>' + f'Amount: {CURRENCY}%{{y:.2f}}<extra></extra>'
            )])
            
            fig.update_layout(
                title_text=f"Expenses by {group_by.capitalize()} ({CURRENCY})",
                xaxis_title=group_by.capitalize(),
                yaxis_title=f"Amount ({CURRENCY})",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#2c3e50", size=12),
                height=500
            )
            
            if group_by in ['month', 'week']:
                fig.update_xaxes(tickangle=45)
        
        graph_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    
    return render_page("summary.html", graph_json=graph_json, group_by=group_by, total_expense=total)

@app.route("/debug_raw_data")
@login_required
def debug_raw_data():
    """Debug route to check raw expense data"""
    from databases import EXPENSES_COLLECTION
    from bson.objectid import ObjectId
    
    # Get raw data from MongoDB
    raw_expenses = list(EXPENSES_COLLECTION.find({"user_id": ObjectId(current_user.id)}))
    
    debug_info = "<h1>Raw Expense Data Debug</h1>"
    debug_info += f"<p>User ID: {current_user.id}</p>"
    debug_info += f"<p>Number of expenses: {len(raw_expenses)}</p>"
    
    debug_info += "<h3>Raw MongoDB Data:</h3>"
    for expense in raw_expenses:
        debug_info += f"<pre>{expense}</pre><hr>"
    
    # Get DataFrame data
    df = get_user_expenses_df(current_user.id)
    debug_info += "<h3>DataFrame Data:</h3>"
    debug_info += f"<pre>{df.to_string() if not df.empty else 'No data'}</pre>"
    
    debug_info += "<h3>Summary Data:</h3>"
    summary_df = get_summary_data(current_user.id, "category")
    debug_info += f"<pre>{summary_df.to_string() if not summary_df.empty else 'No data'}</pre>"
    
    return debug_info

@app.route("/debug_summary")
@login_required
def debug_summary():
    """Debug route to check summary data"""
    group_by = request.args.get("group_by", "category")
    df = get_summary_data(current_user.id, group_by)
    
    print("=== DEBUG SUMMARY DATA ===")
    print(f"Group by: {group_by}")
    print(f"DataFrame shape: {df.shape}")
    print(f"DataFrame columns: {df.columns.tolist()}")
    print(f"DataFrame data:")
    print(df)
    print(f"Total sum: {df['Total'].sum() if not df.empty else 0}")
    print("==========================")
    
    return f"""
    <h1>Debug Summary Data</h1>
    <p>Group by: {group_by}</p>
    <p>DataFrame shape: {df.shape}</p>
    <p>Total sum: {df['Total'].sum() if not df.empty else 0}</p>
    <h3>Data:</h3>
    <pre>{df.to_string() if not df.empty else 'No data'}</pre>
    """
# Reset database (for testing)
@app.route("/reset")
def reset_database():
    """Reset database for testing"""
    from databases import USERS_COLLECTION, EXPENSES_COLLECTION
    USERS_COLLECTION.delete_many({})
    EXPENSES_COLLECTION.delete_many({})
    flash("Database reset successfully", "info")
    return redirect(url_for("register"))

if __name__ == "__main__":
    print("Flask Expense Tracker running at http://127.0.0.1:5000/")
    app.run(debug=True)