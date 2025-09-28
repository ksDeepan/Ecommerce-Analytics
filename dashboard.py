import streamlit as st
import pandas as pd
import pymysql
import plotly.express as px

# === Database Connection ===
def get_connection():
    return pymysql.connect(
        host="localhost",
        user="root",
        password="",          # Add your MySQL password if set
        database="ecommerce", # Make sure this DB exists
        port=3307             # XAMPP often runs MySQL on 3307
    )

# === Load Data ===
@st.cache_data
def load_data():
    conn = get_connection()
    try:
        query = """
        SELECT o.order_id, o.user_id, o.order_date, o.total_amount,
               p.product_name, p.category, od.quantity, od.price,
               pay.payment_method
        FROM Orders o
        JOIN OrderDetails od ON o.order_id = od.order_id
        JOIN Products p ON od.product_id = p.product_id
        LEFT JOIN Payments pay ON o.order_id = pay.order_id;
        """
        df = pd.read_sql(query, conn)
    except Exception:
        # fallback if Payments table/column is missing
        query = """
        SELECT o.order_id, o.user_id, o.order_date, o.total_amount,
               p.product_name, p.category, od.quantity, od.price
        FROM Orders o
        JOIN OrderDetails od ON o.order_id = od.order_id
        JOIN Products p ON od.product_id = p.product_id;
        """
        df = pd.read_sql(query, conn)
    conn.close()
    return df

df = load_data()

# Ensure correct datatypes
df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")

# === Sidebar Filters ===
st.sidebar.header("🔎 Filters")

date_range = st.sidebar.date_input("Select Date Range", [])

# 🔽 Category filter as dropdown
if "category" in df.columns:
    categories = df["category"].dropna().unique().tolist()
    category_filter = st.sidebar.selectbox("Filter by Category", ["All"] + categories)
else:
    category_filter = "All"

# 🔽 Payment method filter as dropdown
if "payment_method" in df.columns:
    payment_methods = df["payment_method"].dropna().unique().tolist()
    payment_filter = st.sidebar.selectbox("Filter by Payment Method", ["All"] + payment_methods)
else:
    payment_filter = "All"

auto_refresh = st.sidebar.checkbox("Auto-refresh every 1 min", value=False)

# === Apply Filters ===
if len(date_range) == 2:
    df = df[
        (df["order_date"] >= pd.to_datetime(date_range[0])) &
        (df["order_date"] <= pd.to_datetime(date_range[1]))
    ]

if category_filter != "All":
    df = df[df["category"] == category_filter]

if payment_filter != "All" and "payment_method" in df.columns:
    df = df[df["payment_method"] == payment_filter]

# === KPIs ===
st.title("📊 E-Commerce Sales Dashboard")

if not df.empty:
    total_revenue = df["total_amount"].sum()
    total_orders = df["order_id"].nunique()
    unique_customers = df["user_id"].nunique()
    avg_order_value = df["total_amount"].mean()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("💰 Total Revenue", f"${total_revenue:,.2f}")
    col2.metric("🛒 Total Orders", total_orders)
    col3.metric("👥 Unique Customers", unique_customers)
    col4.metric("📦 Avg Order Value", f"${avg_order_value:,.2f}")

    # === Charts ===
    st.subheader("📈 Revenue Trends")
    revenue_trend = df.groupby("order_date")["total_amount"].sum().reset_index()
    fig1 = px.line(revenue_trend, x="order_date", y="total_amount", title="Revenue Over Time")
    st.plotly_chart(fig1, use_container_width=True)

    st.subheader("🏆 Top Selling Products")
    top_products = (
        df.groupby("product_name")["quantity"]
        .sum()
        .reset_index()
        .sort_values(by="quantity", ascending=False)
        .head(10)
    )
    fig2 = px.bar(top_products, x="product_name", y="quantity", title="Top 10 Products")
    st.plotly_chart(fig2, use_container_width=True)

    st.subheader("📊 Revenue by Category")
    cat_rev = df.groupby("category")["total_amount"].sum().reset_index()
    fig3 = px.pie(cat_rev, names="category", values="total_amount", title="Revenue by Category")
    st.plotly_chart(fig3, use_container_width=True)

    # === Payment Method Distribution / Fallback ===
    if "payment_method" in df.columns:
        st.subheader("💳 Payment Method Distribution")
        pay_rev = df.groupby("payment_method")["total_amount"].sum().reset_index()
        if not pay_rev.empty:
            fig4 = px.pie(pay_rev, names="payment_method", values="total_amount", title="Revenue by Payment Method")
            st.plotly_chart(fig4, use_container_width=True)
        else:
            st.info("ℹ️ No payment method data found. Showing Top Customers instead.")
            top_customers = (
                df.groupby("user_id")["total_amount"]
                .sum()
                .reset_index()
                .sort_values(by="total_amount", ascending=False)
                .head(10)
            )
            fig5 = px.bar(top_customers, x="user_id", y="total_amount", title="Top 10 Customers by Spending")
            st.plotly_chart(fig5, use_container_width=True)
    else:
        st.info("ℹ️ Payment method column not available in this dataset.")

    # === Latest Orders Table ===
    st.subheader("🕒 Latest 10 Orders")
    latest_orders = df.sort_values(by="order_date", ascending=False).head(10)
    st.dataframe(latest_orders[["order_id", "user_id", "product_name", "quantity", "total_amount", "order_date"]])

    # === Export Data ===
    st.subheader("⬇️ Export Data")
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("Download CSV", csv, "ecommerce_report.csv", "text/csv")

else:
    st.warning("⚠️ No data available for the selected filters.")

# === Auto-refresh (optional) ===
if auto_refresh:
    st.experimental_autorefresh(interval=60*1000, key="refresh")
