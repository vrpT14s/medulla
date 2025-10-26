#-------------------------------------------------- CHAT --------------------------------------------------
json_parse_err = """
ERROR while parsing your output JSON:
{parse_err}

This is the input passed to the parser:
{cleaned_text}

You MUST fix the JSON syntax mistake that caused this error and output the fixed response. We will then try to decode it again.
"""

output_query_run_err = """
ERROR while running your query `{llm_query}`:
{run_err}

If you meant to leave the query empty then leave it as an empty string.
Please fix it and resend the full, complete, fixed output and we will try it again.
"""

output_query_match_err = """
ERROR while checking your output queries: Your output for `{llm_query}` did not match the true output from running the query.

Your output:
{llm_output}

Correct output:
{true_output}

Please correct this and send the new fixed response. You can change either or both query or output. You must change the observations you made as well if they are no longer accurate with the new query/output.
"""

prompt_check_flags = """
Based on the analysis you've done as well as the analysis of the previous sections in the rest of the report, please choose whether or not you will mark some issues as causes for inefficiency. Only flag them if you think fixing that issue can cause a large, marked improvement, say at least 25%. We are not worried about smaller issues at this stage.

Here are the choices of flags you have:
{flags}

You should flag multiple issues if multiple hold true.

You should respond with a dict mapping from a flag name to the reason why it was flagged, explaining how much improvement you think could be gotten from fixing it.
Example:
{{
    "MISALIGNED_ACCESS" : "99.5% of all reads and thus 48% of all operations in the program were misaligned. This means almost all of the time spent reading, which was 80% of the total cumulative time compared to write and metadata, was spent on misaligned accesses, and thus there is great scope for improvement.",
    "NO_MPIIO_USAGE" : "MPIIO table does not exist in the database."
}}

Although you are free to make queries still, we do not believe you will need to do so, and that all information should already exist in your current analysis and analysis from previous sections.
"""


#-------------------------------------------------- BRAIN --------------------------------------------------
prompt_skel_brain = """
You are an HPC I/O expert who will be analyzing the logs of a job. You will be given tools to interact with a database system containing these logs as tables. You are currently focusing on one section of a larger report.

Title of the section: {title}
{example}

Here are the parent sections leading up to this one:
{parents_toc}

The user may describe the approach of what to focus on in this section and how to get this from the logs.
"""

prompt_skel_medulla = """
Your analysis will be a list of queries and conclusions. You do not need to list all of the queries you have run, only the desicive ones that have confirmed your conclusion. Each conclusion needs a query to prove it, though.

You should submit your final analysis in json format such that it's directly parseable. However, after checking the analysis, if there are errors, you should fix those errors and respond with a new messages with the new complete and fixed final analysis. Here is an example of the structure of the data where we are analyzing for the number of small files:
[
    {
        "query": "SELECT AVG(GREATEST(POSIX_MAX_BYTE_READ, POSIX_MAX_BYTE_WRITTEN) + 1) / 1024 / 1024 / 1024 AS avg_filesize, COUNT(*) AS num_files FROM POSIX;",
        "output": [ { "avg_filesize" : 2.44, "num_files": 599 } ],
        "conclusion": "Average filesize is small (< 5 GB)."
    },
    {
        "query": "SELECT COUNT(*)::float / (SELECT COUNT(*) FROM POSIX) AS fraction_small_files FROM POSIX WHERE GREATEST(POSIX_MAX_BYTE_READ, POSIX_MAX_BYTE_WRITTEN) + 1 < 10 * 1024 * 1024 * 1024;",
        "output": [ { "fraction_small_files": 0.90 } ],
        "conclusion": "Most files are small: about 90% of files are smaller than 10 GB."
    }
]

You must submit your analysis even if you believe the pattern is not detected.
Your queries will be run and the output will be checked to see if they match and we'll check if it's the same, and all numbers are equal to two significant figures (note we said significant figures here, NOT decimal points). We also ignore column order. If any of your outputs were wrong, we ask you to fix it, you must do so and send your new complete output in the same format afterwards, like I mentioned before.
"""

prompt_skel_nerves = """
A data source is a collection of tables from a specific log along with expert descriptions of the columns and their uses. You only have one data source currently, a darshan log:


# Darshan log data source -
> The tables are related in this way: MPIIO calls indirectly call POSIX, while STDIO calls are separate. However the call in the POSIX table will be a transformed version, with a different I/O pattern.
> For example with MPIIO, if collective read/writes are used then many small writes can be transformed into one large write (collective buffering), and similarly many reads into one large read (data sieving). So there is a correlation between the two layers but not a one-to-one mapping of the I/O pattern.

> If the rank is -1 this simply means many ranks wrote to that file but to save log space, that log info was aggregated. You have info about the fastest and slowest ranks and the variance in times of each, but there's not as much information as a full listing. Again, this is not because the files are different but simply due to log constraints. The rank being -1 does NOT mean that there weren't individual accesses to that file, it only means that we couldn't record them in the log due to space constraingt.
> Note that it does NOT mean that the record is missing. Those records also contain important information about the log and MUST be considered. In general, do NOT believe that number of records is the same as amount of usage. Some records can be much more important than other ones.

{data_sources}

You have two tools available to you that you MUST use in order to understand the log: ```get_schema``` to get the schema and the expert descriptions, and ```sql_query``` to run a sql query and get back results. You MUST run the tool get_schema to understand the schema before running sql_query. You must run either tool as many times as you'd like until you feel satisfied with the accuracy of the analysis in this section. Every number MUST come from the database and through a SQL query, however it is fine to use numbers from previous analysis sections, as those were all found by running SQL queries. However only do this if it's unequivocal and obvious and when in doubt/when the wording isn't clear, then rerun the query and recompute.

Do NOT use sql_query to get the schema of a table, instead use the expert descriptions. You will not need any other columns.

(sql_query uses postgres syntax).

Avoid doing arithmetic by hand. Remember to pay attention to the output example of the parent section. Avoid joining tables fully unnecessarily as they can be quite large.
"""

prompt_skel_header = """
Some global information about the job:
{header_info}
"""

prompt_skel_context = """
Here is some additional context about the job:
{context}
"""

prompt_skel_accum = """
Conclusions from previous sections:
{previous_section_conclusions}
"""
