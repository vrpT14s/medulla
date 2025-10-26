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
        print(f"SQL: Error: {e}")
        return {"error": f"Error running your query with SQLAlchemy: {e}"}

    if len(result) < 100:
        result = [fix_decimal_type(r) for r in result]

    print(f"SQL: result:")
    print(f"This is result = {result}")

    if len(yaml.dump(result)) > 2000:
        print("result too long")
        return {"error": f"Error: Query result longer than 2000 characters. (It returned {len(results)} rows and {len(results[0]) if len(results) != 0 else 0} columns). Please reframe your query."}
    else:
        return {"output": result}

from descriptions import get_schema
agent_tools = [sql_query, get_schema]



#------------ HELPERS ------------
from decimal import Decimal
def fix_decimal_type(d):
    """
    Convert Decimal values in a dict:
    - to int if they are whole numbers
    - to float if they have a fractional part
    Leaves other types unchanged.
    """
    fixed = {}
    for k, v in d.items():
        if isinstance(v, Decimal):
            if v == v.to_integral_value():
                fixed[k] = int(v)
            else:
                fixed[k] = float(v)
        else:
            fixed[k] = v
    return fixed
