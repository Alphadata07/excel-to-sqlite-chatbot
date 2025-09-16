import sqlite3
import os
import pandas as pd
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
import streamlit as st
import io
import time

os.environ["GROQ_API_KEY"] = ""

USER_CREDENTIALS = {
    "admin": {"password": "admin123", "role": "admin"},
    "viewer": {"password": "viewer123", "role": "viewer"}
}

db_path = "uploaded_excel.db"

def sanitize_column_names(columns):     
    return [col.strip().replace(" ", "_").replace("-", "_").replace("'", "").lower() for col in columns]     

def load_excel_to_sqlite(db_path: str, excel_file_path, table_name="uploaded_data"): 
    conn = sqlite3.connect(db_path, check_same_thread=False)
    df = pd.read_excel(excel_file_path)
    df.columns = sanitize_column_names(df.columns)
    df.to_sql(table_name, conn, if_exists="replace", index=False)
    conn.close()
    return table_name, df.columns

def get_connection(db_path: str) -> sqlite3.Connection:
    return sqlite3.connect(db_path, check_same_thread=False)

def get_schema(db_path: str, table_name: str) -> list:
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info('{table_name}');")
    columns = [row[1] for row in cursor.fetchall()]  
    conn.close()
    return columns

def run_query_with_retry(conn, query: str, retries=3, delay=1):
    """A helper function to retry the query in case of database lock."""
    for attempt in range(retries):
        try:
            cursor = conn.cursor()
            cursor.execute(query)
            column_names = [description[0] for description in cursor.description]
            result = cursor.fetchall()
            return pd.DataFrame(result, columns=column_names)
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e) and attempt < retries - 1:
                time.sleep(delay)  # Wait for a short period before retrying
                continue
            else:
                return f"Error executing query: {e}"

def load_data_from_db(query: str):
    conn = get_connection(db_path)  
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def export_table_to_excel_memory(db_path, table_name):
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
    conn.close()

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name=table_name)

    output.seek(0)
    return output

def get_sql_chain(schema: str):
    template = f"""
        You are an expert data analyst. Generate a valid SQL query to answer user questions using the database schema provided below.

       The only table you can use is named 'uploaded_data'. Do not use any other table name in your query.

       Schema of the table 'uploaded_data': Schema: {schema}

        Follow these rules strictly:
        1. Write "only the SQL query" and nothing else.
        2. Do not add explanations or formatting like backticks.
        3. The query should be syntactically valid for a SQLite database.
        4. Place the ORDER BY after UNION ALL if present.
        5. The query should be case-insensitive for comparisons by using the LOWER() function.
        6. Use SQL patterns like LIKE '%keyword%' to match partial values dynamically.
        7. Use a CASE statement to map short forms to full forms dynamically.
        8. If the user's question is a yes/no question (e.g., "Is this record available?", "Do you have data on X?", "Can I update this record?"):
        - Do not generate an SQL query. Instead, respond with "Yes" or "No" based on the context.
        - If the question involves a specific condition, check the database for that condition (e.g., checking if a record exists) and return the appropriate response.
        - Use SQL queries where needed to check the database and generate a simple "Yes" or "No" based on the result.
        9. If a question is irrelevant, out-of-context, or not answerable from this data, reply: "Sorry, I can't answer that question based on the provided data."
        10. Always use case whenever query is using when int he sql query.

        User Question: {{question}}
        SQL Query:
    """
    prompt = ChatPromptTemplate.from_template(template)
    llm = ChatGroq(model="llama3-70b-8192", temperature=0, api_key=os.getenv("GROQ_API_KEY"))
    return prompt | llm

def record_exists(conn, table_name, filters: dict):
    where_clause = " AND ".join([f"{col} = ?" for col in filters.keys()])
    query = f"SELECT 1 FROM {table_name} WHERE {where_clause} LIMIT 1"
    cursor = conn.cursor()
    cursor.execute(query, list(filters.values()))
    return cursor.fetchone() is not None

#  Streamlit App Setup
st.set_page_config(page_title="Excel to SQLite Chatbot", page_icon="📊")
st.title("📊 Excel to SQLite Chatbot")

if "role" not in st.session_state:
    st.session_state["role"] = None

#  Sidebar File Upload
with st.sidebar:
    st.subheader("Upload Excel File")
    excel_file = st.file_uploader("Upload Excel", type=["xlsx", "xls"])
    
    if st.button("Load Data") and excel_file:
        with st.spinner("Loading Excel data..."):
            try:
                uploaded_excel_path = excel_file.name
                with open(uploaded_excel_path, "wb") as f:
                    f.write(excel_file.read())

                table_name, columns = load_excel_to_sqlite(db_path, uploaded_excel_path)

                st.session_state["excel_file_path"] = uploaded_excel_path
                st.session_state.table_name = table_name
                
                st.success(f"Data loaded successfully into table '{table_name}'!")

            except Exception as e:
                st.error(f"Error loading data: {e}")

#  Login Page
if st.session_state["role"] is None:
    with st.form(key="login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit_button = st.form_submit_button(label="Login")

        if submit_button:
            user = USER_CREDENTIALS.get(username)
            if user and user["password"] == password:
                st.session_state["role"] = user["role"]
                st.session_state["username"] = username
                st.success(f"Logged in as {username} ({user['role']})!")
                st.experimental_rerun()
            else:
                st.error("Invalid username or password")

#  After Login: Main Dashboard
if st.session_state["role"] is not None:
    user_role = st.session_state["role"]
    st.write(f"Welcome, {st.session_state['username']}! (Role: {user_role.capitalize()})")

    #  Display current data from SQLite
    table_name = "uploaded_data"
    query = f"SELECT * FROM {table_name}"

    try:
        data = load_data_from_db(query)
        st.subheader("📄 Current Table Data")
        st.dataframe(data)
    except Exception as e:
        st.error(f"Error retrieving data from table '{table_name}': {e}")

    #  Ask Question Section
    st.subheader("💬 Ask a Question")
    user_query = st.text_input("Enter your question:")
    
    if user_query:
        schema = get_schema(db_path, st.session_state.table_name)
        sql_chain = get_sql_chain(schema)

        generated_query = sql_chain.invoke({"question": user_query})
        query_text = generated_query.content.strip()

        if not query_text.lower().startswith("select") and "sorry" in query_text.lower():
            st.warning(query_text)
        else:
            fixed_query = query_text.replace("table_name", "uploaded_data")

            if "uploaded_data" not in fixed_query.lower():
                st.error("The generated query doesn't refer to the uploaded_data table.")
            else:
                st.write(f"Generated SQL Query: {fixed_query}")
                query_result = run_query_with_retry(get_connection(db_path), fixed_query)

                if isinstance(query_result, pd.DataFrame):
                    if query_result.empty:
                        st.warning("No data found matching your query.")
                    else:
                        st.dataframe(query_result)
                else:
                    st.error(query_result)

    #  Admin CRUD Operations
    if user_role == "admin":
        st.subheader("🔧 Admin Operations")

        columns = get_schema(db_path, st.session_state.table_name)

        #  Insert Data Form
        with st.form(key="insert_form"):
            form_data = {}
            for column in columns:
                form_data[column] = st.text_input(f"Enter value for {column}:", key=f"insert_{column}")
            
            insert_button = st.form_submit_button("Insert Record")
            if insert_button:
                column_names = ', '.join(columns)
                values = ', '.join([f"'{form_data[column]}'" for column in columns])
                insert_query = f"INSERT INTO {st.session_state.table_name} ({column_names}) VALUES ({values})"

                conn = get_connection(db_path)
                conn.execute(insert_query)
                conn.commit()
                conn.close()

                st.success("✅ Record inserted successfully!")
                st.experimental_rerun()

        #  Update Data Form with Multi-Column Filter
        with st.form(key="update_form"):
            st.subheader("🔧 Update Record (Multi-Column Filter)")

            # Filter columns selection
            st.markdown("### Filter Criteria")
            filter_values = {}
            for column in columns:
                val = st.text_input(f"Filter by {column} (leave blank to ignore):", key=f"filter_{column}_update")
                if val:
                    filter_values[column] = val

            st.markdown("### New Values to Update")
            update_values = {}
            for column in columns:
                update_values[column] = st.text_input(f"New value for {column} (leave blank to skip):", key=f"update_{column}")

            update_button = st.form_submit_button("Update Record")

            if update_button:
                update_columns = [column for column in columns if update_values[column] != ""]

                if not filter_values:
                    st.error("You must specify at least one filter column to identify records.")
                elif not update_columns:
                    st.error("Please enter at least one field to update.")
                else:
                    conn = get_connection(db_path)

                    if not record_exists(conn, st.session_state.table_name, filter_values):
                        st.warning("No matching records found to update.")
                        conn.close()
                    else:
                        set_clause = ", ".join([f"{column} = ?" for column in update_columns])
                        where_clause = " AND ".join([f"{col} = ?" for col in filter_values.keys()])
                        values = [update_values[column] for column in update_columns]

                        update_query = f"""
                            UPDATE {st.session_state.table_name}
                            SET {set_clause}
                            WHERE {where_clause}
                        """

                        conn.execute(update_query, values + list(filter_values.values()))
                        conn.commit()
                        conn.close()

                        st.success("✅ Record(s) updated successfully!")
                        st.experimental_rerun()

        #  Delete Data Form with Multi-Column Filter
        with st.form(key="delete_form"):
            st.subheader("🗑️ Delete Record (Multi-Column Filter)")

            delete_filters = {}
            for column in columns:
                val = st.text_input(f"Filter by {column} (leave blank to ignore):", key=f"filter_{column}_delete")
                if val:
                    delete_filters[column] = val

            delete_button = st.form_submit_button("Delete Record")

            if delete_button:
                if not delete_filters:
                    st.error("You must specify at least one filter column to identify records.")
                else:
                    conn = get_connection(db_path)

                    if not record_exists(conn, st.session_state.table_name, delete_filters):
                        st.warning("No matching records found to delete.")
                        conn.close()
                    else:
                        where_clause = " AND ".join([f"{col} = ?" for col in delete_filters.keys()])

                        delete_query = f"""
                            DELETE FROM {st.session_state.table_name}
                            WHERE {where_clause}
                        """

                        conn.execute(delete_query, list(delete_filters.values()))
                        conn.commit()
                        conn.close()

                        st.success("✅ Record(s) deleted successfully!")
                        st.experimental_rerun()

    #  Download Updated Excel Button
    st.subheader("📥 Download Updated Excel File")
    updated_excel = export_table_to_excel_memory(db_path, "uploaded_data")

    st.download_button(
        label="Download Updated Excel",
        data=updated_excel,
        file_name="updated_file.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    #  Logout Button
    if st.button("Logout"):
        st.session_state["role"] = None
        st.experimental_rerun()
