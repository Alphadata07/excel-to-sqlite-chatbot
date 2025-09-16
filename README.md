# 📊 Excel to SQLite Chatbot  

A **Streamlit-based chatbot** that allows users to upload Excel files, store them in an SQLite database, and interact with the data using **natural language queries**. The chatbot uses **LangChain + Groq LLM** to generate SQL queries automatically and supports **admin CRUD operations** with authentication.  

---

## 🚀 Features  

- **Excel to SQLite conversion**  
  - Upload Excel (`.xlsx`, `.xls`) files.  
  - Automatically stores the data in an SQLite database (`uploaded_excel.db`).  

- **Natural Language to SQL**  
  - Ask questions in plain English.  
  - LangChain + Groq LLM generates SQL queries dynamically.  
  - Case-insensitive and partial search supported using `LOWER()` and `LIKE`.  

- **Authentication System**  
  - **Admin Role**: Can insert, update, delete records.  
  - **Viewer Role**: Can only query and view records.  

- **Admin CRUD Operations**  
  - **Insert**: Add new rows into the database.  
  - **Update**: Multi-column filter with validation before updating.  
  - **Delete**: Multi-column filter with validation before deleting.  

- **Data Export**  
  - Download the updated database as an Excel file (`.xlsx`).  

- **Error Handling**  
  - Automatic retry on SQLite database locks.  
  - User-friendly messages when queries fail.  

---

## 🛠️ Tech Stack  

- **Frontend**: Streamlit  
- **Database**: SQLite  
- **AI/LLM**: LangChain + Groq (`llama3-70b-8192`)  
- **Data Handling**: Pandas, OpenPyXL  

---

## ⚙️ Setup Instructions  

### 1️⃣ Clone the Repository  
```bash
git clone https://github.com/your-username/excel-to-sqlite-chatbot.git
cd excel-to-sqlite-chatbot

Create Virtual Environment & Install Dependencies

    python -m venv venv
    source venv/bin/activate   # (Linux/Mac)
    venv\Scripts\activate      # (Windows)

    pip install -r requirements.txt

Set Groq API Key:

     # Linux/Mac
    export GROQ_API_KEY="your_api_key_here"

    # Windows (PowerShell)
    setx GROQ_API_KEY "your_api_key_here"

Run the Streamlit App:

    streamlit run app.py

