import json
import sqlite3
from groq import Groq
import yaml
import json
from dotenv import load_dotenv
from tools import *
import os

load_dotenv()
client = Groq()

class Chat:
    def __init__(self, db_path: str):
        self.messages = []
        self.garbage = []
        self.tools = tools
        print("tools is", tools)
        self.db_path = db_path

        sys_prompt = f"""
You are an expert in HPC I/O analysis. You will be analyzing a darshan log to search it for inefficient I/O patterns.

The log is accesible through a database table, containing counters as columns and ranks as rows. You will use tools to interact with the database table. This information will go into a scratchpad that will be removed from context/message history after use. You can reuse tools as you see fit if necessary.

Please explain your reasoning as you go along. You are expected to query the database, make some conclusions based on that, then query again to test your hypotheses and make more conclusions. So it will be an investigation. Please add explanations after every 2 or 3 tool calls or sooner. Try to make your query output not too large. If its possible to do multiple things in a query, you can try that.

Try to look at all both POSIX and MPIIO.

Here are the tables currently in the database:
""" + list_tables(db_path)

        self.add_sys(sys_prompt)



    def add_msg(self, role: str, txt: str):
        self.messages.append({
            "role": role,
            "content": txt,
        })

    def add_sys(self, txt: str):
        self.add_msg("system", txt)


    def add_tool_output(self, tool_call_id: str, name: str, content: str):
        self.messages.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "name": name,
            "content": content,
        })

    def process_tool_calls(self, last): #raw non-dict message
        assert(last.role == 'assistant')

        if not hasattr(last, "tool_calls") or not last.tool_calls:
            print("NO TOOL CALLS!!!!")
            return

        for tool_call in last.tool_calls:
            function_name = tool_call.function.name
            function_to_call = tool_registry[function_name]
            function_args = json.loads(tool_call.function.arguments)

            print(f"processing tool call f{function_name} with args f{function_args}")

            extra = {"db_path": self.db_path}
            function_response = function_to_call(
                    **function_args,
                    **extra,
            )

            self.add_tool_output(
                    tool_call.id,
                    function_name,
                    function_response,
            )

    def strip_old_tool_calls(self):
        self.garbage += [msg for msg in self.messages if msg.get('role') == 'tool']
        self.messages = [msg for msg in self.messages if msg.get('role') != 'tool']

    def call_llm(self):
        print(f"USING MODEL: {os.getenv('GROQ_MODEL')}")
        response = client.chat.completions.create(
            model=os.getenv("GROQ_MODEL"),
            messages=self.messages, # Conversation history
            stream=False,
            tools=self.tools, # Available tools (i.e. functions) for our LLM to use
            tool_choice="auto", # Let our LLM decide when to use tools
            max_completion_tokens=4096 # Maximum number of tokens to allow in our response
        )
        print("Response received")
        breakpoint()
        msg = response.choices[0].message
        #self.messages.append(msg.dict())
        self.messages.append(msg.model_dump(include={"role", "content"}))
        #self.strip_old_tool_calls()
        self.process_tool_calls(msg)
        return msg.content

    def __run__(self):
        while True:
            output = self.call_llm()
            print("Assistant:", output)

            cont = input("Press Enter to continue, or type 'q' to quit: ")
            if cont.lower() == 'q':
                break

if __name__ == '__main__':
    Chat('sqlite/final.sqlite').__run__()
