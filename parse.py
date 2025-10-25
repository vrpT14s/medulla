import sys
from dotenv import load_dotenv
import os

load_dotenv()
DB_PATH = os.getenv("DB_PATH")
assert DB_PATH

print(f"Using database: {DB_PATH}")

SAVE_PATH = DB_PATH + ".pkl"
MD_FILE="orig.md"
#-----------------SECTION:BRAIN--------------------------
from mrkdwn_analysis import MarkdownAnalyzer

analyzer = MarkdownAnalyzer(MD_FILE)
headers = analyzer.identify_headers()['Header']
'''
Shape of headers (flat list)
[
        {'line': 1, 'level': 1, 'text': 'HPC Job I/O Analysis'},
            {'line': 4, 'level': 2, 'text': 'Global Summary'},
            {'line': 14, 'level': 2, 'text': 'I/O Inefficiencies'},
                {'line': 22, 'level': 3, 'text': 'Small Transfer Sizes'},
                {'line': 31, 'level': 3, 'text': 'No Use of Collectives in MPI-IO'},
                {'line': 40, 'level': 3, 'text': 'Inefficient Use of Server Resources'}
]
'''


from pprint import pprint
pprint(headers)

def parse_section_tree(headers, start=0):
    '''starts at headers[start] and gets the full section tree of that heading'''
    cur = headers[start]
    tree = {
        'title': cur['text'],
        'line_start': cur['line']-1,
        'content_line_end': headers[start+1]['line']-1 if start+1 < len(headers) else None,
        'children': [],
        'children_line_end': None,
        'header_i': start
    }

    next_header_i = start + 1
    while True:
        if (next_header_i is None) or (next_header_i >= len(headers)):
            return (tree, next_header_i)
        nh = headers[next_header_i]
        if cur['level'] >= nh['level']:
            tree['children_line_end'] = nh['line']-1
            return (tree, next_header_i)
        (child, end) = parse_section_tree(headers, next_header_i)
        tree['children'].append(child)
        next_header_i = end


#we can't use this function directly in the main one because we need to find the line_end
def parse_section_tree_list(headers, start=0):
    trees = []
    while start < len(headers):
        (tree, end) = parse_section_tree(headers, start)
        start = end
        trees.append(tree)
    return trees

import yaml
def attach_content(root, lines):
    content_lines = "".join(lines[root["line_start"]:root["content_line_end"]])
    analyzer = MarkdownAnalyzer.from_string(content_lines)
    print(content_lines)

    cb = analyzer.identify_code_blocks().get("Code block")
    if cb is not None:
        assert(len(cb) == 1) #only 1 frontmatter
        frontmatter_text = cb[0]["content"] #TODO: default is yaml but add support for other langs like json
        print(frontmatter_text)
        frontmatter = yaml.safe_load(frontmatter_text)
        root |= frontmatter #adds all the k-v pairs to the root dict

    paras = analyzer.identify_paragraphs().get("Paragraph")
    if paras is not None:
        root['approach'] = "\n\n".join(paras)

    quotes = analyzer.identify_blockquotes().get('Blockquote')
    if quotes is not None:
        assert(len(quotes) == 1) #only 1 desc
        root['description'] = quotes[0]

    for child in root["children"]:
        attach_content(child, lines)

tree, end = parse_section_tree(headers, 0)
pprint(tree)

with open(MD_FILE, 'r') as file:
    lines = file.readlines()

attach_content(tree, lines)
pprint(tree, sort_dicts=False)
#-----------------SECTION:STEM--------------------------
prompt_skel_brain = """
You are an HPC I/O expert who will be analyzing the logs of a job. You will be given tools to interact with a database system containing these logs as tables. You are currently focusing on one section of a larger report, here is the title of this section: {title}

Here is some more information about this section -
{parents_toc}
{description}

The user may describe the approach of what to focus on in this section and how to get this from the logs.
"""

prompt_skel_medulla = """
Your analysis is in a list of queries and conclusions. You do not need to list all of the queries you have run, only the desicive ones that have confirmed your conclusion. Each conclusion needs a query to prove it, though.

You should submit your final analysis in json format such that it's directly parseable. However, after checking the analysis, if there are errors, you should fix those errors and respond with a new messages with the new complete and fixed final analysis. Here is an example of the structure of the data where we are analyzing for the number of small files:
{
    "pattern_detected": true,
    "analysis": [
        {
            "query": "SELECT AVG(CASE WHEN POSIX_MAX_BYTE_READ > POSIX_MAX_BYTE_WRITTEN THEN POSIX_MAX_BYTE_READ + 1 ELSE POSIX_MAX_BYTE_WRITTEN + 1 END)/1024/1024/1024 AS avg_filesize, COUNT(*) AS num_files FROM POSIX;",
            "output": [ { "avg_filesize" : 2.44, "num_files": 599 } ],
            "conclusion": "Average filesize is small (< 5 GB)."
        },
        {
            "query": "SELECT COUNT(*) * 1.0 / (SELECT COUNT(*) FROM POSIX) AS fraction_small_files FROM POSIX WHERE (CASE WHEN POSIX_MAX_BYTE_READ > POSIX_MAX_BYTE_WRITTEN THEN POSIX_MAX_BYTE_READ + 1 ELSE POSIX_MAX_BYTE_WRITTEN + 1 END) < 10 * 1024 * 1024 * 1024;",
            "output": [ { "fraction_small_files": 0.90 } ],
            "conclusion": "Most files are small: about 90% of files are smaller than 10 GB."
        }
    ]
}
You must submit your analysis even if you believe the pattern is not detected.
Your queries will be run and the output will be checked to see if they match and we'll check if it's the same, and all numbers are equal to two significant figures. We also ignore column order. If any of your outputs were wrong, we ask you to fix it, you must do so and send your new complete output in the same format afterwards, like I mentioned before.

Do not flag everything as an inefficiency. Only if you feel like you have good evidence, flag it as one. Treat it as a court of law. Even if you detect this inefficiency, consider whether or not it is useful to flag this to the user, i.e. how much percentage improvement in the application runtime could be received by fixing this inefficiency.

"""
#Describe what you found out about the application and include a section about your reasoning, explaining what queries you sent and what you got in return.

prompt_skel_nerves = """
A data source is a collection of tables from a specific log along with expert descriptions of the columns and their uses. You only have one data source currently, a darshan log:


# Darshan log data source -
> Darshan works by instrumenting function calls such as POSIX read()/write()/etc., STDIO's fwrite()/etc., and MPIIO's MPI_File_read_at() as well as all the other kinds of read, write, metadata functions available to MPI. The module then records properties of this function call before letting the underlying operation run. After the program is done, darshan then aggregates all this information into a log. Some properties recorded are 1) Operation counts for each kind of operation (POSIX reads, MPIIO collective writes, STDIO reads, etc.), 2) a course histogram of access sizes for read/write ops (it needs to be course because darshan needs to have low overhead), 3) timestamps at which the file was open and closed and when the first and last reads and writes happened, 4) net time taken for all operations for read and write and meta, as well as the maximum time taken for a single operation, and the size of this maximum time. It also records other properties such whether access was sequential and consecutive for POSIX and records the top 4 most common strides and access sizes as well.
> When an MPIIO operation is called, the MPIIO library usually transforms this operation to get better performance, and then calls an underlying POSIX function to do the actual read/write. Thus a read operation will be seen both in the MPIIO layer and a transformed version in the POSIX layer. For example, operations can be aggregated between ranks on the same node causing the POSIX layer to have only one rank per physical node do I/O. In that case the access sizes will be larger because all the data has been aggregated into one rank.
> In general darshan usually has limited information. For example it doesn't record all access sizes (as that would cause too much overhead) but only records a coarse histogram and the top 4 most common ones. Sometimes 4 is enough for almost all operations and sometimes 4 isn't. You can tell how well the log captures information by checking the operation frequencies in this case.
> Another issue is that if a file is accessed by all ranks then darshan aggregates that log, i.e. it only records the total number of reads by summing all of them and doesn't record per-rank statistics. This is only to decrease overhead. However this aggregation is sometimes disabled by cluster admins, in which case each rank gets its own record in the log. These aggregated records can be very important since a lot of the time the main file in an application is a shared file accessed by all ranks. Aggregated records can mess with timing calculations if you don't pay attention. The timestamps are calculated by taking minimums and maximums (the read start time is the minimum, the read end is the maximum, etc.) while the cumulative time values are calculated by taking the sums. Thus you can't compare the two directly or cumulative operation time values with total runtime as they have different meanings: total runtime and timestamp values are about the maximums over all ranks and is viewed from a single rank while cumulative time values are about the sums over all ranks.
> In case the record is aggregated, the rank column will hold the value -1. Remember that this does not mean that the record is missing. If MMAP or other counters have -1 though, it does mean that it's missing. So rank is an exception when it comes to the meaning of -1.

> Darshan also stores data for how a file is striped over OST's in the lustre table, though not always. Some clusters opt out of this data or the log was from before this was introduced, in those cases the information will not be present.

{data_sources}

Here is the number of procs and runtime in seconds:
{header}

You have two tools available to you that you MUST use in order to understand the log: ```get_schema``` to get the schema and the expert descriptions, and ```sql_query``` to run a sql query and get back results. You MUST run the tool get_schema to understand the schema before running sql_query. You must run either as many times as you'd like until you feel satisfied with the accuracy of the analysis in this section. Every number MUST come from the database and through a SQL query. You MUST use these tools to make conclusions about this log.

Do NOT use sql_query to get the schema of a table, instead use the expert descriptions. You will not need any other columns.

Avoid doing arithmetic by hand.
"""

prompt_skel_context = """
Here are some observations found in prior investigations to give you a wider context about the job:
{context}
"""

def find_node_by_id(tree, target_id):
    """
    Recursively search the tree rooted at `node` for a node with id == target_id.
    Returns the node dict if found, else None.
    """
    if tree.get("id") == target_id:
        return tree

    for child in tree.get("children", []):
        result = find_node_by_id(child, target_id)
        if result:
            return result

    return None


def attach_prompt(node, parents):
    description = ""
    if node.get("description"):
        description = f"\nDescription of current section: {node['description']}"

    parents_toc = "This is the topmost root section."
    if parents:
        snippet = "\n".join(f"{pi[0]} {pi[1]['title']}{'' if not pi[1]['description'] else ' - ' + pi[1]['description']}" for pi in parents)
        parents_toc = f"""
Snippet of table of contents for context:
{snippet}
""".strip()

    from tools import list_tables, sql_query
    node["sys_prompt"] = (
        prompt_skel_brain.format(
            title=node["title"],
            description=description,
            parents_toc=parents_toc,
        )
        + prompt_skel_medulla
        + prompt_skel_nerves.format(
            data_sources=list_tables(),
            header=sql_query('select nprocs, runtime from HEADER')['output'][0],
            )
    )

    if node.get('context_from'):
        ctx_id = node['context_from']
        subnode = find_node_by_id(tree, ctx_id)
        context = subnode['value']
        node["sys_prompt"] += prompt_skel_context.format(context=context)

    print(node['sys_prompt'])

#TODO: Chat interface from chat.py

from chat import Chat
def attach_node_value(node):
    #run the chat and get back the output. if the output is wrong then tell the chat that

    node['chat'] = Chat(node["sys_prompt"], DB_PATH)

    approach = "Please rely on the title and the description."
    if node.get('approach'):
        approach = node['approach']
    node['chat'].add_msg("user", approach)
    node['value'] = node['chat'].__run__()
    #breakpoint()


def handle(node, parents=None, number_prefix="1"):
    if parents is None:
        parents = []

    # Compute the current section number
    if parents:
        section_number = f"{number_prefix}"
    else:
        section_number = "1"

    # Append current node to parents
    current_parents = parents + [(section_number, node)]

    if node.get("children"):
        # Node has children: recurse into them
        for idx, child in enumerate(node["children"], 1):
            child_number_prefix = f"{section_number}.{idx}"
            handle(child, current_parents, number_prefix=child_number_prefix)
#        if node.get("summarize_children"):
#            prompt = f"""
#Summarize what this markdown tells us about the I/O of the application its analyzing:
##{node.get("title")}
#{node.get("description")}
#
#""" + "\n\n".join(f"##{child['title']}\n{child['value']}" for child in node["children"])
#
#            node['summarychat'] = Chat(prompt, "")
#            node['summary'] = node['summarychat'].call_llm()
#            print(f"SUMMARY RECEIVED:\n{node['summary']}")

    else:
        # Leaf node: attach prompt and run LLM
        attach_prompt(node, current_parents)
        attach_node_value(node)
        print(f"Section {section_number}: {node['title']}")
        print(node['value'])

handle(tree)
pprint(tree)

import pickle
def save(obj, path="data.pkl"):
    with open(path, "wb") as f:
        pickle.dump(obj, f)

def load(path="data.pkl"):
    with open(path, "rb") as f:
        return pickle.load(f)

save(tree, SAVE_PATH)



#
#def summarize_node(node, parents):
#    #useful for global summary
#    pass
#
#def generate_document(node):
#    pass
#

#-----------------NERVES------------------------
#copy tools from tools.py
#get data source descriptions, table descriptions, column descriptions
#pass to chat.py
