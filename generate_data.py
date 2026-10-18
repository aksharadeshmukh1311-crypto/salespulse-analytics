"""Re-creates the 240-row fictional dataset that the SalesPulse dashboard (app.js -> makeSample) builds in the browser."""
import csv, datetime as dt, math
products=[('Wireless Mouse','Electronics','Accessories',799),('Desk Lamp','Home Office','Lighting',1499),('Notebook Set','Stationery','Paper',349),('USB-C Hub','Electronics','Accessories',2199),('Office Chair','Furniture','Seating',7499),('Water Bottle','Lifestyle','Drinkware',599),('Monitor Stand','Furniture','Desk Setup',1899),('Pen Pack','Stationery','Writing',199),('Keyboard','Electronics','Accessories',2599),('Storage Box','Home Office','Organization',899)]
regions=[('West','Maharashtra'),('North','Delhi'),('South','Karnataka'),('East','West Bengal'),('Central','Madhya Pradesh')]
rows=[]
for i in range(240):
    p=products[(i*7+i//5)%10]; r=regions[(i*3+i//8)%5]
    date=dt.date(2025,1,1)+dt.timedelta(days=(i*11+(i//4)*3)%365)
    qty=1+((i*5+i//3)%7); sales=qty*p[3]
    profit=math.floor(sales*(.11+((i*13)%23)/100)+0.5)
    rows.append([f"SP-{10001+i}",date.isoformat(),p[0],p[1],p[2],qty,p[3],sales,profit,f"Customer {100+i%67:03d}",r[0],r[1]])
rows.sort(key=lambda x:x[1])
with open('data/sales_data.csv','w',newline='') as f:
    w=csv.writer(f); w.writerow(['Order ID','Order Date','Product Name','Category','Subcategory','Quantity','Unit Price','Sales','Profit','Customer Name','Region','State']); w.writerows(rows)
print(len(rows),'rows written')
