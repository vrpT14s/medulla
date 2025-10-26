def process_node(node):
    if getattr(node, "children_eval", None) == "sequential" and len(node.children) > 1:
        for child in node.children:
            if len(child.children) > 1:
                child.children_eval = 'sequential'

    if hasattr(node, "context_from"):
        for child in node.children:
            child.context_from = node.context_from

    print(node.title)

    i = 1
    for child in node.children:
        child.child_number = i
        i += 1
        process_node(child)
