from pocketflow import Node, Flow
from utils.call_llm import call_llm
import sqlite3
import warnings

class ParseDarshanLog(Node):
    """Parse the Darshan log and load it into a SQLite database."""
    def exec(self, shared):
        # TODO: Implement Darshan log parsing and SQLite loading
        pass
    def post(self, shared, prep_res, exec_res):
        # TODO: Store the path to the SQLite DB in shared
        pass

class ReasonAndProposeNode(Node):
    """LLM reasons over current state and proposes new symptoms/queries."""
    def exec(self, shared):
        print("[ReasonAndProposeNode] Executing...")
        breakpoint()
        # Gather schema and symptom history
        schema = shared.get("schema")
        symptom_history = shared.get("symptom_history", [])

        # Construct prompt for LLM (placeholder) - vrpt14s: will need to add darshan specific info
        prompt = f"""
You are an expert in HPC I/O analysis. Given the following database schema and the history of previously checked symptoms, propose the next set of I/O inefficiency symptoms to check. Each symptom should have a title, a description, and an SQL query to measure it.

Schema:
{schema}

Symptom History:
{symptom_history}

Respond with a list of new symptoms in JSON format:
[
  {{"title": ..., "description": ..., "sql": ...}},
  ...
]
"""
        # Call the LLM (placeholder)
        llm_response = call_llm(prompt)

        # Parse the LLM response (placeholder: assume it's a list of dicts)
        # In real code, use json.loads and error handling
        proposed_symptoms = []  # TODO: parse llm_response into a list of dicts
        # Example placeholder:
        # proposed_symptoms = json.loads(llm_response)
        pass  # Replace with actual parsing

        return proposed_symptoms
    
    def post(self, shared, prep_res, exec_res):
        # Store proposed symptoms/queries in shared for the next node
        shared["proposed_symptoms"] = exec_res
        # Optionally log or print for debugging
        print("[ReasonAndProposeNode] Proposed symptoms:", exec_res)
        return None

class RunSQLMeasurementsNode(Node):
    """Run the SQL measurements for the proposed symptoms."""
    def exec(self, shared):
        print("[RunSQLMeasurementsNode] Executing...")
        breakpoint()
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
            title = symptom.get("title")
            sql = symptom.get("sql")
            # Per docs: let errors propagate, handled by node retry/fallback
            cursor.execute(sql)
            # Fetch all results (could be improved for large queries)
            result = cursor.fetchall()
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
    """Decide whether to continue the loop or exit based on LLM's reasoning/results."""
    def exec(self, shared):
        print("[LoopControllerNode] Executing...")
        breakpoint()
        # If there are no more proposed symptoms, we're done
        proposed_symptoms = shared.get("proposed_symptoms")
        if not proposed_symptoms:
            print("[LoopControllerNode] No more symptoms to check. Exiting loop.")
            return "done"
        print("[LoopControllerNode] More symptoms to check. Continuing loop.")
        return "continue"
    
    def post(self, shared, prep_res, exec_res):
        print(f"[LoopControllerNode] Action: {exec_res}")
        return exec_res

class IterativeSymptomLoop(Flow):
    """Iteratively propose, measure, and reason about I/O inefficiency symptoms using the LLM and SQL queries."""
    def __init__(self):
        reason_node = ReasonAndProposeNode()
        measure_node = RunSQLMeasurementsNode()
        loop_node = LoopControllerNode()
        reason_node >> measure_node >> loop_node
        # Loop: if loop_node returns 'continue', go back to reason_node
        loop_node - "continue" >> reason_node
        # If 'done', exit the loop
        super().__init__(start=reason_node)

class GenerateReport(Node):
    """Summarize findings, generate explanations, and create visualizations."""
    def exec(self, shared):
        # TODO: Implement report generation and plotting
        pass
    def post(self, shared, prep_res, exec_res):
        # TODO: Store the report in shared
        pass

class OutputReport(Node):
    """Present the final report to the user."""
    def exec(self, shared):
        # TODO: Implement report output (print, save, or display)
        pass
    def post(self, shared, prep_res, exec_res):
        pass