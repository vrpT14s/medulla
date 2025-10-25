import chat
from markdown_to_dict import trees #i should change this to use anytree instead, later

#-----------------SECTION:STEM--------------------------
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
        snippet = "\n".join(f"{pi[0]} {pi[1]['title']}{'' if not pi[1].get('description') else ' - ' + pi[1]['description']}" for pi in parents)
        parents_toc = f"""
Snippet of table of contents for context:
{snippet}
""".strip()

    import nerves, descriptions, prompts
    node["sys_prompt"] = (
        prompts.prompt_skel_brain.format(
            title=node["title"],
            description=description,
            parents_toc=parents_toc,
        )
        + prompts.prompt_skel_medulla
        + prompts.prompt_skel_nerves.format(data_sources=descriptions.list_tables())
    )

    if node.get('context_from'):
        ctx_id = node['context_from']
        subnode = find_node_by_id(trees[0], ctx_id)
        #context = subnode['summary']
        context = '\n'.join([x['conclusion'] for x in subnode['value']['analysis']])
        print(context)
        #breakpoint()
        node["sys_prompt"] += prompts.prompt_skel_context.format(context=context)

    print(node['sys_prompt'])

def attach_node_value(node):

    approach = "Please rely on the title and the description."
    if node.get('approach'):
        approach = node['approach']
    node['chat'] = chat.create_chat(node["sys_prompt"], approach, breakpoint_on_failure = True, fact_list_from_output = lambda x: x['analysis'])

    while node.get('value') is None:
        node['value'] = node['chat'].run_until_completion() #i need to add flag handling after completion
    #assert node['value'], "Either mistake in code or ran out of retries"

    #breakpoint()
    print(f"pattern present - f{node.get('pattern_detected')}")


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

from anytree import Node, RenderTree
def dict_to_anytree(d, parent=None):
    # name is required
    node_name = d.get("title", "Unnamed")

    # other attributes
    node_attrs = {k: v for k, v in d.items() if k not in ("children", "title")}

    node = Node(node_name, parent=parent, **node_attrs)

    for child in d.get("children", []):
        dict_to_anytree(child, node)

    return node

root = dict_to_anytree(trees[0])
for pre, _, node in RenderTree(root):
    print(f"{pre}{node.name}: {getattr(node, 'description', '')}")
handle(trees[0])
print(RenderTree(dict_to_anytree(trees[0])))
from pprint import pprint
#pprint(trees[0])

breakpoint()
anyt = dict_to_anytree(trees[0])
for leaf in anyt.leaves:
    value = getattr(leaf, "value", None)
    if value and value.get('pattern_detected'):
        print(f"----- {leaf.name} -----")  # heading
        analysis_list = value.get('analysis', [])
        for i, item in enumerate(analysis_list):
            conclusion = item.get('conclusion')
            if conclusion:
                print(f"{i+1}. {conclusion}")
        print()  # newline between leaves
