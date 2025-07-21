from flow import darshan_flow

# Example main function for Darshan I/O inefficiency analysis

def main():
    shared = {
        "darshan_log_path": "path/to/darshan.log",  # TODO: Set actual log path
        "sqlite_db_path": None,
        "schema": None,
        "symptom_history": [],
        "report": None
    }

    darshan_flow.run(shared)
    print("Darshan I/O inefficiency analysis complete.")
    # Optionally print or inspect shared["report"]

if __name__ == "__main__":
    main()

# Previous QA flow example:
# from flow import create_qa_flow
# def main():
#     shared = {
#         "question": "In one sentence, what's the end of universe?",
#         "answer": None
#     }
#     qa_flow = create_qa_flow()
#     qa_flow.run(shared)
#     print("Question:", shared["question"])
#     print("Answer:", shared["answer"])
