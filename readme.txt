parse.py is the main file and calls chat.py (the llm interface) which calls tools.py (the sql handling stuff), load.py is for loading the preprocessed traces that are in tracebench. orig.md is what guides the llm.

To run, you need to add a gemini key and a model name and database path to the .env file and then run parse.py.

Code is pretty bad because of the deadline and also because I change things very often. But it does work and the llm has some error handling stuff where we ask it to fix its output too. I'll add more details in the paper draft explaining this.
