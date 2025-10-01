import original_databases as db
while(True):
    n=int(input("1 Add an expense\n2 View\n3 delete \n4 Update \n5 view Totals \n6 To export data \n7 Summary\n8 Exit!==> "))
    match n:
        case 1:
            db.add()
        case 2:
            db.view()
        case 3:
            db.delete()
        case 4:
            db.update()
        case 5:
            while(True):
                o=int(input("1 Total by Category\n2 Total by Month\n3 Total by Week\n4 total of All Expenses \n5 Back to main menu \n==>"))
                match o:
                    case 1:
                        db.Total_category()
                    case 2:
                        db.Total_month()
                    case 3:
                        db.Total_week()
                    case 4:
                        db.Total_all()
                    case 5:
                        break
                    case _:
                        print("Invalid Choice!!!")
        case 6:
            a=input("enter the file name: ")
            db.export_data(a)
        case 7:
            db.summary()
        case 8:
            break
        case _:
            print("invalid !!")