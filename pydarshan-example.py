import darshan

filename="data/" + input("enter filename: ") + ".darshan"
with darshan.DarshanReport(filename, read_all=True) as report:
    # Print the metadata dict for this log
    print("metadata:", report.metadata)

    # Print job runtime and number of processes
    print("run_time:", report.metadata['job']['run_time'])
    print("nprocs:", report.metadata['job']['nprocs'])

    # Print modules contained in the report
    print("modules:", list(report.modules.keys()))

    posix_df = report.records['POSIX'].to_df()
    print(posix_df['counters'])
    print(posix_df['fcounters'])
    breakpoint()

'''
Some data i got from using python debugger in breakpoint, to document the shape of the data (to_df() changes it to a pandas dataframe)

(Pdb) report.metadata
{'job': {'uid': 0, 'start_time_sec': 1743224039, 'start_time_nsec': 270611678, 'end_time_sec': 1743224039, 'end_time_nsec': 279071025, 'nprocs': 4, 'jobid': 43, 'run_time': 0.008459329605102539, 'log_ver': '3.41', 'metadata': {'lib_ver': '3.4.6'}}, 'exe': 'ior -t 128k -b 1m'}

(Pdb) report.modules
{'POSIX': {'len': 158, 'ver': 4, 'idx': 1, 'partial_flag': False, 'num_records': 1}, 'STDIO': {'len': 54, 'ver': 2, 'idx': 9, 'partial_flag': False, 'num_records': 1}, 'HEATMAP': {'len': 203, 'ver': 1, 'idx': 15, 'partial_flag': False}}

(Pdb) report.records['POSIX'][0]
{'id': 2462894695111347762, 'rank': -1, 'counters': array([      8,       0
,       0,      32,      32,      64,       0,
            -1,       0,       0,       0,       0,       0,     436,
       4194304, 4194304, 4194303, 4194303,      28,      28,      31,
            31,       4,       0,       8,       0,    4096,  131072,
        131072,       0,       0,       0,       0,      32,       0,
             0,       0,       0,       0,       0,       0,       0,
             0,      32,       0,       0,       0,       0,       0,
             0,       0,       0,       0,       0,       0,       0,
             0,  131072,       0,       0,       0,      64,       0,
             0,       0,       0, 2097152,       3, 2097152]), 'fcounters':
 array([7.90405273e-03, 1.31077766e-02, 8.00466537e-03, 1.25441551e-02,
       1.32629871e-02, 1.34775639e-02, 1.30357742e-02, 1.34813786e-02,
       7.93218613e-04, 1.85818672e-02, 4.01973724e-04, 3.57627869e-05,
       1.29151344e-03, 4.81557846e-03, 5.11193275e-03, 1.26234845e-08,
       0.00000000e+00])}

(Pdb) report.records['POSIX'].to_df()['counters']
   rank                   id  POSIX_OPENS  POSIX_FILENOS  ...  POSIX_FASTEST_RANK  POSIX_FASTEST_RANK_BYTES  POSIX_SLOWEST_RANK  POSIX_SLOWEST_RANK_BYTES
0    -1  2462894695111347762            8              0  ...              0                   2097152                   3                   2097 152

[1 rows x 71 columns]

(Pdb) report.records['POSIX'].to_df()['fcounters']
   rank  ...  POSIX_F_VARIANCE_RANK_BYTES
0    -1  ...                          0.0

[1 rows x 19 columns]

'''
