import os
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

url = "https://api.groq.com/openai/v1/chat/completions"
model = os.getenv("MODEL")
if not model: model = "llama-3.1-8b-instant"

headers = {
    "Authorization": f"Bearer {GROQ_API_KEY}",
    "Content-Type": "application/json",
}

def chat_llm(messages):
    data = {
        "model": model,
        "messages": messages,
    }
    res = requests.post(url, headers=headers, json=data)
    if res.status_code != 200:
        print(f"Groq API request failed with status code {res.status_code}")
        print(res.text)
        raise RuntimeError("Groq API request failed")
    response_json = res.json()
    return response_json["choices"][0]["message"]["content"]


def call_llm(prompt):
    print("[call_llm] Latest prompt sent to LLM:\n", prompt)
    return chat_llm([
        {"role": "user", "content": prompt}
    ])

if __name__ == "__main__":
    prompt = """You have access to tools. Here are the tools available
- db_query - which takes in an sql query
- add_conclusion - adds conclusion to list (text)

Using these tools, please try to find out more about the database. the database contains hpc darshan i/o logs and you will want to find inefficient i/o patterns.
"""
    print(call_llm(prompt))
