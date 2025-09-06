import json
import sqlite3
from groq import Groq
import yaml
import json
from dotenv import load_dotenv

def sql_query(query: str, db_path: str, return_json = False):
    if not db_path or not query:
        raise ValueError("No database path or queries!")

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        print(f"SQL: executing {query}")
        try:
            cursor.execute(query)
            result = cursor.fetchall()
            result = [dict(row) for row in result]
            if not return_json:
                result = yaml.dump(result, sort_keys=False)
        except Exception as e:
            result = f"SQL error: {e}"
        #print(f"SQL: result: ")
        print(result)

    return result

def list_tables(db_path: str):
    return sql_query("select name from sqlite_master where type = 'table';", db_path);

def get_schema(table: str, db_path: str):
    ret = sql_query(f"select sql from sqlite_master where type = 'table' and name = '{table}';", db_path, return_json = True);
    #print(ret[0]['sql'])
    return (ret[0]['sql'])
    #return ret['sql']

def add_to_report(text: str, report):
    report += '\n'
    report += text


tools = [
    {
        "type": "function",
        "function": {
            "name": "sql_query",
            "description": "Run a query against the darshan log which has been moved into a database",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The SQL query to execute"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_schema",
            "description": "Get the CREATE TABLE statement (schema) for a given table in the darshan log database",
            "parameters": {
                "type": "object",
                "properties": {
                    "table": {
                        "type": "string",
                        "description": "The name of the table to inspect"
                    }
                },
                "required": ["table"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_to_report",
            "description": "Append text to final report",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "The text to append"
                    }
                },
                "required": ["text"]
            }
        }
    },
]

#tool name to function
tool_registry = {
    "sql_query": sql_query,
    "get_schema": get_schema,
    "add_to_report": add_to_report,
}
