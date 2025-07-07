import streamlit as st
import sqlite3
from datetime import datetime

# --- Database Initialization and Utilities ---
def init_db():
    """Initializes the database connection and creates tables if they don't exist.
    Stores connection and cursor in Streamlit's session state.
    Also seeds default admin, categories, and products if the database is empty.
    """
    if 'db_conn' not in st.session_state:
        # Connect to the SQLite database.
        # check_same_thread=False is important for Streamlit as it runs in multiple threads
        # and SQLite connections are not thread-safe by default.
        conn = sqlite3.connect('ample_bills.db', check_same_thread=False)
        c = conn.cursor()

        # Create tables if they do not already exist.
        # Each table definition includes its columns and primary/foreign key constraints.
        c.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            category_id INTEGER,
            price REAL,
            quantity INTEGER,
            image TEXT,
            FOREIGN KEY (category_id) REFERENCES categories(id)
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            contact TEXT,
            email TEXT
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS customer_products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER,
            product_id INTEGER,
            FOREIGN KEY (customer_id) REFERENCES customers(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS suppliers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            contact TEXT,
            email TEXT
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            customer_id INTEGER,
            total REAL
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS sale_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_id INTEGER,
            product_id INTEGER,
            quantity INTEGER,
            price_at_sale REAL,
            FOREIGN KEY (sale_id) REFERENCES sales(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            supplier_id INTEGER,
            total REAL
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS purchase_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            purchase_id INTEGER,
            product_id INTEGER,
            quantity INTEGER,
            price_at_purchase REAL,
            FOREIGN KEY (purchase_id) REFERENCES purchases(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            category TEXT,
            amount REAL,
            notes TEXT
        )''')
        conn.commit() # Commit changes to make sure tables are created

        # Store the connection and cursor in Streamlit's session state.
        # This ensures they persist across reruns without needing to reconnect.
        st.session_state.db_conn = conn
        st.session_state.db_cursor = c

        # Add a default 'admin' user if no users exist.
        # This prevents an error if the 'admin' user already exists due to UNIQUE constraint.
        try:
            c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", ("admin", "admin", "admin"))
            conn.commit()
        except sqlite3.IntegrityError:
            # If the admin user already exists, a sqlite3.IntegrityError will be raised.
            # We catch it and simply pass, as the goal is to ensure an admin exists.
            pass
        except Exception as e:
            # Catch any other unexpected errors during admin creation.
            st.error(f"Error adding default admin: {e}")

        # Seed initial categories if the categories table is empty.
        c.execute("SELECT COUNT(*) FROM categories")
        if c.fetchone()[0] == 0:
            c.execute("INSERT INTO categories (name) VALUES (?)", ("Processor",))
            c.execute("INSERT INTO categories (name) VALUES (?)", ("RAM Module",))
            conn.commit()

        # Seed initial products if the products table is empty.
        c.execute("SELECT COUNT(*) FROM products")
        if c.fetchone()[0] == 0:
            # Retrieve category IDs for seeding products, ensuring foreign key integrity.
            processor_cat_id = get_category_id_by_name("Processor")
            ram_cat_id = get_category_id_by_name("RAM Module")

            if processor_cat_id:
                c.execute("INSERT INTO products (name, category_id, price, quantity, image) VALUES (?,?,?,?,?)",
                          ("Intel Core i5-10400", processor_cat_id, 250.0, 10, "https://media.istockphoto.com/id/458247199/photo/intel-processor-core-i5-2500k.jpg?s=612x612&w=0&k=20&c=dFrBw5-hK6XuwZp00WnWIHmc3R1HW0vi277bhy9cTXQ="))
            if ram_cat_id:
                c.execute("INSERT INTO products (name, category_id, price, quantity, image) VALUES (?,?,?,?,?)",
                          ("Adata XPG Gammix D30 8GB DDR4", ram_cat_id, 80.0, 15, "https://eu-images.contentstack.com/v3/assets/blt5412ff9af9aef77f/bltfefe5aa70a916297/681da885dc3f69ef6845fcae/IQ-R_PROCESS_CPU.jpg?auto=webp&quality=100&format=jpg&disable=upscale&width=768"))
            conn.commit()

def get_category_id_by_name(category_name):
    """Retrieves the ID of a category by its name from the database."""
    c = st.session_state.db_cursor
    c.execute("SELECT id FROM categories WHERE name=?", (category_name,))
    result = c.fetchone()
    return result[0] if result else None

def login_user(username, password):
    """Authenticates a user against the 'users' table."""
    c = st.session_state.db_cursor
    c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
    return c.fetchone()

# --- Page Functions ---

def show_dashboard():
    """Displays the main dashboard with key metrics and stock alerts."""
    st.title("Welcome to Inventory!")
    c = st.session_state.db_cursor

    # Display key metrics using columns for a clean layout
    col1, col2, col3, col4 = st.columns(4)
    
    c.execute("SELECT COUNT(*) FROM customers")
    total_customers = c.fetchone()[0]
    col1.metric("Total Customers", total_customers)

    c.execute("SELECT COUNT(*) FROM suppliers")
    total_suppliers = c.fetchone()[0]
    col2.metric("Total Suppliers", total_suppliers)

    c.execute("SELECT SUM(total) FROM sales")
    total_sales = c.fetchone()[0] or 0 # Use 'or 0' to handle cases where SUM returns NULL (no sales yet)
    col3.metric("Total Sales", f"${total_sales:.2f}")

    c.execute("SELECT SUM(total) FROM purchases")
    total_purchase = c.fetchone()[0] or 0
    col4.metric("Total Purchases", f"${total_purchase:.2f}")

    st.subheader("Today's Summary")
    today = datetime.now().strftime("%Y-%m-%d")

    c.execute("SELECT SUM(total) FROM sales WHERE date=?", (today,))
    today_sales = c.fetchone()[0] or 0

    c.execute("SELECT SUM(total) FROM purchases WHERE date=?", (today,))
    today_purchase = c.fetchone()[0] or 0

    col5, col6 = st.columns(2)
    col5.metric("Sales Today", f"${today_sales:.2f}")
    col6.metric("Purchases Today", f"${today_purchase:.2f}")

    st.subheader("Monthly Summary")
    this_month = datetime.now().strftime("%Y-%m")

    c.execute("SELECT SUM(total) FROM sales WHERE date LIKE ?", (this_month + '%',))
    month_sales = c.fetchone()[0] or 0

    c.execute("SELECT SUM(total) FROM purchases WHERE date LIKE ?", (this_month + '%',))
    month_purchase = c.fetchone()[0] or 0

    col7, col8 = st.columns(2)
    col7.metric("Monthly Sales", f"${month_sales:.2f}")
    col8.metric("Monthly Purchases", f"${month_purchase:.2f}")

    st.subheader("Stock Alert - Low Quantity Products")
    # Fetch products with quantity 5 or less for a low stock alert
    c.execute("SELECT id, name, quantity FROM products WHERE quantity <= 5 ORDER BY quantity ASC")
    stock_alerts = c.fetchall()
    if stock_alerts:
        st.warning("The following products are running low on stock:")
        # Display alerts in a table for clarity
        st.table(stock_alerts)
    else:
        st.success("All products are well-stocked!")

def show_customer_management():
    """Manages adding and viewing customer records."""
    st.title("Customer Management")
    c = st.session_state.db_cursor
    conn = st.session_state.db_conn

    # Use tabs for different customer actions
    tabs = st.tabs(["Add Customer", "View Customers"])

    with tabs[0]:
        st.subheader("Add New Customer")
        # Use a Streamlit form for better input handling and clear_on_submit
        with st.form("add_customer_form", clear_on_submit=True):
            name = st.text_input("Customer Name", key="customer_name")
            contact = st.text_input("Contact Number", key="customer_contact")
            email = st.text_input("Email Address", key="customer_email")

            # Fetch categories to allow associating a product with the customer
            c.execute("SELECT id, name FROM categories")
            categories = c.fetchall()
            category_dict = {cat[1]: cat[0] for cat in categories} # Map category name to ID

            category_choice = None
            if not categories:
                st.warning("Please add some categories first in 'Category' section to link products.")
            else:
                category_names = [cat[1] for cat in categories]
                # Allow user to select a category
                category_choice = st.selectbox("Select Category for Product", category_names, key="product_category_select")

            products = []
            selected_product_id = None
            if category_choice:
                category_id = category_dict[category_choice]
                # Fetch products based on the selected category
                c.execute("SELECT id, name, image FROM products WHERE category_id=?", (category_id,))
                products = c.fetchall()

            product_info_dict = {prod[1]: {"id": prod[0], "image": prod[2]} for prod in products}

            if products:
                product_choice = st.selectbox("Select Product to Associate", list(product_info_dict.keys()), key="product_select")
                if product_choice:
                    selected_product_id = product_info_dict[product_choice]["id"]
                    # Display product image for the selected product
                    st.image(product_info_dict[product_choice]["image"], width=150, caption=product_choice)
            else:
                st.info(f"No products found for category '{category_choice}'. Please add products or select another category.")

            submitted = st.form_submit_button("Add Customer")
            if submitted:
                if name and contact and email:
                    try:
                        # Insert new customer record
                        c.execute("INSERT INTO customers (name, contact, email) VALUES (?,?,?)", (name, contact, email))
                        customer_id = c.lastrowid # Get the ID of the newly inserted customer
                        
                        # Associate product if one was selected
                        if selected_product_id:
                            c.execute("INSERT INTO customer_products (customer_id, product_id) VALUES (?,?)", (customer_id, selected_product_id))
                        
                        conn.commit()
                        st.success(f"Customer '{name}' added successfully! {'Product associated.' if selected_product_id else ''}")
                        st.rerun() # Rerun to clear the form and update the "View Customers" tab
                    except sqlite3.Error as e:
                        st.error(f"Error adding customer: {e}")
                else:
                    st.warning("Please fill in all customer details.")

    with tabs[1]:
        st.subheader("Existing Customers")
        # SQL query to fetch customer details and their associated products (if any)
        c.execute("""
            SELECT
                c.id,
                c.name,
                c.contact,
                c.email,
                GROUP_CONCAT(p.name, ', ') AS associated_products -- Concatenate product names
            FROM customers c
            LEFT JOIN customer_products cp ON c.id = cp.customer_id
            LEFT JOIN products p ON p.id = cp.product_id
            GROUP BY c.id, c.name, c.contact, c.email
            ORDER BY c.name ASC
        """)
        customers_data = c.fetchall()

        if customers_data:
            # Prepare data for display in a Streamlit dataframe
            columns = ["ID", "Name", "Contact", "Email", "Associated Products"]
            # Convert fetched rows to a list of dictionaries for better column naming in dataframe
            df_customers = [dict(zip(columns, row)) for row in customers_data]
            st.dataframe(df_customers, use_container_width=True)
        else:
            st.info("No customers added yet.")

def show_supplier_management():
    """Manages adding and viewing supplier records."""
    st.title("Supplier Management")
    c = st.session_state.db_cursor
    conn = st.session_state.db_conn

    tabs = st.tabs(["Add Supplier", "View Suppliers"])

    with tabs[0]:
        st.subheader("Add New Supplier")
        with st.form("add_supplier_form", clear_on_submit=True):
            name = st.text_input("Supplier Name", key="supplier_name")
            contact = st.text_input("Contact Number", key="supplier_contact")
            email = st.text_input("Email Address", key="supplier_email")
            
            submitted = st.form_submit_button("Add Supplier")
            if submitted:
                if name and contact and email:
                    try:
                        c.execute("INSERT INTO suppliers (name, contact, email) VALUES (?,?,?)", (name, contact, email))
                        conn.commit()
                        st.success(f"Supplier '{name}' added successfully!")
                        st.rerun()
                    except sqlite3.Error as e:
                        st.error(f"Error adding supplier: {e}")
                else:
                    st.warning("Please fill in all supplier details.")

    with tabs[1]:
        st.subheader("Existing Suppliers")
        c.execute("SELECT id, name, contact, email FROM suppliers ORDER BY name ASC")
        suppliers_data = c.fetchall()
        if suppliers_data:
            columns = ["ID", "Name", "Contact", "Email"]
            df_suppliers = [dict(zip(columns, row)) for row in suppliers_data]
            st.dataframe(df_suppliers, use_container_width=True)
        else:
            st.info("No suppliers added yet.")

def show_category_management():
    """Manages adding and viewing product categories."""
    st.title("Category Management")
    c = st.session_state.db_cursor
    conn = st.session_state.db_conn

    tabs = st.tabs(["Add Category", "View Categories"])

    with tabs[0]:
        st.subheader("Add New Category")
        category_name = st.text_input("Category Name", key="new_category_name")
        if st.button("Add Category"):
            if category_name:
                try:
                    c.execute("INSERT INTO categories (name) VALUES (?)", (category_name,))
                    conn.commit()
                    st.success(f"Category '{category_name}' added successfully!")
                    st.rerun() # Rerun to update the "View Categories" tab
                except sqlite3.IntegrityError:
                    st.error(f"Category '{category_name}' already exists.")
                except sqlite3.Error as e:
                    st.error(f"Error adding category: {e}")
            else:
                st.warning("Please enter a category name.")

    with tabs[1]:
        st.subheader("Existing Categories")
        c.execute("SELECT id, name FROM categories ORDER BY name ASC")
        categories = c.fetchall()
        if categories:
            # Display categories in a dataframe
            st.dataframe(categories, use_container_width=True, hide_index=True, column_order=("id", "name"))
        else:
            st.info("No categories added yet.")

def show_products_management():
    """Manages adding, viewing, and updating product records."""
    st.title("Product Management (Stock)")
    c = st.session_state.db_cursor
    conn = st.session_state.db_conn

    tabs = st.tabs(["Add Product", "View Products", "Update Product Stock"])

    with tabs[0]:
        st.subheader("Add New Product")
        with st.form("add_product_form", clear_on_submit=True):
            name = st.text_input("Product Name", key="product_name_add")
            price = st.number_input("Price", min_value=0.01, format="%.2f", key="product_price_add")
            quantity = st.number_input("Quantity", min_value=0, step=1, key="product_quantity_add")
            image_url = st.text_input("Image URL (optional)", key="product_image_add")

            c.execute("SELECT id, name FROM categories")
            categories = c.fetchall()
            category_dict = {cat[1]: cat[0] for cat in categories}
            
            category_choice = None
            if not categories:
                st.warning("Please add some categories first in 'Category' section.")
            else:
                category_names = [cat[1] for cat in categories]
                category_choice = st.selectbox("Select Category", category_names, key="product_category_add")

            submitted = st.form_submit_button("Add Product")
            if submitted:
                if name and price is not None and quantity is not None and category_choice:
                    try:
                        category_id = category_dict[category_choice]
                        c.execute("INSERT INTO products (name, category_id, price, quantity, image) VALUES (?,?,?,?,?)",
                                  (name, category_id, price, quantity, image_url if image_url else None))
                        conn.commit()
                        st.success(f"Product '{name}' added successfully!")
                        st.rerun()
                    except sqlite3.Error as e:
                        st.error(f"Error adding product: {e}")
                else:
                    st.warning("Please fill in all required product details (Name, Price, Quantity, Category).")

    with tabs[1]:
        st.subheader("Existing Products")
        c.execute("""
            SELECT
                p.id,
                p.name,
                c.name AS category_name,
                p.price,
                p.quantity,
                p.image
            FROM products p
            JOIN categories c ON p.category_id = c.id
            ORDER BY p.name ASC
        """)
        products_data = c.fetchall()
        if products_data:
            columns = ["ID", "Name", "Category", "Price", "Quantity", "Image URL"]
            df_products = [dict(zip(columns, row)) for row in products_data]
            st.dataframe(df_products, use_container_width=True)
        else:
            st.info("No products added yet.")

    with tabs[2]:
        st.subheader("Update Existing Product Stock")
        c.execute("SELECT id, name, quantity FROM products ORDER BY name ASC")
        current_products = c.fetchall()
        product_options = {f"{p[1]} (Current Stock: {p[2]})": p[0] for p in current_products}

        if not product_options:
            st.info("No products available to update stock.")
        else:
            selected_product_option = st.selectbox("Select Product to Update", list(product_options.keys()), key="update_product_select")
            selected_product_id = product_options[selected_product_option]

            c.execute("SELECT quantity FROM products WHERE id=?", (selected_product_id,))
            current_quantity = c.fetchone()[0]

            col_stock_update1, col_stock_update2 = st.columns(2)
            new_quantity = col_stock_update1.number_input(f"New Quantity for {selected_product_option.split('(')[0].strip()}", 
                                                      min_value=0, value=current_quantity, step=1, key="new_quantity_input")
            
            if col_stock_update2.button("Update Stock", key="update_stock_button"):
                try:
                    c.execute("UPDATE products SET quantity=? WHERE id=?", (new_quantity, selected_product_id))
                    conn.commit()
                    st.success(f"Stock for '{selected_product_option.split('(')[0].strip()}' updated to {new_quantity}.")
                    st.rerun()
                except sqlite3.Error as e:
                    st.error(f"Error updating stock: {e}")

def show_sales_module():
    """Handles recording sales, updating stock, and customer purchases."""
    st.title("Sales Module")
    c = st.session_state.db_cursor
    conn = st.session_state.db_conn

    if 'current_sale_items' not in st.session_state:
        st.session_state.current_sale_items = [] # Stores products added to the current sale

    # Tabs for "Create New Sale" and "View Past Sales"
    sale_tabs = st.tabs(["Create New Sale", "View Past Sales"])

    with sale_tabs[0]: # Create New Sale tab
        st.subheader("Create New Sale")

        # Select Customer for the Sale
        c.execute("SELECT id, name FROM customers ORDER BY name ASC")
        customers = c.fetchall()
        customer_options = {c[1]: c[0] for c in customers}
        
        selected_customer_name = st.selectbox("Select Customer", ["--- Select a Customer ---"] + list(customer_options.keys()), key="sale_customer_select")
        selected_customer_id = customer_options.get(selected_customer_name)

        st.markdown("---")
        st.subheader("Add Products to Sale")

        # Select Category to filter products
        c.execute("SELECT id, name FROM categories ORDER BY name ASC")
        categories = c.fetchall()
        category_dict = {cat[1]: cat[0] for cat in categories}

        selected_category_name = st.selectbox("Filter Products by Category", ["--- All Categories ---"] + list(category_dict.keys()), key="sale_category_filter")
        selected_category_id = category_dict.get(selected_category_name)

        # Fetch products based on selected category or all products
        products = []
        if selected_category_id:
            c.execute("SELECT id, name, price, quantity FROM products WHERE category_id=? AND quantity > 0 ORDER BY name ASC", (selected_category_id,))
        else:
            c.execute("SELECT id, name, price, quantity FROM products WHERE quantity > 0 ORDER BY name ASC") # Only show in-stock products
        products = c.fetchall()
        
        product_options_for_select = {f"{p[1]} (${p[2]:.2f} - Stock: {p[3]})": p for p in products}

        col_product_select, col_product_qty = st.columns([3, 1])
        selected_product_option = col_product_select.selectbox("Select Product", ["--- Select a Product ---"] + list(product_options_for_select.keys()), key="product_to_add_sale")
        
        product_to_add_data = None
        if selected_product_option and selected_product_option != "--- Select a Product ---":
            product_to_add_data = product_options_for_select[selected_product_option]
            # product_to_add_data is (id, name, price, quantity)
            available_stock = product_to_add_data[3]
            quantity_to_add = col_product_qty.number_input("Quantity", min_value=1, max_value=available_stock, step=1, key="sale_qty_input")
        else:
            quantity_to_add = 0 # Default if no product selected

        if st.button("Add to Cart", key="add_to_cart_button"):
            if product_to_add_data and quantity_to_add > 0:
                product_id, product_name, product_price, _ = product_to_add_data
                
                # Check if product is already in cart, update quantity if so
                found_in_cart = False
                for item in st.session_state.current_sale_items:
                    if item['product_id'] == product_id:
                        item['quantity'] += quantity_to_add
                        item['total'] = item['quantity'] * item['price_at_sale']
                        found_in_cart = True
                        break
                
                if not found_in_cart:
                    st.session_state.current_sale_items.append({
                        'product_id': product_id,
                        'name': product_name,
                        'price_at_sale': product_price,
                        'quantity': quantity_to_add,
                        'total': product_price * quantity_to_add
                    })
                st.success(f"Added {quantity_to_add} x {product_name} to cart.")
            else:
                st.warning("Please select a product and a valid quantity to add to cart.")
        
        st.markdown("---")
        st.subheader("Current Cart")
        
        if st.session_state.current_sale_items:
            cart_total = sum(item['total'] for item in st.session_state.current_sale_items)
            st.dataframe(st.session_state.current_sale_items, use_container_width=True)
            st.markdown(f"**Cart Total: ${cart_total:.2f}**")

            if st.button("Complete Sale", key="complete_sale_button"):
                if selected_customer_id:
                    try:
                        # 1. Record the main sale transaction
                        sale_date = datetime.now().strftime("%Y-%m-%d")
                        c.execute("INSERT INTO sales (date, customer_id, total) VALUES (?,?,?)", (sale_date, selected_customer_id, cart_total))
                        sale_id = c.lastrowid

                        # 2. Record each item in the sale_items table and update product stock
                        for item in st.session_state.current_sale_items:
                            c.execute("INSERT INTO sale_items (sale_id, product_id, quantity, price_at_sale) VALUES (?,?,?,?)",
                                      (sale_id, item['product_id'], item['quantity'], item['price_at_sale']))
                            
                            # Update product quantity in stock
                            c.execute("UPDATE products SET quantity = quantity - ? WHERE id = ?", (item['quantity'], item['product_id']))
                        
                        conn.commit()
                        st.success(f"Sale completed successfully for customer {selected_customer_name}! Total: ${cart_total:.2f}")
                        st.session_state.current_sale_items = [] # Clear cart after successful sale
                        st.rerun() # Refresh to clear form and update dashboard metrics
                    except sqlite3.Error as e:
                        st.error(f"Error completing sale: {e}")
                else:
                    st.warning("Please select a customer before completing the sale.")
        else:
            st.info("Your cart is empty. Add products to start a sale.")

    with sale_tabs[1]: # View Past Sales tab
        st.subheader("Past Sales Records")
        c.execute("""
            SELECT 
                s.id,
                s.date,
                cust.name AS customer_name,
                GROUP_CONCAT(p.name || ' (x' || si.quantity || ')', '; ') AS products_sold,
                s.total
            FROM sales s
            JOIN customers cust ON s.customer_id = cust.id
            LEFT JOIN sale_items si ON s.id = si.sale_id
            LEFT JOIN products p ON si.product_id = p.id
            GROUP BY s.id, s.date, cust.name, s.total
            ORDER BY s.date DESC, s.id DESC
        """)
        past_sales = c.fetchall()

        if past_sales:
            columns = ["Sale ID", "Date", "Customer Name", "Products Sold", "Total ($)"]
            df_past_sales = [dict(zip(columns, row)) for row in past_sales]
            st.dataframe(df_past_sales, use_container_width=True)
        else:
            st.info("No sales records found yet.")

def show_purchase_module():
    """Handles recording purchases, updating stock, and supplier purchases."""
    st.title("Purchase Module")
    c = st.session_state.db_cursor
    conn = st.session_state.db_conn

    if 'current_purchase_items' not in st.session_state:
        st.session_state.current_purchase_items = [] # Stores products added to the current purchase

    # Tabs for "Create New Purchase Order" and "View Past Purchases"
    purchase_tabs = st.tabs(["Create New Purchase Order", "View Past Purchases"])

    with purchase_tabs[0]: # Create New Purchase Order tab
        st.subheader("Create New Purchase Order")

        # Select Supplier for the Purchase
        c.execute("SELECT id, name FROM suppliers ORDER BY name ASC")
        suppliers = c.fetchall()
        supplier_options = {s[1]: s[0] for s in suppliers}
        
        selected_supplier_name = st.selectbox("Select Supplier", ["--- Select a Supplier ---"] + list(supplier_options.keys()), key="purchase_supplier_select")
        selected_supplier_id = supplier_options.get(selected_supplier_name)

        st.markdown("---")
        st.subheader("Add Products to Purchase Order")

        # Select Category to filter products (optional, can show all products too)
        c.execute("SELECT id, name FROM categories ORDER BY name ASC")
        categories = c.fetchall()
        category_dict = {cat[1]: cat[0] for cat in categories}

        selected_category_name = st.selectbox("Filter Products by Category", ["--- All Categories ---"] + list(category_dict.keys()), key="purchase_category_filter")
        selected_category_id = category_dict.get(selected_category_name)

        # Fetch products based on selected category or all products
        products = []
        if selected_category_id:
            c.execute("SELECT id, name, price, quantity FROM products WHERE category_id=? ORDER BY name ASC", (selected_category_id,))
        else:
            c.execute("SELECT id, name, price, quantity FROM products ORDER BY name ASC")
        products = c.fetchall()
        
        product_options_for_select = {f"{p[1]} (Current Price: ${p[2]:.2f} - Stock: {p[3]})": p for p in products}

        col_product_select_pur, col_product_qty_pur, col_unit_cost_pur = st.columns([3, 1, 1])
        selected_product_option_pur = col_product_select_pur.selectbox("Select Product", ["--- Select a Product ---"] + list(product_options_for_select.keys()), key="product_to_add_purchase")
        
        product_to_add_data_pur = None
        if selected_product_option_pur and selected_product_option_pur != "--- Select a Product ---":
            product_to_add_data_pur = product_options_for_select[selected_product_option_pur]
            # product_to_add_data_pur is (id, name, price, quantity)
            quantity_to_add_pur = col_product_qty_pur.number_input("Quantity", min_value=1, step=1, key="purchase_qty_input")
            # Allow user to specify purchase price, defaulting to current product price
            purchase_price = col_unit_cost_pur.number_input("Unit Cost", min_value=0.01, value=float(product_to_add_data_pur[2]), format="%.2f", key="purchase_price_input")
        else:
            quantity_to_add_pur = 0
            purchase_price = 0.0

        if st.button("Add to Purchase List", key="add_to_purchase_list_button"):
            if product_to_add_data_pur and quantity_to_add_pur > 0 and purchase_price > 0:
                product_id, product_name, _, _ = product_to_add_data_pur
                
                # Check if product is already in list, update quantity if so
                found_in_list = False
                for item in st.session_state.current_purchase_items:
                    if item['product_id'] == product_id:
                        item['quantity'] += quantity_to_add_pur
                        item['total'] = item['quantity'] * item['price_at_purchase']
                        found_in_list = True
                        break
                
                if not found_in_list:
                    st.session_state.current_purchase_items.append({
                        'product_id': product_id,
                        'name': product_name,
                        'price_at_purchase': purchase_price,
                        'quantity': quantity_to_add_pur,
                        'total': purchase_price * quantity_to_add_pur
                    })
                st.success(f"Added {quantity_to_add_pur} x {product_name} to purchase list.")
            else:
                st.warning("Please select a product, quantity, and unit cost to add to purchase list.")
        
        st.markdown("---")
        st.subheader("Current Purchase Order")
        
        if st.session_state.current_purchase_items:
            purchase_total = sum(item['total'] for item in st.session_state.current_purchase_items)
            st.dataframe(st.session_state.current_purchase_items, use_container_width=True)
            st.markdown(f"**Purchase Order Total: ${purchase_total:.2f}**")

            if st.button("Complete Purchase", key="complete_purchase_button"):
                if selected_supplier_id:
                    try:
                        # 1. Record the main purchase transaction
                        purchase_date = datetime.now().strftime("%Y-%m-%d")
                        c.execute("INSERT INTO purchases (date, supplier_id, total) VALUES (?,?,?)", (purchase_date, selected_supplier_id, purchase_total))
                        purchase_id = c.lastrowid

                        # 2. Record each item in the purchase_items table and update product stock
                        for item in st.session_state.current_purchase_items:
                            c.execute("INSERT INTO purchase_items (purchase_id, product_id, quantity, price_at_purchase) VALUES (?,?,?,?)",
                                      (purchase_id, item['product_id'], item['quantity'], item['price_at_purchase']))
                            
                            # Update product quantity in stock (add to stock)
                            c.execute("UPDATE products SET quantity = quantity + ? WHERE id = ?", (item['quantity'], item['product_id']))
                        
                        conn.commit()
                        st.success(f"Purchase completed successfully from supplier {selected_supplier_name}! Total: ${purchase_total:.2f}")
                        st.session_state.current_purchase_items = [] # Clear purchase list
                        st.rerun() # Refresh to clear form and update dashboard metrics
                    except sqlite3.Error as e:
                        st.error(f"Error completing purchase: {e}")
                else:
                    st.warning("Please select a supplier before completing the purchase.")
        else:
            st.info("Your purchase list is empty. Add products to create a purchase order.")

    with purchase_tabs[1]: # View Past Purchases tab
        st.subheader("Past Purchase Records")
        c.execute("""
            SELECT 
                pu.id,
                pu.date,
                sup.name AS supplier_name,
                GROUP_CONCAT(p.name || ' (x' || pi.quantity || ')', '; ') AS products_purchased,
                pu.total
            FROM purchases pu
            JOIN suppliers sup ON pu.supplier_id = sup.id
            LEFT JOIN purchase_items pi ON pu.id = pi.purchase_id
            LEFT JOIN products p ON pi.product_id = p.id
            GROUP BY pu.id, pu.date, sup.name, pu.total
            ORDER BY pu.date DESC, pu.id DESC
        """)
        past_purchases = c.fetchall()

        if past_purchases:
            columns = ["Purchase ID", "Date", "Supplier Name", "Products Purchased", "Total ($)"]
            df_past_purchases = [dict(zip(columns, row)) for row in past_purchases]
            st.dataframe(df_past_purchases, use_container_width=True)
        else:
            st.info("No purchase records found yet.")

# --- Main Application Logic ---

# Initialize database connection and tables. This runs only once per session.
init_db()

# --- Session State Initialization for Login and Navigation ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.role = None
    st.session_state.menu_selection = "Dashboard" # Default menu selection

# --- Login Page ---
if not st.session_state.logged_in:
    # Custom CSS for the login page to center content and apply basic styling
    st.markdown(
        """
        <style>
        .stApp {
            background-color: #f0f2f6; /* Light gray background */
            font-family: 'Inter', sans-serif; /* Use Inter font */
        }
        .stTextInput > div > div > input, .stTextInput > label, .stButton button {
            border-radius: 0.5rem; /* Rounded corners for inputs and buttons */
        }
        .stButton button {
            background-color: #4CAF50; /* Green button */
            color: white;
            border: none;
            padding: 0.8rem 1.2rem;
            font-size: 1rem;
            box-shadow: 2px 2px 5px rgba(0,0,0,0.2); /* Subtle shadow */
            cursor: pointer;
        }
        .stButton button:hover {
            background-color: #45a049; /* Darker green on hover */
            transform: translateY(-1px); /* Slight lift effect */
            box-shadow: 3px 3px 6px rgba(0,0,0,0.3);
        }
        .stTitle, .stSubheader {
            text-align: center;
            color: #333;
        }
        /* Centering the login form */
        .block-container {
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 80vh; /* Adjust as needed */
        }
        .centered-form {
            background-color: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 5px 5px 15px rgba(0,0,0,0.1);
            width: 100%;
            max-width: 400px;
        }
        </style>
        """,
        unsafe_allow_html=True
    )
    
    # Create a centered column for the login form
    col_login_spacer1, col_login_form, col_login_spacer2 = st.columns([1, 2, 1]) 
    with col_login_form:
        st.markdown('<div class="centered-form">', unsafe_allow_html=True) # Apply custom class for styling
        st.title("Sajilo")
        st.subheader("Inventory & Billing System Login")
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        if st.button("Login", key="login_button"):
            user = login_user(username, password)
            if user:
                st.session_state.logged_in = True
                st.session_state.role = user[3]
                st.success("Logged in successfully! Redirecting...")
                st.rerun() # Use st.rerun() to immediately update the app state
            else:
                st.error("Invalid credentials. Please try again.")
        st.markdown('</div>', unsafe_allow_html=True) # Close custom class div
    
    st.stop() # Stop execution if user is not logged in

# --- Main Application (Logged In) ---
# Custom CSS for the main application layout and sidebar
st.markdown(
    """
    <style>
    .stApp {
        background-color: #f0f2f6; /* Light gray background */
        font-family: 'Inter', sans-serif;
    }
    .stSidebar {
        background-color: #e0e0e0; /* Slightly darker gray for sidebar */
        padding-top: 20px;
        border-radius: 0 10px 10px 0; /* Rounded right corners for sidebar */
        box-shadow: 2px 0px 5px rgba(0,0,0,0.1);
    }
    .stRadio > label > div {
        font-size: 1.1em;
        font-weight: bold;
        padding: 8px 0;
        color: #333;
    }
    .stRadio div[role="radiogroup"] label {
        margin-bottom: 0.5rem;
    }
    .stRadio div[role="radiogroup"] label:hover {
        background-color: #d0d0d0; /* Light hover effect for sidebar items */
        border-radius: 0.3rem;
    }
    .stRadio div[role="radiogroup"] label[data-baseweb="radio"] {
        padding: 5px 10px;
    }
    .stRadio div[role="radiogroup"] label[data-baseweb="radio"] span {
        margin-left: 0.5rem; /* Space between radio button and text */
    }
    h1, h2, h3, h4, h5, h6 {
        color: #2c3e50; /* Darker headings */
    }
    .stMetric {
        background-color: white;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 1px 1px 3px rgba(0,0,0,0.1);
    }
    .stAlert {
        border-radius: 8px;
    }
    .stTable, .stDataFrame {
        border-radius: 8px;
        box-shadow: 1px 1px 3px rgba(0,0,0,0.05);
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #f0f2f6;
        border-radius: 4px 4px 0 0;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
        padding-left: 10px;
        padding-right: 10px;
        line-height: 1.25;
        font-weight: 500;
        border-bottom: 2px solid transparent;
        color: #555;
    }
    .stTabs [aria-selected="true"] {
        background-color: white;
        border-bottom: 2px solid #4CAF50; /* Highlight color for active tab */
        color: #2c3e50;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Sidebar content
st.sidebar.image("/Users/manish shrestha/Desktop/TryProj/pic/Unknown.png", width=180, use_column_width=False, caption="SAJILO")
st.sidebar.markdown("---") # Separator for visual clarity

# Sidebar navigation radio buttons.
# The 'index' argument ensures the correct radio button is selected on rerun.
menu = st.sidebar.radio("Navigation",
                        ["Dashboard", "Customer", "Supplier", "Category", "Products", "Sells", "Purchase", "Logout"],
                        key="main_navigation",
                        index=["Dashboard", "Customer", "Supplier", "Category", "Products", "Sells", "Purchase", "Logout"].index(st.session_state.get('menu_selection', 'Dashboard')))

# Update the session state with the current menu selection
st.session_state.menu_selection = menu

# Handle Logout separately as it changes session state and reruns
if st.session_state.menu_selection == "Logout":
    st.session_state.logged_in = False
    st.session_state.role = None
    st.session_state.menu_selection = "Dashboard" # Reset menu to dashboard after logout
    st.success("You have been successfully logged out!")
    st.rerun() # Use st.rerun() to refresh the app to the login page

# Display content based on the selected menu item using if/elif blocks
if st.session_state.menu_selection == "Dashboard":
    show_dashboard()
elif st.session_state.menu_selection == "Customer":
    show_customer_management()
elif st.session_state.menu_selection == "Supplier":
    show_supplier_management()
elif st.session_state.menu_selection == "Category":
    show_category_management()
elif st.session_state.menu_selection == "Products": # Renamed from Stock
    show_products_management()
elif st.session_state.menu_selection == "Sells":
    show_sales_module()
elif st.session_state.menu_selection == "Purchase":
    show_purchase_module()
# Removed Expense, Reports, Staff, Settings as per user's request.

# Do NOT close the database connection here (conn.close()).
# Streamlit reruns the script from top to bottom on every user interaction.
# Closing the connection here would lead to "database is locked" or
# "cannot operate on a closed database" errors on subsequent interactions.
# The connection is managed via st.session_state and persists for the session.
