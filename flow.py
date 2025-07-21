from pocketflow import Flow
from nodes import GetQuestionNode, AnswerNode, ParseDarshanLog, IterativeSymptomLoop, GenerateReport, OutputReport

def create_qa_flow():
    """Create and return a question-answering flow."""
    # Create nodes
    get_question_node = GetQuestionNode()
    answer_node = AnswerNode()
    
    # Connect nodes in sequence
    get_question_node >> answer_node
    
    # Create flow starting with input node
    return Flow(start=get_question_node)

qa_flow = create_qa_flow()

# New Darshan I/O inefficiency analysis flow
def create_darshan_flow():
    """Create and return the Darshan I/O inefficiency analysis flow."""
    parse_node = ParseDarshanLog()
    loop_node = IterativeSymptomLoop()
    report_node = GenerateReport()
    output_node = OutputReport()
    
    parse_node >> loop_node >> report_node >> output_node
    return Flow(start=parse_node)

darshan_flow = create_darshan_flow()