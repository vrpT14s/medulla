import pickle, sys

def save(obj, path="data.pkl"):
    with open(path, "wb") as f:
        pickle.dump(obj, f)

def load(path="data.pkl"):
    with open(path, "rb") as f:
        return pickle.load(f)

DB_PATH = sys.argv[1] if len(sys.argv) > 1 else "sw4.db"
tree = load(DB_PATH)
#print(tree)

patterns = [(c['title'], c['value']['pattern_detected']) for c in tree['children'][0]['children']]

from pprint import pprint

x = patterns
pprint([i[0] for i in x if i[1] == True])

y = tree['children'][0]['children']

if len(sys.argv) > 2:
    for i in y:
        print(i['title'])
        pprint(i['value'], sort_dicts=False)
        breakpoint()
