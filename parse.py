import chat
from markdown_to_tree import root

#-----------------SECTION:STEM--------------------------
from anytree.search import find
def find_node(root, name):
    return find(root, lambda n: n.name == name)


def attach_prompt(node):
    if node.example != '':
        example = f"Example analysis:\n{node.example}"
    else:
        example = ''

    assert len(node.ancestors) != 0
    nums = [] #bug if we're dealing with topmost section
    table_of_contents = []
    for p in list(node.ancestors[1:]) + [node]:
        nums += [p.child_number]
        section_number = '.'.join(str(num) for num in nums)
        node.section_number = section_number
        text = f"{section_number} - {p.title}"
        #breakpoint()
        if hasattr(p, 'example') and p.example:
            text += f" [Example: {p.example}]"
        table_of_contents += [text]
    parents_toc = '\n'.join(table_of_contents)

    import nerves, descriptions, prompts
    node.sys_prompt = (
        prompts.prompt_skel_brain.format(
            title=node.title,
            example=example,
            parents_toc=parents_toc,
        )
        + prompts.prompt_skel_medulla
        + prompts.prompt_skel_nerves.format(data_sources=descriptions.list_tables())
        + prompts.prompt_skel_header.format(header_info=nerves.sql_query("select nprocs, runtime from header;")['output'][0])
    )

    if hasattr(node, 'context_from'):
        ctx_id = node.context_from
        subnode = find_node(root, ctx_id)
        #context = subnode['summary']
        #context = '\n'.join([x['conclusion'] for x in subnode['value']['analysis']])
        context  = get_value(subnode)
        print(context)
        #breakpoint()
        node.sys_prompt += prompts.prompt_skel_context.format(context=context)

    if getattr(node.parent, 'children_eval', None) == 'sequential':
        siblings = node.parent.children
        assert node in siblings
        less_siblings = siblings[:siblings.index(node)]
        if len(less_siblings) > 0:
            previous_section_conclusions = '\n'.join(sib.value for sib in less_siblings)
            node.sys_prompt += \
                prompts.prompt_skel_accum.format(previous_section_conclusions=previous_section_conclusions)

    print(node.sys_prompt)

def attach_node_value(node):
    approach = getattr(node, 'approach', "Please rely on the title and the description.")
    node.chat = chat.create_chat(node.sys_prompt, approach, breakpoint_on_failure = True, fact_list_from_output = lambda x: x)

    while getattr(node, 'facts', None) == None:
        node.facts = node.chat.run_until_completion() #i need to add flag handling after completion

    conclusions = '\n'.join([fact['conclusion'] for fact in node.facts])
    node.value = f"> {node.section_number}: {node.title}\n{conclusions}\n"
    print(node.value)
    breakpoint()


def handle(node):
    if len(node.children) > 1:
        for child in node.children:
            handle(child)

        subsections = '\n'.join([child.value for child in node.children])
        node.value = f"> {node.section_number}: {node.title}\n{subsections}\n"
    else:
        attach_prompt(node)
        attach_node_value(node)

def get_value(node):
    if getattr(node, 'value'):
        return node.value
    else:
        handle(node)

from anytree import RenderTree
for pre, _, node in RenderTree(root):
    print(f"{pre}{node.name}: {getattr(node, 'example', '')}")
handle(root)

for pre, _, node in RenderTree(root):
    print(f"{pre}{node.name}: {getattr(node, 'value', '')}")
#for leaf in root.leaves:
#    value = getattr(leaf, "value", None)
#    if value and value.get('pattern_detected'):
#        print(f"----- {leaf.name} -----")  # heading
#        analysis_list = value.get('analysis', [])
#        for i, item in enumerate(analysis_list):
#            conclusion = item.get('conclusion')
#            if conclusion:
#                print(f"{i+1}. {conclusion}")
#        print()  # newline between leaves
