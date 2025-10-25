import json
import sqlite3
import yaml
import json
from dotenv import load_dotenv
import os

load_dotenv()
DB_PATH = os.getenv("DB_PATH")
def sql_query(query: str):
    return_tool_call = True
    if not DB_PATH or not query:
        raise ValueError("No database path or queries!")

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        print(f"SQL: executing {query}")
        try:
            cursor.execute(query)
            result = cursor.fetchall()
            result = [dict(row) for row in result]

        except Exception as e:
            result = {"error": f"Error running your query by sqlite3: {e}"}
            return result
        print(f"SQL: result: ")
        print(f"This is result = {result}")
        #breakpoint()
    if len(yaml.dump(result)) > 2000:
        print("result too long")
        return {"error": "Error: Query result longer than 2000 bytes. Please reframe your query."}
    elif len(result) != 0 and len(result) * len(result[0].keys()) > 100:
        print("result too long")
        return {"error": "Error: Query result contained more than 100 objects (i.e. rows * columns). Please reframe your query."}
    else:
        return {"output": result}

short_descriptions = {
    "lustre": """
table name LUSTRE:
 - Only contains info about over which OST's each file was striped
 - Does NOT contain any byte counts or operation counts
 - Also contains global information about number of OST's and MDT's
""",

    "stdio": """
table name STDIO:
- Less informative than the other tables
- Gross I/O size, read/write operation counts, approximate file size
- Metadata operation counts (opens, seeks)
- Cumulative time in reads, writes, and metadata
- Rank performance and variability (fastest/slowest ranks, bytes, times, variance)
""",

    "posix": """
table name POSIX:
- Gross I/O size, read/write operation counts, approximate file size
- 4 most common access sizes and their frequencies
- Access patterns (consecutive, sequential)
- 4 most common strides between successive operations
- Metadata operation counts (opens, stats, seeks, renames, syncs, mmaps)
- File and memory alignment, unaligned operations
- Operation start/end timestamps (open, read, write, close)
- Cumulative time spent in reads, writes, and metadata
- Rank performance and variability (fastest/slowest ranks, bytes, times, variance)
- Slowest operation durations and their sizes
- Data volume distribution by read/write size buckets
""",

    "mpiio": """
table name MPIIO:
 - I/O counts & sizes: independent, collective, non-blocking, and split reads/writes; total bytes read/written; 4 most common access sizes with counts; bucketed I/O sizes for reads and writes
 - Other operations counts: independent/collective opens, syncs, hints, views
 - Cumulative time spent in reads, writes, and metadata
 - Operation start/end timestamps (open, read, write, close)
 - Rank performance and variability (fastest/slowest ranks, bytes, times, variance, slowest operation durations and their sizes)
 - Data volume distribution by read/write size buckets

 Remember MPIIO data indirectly becomes POSIX data, so an application using only MPIIO will have records and I/O in both MPIIO and POSIX tables.
""",
}


def list_tables():
    tables = sql_query("select name from sqlite_master where type = 'table';")
    tables = tables['output']

    table_names = [row["name"] for row in tables]
    return '\n\n'.join(short_descriptions.get(n.lower()) for n in table_names if n.lower() in short_descriptions.keys())

def get_schema(name: str):

    descriptions = {
        "lustre": """
Do not access this table! Under construction.
""",
        "stdio": """
Do not access this table! Under construction.
""",
        "posix": """
Do not access this table! Under construction.
""",
        "mpiio": """
Do not access this table! Under construction.
""",
    }
    with open("posix_cols.txt", 'r') as posix_file:
        descriptions['posix'] = posix_file.read()
    with open("mpiio_cols.txt", 'r') as mpiio_file:
        descriptions['mpiio'] = mpiio_file.read()
    with open("stdio_cols.txt", 'r') as stdio_file:
        descriptions['stdio'] = stdio_file.read()
    with open("lustre_cols.txt", 'r') as lustre_file:
        descriptions['lustre'] = lustre_file.read()

    return descriptions[name.lower()]

def submit_final_analysis(analysis: str):
    assert(0, "You shouldn't be here.");
    return


tools = [
    {
        "type": "function",
        "function": {
            "name": "sql_query",
            "description": "Run a query against the darshan log which has been moved into a database. Do NOT construct a query such that the output will be very large.",
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
            "description": "Get the exact schema of the fields along with their descriptions for a given table in the darshan log database.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "The name of the table to inspect"
                    }
                },
                "required": ["name"]
            }
        }
    },
#    {
#        "type": "function",
#        "function": {
#            "name": "submit_final_analysis",
#            "description": "Submit your final analysis for this section. The chat will end afterwards.",
#            "parameters": {
#                "type": "object",
#                "properties": {
#                    "name": {
#                        "analysis": "string",
#                        "description": """
#Your analysis, in a list of queries and conclusions. You do not need to list all of the queries you have run, only the desicive ones that have confirmed your conclusion. Each conclusion needs a query to prove it, though. For example:
#Query 1: ran
#```
#SELECT AVG(
#           CASE
#               WHEN POSIX_MAX_BYTE_READ > POSIX_MAX_BYTE_WRITTEN
#               THEN POSIX_MAX_BYTE_READ + 1
#               ELSE POSIX_MAX_BYTE_WRITTEN + 1
#           END
#       ) AS avg_filesize
#FROM POSIX;
#```
#and received 4.9 GB
#Conclusion 1: Average filesize is small (< 5 GB).
#
#Query 2:
#```
#SELECT COUNT(*) * 1.0 / (SELECT COUNT(*) FROM POSIX) AS fraction_small_files
#FROM POSIX
#WHERE
#    (CASE
#        WHEN POSIX_MAX_BYTE_READ > POSIX_MAX_BYTE_WRITTEN
#        THEN POSIX_MAX_BYTE_READ + 1
#        ELSE POSIX_MAX_BYTE_WRITTEN + 1
#     END) < 10 * 1024 * 1024 * 1024;  -- 10 GB in bytes
#```
#Conclusion 2: Most files are small: about 90% of files are smaller than 10 GB.
#"""
#                    }
#                },
#                "required": ["analysis"]
#            }
#        }


#    {
#        "type": "function",
#        "function": {
#            "name": "get_description",
#            "description": "Get a description of the fields for a given table in the darshan log database",
#            "parameters": {
#                "type": "object",
#                "properties": {
#                    "name": {
#                        "type": "string",
#                        "description": "The name of the table to inspect"
#                    }
#                },
#                "required": ["name"]
#            }
#        }
]

#tool name to function
tool_registry = {
    "sql_query": sql_query,
 #   "get_description": get_description,
    "get_schema": get_schema,
    #"add_to_report": add_to_report,
#    "submit_final_analysis": submit_final_analysis
}
