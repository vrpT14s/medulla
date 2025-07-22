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
