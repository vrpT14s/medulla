import darshan

filename="test.darshan"
# Open a Darshan log file and read all data
with darshan.DarshanReport(filename, read_all=True) as report:
    # Print the metadata dict for this log
    print("metadata:", report.metadata)

    # Print job runtime and number of processes
    print("run_time:", report.metadata['job']['run_time'])
    print("nprocs:", report.metadata['job']['nprocs'])

    # Print modules contained in the report
    print("modules:", list(report.modules.keys()))

    # Export POSIX module records to DataFrame and print
    posix_df = report.records['MPI-IO'].to_df()
    print(posix_df)

