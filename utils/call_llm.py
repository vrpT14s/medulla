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

def call_llm(prompt):
    data = {
        "model": model,
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }
    res = requests.post(url, headers=headers, json=data)
    if res.status_code != 200:
        print(f"Groq API request failed with status code {res.status_code}")
        print(res.text)
        raise RuntimeError("Groq API request failed")
    response_json = res.json()
    return response_json["choices"][0]["message"]["content"]

if __name__ == "__main__":
    prompt = "What is the meaning of life?"
    print(call_llm(prompt))
