from pocketflow import Flow
from nodes import ParseDarshanLog, IterativeSymptomLoop, GenerateReport, OutputReport

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
