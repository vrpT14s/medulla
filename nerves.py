from dotenv import load_dotenv
import os

def get_db_path():
    load_dotenv()
    return os.getenv("DB_PATH")

from sqlalchemy import create_engine, text
import yaml

engine = create_engine(get_db_path(), echo=True, future=True)

def sql_query(query: str):
    try:
        with engine.connect() as conn:
            result_proxy = conn.execute(text(query))
            rows = result_proxy.fetchall()
            result = [dict(row._mapping) for row in rows]  # Convert to dict

    except Exception as e: #change to sql alchemy error
        return {"error": f"Error running your query with SQLAlchemy: {e}"}

    print(f"SQL: result:")
    print(f"This is result = {result}")

    if len(yaml.dump(result)) > 2000:
        print("result too long")
        return {"error": "Error: Query result longer than 2000 characters. Please reframe your query."}
    else:
        return {"output": result}

from descriptions import get_schema
agent_tools = [sql_query, get_schema]
