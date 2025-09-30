import sys

DB_PATH = sys.argv[1] if len(sys.argv) > 1 else "sw4.db"

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

Do not flag everything as an inefficiency. Only if you feel like you have good evidence, flag it as one. Treat it as a court of law.

"""
#Describe what you found out about the application and include a section about your reasoning, explaining what queries you sent and what you got in return.

prompt_skel_nerves = """
A data source is a collection of tables from a specific log along with expert descriptions of the columns and their uses. You only have one data source currently, a darshan log:


# Darshan log data source - 
> The tables are related in this way: both STDIO and MPIIO indirectly call POSIX. Thus a call in either will also indirectly show up in the POSIX table, but the I/O access pattern will be transformed.
> For example with MPIIO, if collective read/writes are used then many small writes can be transformed into one large write (collective buffering), and similarly many reads into one large read (data sieving). So there is a correlation between the two layers but not a one-to-one mapping of the I/O pattern.

> If the rank is -1 this simply means many ranks wrote to that file but to save log space, that log info was aggregated. You have info about the fastest and slowest ranks and the variance in times of each, but there's not as much information as a full listing. Again, this is not because the files are different but simply due to log constraints. The rank being -1 does NOT mean that there weren't individual accesses to that file, it only means that we couldn't record them in the log due to space constraingt.
> Note that it does NOT mean that the record is missing. Those records also contain important information about the log and MUST be considered. In general, do NOT believe that number of records is the same as amount of usage. Some records can be much more important than other ones.

{data_sources}

You have two tools available to you that you MUST use in order to understand the log: ```get_schema``` to get the schema and the expert descriptions, and ```sql_query``` to run a sql query and get back results. You MUST run the tool get_schema to understand the schema before running sql_query. You must run either as many times as you'd like until you feel satisfied with the accuracy of the analysis in this section. Every number MUST come from the database and through a SQL query. You MUST use these tools to make conclusions about this log.

Do NOT use sql_query to get the schema of a table, instead use the expert descriptions. You will not need any other columns.

Avoid doing arithmetic by hand.
"""

prompt_skel_context = """
Here is some additional context about the job:
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

    from tools import list_tables
    node["sys_prompt"] = (
        prompt_skel_brain.format(
            title=node["title"],
            description=description,
            parents_toc=parents_toc,
        )
        + prompt_skel_medulla
        + prompt_skel_nerves.format(data_sources=list_tables())
    )

    if node.get('context_from'):
        ctx_id = node['context_from']
        subnode = find_node_by_id(tree, ctx_id)
        context = subnode['summary']
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
        if node.get("summarize_children"):
            prompt = f"""
Summarize what this markdown tells us about the I/O of the application its analyzing:
#{node.get("title")}
{node.get("description")}

""" + "\n\n".join(f"##{child['title']}\n{child['value']}" for child in node["children"])

            node['summarychat'] = Chat(prompt, "")
            node['summary'] = node['summarychat'].call_llm()
            print(f"SUMMARY RECEIVED:\n{node['summary']}")
            
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
