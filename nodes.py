from pocketflow import Node, Flow
from utils.call_llm import call_llm
import sqlite3
import warnings
import json
from utils.darshan_to_sqlite import darshan_to_sqlite
import yaml

from pprint import pprint as pp


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
    """LLM reasons over current state and proposes new symptoms/queries."""
    def exec(self, shared):
        print("[ReasonAndProposeNode] Executing...")
        #breakpoint()
        # Gather schema and enriched symptom history
        schema = shared.get("schema")
        symptom_history = shared.get("symptom_history", [])
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


        # Construct prompt for LLM
        prompt = f"""
You are an expert in HPC I/O analysis. You will be given the database schema, the number of rows in the main table, and the history of previously checked symptoms. Each entry in the symptom history includes the result of the measurement. Your task is to propose the next set of I/O inefficiency symptoms to check.

Only generate 2 symptoms.

Database schema:
{schema}

There are {row_count} rows in the posix_counters table. Currently there is only one rank and that has the value "-1".

Symptom History (each entry includes the result of the measurement):
{yaml.dump(symptom_history)}

Respond with a list of new symptoms in JSON format:

```json
[
    {{
        "title": ...,
        "description": ...,
        "sql": ...
    }},
    ...
]
```
""" #The {{'s are doubled because otherwise python will try to format them.
        # Call the LLM
        llm_response = call_llm(prompt)

        # Parse the LLM response as JSON
        try:
            json_section = llm_response.split('```json\n')[-1].split('\n```')[0]
            print(f"Found json: {json_section}")
            proposed_symptoms = json.loads(json_section)
        except Exception as e:
            print("[ReasonAndProposeNode] Failed to parse LLM response as JSON:", e)
            print("[ReasonAndProposeNode] LLM response was:\n", llm_response)
            breakpoint()
            proposed_symptoms = []

        return proposed_symptoms

    def post(self, shared, prep_res, exec_res):
        # Store proposed symptoms/queries in shared for the next node
        shared["proposed_symptoms"] = exec_res
        # No need to append to symptom_history here (handled in RunSQLMeasurementsNode)
        print("[ReasonAndProposeNode] Proposed symptoms:", exec_res)
        return None

class RunSQLMeasurementsNode(Node):
    def prep(self, shared):
        return shared
    """Run the SQL measurements for the proposed symptoms."""
    def exec(self, shared):
        print("[RunSQLMeasurementsNode] Executing...")
        #breakpoint()
        db_path = shared.get("sqlite_db_path")
        proposed_symptoms = shared.get("proposed_symptoms", [])
        measurement_results = []

        if not db_path or not proposed_symptoms:
            warnings.warn("No database path or proposed symptoms!", UserWarning)
            # Nothing to do
            return measurement_results

        # Connect to SQLite DB
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        for symptom in proposed_symptoms:
            print("Processing symptom:")
            pp(symptom)
            title = symptom.get("title")
            sql = symptom.get("sql")
            # Per docs: let errors propagate, handled by node retry/fallback
            print(f"SQL: executing {sql}")
            cursor.execute(sql)
            # Fetch all results (could be improved for large queries)
            col_names = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            result = [dict(zip(col_names, row)) for row in rows]
            print(f"SQL: result: {result}")

            measurement_results.append({
                "title": title,
                "description": symptom.get("description"),
                "reasoning": symptom.get("reasoning"),
                "sql": sql,
                "result": result
            })

        conn.close()
        return measurement_results

    def post(self, shared, prep_res, exec_res):
        # Store measurement results in shared for the next node
        shared["measurement_results"] = exec_res
        print("[RunSQLMeasurementsNode] Measurement results:", exec_res)
        # Append enriched results to symptom_history
        if "symptom_history" not in shared or shared["symptom_history"] is None:
            shared["symptom_history"] = []
        shared["symptom_history"].extend(exec_res)
        return None

class LoopControllerNode(Node):
    def prep(self, shared):
        return shared
    """Decide whether to continue the loop or exit based on LLM's reasoning/results."""
    def exec(self, shared):
        print("[LoopControllerNode] Executing...")
        #breakpoint()
        # If there are no more proposed symptoms, we're done
        proposed_symptoms = shared.get("proposed_symptoms")
        symptom_history = shared.get("symptom_history")
        if not proposed_symptoms:
            print("[LoopControllerNode] No more symptoms to check. Exiting loop.")
            return "default"
        if len(symptom_history) >= 4:
            print("[LoopControllerNode] Reached symptom limit")
            return "default"
        print("[LoopControllerNode] More symptoms to check. Continuing loop.")
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
        pp(shared["symptom_history"])
        #breakpoint()
        # TODO: Implement report output (print, save, or display)
        return None
    def post(self, shared, prep_res, exec_res):
        print("[OutputReport] Report output complete.")
        return None
