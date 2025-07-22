from pocketflow import Node, Flow
from utils.call_llm import call_llm
import sqlite3
import warnings
import json
from utils.darshan_to_sqlite import darshan_to_sqlite
import yaml

from pprint import pprint as pp, pformat as pf
from utils.call_llm import chat_llm


class ParseDarshanLog(Node):
    def prep(self, shared):
        return shared
    """Parse the Darshan log and load it into a SQLite database."""
    def exec(self, prep_res):
        shared = prep_res
        print("[ParseDarshanLog] Executing...")
        #breakpoint()
        darshan_log_path = shared.get("darshan_log_path")
        sqlite_db_path = shared.get("sqlite_db_path")
        if not darshan_log_path or not sqlite_db_path:
            raise ValueError("darshan_log_path and sqlite_db_path must be set in shared")
        print(f"[ParseDarshanLog] Converting {darshan_log_path} to {sqlite_db_path}")
        darshan_to_sqlite(darshan_log_path, sqlite_db_path)
        print("[ParseDarshanLog] Conversion complete.")
        # Read schema from SQLite and store in shared
        import sqlite3
        try:
            conn = sqlite3.connect(sqlite_db_path)
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info('posix_counters')")
            columns = cursor.fetchall()
            schema_str = "posix_counters table columns:\n" + "\n".join([f"- {col[1]} ({col[2]})" for col in columns])
            conn.close()
        except Exception as e:
            schema_str = f"[Error reading schema: {e}]"
        shared["schema"] = schema_str
        return None
    def post(self, shared, prep_res, exec_res):
        # No-op for now
        return None

class ReasonAndProposeNode(Node):
    def prep(self, shared):
        return shared
    """LLM reasons over current state and proposes new queries."""
    def exec(self, shared):
        print("[ReasonAndProposeNode] Executing...")
        # Gather schema and enriched symptom history
        schema = shared.get("schema")
        measurement_results = shared.get("measurement_results", [])
        sqlite_db_path = shared.get("sqlite_db_path")
        row_count = None
        if sqlite_db_path:
            try:
                conn = sqlite3.connect(sqlite_db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM posix_counters")
                row_count = cursor.fetchone()[0]
                conn.close()
            except Exception as e:
                row_count = f"[Error: {e}]"
        else:
            row_count = "[No sqlite_db_path provided]"

        # Ensure chat_history exists in shared
        if "chat_history" not in shared or shared["chat_history"] is None:
            shared["chat_history"] = []

        # Only add the initial prompt if chat_history is empty
        if not shared["chat_history"]:
            initial_prompt = f"""
You are an expert in HPC I/O analysis. You will be analyzing a darshan log to search it for inefficient I/O patterns. At the end you will make a small report about what you think the I/O problems are, explaining why you think so. Please finish in around 6 to 7 responses so it will not take too long.

The log is accesible through a database table and its schema is as follows:

Database schema:
{schema}

The number of ranks that were run is {row_count}.

You will be able to query the database with SQL. You will give a title to each query and can run as many queries as you'd like at the same time. Please gather all your queries into one block per prompt. I will return the results afterwards.

To query, write a block in the following format.

```queries
[
    {{
        "title": ...,
        "sql": ...
    }},
    ...
]
```

Please start.
"""
            print("[ReasonAndProposeNode] Initial prompt sent to LLM:\n", initial_prompt)
            shared["chat_history"].append({"role": "system", "content": initial_prompt})

        # If there are measurement results, send them to the LLM as a user message
        if measurement_results:
            results_str = pf(measurement_results, indent=2, width=120)
            print("[ReasonAndProposeNode] Sending measurement results to LLM:")
            print(results_str)
            shared["chat_history"].append({"role": "system", "content": f"Here are the results of your last queries:\n{results_str}"})

        # Call the LLM with the full chat history
        llm_response = chat_llm(shared["chat_history"])
        # Add LLM response to chat_history
        shared["chat_history"].append({"role": "assistant", "content": llm_response})
        # Print only the new LLM message
        print(f"[assistant] {llm_response}\n")

        # Parse the LLM response as JSON from the ```queries ... ``` block
        try:
            json_section = llm_response.split('```queries\n')[-1].split('\n```')[0]
            queries = json.loads(json_section)
        except Exception as e:
            print("[ReasonAndProposeNode] Failed to parse LLM response as JSON:", e)
            print("[ReasonAndProposeNode] LLM response was:\n", llm_response)
            queries = []

        return queries
    
    def post(self, shared, prep_res, exec_res):
        # Store queries in shared for the next node
        shared["queries"] = exec_res
        print("[ReasonAndProposeNode] Queries:", exec_res)
        return None

class RunSQLMeasurementsNode(Node):
    def prep(self, shared):
        return shared
    """Run the SQL measurements for the queries."""
    def exec(self, shared):
        print("[RunSQLMeasurementsNode] Executing...")
        db_path = shared.get("sqlite_db_path")
        queries = shared.get("queries", [])
        measurement_results = []

        if not db_path or not queries:
            warnings.warn("No database path or queries!", UserWarning)
            # Nothing to do
            return measurement_results

        # Connect to SQLite DB
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        for query in queries:
            title = query.get("title")
            sql = query.get("sql")
            print(f"SQL: executing {sql}")
            try:
                cursor.execute(sql)
                col_names = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()
                result = [dict(zip(col_names, row)) for row in rows]
            except Exception as e:
                result = f"SQL error: {e}"
            print(f"SQL: result: {result}")

            measurement_results.append({
                "title": title,
                "sql": sql,
                "result": result
            })

        conn.close()
        return measurement_results

    def post(self, shared, prep_res, exec_res):
        # Store measurement results in shared for the next node
        shared["measurement_results"] = exec_res
        print("[RunSQLMeasurementsNode] Measurement results:", exec_res)
        return None

class LoopControllerNode(Node):
    def prep(self, shared):
        return shared
    """Decide whether to continue the loop or exit based on LLM's reasoning/results."""
    def exec(self, shared):
        print("[LoopControllerNode] Executing...")
        # If there are no more queries, we'll leave and go the default route
        queries = shared.get("queries")
        if not queries:
            print("[LoopControllerNode] No more queries to check. Exiting loop.")
            return "default"
        print("[LoopControllerNode] More queries to check. Continuing loop.")
        return "continue"
    
    def post(self, shared, prep_res, exec_res):
        print(f"[LoopControllerNode] Action: {exec_res}")
        return exec_res

class FinishSymptomLoop(Flow):
    def prep(self, shared):
        return None


class IterativeSymptomLoop(Flow):
    """Iteratively propose, measure, and reason about I/O inefficiency symptoms using the LLM and SQL queries."""
    def __init__(self):
        reason_node = ReasonAndProposeNode(2, 5) #try 2 times with a 5 second gap in between
        measure_node = RunSQLMeasurementsNode(2, 5)
        loop_node = LoopControllerNode(2, 5)
        finish_node = FinishSymptomLoop()

        reason_node >> measure_node >> loop_node >> finish_node
        loop_node - "continue" >> reason_node

        super().__init__(start=reason_node)

class GenerateReport(Node):
    def prep(self, shared):
        return shared
    """Summarize findings, generate explanations, and create visualizations."""
    def exec(self, shared):
        print("[GenerateReport] Executing...")
        #breakpoint()
        # TODO: Implement report generation and plotting
        return None
    def post(self, shared, prep_res, exec_res):
        print("[GenerateReport] Report generated.")
        # TODO: Store the report in shared
        return None

class OutputReport(Node):
    def prep(self, shared):
        return shared
    """Present the final report to the user."""
    def exec(self, shared):
        print("[OutputReport] Executing...")
        #breakpoint()
        # TODO: Implement report output (print, save, or display)
        # Print the chat history at the end
        chat_history = shared.get("chat_history", [])
        print("The program has mostly finished.")
        breakpoint()

        #print("\n--- Chat History ---")
        #for msg in chat_history:
        #    print(f"[{msg['role']}] {msg['content']}\n")
        #print("--- End of Chat History ---\n")
        return None
    def post(self, shared, prep_res, exec_res):
        print("[OutputReport] Report output complete.")
        return None
