import requests
import json
import pickle
import sys

# Set your OpenAI API key
GROQ_API_KEY="1234567890"

# Define the endpoint URL
url = "https://api.groq.com/openai/v1/chat/completions"
#url = "https://api.together.xyz/v1/chat/completions"

'''
"model": ",
"messages": [{
    "role": "user",
    "content": "How would I add a RAG when Im using the groqcloud api? i mean on my local computer on linux"
},

]
}' | tee out.txt
'''


headers = {
    "Authorization": f"Bearer {GROQ_API_KEY}",
    "Content-Type": "application/json",
}

#model="Qwen/Qwen3-235B-A22B-fp8-tput"

data = {
    #"model": "meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8",
    "model": "llama-3.1-8b-instant",
    #"model": "llama-3.1-70b",
    #"model": "deepseek-ai/DeepSeek-V3",
    #"model": model,
    "messages" : []
}

def request():
    res = requests.post(url, headers=headers, data=json.dumps(data))
    if res.status_code != 200:
        print(f"Request failed with status code {res.status_code}")
        print(res.text)
        breakpoint()
    return res.json()

loaded_filename = None
def save(filename=None):
    global loaded_filename, data
    if filename == '' or not filename:
        filename = loaded_filename
    if not filename:
        print("SYSTEM ERROR: No filename given or loaded.")
        breakpoint()
        return
    with open(f'{filename}.pkl', 'wb') as f:
        pickle.dump(data, f)
    if filename != loaded_filename:
        loaded_filename = filename

def load(filename):
    global data
    with open(f'{filename}.pkl', 'rb') as f:
        data = pickle.load(f)
    global loaded_filename
    loaded_filename = filename
    view()

def view():
    print("SYSTEM: viewing messages")
    for msg in data["messages"]:
        if msg["role"] == "user":
            print(">> ", end="")
        print(msg["content"])

def handle_command(t):
    c = t[1]
    if t[:2] == ":q" or t[:3] == ":wq":
        save()
        sys.exit(0)
    elif t[:2] == ':w':
        filename = t[3:].strip();
        save(filename)
    elif t[:2] == ':e':
        filename = t[2:].strip();
        load(filename)
    elif c == 'v':
        view()


while True:
    t = input("> ").strip()
    if (t == 'quit' or t == 'q'):
        break
    if (t == ':b'):
        breakpoint()
        continue
    if t[0] == ':':
        handle_command(t)
        continue
    data['messages'] += [{"role": "user", "content": t}]
    res = request()
    data['messages'] += [res['choices'][0]['message']]
    print(data['messages'][-1]['content'])
