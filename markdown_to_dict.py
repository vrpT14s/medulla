from mrkdwn_analysis import MarkdownAnalyzer

from dotenv import load_dotenv
import os
load_dotenv()
MD_FILE = os.getenv("MD_FILE")
assert MD_FILE

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

trees = parse_section_tree_list(headers)

with open(MD_FILE, 'r') as file:
    lines = file.readlines()

for tree in trees:
    attach_content(tree, lines)

#pprint(trees, sort_dicts=False)

def get_outline_trees():
    return trees
