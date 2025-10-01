from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from bson.objectid import ObjectId
import databases as db
import plotly.express as px
import json
import plotly.utils

# --- Flask App Initialization ---
app = Flask(__name__)
# IMPORTANT: Change this secret key! Used for session security.
app.config['SECRET_KEY'] = 'a_very_secret_and_long_key_you_should_change' 

# --- Flask-Login Setup ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'warning'

class User(UserMixin):
    """User class for Flask-Login"""
    def __init__(self, user_data):
        self.id = str(user_data['_id'])
        self.username = user_data['username']
        self.password_hash = user_data['password_hash']

@login_manager.user_loader
def load_user(user_id):
    """Callback to load user object from session ID."""
    user_data = db.get_user_by_id(user_id)
    if user_data:
        return User(user_data)
    return None

# --- Routes ---

@app.route('/')
@login_required
def dashboard():
    """Main dashboard showing summary statistics."""
    # Use the enhanced function to get all dashboard stats
    stats = db.get_dashboard_stats(current_user.id) 
    # RENDER CHANGE: Use the specific template file
    return render_template('dashboard.html', stats=stats)

# --- Authentication Routes ---

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Route for new user registration."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('Both username and password are required.', 'danger')
            return redirect(url_for('register'))

        try:
            # Hash password before storing
            hashed_password = generate_password_hash(password)
            db.add_user(username, hashed_password)
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        except ValueError as e:
            flash(str(e), 'danger')
        except Exception:
            flash('A database error occurred during registration.', 'danger')
    
    # RENDER CHANGE: Use the specific template file
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Route for user login."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user_data = db.get_user_by_username(username)
        
        if user_data and check_password_hash(user_data['password_hash'], password):
            user = User(user_data)
            login_user(user)
            flash('Logged in successfully.', 'success')
            # Redirect to the page the user wanted to access, or dashboard
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'danger')

    # RENDER CHANGE: Use the specific template file
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """Route for logging out the current user."""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# --- Expense Routes ---

@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_expense():
    """Route to add a new expense."""
    categories = db.CATEGORIES
    if request.method == 'POST':
        amount = request.form.get('amount')
        category = request.form.get('category')
        date_str = request.form.get('date')
        notes = request.form.get('notes')
        
        if db.add_expenses(current_user.id, amount, category, date_str, notes):
            flash(f'Expense of ${amount} added successfully!', 'success')
            return redirect(url_for('view_expenses'))
        else:
            flash('Error adding expense. Check your input values.', 'danger')

    # RENDER CHANGE: Use the specific template file
    return render_template('add_expense.html', categories=categories)

@app.route('/view')
@login_required
def view_expenses():
    """Route to view all expenses in a table."""
    df = db.get_user_expenses_df(current_user.id)
    
    # Convert DataFrame rows to a list of dicts for easy rendering in HTML
    expenses_list = df.to_dict('records')
    
    # RENDER CHANGE: The user's filename is view_expenses.htm, not view_expenses.html.
    # Note: Jinja2 can load both, but I'll use the user's provided filename for accuracy.
    return render_template('view_expenses.htm', expenses=expenses_list)

@app.route('/summary')
@login_required
def summary():
    """Route to show expense summaries and charts."""
    group_by = request.args.get('group_by', 'category')
    summary_df = db.get_summary_data(current_user.id, group_by)
    
    # Total expenses for display
    total_expense = summary_df['Total'].sum().round(2)
    graph_json = "" # Initialize to empty string

    # Plotly integration for interactive chart
    # FIX: Check if DataFrame is NOT empty before attempting to plot
    if not summary_df.empty: 
        if group_by == 'category':
            fig = px.pie(summary_df, values='Total', names='Group', title='Expenses by Category',
                         hole=.3, color_discrete_sequence=px.colors.sequential.RdBu)
            fig.update_traces(textposition='inside', textinfo='percent+label')
        else:
            fig = px.bar(summary_df, x='Group', y='Total', title=f'Expenses by {group_by.capitalize()}',
                         labels={'Group': group_by.capitalize(), 'Total': 'Total Amount'},
                         color='Group', color_discrete_sequence=px.colors.qualitative.Bold)
            fig.update_layout(xaxis_tickangle=-45)
        
        # Convert the Plotly figure to JSON for embedding in the HTML template
        graph_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder) 
    else:
        # If the DataFrame is empty, ensure graph_json is an empty string
        graph_json = ""
        
    # RENDER CHANGE: Use the specific template file
    return render_template('summary.html', graph_json=graph_json, group_by=group_by, total_expense=total_expense)

# --- Run Application ---
if __name__ == '__main__':
    # Add a check to ensure users collection exists for the first run
    if "users" not in db.DB.list_collection_names():
        db.DB.create_collection("users")
    
    print("---------------------------------------------------------")
    print(f"Flask Expense Tracker running at http://127.0.0.1:5000/")
    print("---------------------------------------------------------")
    # Set debug to False for production environment, but keep it True for development
    app.run(debug=True)
