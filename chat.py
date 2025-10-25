import json
import time
import sqlite3
import yaml
import json
from dotenv import load_dotenv
import os
#import litellm
import yaml
import re
from google import genai
from google.genai import types

from tools import *

load_dotenv()
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

from typing import Optional, Union
from pydantic import BaseModel, ConfigDict


class Observation(BaseModel):
    #model_config = ConfigDict(extra='forbid')

    query: Optional[str]
    output: Optional[list[list[(str, Union[str, float, int])]]]
    conclusion: str

class Result(BaseModel):
    #model_config = ConfigDict(extra='forbid')

    inefficiency_detected: bool
    analysis: list[Observation]

class Chat:
    def __init__(self, sys_prompt: str, no_tools = False):
        self.messages = []
        self.garbage = []
        self.tools = tools
        if no_tools: self.tools = None
        self.sys_prompt = sys_prompt

        self.add_sys(sys_prompt)

        self.value = None
        self.ended = False
        self.error = True

        self.output_retries = 0


    @staticmethod
    def make_msg(role: str, text: str):
        """
        Create a Google GenAI-compatible message for chat history.
        role: "user" or "model"
        text: message text
        """
        #return { "role" : role, "content" : text }
        mytextpart = types.Part.from_text(text=text)
        return types.Content(
            role=role,
            parts=[mytextpart]
        )

    def add_msg(self, role: str, txt: str):
        self.messages.append(self.make_msg(role, txt))

    def add_sys(self, txt: str):
        self.add_msg("system", txt)

    def add_user(self, txt: str):
        self.add_msg("user", txt)

    def add_tool_output(self, name: str, response: dict):
        self.messages.append(
            types.Content(
                role="user",
                parts=[
                    types.Part(
                        function_response=types.FunctionResponse(
                            name=name,
                            response=response
                        )
                    )
                ]
            )
        )

    def process_tool_calls(self, last, extra=dict()): #raw non-dict message
        call_present = False

        print("checking func calls")
        breakpoint()
        if last.parts is None:
            return


        for part in last.parts:
            if part.function_call:
                call_present = True
                function_name = part.function_call.name
                function_args = part.function_call.args or {}
                function_to_call = tool_registry[function_name]

                print(f"processing tool call {function_name} with args {function_args}")

                function_response = function_to_call(
                    **function_args,
                    **extra,
                )

                self.add_tool_output(function_name, function_response)
        if not call_present:
            print("NO TOOL CALL!!")

    def call_llm_full(self):
        print(f"USING MODEL: {os.getenv('LLM_MODEL')}")
        print(f"Us: {self.messages[-1]}\n")
        response = client.models.generate_content(
            model=os.getenv("GEMINI_MODEL"),    # e.g., "gemini-1.5-pro"
            contents=self.messages[1:],           # your accumulated Content list
            config=types.GenerateContentConfig(
                automatic_function_calling=types.AutomaticFunctionCallingConfig(
                    maximum_remote_calls=15
                ),
                system_instruction=self.messages[0],
                max_output_tokens=8096,
                thinking_config=types.ThinkingConfig(thinking_budget="1024"),
                # temperature=0.7, top_p=0.9, etc.
                tools=[get_schema, sql_query],
                #responseSchema = Result
            ),
        )
        main_response = response.candidates[0]

        print("Response received")
        self.messages.append(main_response.content)
        #print(f"ASSISTANT: {main_response.text}")
        #self.process_tool_calls(response)
        #if (response.text == None):
        #    self.add_user("You haven't submitted your analysis yet. Continue analyzing by using sql_query and get_schema then submit your analysis in the json schema I mentioned at the start in my first message.")
        #    return response
        #print(self.messages[-1])
        #breakpoint()
        #self.strip_old_tool_calls()
        return response

    def call_llm(self):
        return self.call_llm_full().content

    def __run__(self, max_retries=10, base_delay=1, max_delay=60):
        retries = 0
        delay = 3  # normal delay between successful polls

        while True:
            for _ in [1]:
            #try:
                output = self.call_llm_full()

                if output.text:
                    try:
                        cleaned = re.sub(r"<think>.*?</think>", "", output.text.strip(), flags=re.DOTALL).strip()
                        if cleaned == "": continue
                        # Remove <json> ... </json>
                        if cleaned.startswith("<json>") and cleaned.endswith("</json>"):
                            cleaned = cleaned[len("<json>"):-len("</json>")].strip()
                        # Remove ```json ... ```
                        elif cleaned.startswith("```json") and cleaned.endswith("```"):
                            cleaned = cleaned[len("```json"): -len("```")].strip()
                        elif cleaned.startswith("```") and cleaned.endswith("```"):
                            cleaned = cleaned[len("```"):-len("```")].strip()

                        # Remove any leading non-JSON characters
                        valid_starts = ('[', '{', '}', ']')
                        for i, ch in enumerate(cleaned):
                            if ch in valid_starts:
                                cleaned = cleaned[i:]
                                break

                        cleaned = re.sub(r"```json", "", cleaned.strip(), flags=re.DOTALL).strip()
                        cleaned = re.sub(r"<json>", "", cleaned.strip(), flags=re.DOTALL).strip()
                        cleaned = re.sub(r"</json>", "", cleaned.strip(), flags=re.DOTALL).strip()
                        cleaned = re.sub(r"```", "", cleaned.strip(), flags=re.DOTALL).strip()


                        value = json.loads(cleaned)
                    except Exception as e:
                        breakpoint()
                        self.add_user(f"""
There was an error parsing your final analysis json: {e}
This was not a problem with what was inside, it was a problem with the json. You must ONLY respond with json text, do NOT include any text at the beginning that is not json. Please fix whatever was the issue here and send your new, fixed output, and the system will try to parse it again. Your next message should be the new output, do NOT respond with anything that is not json.
""")
                        continue
                    try:
                        self.pattern_detected = value['pattern_detected']
                        if not (self.pattern_detected == True or self.pattern_detected == False):
                            print("Error.")
                            breakpoint()
                    except Exception as e:
                        breakpoint()
                        self.add_user(f"""
There was an error: {e}
We were able to parse your json but the shape is wrong, specifically we couldn't find the value of pattern_detected.
""")
                        continue

                    self.value = value

                    if self.check_queries(value) == True:
                        return self.value
                    retries = 0
                    time.sleep(delay)

            #except Exception as e:
            #    print(f"Error during call: {e}")
            #    breakpoint()
            #    if retries >= max_retries:
            #        print("Max retries reached, aborting.")
            #        return None

            #    backoff = min(base_delay * (2 ** retries), max_delay)
            #    print(f"Retrying in {backoff} seconds...")
            #    time.sleep(backoff)
            #    retries += 1

    def check_queries(self, value):
        for a in value["analysis"]:
            llm_query = a['query']
            llm_output = a['output']

            if llm_query is None or llm_query.strip() == "":
                continue #should i let the llm fill the whole list with empty queries? lol

            true_output = sql_query(llm_query)
            if true_output.get('error') is not None:
                print("SQL Error")
                self.add_user(f"""Your query:
{llm_query}
had an error while running. Please fix it. If you added something like 'N/A' then please remove that and replace the query with null.
Specifically, here is the error:
{true_output['error']}
Fix it and resend the full, complete, fixed output.
""")
                return False
            true_output = true_output['output']
            diff = diff_query_output(true_output, llm_output)
            if diff is not None:
                if self.output_retries > 0:
                    del self.messages[-2]
                    del self.messages[-3]

                self.output_retries += 1
                self.add_user(f"""
One of the outputs you gave did not match the query output we gave.
It was for this query:
{llm_query}

This is the correct output:
{json.dumps(true_output)}

This was the output you passed:
{json.dumps(llm_output)}

Please correct this output, or if your query was wrong, change your query. You might need to change your analysis based on this as well. Send your new output afterwards.
""")
                return False
        print("\n\nNo errors in llm output found.\n")
        return True


#    def __run__(self):
#        while True:
#            output = self.call_llm_full()
#            print("Assistant:", output.content)
#            print("Reasoning:", output.reasoning)
#
#            final = self.extract_final_yaml(output.content)
#            if final is not None:
#                #cont = input("Node finished. Press enter: ")
#                print("Node finished.\n")
#                return final
#
#            #cont = input("Press Enter to continue, or type 'q' to quit: ")
#            #if cont.lower() == 'q':
#            #    return None
#            import time
#            time.sleep(5)

if __name__ == '__main__':
    Chat('sqlite/final.sqlite').__run__()

#--------------------------------------------------------------------------------

def round_sig(x, sig_figs):
    """Round a number to the given number of significant figures."""
    if x == 0:
        return 0
    from math import log10, floor
    return round(x, sig_figs - int(floor(log10(abs(x)))) - 1)

def diff_query_output(a, b, sig_figs=1):
    """
    Compare two list-of-dicts objects.
    Numbers are compared up to sig_figs significant figures.
    List order is ignored.
    Returns None if equal, else a string describing the differences.
    """
    assert sig_figs >= 1

    # Helper to normalize dicts: round floats to sig_figs, leave others as-is
    def normalize(d):
        norm = {}
        for k, v in d.items():
            if isinstance(v, (float, int)):
                norm[k] = round_sig(v, sig_figs)
            else:
                norm[k] = v
        return norm

    # Normalize both lists
    norm_a = [normalize(d) for d in a]
    norm_b = [normalize(d) for d in b]

    # Since order doesn't matter, convert lists of dicts to sets of tuples
    set_a = {tuple(sorted(d.items())) for d in norm_a}
    set_b = {tuple(sorted(d.items())) for d in norm_b}

    if set_a == set_b:
        return None  # they are equal

    return True

#------------------------------------------------------
