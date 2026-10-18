"""SalesPulse sales analysis: cleaning -> KPIs -> EDA -> charts -> insights.
Run: python analysis.py"""
import pandas as pd, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

OUT, CH = "outputs/", "outputs/charts/"
plt.rcParams.update({"figure.dpi": 130, "axes.spines.top": False, "axes.spines.right": False, "font.size": 10})
BLUE, TEAL, RED = "#2563eb", "#0f9f91", "#d95362"
inr = FuncFormatter(lambda x, _: f"₹{x/1e5:.1f}L" if abs(x) >= 1e5 else f"₹{x:,.0f}")

# 1. LOAD + QUALITY CHECKS
df = pd.read_csv("data/sales_data.csv", parse_dates=["Order Date"])
quality = {
    "Rows": len(df),
    "Missing values": int(df.isna().sum().sum()),
    "Duplicate Order IDs": int(df["Order ID"].duplicated().sum()),
    "Duplicate rows": int(df.duplicated().sum()),
    "Sales != Qty x Unit Price": int((df["Sales"] != df["Quantity"] * df["Unit Price"]).sum()),
    "Negative profit rows": int((df["Profit"] < 0).sum()),
    "Zero/negative quantity": int((df["Quantity"] <= 0).sum()),
    "Date range": f"{df['Order Date'].min():%Y-%m-%d} to {df['Order Date'].max():%Y-%m-%d}",
}
pd.Series(quality).to_csv(OUT + "data_quality.csv", header=["Value"])

# 2. FEATURES
df["Margin %"] = df["Profit"] / df["Sales"] * 100
df["Month"] = df["Order Date"].dt.to_period("M").dt.to_timestamp()
df["Quarter"] = df["Order Date"].dt.to_period("Q").astype(str)
df["Weekday"] = df["Order Date"].dt.day_name()

# 3. KPIs
kpi = {
    "Revenue": df["Sales"].sum(), "Profit": df["Profit"].sum(),
    "Profit margin %": df["Profit"].sum() / df["Sales"].sum() * 100,
    "Orders": df["Order ID"].nunique(), "Units sold": df["Quantity"].sum(),
    "Avg order value": df["Sales"].sum() / df["Order ID"].nunique(),
    "Unique customers": df["Customer Name"].nunique(),
}
pd.Series(kpi).round(2).to_csv(OUT + "kpis.csv", header=["Value"])

def agg(by):
    g = df.groupby(by).agg(Revenue=("Sales", "sum"), Profit=("Profit", "sum"), Units=("Quantity", "sum"), Orders=("Order ID", "nunique"))
    g["Margin %"] = (g["Profit"] / g["Revenue"] * 100).round(1)
    g["Revenue share %"] = (g["Revenue"] / g["Revenue"].sum() * 100).round(1)
    return g.sort_values("Revenue", ascending=False)

by_cat, by_prod, by_reg, by_month = agg("Category"), agg("Product Name"), agg("Region"), agg("Month").sort_index()
by_state, by_sub = agg("State"), agg("Subcategory")
for name, t in [("category", by_cat), ("product", by_prod), ("region", by_reg), ("month", by_month)]:
    t.to_csv(OUT + f"by_{name}.csv")

# Customer segmentation (repeat buyers + top customers)
cust = df.groupby("Customer Name").agg(Revenue=("Sales", "sum"), Profit=("Profit", "sum"), Orders=("Order ID", "nunique")).sort_values("Revenue", ascending=False)
cust.to_csv(OUT + "by_customer.csv")
top10_share = cust["Revenue"].head(10).sum() / cust["Revenue"].sum() * 100
repeat_pct = (cust["Orders"] > 1).mean() * 100

# Pareto: products making up 80% revenue
cum = by_prod["Revenue"].cumsum() / by_prod["Revenue"].sum()
n80 = int((cum < 0.8).sum() + 1)

# Region x category matrix
pivot = df.pivot_table(index="Region", columns="Category", values="Sales", aggfunc="sum", fill_value=0)

# Quantity vs margin
qty_margin = df.groupby("Quantity")["Margin %"].mean().round(1)
corr = df[["Quantity", "Unit Price", "Sales", "Profit", "Margin %"]].corr().round(2)

# 4. CHARTS
def save(name): plt.tight_layout(); plt.savefig(CH + name); plt.close()

fig, ax = plt.subplots(figsize=(9, 4))
ax.bar(by_month.index, by_month["Revenue"], width=20, color=BLUE, label="Revenue")
ax.bar(by_month.index, by_month["Profit"], width=20, color=TEAL, label="Profit")
ax.yaxis.set_major_formatter(inr); ax.set_title("Monthly revenue and profit (2025)", loc="left", fontweight="bold"); ax.legend(frameon=False)
save("01_monthly_trend.png")

fig, ax = plt.subplots(figsize=(7, 4))
ax.barh(by_cat.index[::-1], by_cat["Revenue"][::-1], color=BLUE)
for i, (r, m) in enumerate(zip(by_cat["Revenue"][::-1], by_cat["Margin %"][::-1])): ax.text(r, i, f"  {m}% margin", va="center", fontsize=9)
ax.xaxis.set_major_formatter(inr); ax.set_title("Revenue by category (with profit margin)", loc="left", fontweight="bold"); ax.set_xlim(0, by_cat["Revenue"].max() * 1.25)
save("02_category.png")

fig, ax = plt.subplots(figsize=(8, 4.5))
ax.barh(by_prod.index[::-1], by_prod["Revenue"][::-1], color=BLUE)
ax.xaxis.set_major_formatter(inr); ax.set_title("Product ranking by revenue", loc="left", fontweight="bold")
save("03_products.png")

fig, ax = plt.subplots(figsize=(7, 4))
ax.bar(by_reg.index, by_reg["Revenue"], color=BLUE)
ax.yaxis.set_major_formatter(inr); ax.set_title("Revenue by region", loc="left", fontweight="bold")
for i, (r, p) in enumerate(zip(by_reg["Revenue"], by_reg["Revenue share %"])): ax.text(i, r, f"{p}%", ha="center", va="bottom", fontsize=9)
save("04_region.png")

fig, ax = plt.subplots(figsize=(7, 4))
im = ax.imshow(pivot.values, cmap="Blues"); ax.set_xticks(range(len(pivot.columns)), pivot.columns, rotation=30, ha="right"); ax.set_yticks(range(len(pivot.index)), pivot.index)
for i in range(pivot.shape[0]):
    for j in range(pivot.shape[1]): ax.text(j, i, f"{pivot.values[i,j]/1000:.0f}k", ha="center", va="center", fontsize=8)
ax.set_title("Revenue heatmap: region x category", loc="left", fontweight="bold"); ax.spines[:].set_visible(False)
save("05_region_category_heatmap.png")

fig, ax = plt.subplots(figsize=(8, 4.5))
sc = ax.scatter(by_prod["Revenue"], by_prod["Margin %"], s=by_prod["Units"] * 2, color=BLUE, alpha=.6)
for n, r in by_prod.iterrows(): ax.annotate(n, (r["Revenue"], r["Margin %"]), fontsize=8, xytext=(5, 4), textcoords="offset points")
ax.xaxis.set_major_formatter(inr); ax.set_xlabel("Revenue"); ax.set_ylabel("Margin %"); ax.set_title("Product revenue vs margin (bubble = units)", loc="left", fontweight="bold")
save("06_product_revenue_vs_margin.png")

fig, ax = plt.subplots(figsize=(8, 4))
ax.plot(range(1, len(cum) + 1), cum.values * 100, marker="o", color=BLUE); ax.axhline(80, ls="--", color=RED, lw=1)
ax.set_xlabel("Products (ranked)"); ax.set_ylabel("Cumulative revenue %"); ax.set_title("Pareto curve of product revenue", loc="left", fontweight="bold")
save("07_pareto.png")

# 5. INSIGHTS
best_m, worst_m = by_month["Revenue"].idxmax(), by_month["Revenue"].idxmin()
q = df.groupby("Quarter")["Sales"].sum()
ins = [
    f"Total revenue ₹{kpi['Revenue']:,.0f} with profit ₹{kpi['Profit']:,.0f} ({kpi['Profit margin %']:.1f}% margin) across {kpi['Orders']} orders.",
    f"Top category: {by_cat.index[0]} ({by_cat['Revenue share %'].iloc[0]}% of revenue). Highest-margin category: {by_cat['Margin %'].idxmax()} ({by_cat['Margin %'].max()}%); lowest: {by_cat['Margin %'].idxmin()} ({by_cat['Margin %'].min()}%).",
    f"Top product: {by_prod.index[0]} (₹{by_prod['Revenue'].iloc[0]:,.0f}). {n80} of {len(by_prod)} products generate 80% of revenue.",
    f"Top region: {by_reg.index[0]} ({by_reg['Revenue share %'].iloc[0]}%); weakest: {by_reg.index[-1]} ({by_reg['Revenue share %'].iloc[-1]}%).",
    f"Best month: {best_m:%b %Y} (₹{by_month['Revenue'].max():,.0f}); weakest: {worst_m:%b %Y} (₹{by_month['Revenue'].min():,.0f}).",
    f"Best quarter: {q.idxmax()} (₹{q.max():,.0f}); weakest: {q.idxmin()} (₹{q.min():,.0f}).",
    f"Customers: {kpi['Unique customers']} unique; {repeat_pct:.0f}% are repeat buyers; top 10 customers = {top10_share:.1f}% of revenue.",
    f"Average margin by quantity ranges from {qty_margin.min()}% to {qty_margin.max()}% - correlation of Quantity with Margin % is {corr.loc['Quantity','Margin %']}.",
]
open(OUT + "insights.txt", "w").write("\n".join(f"- {i}" for i in ins))
print("QUALITY"); [print(f"  {k}: {v}") for k, v in quality.items()]
print("KPI"); [print(f"  {k}: {v:,.2f}") for k, v in kpi.items()]
print("\nINSIGHTS"); [print(" -", i) for i in ins]
print("\n", by_cat, "\n", by_prod, "\n", by_reg, "\n", by_month, "\n", q, "\n", qty_margin)
