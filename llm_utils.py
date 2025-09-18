import os
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

def get_sql_chain(schema: str):
    template = f"""
    You are an expert SQLite query generator.

    You will be given:
    - The schema of a table named `uploaded_data`.
    - A natural language user question.

    Your task is to return a valid SQL query OR a simple yes/no/irrelevant message, following these rules:

    Rules:
    1. Output only the SQL query (no explanations, no backticks).
    2. The query must be valid for SQLite.
    3. Use only the table `uploaded_data`.
    4. Place ORDER BY after UNION ALL if present.
    5. For string comparisons, always use LOWER(column) LIKE LOWER('%value%').
    6. Use CASE when mapping short forms to full forms.
    7. If the question is yes/no:
       - Check the database condition.
       - Respond only with "Yes" or "No".
    8. If the question is irrelevant or unanswerable, respond: "Sorry, I can't answer that question based on the provided data."
    9. Always alias numeric calculations (e.g., AVG(col) AS avg_col).
    10. Always choose column names only from the given schema.

    Schema of uploaded_data: {schema}

    User Question: {{question}}
    SQL Query or Answer:
    """

    prompt = ChatPromptTemplate.from_template(template)
    llm = ChatGroq(
        model="llama-3.3-70b-versatile",  # ✅ supported model
        temperature=0,
        api_key=""
    )
    return prompt | llm



