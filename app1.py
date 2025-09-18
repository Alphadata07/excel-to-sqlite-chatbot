import streamlit as st
import pandas as pd
from db_utils import (
    load_excel_to_sqlite,
    get_schema,
    load_data_from_db,
    run_query_with_retry,
    get_connection,
    export_table_to_excel_memory,
    record_exists,
)
from llm_utils import get_sql_chain
from auth import authenticate

db_path = "uploaded_excel.db"
table_name = "uploaded_data"

# Streamlit Page Config
st.set_page_config(page_title="Excel to SQLite Chatbot", page_icon="📊")
st.title("📊 Excel to SQLite Chatbot")

# Initialize session state
if "role" not in st.session_state:
    st.session_state["role"] = None

# ----------------------------
# 🔐 Login Page
# ----------------------------
if st.session_state["role"] is None:
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        login_btn = st.form_submit_button("Login")

        if login_btn:
            role = authenticate(username, password)
            if role:
                st.session_state["role"] = role
                st.session_state["username"] = username
                st.success(f"Logged in as {username} ({role})")
                st.rerun()
            else:
                st.error("Invalid username or password")

# ----------------------------
# 🎯 Main Dashboard
# ----------------------------
else:
    st.write(f"Welcome, {st.session_state['username']}! (Role: {st.session_state['role']})")

    # Sidebar File Upload
    with st.sidebar:
        st.subheader("📂 Upload Excel")
        excel_file = st.file_uploader("Upload Excel", type=["xlsx", "xls"])
        if st.button("Load Data") and excel_file:
            with open(excel_file.name, "wb") as f:
                f.write(excel_file.read())
            table_name, _ = load_excel_to_sqlite(db_path, excel_file.name)
            st.success("✅ Data loaded successfully into SQLite!")
            st.rerun()

    # Show Table Data
    try:
        data = load_data_from_db(f"SELECT * FROM {table_name}")
        st.subheader("📄 Current Table Data")
        st.dataframe(data)
    except Exception as e:
        st.error(f"Error loading data: {e}")

    # ----------------------------
    # 💬 Ask a Question (LLM → SQL)
    # ----------------------------
    st.subheader("💬 Ask a Question")
    user_query = st.text_input("Enter your question:")

    if user_query:
        try:
            schema = get_schema(db_path, table_name)
            sql_chain = get_sql_chain(schema)
            generated = sql_chain.invoke({"question": user_query})
            query = generated.content.strip()

            if "sorry" in query.lower():
                st.warning(query)
            else:
                st.write(f"Generated SQL Query: {query}")
                result = run_query_with_retry(get_connection(db_path), query)

                if isinstance(result, pd.DataFrame):
                    if result.empty:
                        st.warning("No data found for this query.")
                    else:
                        st.dataframe(result)
                else:
                    st.error(result)
        except Exception as e:
            st.error(f"Error running query: {e}")

    # ----------------------------
    # 🔧 Admin CRUD Operations
    # ----------------------------
    if st.session_state["role"] == "admin":
        st.subheader("🔧 Admin Operations")
        columns = get_schema(db_path, table_name)

        # Insert
        with st.form("insert_form"):
            st.markdown("### ➕ Insert Record")
            form_data = {col: st.text_input(f"{col}", key=f"insert_{col}") for col in columns}
            insert_btn = st.form_submit_button("Insert Record")

            if insert_btn:
                col_names = ", ".join(columns)
                values = ", ".join([f"'{form_data[col]}'" for col in columns])
                query = f"INSERT INTO {table_name} ({col_names}) VALUES ({values})"

                conn = get_connection(db_path)
                conn.execute(query)
                conn.commit()
                conn.close()

                st.success("✅ Record inserted successfully!")
                st.rerun()

        # Update
        with st.form("update_form"):
            st.markdown("### ✏️ Update Record (with Filters)")

            filter_values = {}
            st.markdown("#### Filter Criteria")
            for col in columns:
                val = st.text_input(f"Filter by {col}", key=f"filter_{col}_update")
                if val:
                    filter_values[col] = val

            update_values = {}
            st.markdown("#### New Values")
            for col in columns:
                update_values[col] = st.text_input(f"New {col}", key=f"update_{col}")

            update_btn = st.form_submit_button("Update Record")

            if update_btn:
                if not filter_values:
                    st.error("⚠️ Please provide at least one filter condition.")
                else:
                    update_cols = [c for c in columns if update_values[c] != ""]
                    if not update_cols:
                        st.error("⚠️ Enter at least one value to update.")
                    else:
                        conn = get_connection(db_path)
                        if not record_exists(conn, table_name, filter_values):
                            st.warning("⚠️ No matching record found.")
                            conn.close()
                        else:
                            set_clause = ", ".join([f"{c} = ?" for c in update_cols])
                            where_clause = " AND ".join([f"{c} = ?" for c in filter_values.keys()])
                            query = f"UPDATE {table_name} SET {set_clause} WHERE {where_clause}"

                            conn.execute(query, [update_values[c] for c in update_cols] + list(filter_values.values()))
                            conn.commit()
                            conn.close()

                            st.success("✅ Record(s) updated successfully!")
                            st.rerun()

        # Delete
        with st.form("delete_form"):
            st.markdown("### 🗑️ Delete Record (with Filters)")

            delete_filters = {}
            for col in columns:
                val = st.text_input(f"Filter by {col}", key=f"filter_{col}_delete")
                if val:
                    delete_filters[col] = val

            delete_btn = st.form_submit_button("Delete Record")

            if delete_btn:
                if not delete_filters:
                    st.error("⚠️ Provide at least one filter to delete.")
                else:
                    conn = get_connection(db_path)
                    if not record_exists(conn, table_name, delete_filters):
                        st.warning("⚠️ No matching record found to delete.")
                        conn.close()
                    else:
                        where_clause = " AND ".join([f"{c} = ?" for c in delete_filters.keys()])
                        query = f"DELETE FROM {table_name} WHERE {where_clause}"

                        conn.execute(query, list(delete_filters.values()))
                        conn.commit()
                        conn.close()

                        st.success("✅ Record(s) deleted successfully!")
                        st.rerun()

    # ----------------------------
    # 📥 Download Updated Excel
    # ----------------------------
    st.subheader("📥 Download Updated Excel File")
    updated_excel = export_table_to_excel_memory(db_path, table_name)
    st.download_button("Download Excel", data=updated_excel, file_name="updated_file.xlsx")

    # ----------------------------
    # 🚪 Logout
    # ----------------------------
    if st.button("Logout"):
        st.session_state["role"] = None
        st.rerun()
