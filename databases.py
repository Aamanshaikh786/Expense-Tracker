import pymongo as mg
import pandas as pd
import matplotlib.pyplot as plt 
from datetime import datetime
Client=mg.MongoClient("mongodb://localhost:27017/")
db=Client["Expense"]
data=db["My_bill"]
def add():
    dic={"Amount":0,"category":0,"date":None,"notes":0}
    a=int(input("enter the amount: "))
    if(a<0):
        print("enter a valid amount!!")
    else:
        dic["Amount"]=a
        p=int(input("select category : \n1 Food\n2 Transport\n3 Shopping\n4 Others: "))
        if(p==1):
            o="Food"
        elif(p==2):
            o="Transport"
        elif(p==3):
            o="Shopping"
        else:
            o="Others"
        dic["category"]=o
        q=input("Take todays date ? (y/n): ").lower()
        if(q=="y"):
            dic["date"]=datetime.today()
        else:
            d=input("enter date (dd/mm/yy): ")
            try:
                dic["date"]=datetime.strptime(d,"%d/%m/%y")
            except ValueError:
                print("invalid format of date!! Using todays date")
                dic["date"]=datetime.today()
        dic["notes"]=input("note==>: ")
        data.insert_one(dic)
        print("Expense add successfully!!")

def add_expenses(amount,category,date,notes):
    record={'Amount':float(amount),'category':category,'date':date,'notes':notes}
    data.insert_one(record)
    return True

def view_gui():
    x=list(data.find())
    if not x:
        print("No expense Found ")
    else:
        df=pd.DataFrame(x)
        df=df.drop(columns=["_id"])
        #ensuring that date column is in date time format 
        df["date"]=pd.to_datetime(df["date"])
        #sort the values 
        df=df.sort_values(by="date",ascending=True)
        #date formating
        df["date"]=df["date"].dt.strftime("%d/%m/%y")
        return df 
def view():
    x=list(data.find())
    if not x:
        print("No expense Found ")
    else:
        df=pd.DataFrame(x)
        df=df.drop(columns=["_id"])
        #ensuring that date column is in date time format 
        df["date"]=pd.to_datetime(df["date"])
        #sort the values 
        df=df.sort_values(by="date",ascending=True)
        #date formating
        df["date"]=df["date"].dt.strftime("%d/%m/%y")
        print(df)
def get_summary(group_by='category'):
    """Return summarized totals from expenses grouped by category/month/week."""
    df = view()  # reuse your view() to get all data as DataFrame
    if df.empty:
        return pd.DataFrame(columns=['Group','Total'])

    # convert date column back to datetime for grouping
    df['date'] = pd.to_datetime(df['date'], format='%d/%m/%y')

    if group_by == 'month':
        df['month'] = df['date'].dt.to_period('M')
        grouped = df.groupby('month')['amount'].sum().reset_index()
        grouped.rename(columns={'month':'Group','amount':'Total'}, inplace=True)
    elif group_by == 'week':
        df['week'] = df['date'].dt.to_period('W')
        grouped = df.groupby('week')['amount'].sum().reset_index()
        grouped.rename(columns={'week':'Group','amount':'Total'}, inplace=True)
    else:  # default category
        grouped = df.groupby('category')['amount'].sum().reset_index()
        grouped.rename(columns={'category':'Group','amount':'Total'}, inplace=True)

    return grouped
def delete():
    x=list(data.find().sort("date",1))
    if(not x):
        print("not data found")
    else:
        df=pd.DataFrame(x)
        df=df.drop(columns=["_id"])
        df["date"]=pd.to_datetime(df["date"])
        df=df.sort_values(by="date",ascending=True)
        df["date"]=df["date"].dt.strftime("%d/%m/%y")
        print(df.to_string(index=True))
        try:
            ind=int(input("enter the index of the expense you want to delete: "))
            r=x[ind]
            data.delete_one({"_id":r["_id"]})
            print("data deleted succesfully!!!")
        except(ValueError,IndexError):
            print("some error occur !!")

    
def update():
    x=list(data.find().sort("date",1))
    if(not x):
        print("not data found")
    else:
        df=pd.DataFrame(x)
        df=df.drop(columns=["_id"])
        df["date"]=pd.to_datetime(df["date"])
        df=df.sort_values(by="date",ascending=True)
        df["date"]=df["date"].dt.strftime("%d/%m/%y")
        print(df.to_string(index=True))
    try:
        ind=int(input("enter the index of the expense you want to do changes: "))
        r=x[ind]
        prev={"_id":r["_id"]}
        p=int(input("select parameter you want to do changes : \n1 Amount\n2 category\n3 date\n4 notes: "))
        if(p==1):
            o="Amount"
            a=int(input("enter the amount: "))
            if(a<0):
                print("enter a valid amount!!")
            else:
                g=a
        elif(p==2):
            o="category"
            g=input("enter the updated category: ")
        elif(p==3):
            o="date"
            d=input("enter the updated date")
            try:
                g=datetime.strptime(d,"%d/%m/%y")
            except ValueError:
                print("invalid format of date!! Using todays date")
                g=datetime.today()
        else:
            o="notes"
            g=input("Enter the updated notes: ")        
        nexxt={"$set":{o:g}}
        data.update_one(prev,nexxt)
        print("data updated succesfully!!!")
    except:
        print("Something went wrong!!")

def Total_category():
    x=list(data.find().sort("date",1))
    df=pd.DataFrame(x)
    # p=int(input("select category : \n1 Food\n2 Transport\n3 Shopping\n4 Others: "))
    # if(p==1):
    #     o="Food"
    # elif(p==2):
    #     o="Transport"
    # elif(p==3):
    #     o="Shopping"
    # else:
    #     o="Others"
    group=df.groupby('category')['Amount'].sum()
    group.plot.pie(autopct='%1.1f%%',startangle=90)
    plt.title('Expenses by category')
    plt.ylabel('')
    plt.show()
    # print(group)

def Total_month():
    x=list(data.find().sort("date",1))
    df=pd.DataFrame(x)
    df['Date']=pd.to_datetime(df['date'],format='%d/%m/%y')
    df['month']=df['Date'].dt.to_period('M')
    monthly=df.groupby('month')['Amount'].sum()
    # print(monthly)
    monthly.plot(kind="bar")
    plt.title("Montly expenses")
    plt.xlabel("month")
    plt.ylabel('Total Amount')
    plt.show()

def Total_week():
    x=list(data.find().sort("date",1))
    df=pd.DataFrame(x)
    df['Date']=pd.to_datetime(df['date'],format="%d/%m/%y")
    df['week']=df['Date'].dt.isocalendar().week
    weekly=df.groupby('week')['Amount'].sum()
    weekly.plot(kind="bar")
    plt.title("weekly exepenses")
    plt.xlabel("week")
    plt.ylabel("amount")
    plt.show()
    # print(weekly)

def Total_all():
    x=list(data.find().sort("date",1))
    df=pd.DataFrame(x)
    print("Total = ",df['Amount'].sum())


def export_data(a):
    b=a+'.csv'
    x=list(data.find())
    if not x:
        print("No expense Found ")
    else:
        df=pd.DataFrame(x)
        df=df.drop(columns=["_id"])
        #ensuring that date column is in date time format 
        df["date"]=pd.to_datetime(df["date"])
        #sort the values 
        df=df.sort_values(by="date",ascending=True)
        #date formating
        df["date"]=df["date"].dt.strftime("%d/%m/%y")
        df.to_csv(b,index=False)
        print(f"data exported as {b}")

def summary():
    x=list(data.find().sort('date',1))
    df=pd.DataFrame(x)
    df["date"]=pd.to_datetime(df["date"])
    total=df['Amount'].sum()
    categoryy=df.groupby('category')['Amount'].sum().sort_values(ascending=False).head(3)
    daily_avg=df.groupby(df['date'].dt.date)['Amount'].sum().mean()
    month_avg=df.groupby(df['date'].dt.to_period('M'))['Amount'].sum().mean()
    print("\n==== EXPENSE SUMMARY ===")
    print(f"Total Expenses: {total}")
    print("\nTop 3 Categories:")
    print(categoryy)
    print(f"Average Daily Spending: {daily_avg:.2f}")
    print(f"Average monthly Spending: {month_avg:.2f}")
    print("=======================================\n")
