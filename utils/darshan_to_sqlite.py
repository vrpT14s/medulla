import darshan
import sqlite3
import pandas as pd

# Usage: darshan_to_sqlite('input.darshan', 'output.sqlite')
def darshan_to_sqlite(darshan_log_path, sqlite_db_path):
    with darshan.DarshanReport(darshan_log_path, read_all=True) as report:
        # --- 1. Extract job metadata and write as a single-row DataFrame ---
        metadata = report.metadata
        job_metadata = metadata['job']
        library_version = job_metadata.pop('metadata')
        job_df = pd.DataFrame([job_metadata])

        conn = sqlite3.connect(sqlite_db_path)
        # Write job_metadata table
        job_df.to_sql('job_metadata', conn, if_exists='replace', index=False)

        # --- 2. Extract and write POSIX counters/fcounters as one table ---
        if 'POSIX' in report.records:
            posix_df = report.records['POSIX'].to_df()
            counters_df = posix_df['counters']
            fcounters_df = posix_df['fcounters']
            # Merge on id and rank
            merged_df = pd.merge(counters_df, fcounters_df, on=['id', 'rank'], how='outer', suffixes=('', '_f'))
            # Write to SQLite as one table
            merged_df.to_sql('posix_counters', conn, if_exists='replace', index=False)

        conn.close()

if __name__ == '__main__':
    import sys
    if len(sys.argv) != 3:
        print('Usage: python darshan_to_sqlite.py <input.darshan> <output.sqlite>')
        sys.exit(1)
    darshan_to_sqlite(sys.argv[1], sys.argv[2]) 