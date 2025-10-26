# HPC Job IO Performance Analysis
## Job Summary
```
id: global_context
children_eval: sequential
```

### Net operation size, count and time across layers
> In total for ? layer, ? GB was written in ? seconds (adding times across all ranks) across ? writes and ? GB was read in ? seconds across ? reads. Metadata operations accounted for ? seconds in total across all ranks.

#### across POSIX
#### across MPIIO
```
flags:
    NO_MPIIO: no usage of mpiio at all
```

#### across STDIO
```
flags:
    HIGH_STDIO: greater than posix
```

#### Cumulative Load
> Looking across all layers, reads took 40% of the time, writes 59% of the time, metadata 1% of the time.
```
flags:
    HIGH_METADATA_LOAD: total time spent on metadata is very high across the program (> 30% of total)
```

### File analysis in POSIX
#### Coarse File Analysis
> 1000 files were accessed. Average filesize was 10 GB, max was 20 GB, minimum was 500 bytes, standard deviation was xyz

#### File name analysis
> Based on filenames, there were generally two groups: 5 large write-only hdf5 files of the form '/mnt/lustre/output-*.hdf5' (mean 20 GB, stddev 1 GB), and one small read-intensive config file: '/mnt/lustre/output/config.ini'

Specifically do it this way:
First list out 10 filenames to try and understand what common filenames there are, and to come up with patterns. if there's an obvious pattern then go ahead but if each file has a different pattern, then you can give up and say there was no clear file grouping.
If there is, then make a list of glob patterns based on this, to group some files together, and find out some statistics and characteristics about them.

Usually there should be a clear pattern and not too many files (often <= 5). If there are more than 6 patterns, consider it to be too complicated and say too many groups found.

#### File group importance
> 50 GB in total was transferred to the hdf5 file group, with 99.9% being write (mean 10 GB, min 8 GB, max 11 GB, stddev xyz). Only 10 KB was transferred to the config file, with a read-write split of 55-45.
> Since the small config file has very little share of traffic, we will ignore it in our analysis.

## POSIX info analysis
```
context_from: global_context
```
### Redundant reads
```
flags:
    REDUNDANT_READS: a large amount of global read traffic and total traffic is redundant
```
> A 10 MB file had 10 GB of data read from it, implying the same data was read unnecessarily from it instead of buffering. This is 70% of all read traffic and 35% of all traffic so it's a large issue.

### Operation size and offset analysis
```
children_eval: sequential
```
#### Top 4 common access sizes
> 90% of access were in one of these four sizes: ? (40%), ? (20%), ? (15%), ? (5%). So we know the exact size of most operations.

#### Access size histogram
```
flags:
    SMALL_READS: most reads are small (< 1 MB) and read operation counts are large enough for this to be an issue.
    SMALL_WRITES: most writes are small (< 1 MB)
```
> The few 20 reads were spread out across all buckets under 10M. 95% of the 2000 writes were concentrated in the 100-1K access size bucket. We know from the common access sizes that the access size of 512 bytes in particular was very common, being 1500 of the 2000 writes.

#### Sequentiality Analysis
```
flags:
    RANDOM_READS: most reads are not sequential (and reads are common enough to be an issue)
    RANDOM_WRITES: most writes are not sequential
```
> 99% of the 2000 writes were sequential, with 20% being consecutive. Only 35% (124) of the reads were sequential with 10% consecutive. 60% of the sequential non-consecutive operations had a stride (distance between last byte of previous access and first byte of this one) of 2 MB with the other strides having uncommon shares (less than 5% each).

#### Misalignment
```
flags:
    MISALIGNED_ACCESS: most access was misaligned
```
> 78% of all accesses were misaligned with the 1 MB file alignment (? operations out of ? total).

## MPIIO info analysis
```
context_from: global_context
```
### Collective Operations
```
flags:
    ALL_INDEPENDENT_READS: no collective reads
    ALL_INDEPENDENT_WRITES: no collective writes
```
find total number of collective reads and writes and compare to indep reads and writes

### Rank Load Balance
```
flags:
    RANK_LOAD_IMBALANCE: some ranks at the mpiio layer are responsible for disproportionate amounts of bytes accessed and time taken to access those bytes
```
> Across the 5 large hdf5 files that made up all write traffic, per-file bytes standard deviation was high for all, with a minimum of ? bytes. The ratio of the bytes read by the slowest rank to the mean for each file was on average 12.3, with the slowest rank in question being 0 across all files.
only check mpiio because checking variance in posix layer is aggregation analysis, not imbalance analysis.

## PFS analysis
```
context_from: global_context
eval_children: sequential
```
### Resources
> The cluster has 128 OST's and 3 MDT's holding 10 files, each with a mean size of 23 GB (std dev 2 GB), for a total load of 230 GB. The stripe length is 1 MB.

### Striping analysis
```
flags:
    OST_LOAD_IMBALANCE: some important files are striped over a single ost
```
> 7 of the 10 files are striped over 64 of the 128 OST's but 3 are striped over only one each. These 3 files make up 30% of the server load and are large at 23 GB each.
