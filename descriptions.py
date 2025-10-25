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


def get_schema(name: str):
    print(f"Schema gotten: {name}")

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

def list_tables():
    import nerves
    tables = nerves.sql_query("select name from sqlite_master where type = 'table';")
    tables = tables['output']

    table_names = [row["name"] for row in tables]
    return '\n\n'.join(short_descriptions.get(n.lower()) for n in table_names if n.lower() in short_descriptions.keys())
