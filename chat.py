import time
from dataclasses import dataclass, field
import nerves
import prompts
import json
import re
from google import genai
from google.genai import types

import os
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))


@dataclass
class Chat:
    messages: list = field(default_factory=list)
    breakpoint_on_failure: bool = False

    #function to get list of facts, if pattern_detected behaviour is on then you need to change it to lambda x: x['analysis']
    fact_list_from_output: callable = field(default=lambda x: x)

    #retries run if queries/output fails or other parsing failure
    #max number of retries is max_runs
    def run_until_completion(self, max_runs=10):
        delay = 3 #seconds

        for i in range(max_runs):
            response = self.run_once()
            if response == '' or response is None:
                print("empty response received.")
                continue

            #this adds error message onto the message list so that will get treated in the next loop
            validated_response = self.get_validated_response(response)
            if validated_response is not None:
                return validated_response

            #time.sleep(delay) #i dont think i need a delay

        breakpoint()
        print(f"Model couldn't fix output after {max_runs}, probably never going to get it.")
        return None

    def check_flag(self, flag, max_retries = 10):
        prompt = prompts.check_flags.format(flag=flag)
        self.add_user_msg(prompt)
        for _ in range (max_retries):
            text = self.run_once()
            out = self.parse_output_text(text)
            if out != None:
                print(out)
                return out
        breakpoint()
        return None

    def add_user_msg(self, text: str):
        #refer to the confusing genai api docs
        mytextpart = types.Part.from_text(text=text)
        content = types.Content(
            role="user", #if you want to add a system message, change to system (but i don't need that)
            parts=[mytextpart]
        )
        self.messages.append(content)

    def run_once(self) -> str:
        try:
            response = client.models.generate_content(
                model=os.getenv("GEMINI_MODEL"),    # e.g., "gemini-1.5-pro"
                contents=self.messages[1:],
                config=types.GenerateContentConfig(
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(
                        maximum_remote_calls=15
                    ),
                    system_instruction=self.messages[0],
                    max_output_tokens=8096,
                    thinking_config=types.ThinkingConfig(thinking_budget="1024"),
                    # temperature=0.7, top_p=0.9, etc.
                    tools=nerves.agent_tools,
                    #responseSchema = Result #i don't use this because gemini doesn't allow dicts in the schema
                ),
            )
        except Exception as e:
            print(f"Error running completion: {e}")
            print("Waiting 10 seconds then rerunning.")
            time.sleep(10)
            return ""



        main_response = response.candidates[0].content
        self.messages.append(main_response)
        if not hasattr(response, 'text'):
            print("For some reason the model didn't return visible text, maybe it spent all of its tokens on thinking tokens? Or could be malformed function call. Returning empty string.")
            breakpoint()
            return ""
        return response.text

    def parse_output_text(self, response_text):
        cleaned_text = cleanup_response_text(response_text) #removes <json> etc.
        try:
            json_output = json.loads(cleaned_text)
        except json.JSONDecodeError as parse_err:
            if self.breakpoint_on_failure:
                breakpoint()
            user_prompt = prompts.json_parse_err.format(parse_err=parse_err, cleaned_text=cleaned_text)
            print(f"JSON Parsing failed: {user_prompt}") #log
            self.add_user_msg(user_prompt)
            return None

        return json_output

    #fact needs to be a dict with both 'query' and 'output' attributes
    def validate_fact(self, fact) -> bool:
        '''runs queries and checks if outputs match'''
        llm_query = fact['query']
        llm_output = fact['output']

        if llm_query is None or llm_query.strip() == "":
            return True #should i let the llm fill the whole list with empty queries? lol

        true_output_wrapped = nerves.sql_query(llm_query)
        if true_output_wrapped.get('error') is not None:
            err_msg = prompts.output_query_run_err.format(run_err=true_output_wrapped['error'], llm_query=llm_query)
            print(f"Validate query run failed: {err_msg}") #log
            self.add_user_msg(err_msg)
            return False

        true_output = true_output_wrapped['output']
        diff = diff_query_output(true_output, llm_output)
        if diff is not None:
            err_msg = prompts.output_query_match_err.format(llm_query=llm_query, llm_output=llm_output, true_output=true_output)
            print(f"Validate query match failed: {err_msg}") #log
            self.add_user_msg(err_msg)
            return False
        return True

    def get_validated_response(self, response_text):
        parsed_response = self.parse_output_text(response_text)
        if parsed_response is None:
            return None

        for fact in self.fact_list_from_output(parsed_response):
            if self.validate_fact(fact) is False:
                return None

        return parsed_response

def create_chat(sys_prompt: str, user_prompt, breakpoint_on_failure: bool = False, fact_list_from_output: bool = lambda x: x) -> Chat:
    messages = [sys_prompt]

    chat = Chat(messages=messages, breakpoint_on_failure=breakpoint_on_failure, fact_list_from_output=fact_list_from_output)
    if user_prompt is not None:
        chat.add_user_msg(user_prompt)
    return chat



#-------------------------------------------------- HELPERS BELOW --------------------------------------------------


#this doesn't need to be a class function because it doesn't need to add errors to context
def cleanup_response_text(response_text): #bit of a dirty function
    '''removes <json>, ``` markers that the model might have added by accident, so we can parse with json after'''
    cleaned = re.sub(r"<think>.*?</think>", "", response_text.strip(), flags=re.DOTALL).strip()
    assert cleaned != ""
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

    return cleaned

# this is to compare output against db vs output given by llm
# might need to sort query output so they match up so its easier to compare the two? or match up ours with the llm's?

def round_sig(x, sig_figs):
    """Round a number to the given number of significant figures."""
    if x == 0:
        return 0
    from math import log10, floor
    return round(x, sig_figs - int(floor(log10(abs(x)))) - 1)

from collections.abc import Hashable
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
            elif not isinstance(v, Hashable):
                return True
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

if __name__ == '__main__':
    print(create_chat("You are a helpful person", "What is 3 + 3").run_once())
