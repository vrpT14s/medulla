# HPC Job I/O Analysis
> Overview of I/O behavior in this job, highlighting potential inefficiencies.

## Detecting Possible Inefficient I/O Patterns
> In this section, we analyze the logs to detect whether the following common I/O patterns are present or not in a significant manner in this particular job.


### Misaligned Read/Write Requests
> The application makes read or write requests that are not aligned with the file system’s stripe boundaries.
only if greater than 30%


### Multi-Process Without MPI
> The application has multiple processes but does not leverage MPI.


### Rank Load Imbalance
> The application has MPI ranks issuing a disproportionate amount of I/O traffic compared to others. This is irrespective of which servers are targeted by the ranks.
It is fine for POSIX ranks to have imbalances and this is expected for things like aggregation. Only check MPI-IO. After you detect it, however, check if this is large


### Repetitive Data Access on Read
> The application is making read requests to the same data repeatedly.
bytes read vs filesize

### Random Access Patterns on Read/Write
> The application issues read or write requests in a random access pattern.

only if majority of access is random

### No Collective I/O on Read/Write
> The application used MPIIO and read a non-negligible number of bytes but did not use collective I/O.
Handle both read and write. remember to check if there were any reads at all i.e. compare to indep reads. Do not check if there were posix reads, only check the MPIIO table.

### Small Read/Write I/O Requests
> The application is making frequent read or write requests with a small number of bytes.

small means < 1 MB

### Low-Level Library on Read/Write
> The application relies on a low-level library like STDIO for a significant amount of read or write operations outside of loading/reading configuration or output files.

we only mean stdio

### High Metadata Load
> The application spends a significant amount of time performing metadata operations (e.g., directory lookups, file system operations).
focus on time, check both posix and mpiio. Only if time is greater than 20%, otherwise it's not worth it to make it more efficient.

### Shared File Access
> The application has multiple processes or ranks accessing the same file.

this must be an inefficiency issue, so check if the file/files have lots of i/o going to them relative to the job.
### Server Load Imbalance
> The application issues a disproportionate amount of I/O traffic to some servers compared to others or does not properly utilize the available storage resources. This is irrespective of which ranks are issuing the requests.

check for files which aren't striped over few ost's. only check this if the log had a lustre section. otherwise leave your query and output null and write in the conclusion that the lustre table doesn't exist.


# Comments

check if bytes from a single rank reads from a file is significantly greater than its filesize. calculate the number of bytes that is repetitive/unneeded, and only flag if this is a large number compared to the total I/O (say, greater than or equal to 50%).
