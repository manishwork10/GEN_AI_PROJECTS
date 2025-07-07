import streamlit as st
import sqlite3
import os
import pandas as pd
import matplotlib.pyplot as plt
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
import re

# Use secrets if deployed on Streamlit Cloud
import os
GEMINI_API_KEY = os.getenv("Api_key")


@st.cache_resource
def init_llm():
    return ChatGoogleGenerativeAI(
        model="gemini-1.5-flash",
        google_api_key=GEMINI_API_KEY,
        temperature=0.3,
        max_tokens=500
    )

def call_llm(llm, prompt):
    return llm.invoke([HumanMessage(content=prompt)]).content.strip()

def clean_sql_output(raw_sql):
    """Strip markdown formatting and extract SQL."""
    raw_sql = raw_sql.replace("```sql", "").replace("```", "").strip()
    match = re.search(r"(SELECT|INSERT|UPDATE|DELETE).*", raw_sql, re.IGNORECASE | re.DOTALL)
    return match.group(0).strip() if match else raw_sql

def setup_database():
    if not os.path.exists("employee_management.db"):
        conn = sqlite3.connect("employee_management.db")
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE departments (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, location TEXT)")
        cursor.execute("CREATE TABLE jobroles (id INTEGER PRIMARY KEY AUTOINCREMENT, job_title TEXT NOT NULL, min_salary REAL, max_salary REAL)")
        cursor.execute("CREATE TABLE employees (id INTEGER PRIMARY KEY AUTOINCREMENT, first_name TEXT NOT NULL, last_name TEXT NOT NULL, department_id INTEGER, job_title TEXT, salary REAL, hire_date TEXT, FOREIGN KEY(department_id) REFERENCES departments(id))")
        cursor.executemany("INSERT INTO departments (name, location) VALUES (?, ?)", [
            ('Engineering', 'New York'),
            ('Human Resources', 'Los Angeles'),
            ('Sales', 'Chicago')
        ])
        cursor.executemany("INSERT INTO jobroles (job_title, min_salary, max_salary) VALUES (?, ?, ?)", [
            ('Software Engineer', 70000, 120000),
            ('HR Manager', 60000, 90000),
            ('Sales Executive', 50000, 80000)
        ])
        cursor.executemany("INSERT INTO employees (first_name, last_name, department_id, job_title, salary, hire_date) VALUES (?, ?, ?, ?, ?, ?)", [
            ('Alice', 'Smith', 1, 'Software Engineer', 85000, '2022-05-01'),
            ('Bob', 'Brown', 2, 'HR Manager', 75000, '2021-03-15'),
            ('Charlie', 'Davis', 3, 'Sales Executive', 65000, '2023-01-10'),
            ('Diana', 'Miller', 1, 'Software Engineer', 95000, '2023-08-20')
        ])
        conn.commit()
        conn.close()

def generate_sql(llm, question):
    schema = """
    Tables:
    employees(id, first_name, last_name, department_id, job_title, salary, hire_date),
    departments(id, name, location),
    jobroles(id, job_title, min_salary, max_salary)
    """
    prompt = f"""
    Translate the following natural language question to a valid SQLite query based on this schema:
    {schema}
    Question: {question}
    Only return the SQL query.
    """
    raw_sql = call_llm(llm, prompt)
    return clean_sql_output(raw_sql)

def explain_sql(llm, query):
    return call_llm(llm, f"What does this SQL query do? Explain simply:\n{query}")

def summarize_results(llm, question, df):
    if df.empty:
        return "No results found."
    data = df.to_dict(orient="records")
    prompt = f"User asked: '{question}'\nHere are the results: {data}\nSummarize this in a human-friendly sentence."
    return call_llm(llm, prompt)

def execute_sql(query):
    conn = sqlite3.connect("employee_management.db")
    try:
        df = pd.read_sql_query(query, conn)
    except Exception as e:
        df = pd.DataFrame()
        st.error(f"SQL Error: {e}")
    conn.close()
    return df

def main():
    st.set_page_config(page_title="Text to SQL Chatbot", layout="wide")
    st.title("💬 Text to SQL Chatbot for Employee DB")

    setup_database()
    llm = init_llm()

    question = st.text_input("Ask your question:", placeholder="e.g., Who earns the most salary?")
    if question:
        with st.spinner("Processing your question..."):
            sql = generate_sql(llm, question)
            explanation = explain_sql(llm, sql)
            df = execute_sql(sql)
            summary = summarize_results(llm, question, df)

        st.subheader("🔍 Generated SQL Query")
        st.code(sql, language="sql")

        st.subheader("📘 SQL Explanation")
        st.write(explanation)

        if not df.empty:
            st.subheader("📊 Query Result")
            st.dataframe(df)

            # Only draw chart if there are numeric columns
            numeric_df = df.select_dtypes(include='number')
            if not numeric_df.empty and len(numeric_df.columns) >= 2:
                st.bar_chart(numeric_df)

        st.subheader("✅ Summary")
        st.success(summary)

if __name__ == "__main__":
    main()
