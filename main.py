from flow import darshan_flow

# Example main function for Darshan I/O inefficiency analysis

def main():
    shared = {
        "darshan_log_path": "data/16-small-reads.darshan",
        "sqlite_db_path": "db/new.sqlite",
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
