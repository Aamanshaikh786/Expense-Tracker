import tkinter as tk
from tkinter import ttk,messagebox
import original_databases as db
Categories=["Food","Transport","Shopping","Others"]
root =tk.Tk()
root.title("Expense Tracker")
root.geometry("400x400")

# Dropdown to choose summary type
summary_option = tk.StringVar(value='category')
options = ['category','month','week']
ttk.Label(root, text="Summary by:").pack()
ttk.OptionMenu(root, summary_option, options[0], *options).pack()

# Treeview for summary display
tree = ttk.Treeview(root, columns=("Group","Total"), show='headings')
tree.heading("Group", text="Group")
tree.heading("Total", text="Total")
tree.pack(fill='both', expand=True)

def add_expenses():
    add_win=tk.Toplevel(root)
    add_win.title("Add Expenses")
    #amount
    tk.Label(add_win,text="Amount").pack()
    amount_entry=tk.Entry(add_win)
    amount_entry.pack()

    #category
    tk.Label(add_win,text="category").pack()
    selected_cat=tk.StringVar(add_win)
    selected_cat.set(Categories[0])
    tk.OptionMenu(add_win,selected_cat,*Categories).pack()

    #date 
    tk.Label(add_win,text="Date (DD/MM/YY)").pack()
    date_entry=tk.Entry(add_win)
    date_entry.pack()
    #Notes
    tk.Label(add_win,text="Notes").pack()
    notes_entry=tk.Entry(add_win)
    notes_entry.pack()

    def save():
        amount=amount_entry.get()
        category=selected_cat.get()
        date=date_entry.get()
        notes=notes_entry.get()
        try:
            db.add_expenses(amount,category,date,notes)
            messagebox.showinfo("Success",f"Expense added to {category}!")
            add_win.destroy()
        except Exception as e:
            messagebox.showerror("Error",str(e))
    tk.Button(add_win,text="Save",command=save).pack(pady=5)
    
    

def view_expenses(root):
    view_win=tk.Toplevel(root)
    view_win.title("All Expenses")
    view_win.geometry("700x400")
    columns=("date","category","Amount","notes")
    tree=ttk.Treeview(view_win,columns=columns,show="headings")
    tree.heading("date",text="date")
    tree.heading("category",text="category")
    tree.heading("Amount",text="Amount")
    tree.heading("notes",text="notes")
    tree.column("date",width=100)
    tree.column("category",width=100)
    tree.column("Amount",width=100)
    tree.column("notes",width=100)
    tree.pack(fill=tk.BOTH,expand=True)
    try:
        data=db.view_gui()
        if data is not None and not data.empty:
            for _,row in data.iterrows():
                tree.insert("",tk.END,values=(row['date'],row['category'],row['Amount'],row['notes']))
        else:
            messagebox.showinfo("Info","No Expenses Found")
    except Exception as e:
        messagebox.showerror("Error",f"Could not fetch expenses: {str(e)}")
    tk.Button(view_win,text="Close",command=view_win.destroy).pack(pady=5)

def show_summary():
    for i in tree.get_children():
        tree.delete(i)
    df = db.get_summary(summary_option.get())
    for _, row in df.iterrows():
        tree.insert("", tk.END, values=(row['Group'], row['Total']))

def exit_app():
    root.destroy()

tk.Label(root,text="Expense Tracker",font=("Arial",16)).pack(pady=10)
tk.Button(root,text="Add Expenses",width=20,command=add_expenses).pack(pady=5)
tk.Button(root,text="View All Expenses",width=20,command=lambda:view_expenses(root)).pack(pady=5)
ttk.Button(root, text="Show Summary", command=show_summary).pack()
tk.Button(root,text="Exit",width=20,command=exit_app).pack(pady=5)

root.mainloop()