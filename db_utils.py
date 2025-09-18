import sqlite3
import pandas as pd
import io
import time

db_path = "uploaded_excel.db"

def sanitize_column_names(columns):
    return [col.strip().replace(" ", "_").replace("-", "_").replace("'", "").lower() for col in columns]

def load_excel_to_sqlite(db_path, excel_file_path, table_name="uploaded_data"):
    conn = sqlite3.connect(db_path, check_same_thread=False)
    df = pd.read_excel(excel_file_path)
    df.columns = sanitize_column_names(df.columns)
    df.to_sql(table_name, conn, if_exists="replace", index=False)
    conn.close()
    return table_name, df.columns

def get_connection(db_path=db_path):
    return sqlite3.connect(db_path, check_same_thread=False)

def get_schema(db_path, table_name):
    conn = get_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info('{table_name}');")
    columns = [row[1] for row in cursor.fetchall()]
    conn.close()
    return columns

def run_query_with_retry(conn, query, retries=3, delay=1):
    for attempt in range(retries):
        try:
            cursor = conn.cursor()
            cursor.execute(query)
            column_names = [description[0] for description in cursor.description]
            result = cursor.fetchall()
            return pd.DataFrame(result, columns=column_names)
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e) and attempt < retries - 1:
                time.sleep(delay)
                continue
            else:
                return f"Error executing query: {e}"

def load_data_from_db(query):
    conn = get_connection(db_path)
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def export_table_to_excel_memory(db_path, table_name):
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
    conn.close()

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=table_name)
    output.seek(0)
    return output

def record_exists(conn, table_name, filters: dict):
    where_clause = " AND ".join([f"{col} = ?" for col in filters.keys()])
    query = f"SELECT 1 FROM {table_name} WHERE {where_clause} LIMIT 1"
    cursor = conn.cursor()
    cursor.execute(query, list(filters.values()))
    return cursor.fetchone() is not None
