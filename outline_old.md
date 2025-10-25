# HPC Job I/O Analysis
> Overview of I/O behavior in this job, highlighting potential inefficiencies.

## Job Summary
```
id: global_context
```
> A brief summary of the behaviour of the job
this will be used to give context to later investigations. you need to:
0 - add no. of ranks, total time spent
1 - find total number of files and min, max, avg filesize. if there are less files, so less than or equal to 5, treat each file separately. if there's more, then deal with all files at once.
2 - for each file, output (you can find the info for all files at once)
    a. filesize
    b. number of POSIX bytes transferred (both read and write), number of read and write operations in posix
so your final output should contain all three of these.
(just put false for the pattern detected stuff)

## Operation Analysis
### No Collective I/O on Read/Write
```
context_from: global_context
```
> The application used MPIIO and read a non-negligible number of bytes but did not use collective I/O.
Handle both read and write. remember to check if there were any reads at all i.e. compare to indep reads. Do not check if there were posix reads, only check the MPIIO table.

### Misaligned Read/Write Requests
```
context_from: global_context
```
> The application makes read or write requests that are not aligned with the file system’s stripe boundaries.
only if greater than 30%

### Small Read/Write I/O Requests
```
context_from: global_context
```
> The application is making frequent read or write requests with a small number of bytes.

small means < 1 MB

### Random Access Patterns on Read/Write
```
context_from: global_context
```
> The application issues read or write requests in a random access pattern.

only if majority of access is random


## Lustre analysis
### Server Load Imbalance
```
context_from: global_context
```
> The application issues a disproportionate amount of I/O traffic to some servers compared to others or does not properly utilize the available storage resources. This is irrespective of which ranks are issuing the requests.

if the lustre table doesn't exist, don't flag this and just leave in your analysis a listing of the tables and showing there's no lustre table.
if the table does exist, then check for files that are striped over few ost's relative to the total number.



## Interface Breakdown
> Looking at traffic for a specific interface

### Multi-Process Without MPI
```
context_from: global_context
```
> The application has multiple processes but does not leverage MPI.

### Low-Level Library on Read/Write
```
context_from: global_context
```
> The application relies on a low-level library like STDIO for a significant amount of read or write operations outside of loading/reading configuration or output files.

we only mean stdio

## File analysis
### Repetitive Data Access on Read
```
context_from: global_context
```
> The application is making read requests to the same data repeatedly.
bytes read vs filesize

## Timing analysis
### High Metadata Load
```
context_from: global_context
```
> The application spends a significant amount of time performing metadata operations (e.g., directory lookups, file system operations).
focus on time and not operation counts, only investigate operation counts if it's seen that meta time in proportion to read and write time is sizeable (> 20%). Compute the final ratio across all important interfaces. Check if STDIO is important before you flag.

## Rank-level analysis
### Rank Load Imbalance
```
context_from: global_context
```
> The application has MPI ranks issuing a disproportionate amount of I/O traffic compared to others. This is irrespective of which servers are targeted by the ranks.
It is fine for POSIX ranks to have imbalances and this is expected for things like aggregation. Only check MPI-IO. After you detect it, however, check if this is large

# Comments

# I need DXT analysis
### Shared File Access
```
context_from: global_context
```
> The application has multiple processes or ranks accessing the same file.

this must be an inefficiency issue, so check if the file/files have lots of i/o going to them relative to the job.

# Comments

check if bytes from a single rank reads from a file is significantly greater than its filesize. calculate the number of bytes that is repetitive/unneeded, and only flag if this is a large number compared to the total I/O (say, greater than or equal to 50%).
