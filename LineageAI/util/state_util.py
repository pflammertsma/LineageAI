from google.adk.tools import ToolContext
from typing import Dict, Any

def set_current_subject(subject_data: Dict[str, Any], tool_context: ToolContext):
    """Sets the primary individual being researched in the session state."""
    tool_context.state['current_subject'] = subject_data
    return {"status": "success", "message": "Current subject updated in state."}

def add_records_to_subject(records: list, tool_context: ToolContext):
    """Adds a list of found records to the current subject in the session state."""
    if 'current_subject' not in tool_context.state:
        return {"status": "error", "message": "No current subject in state to add records to."}
    
    if 'found_records' not in tool_context.state['current_subject']:
        tool_context.state['current_subject']['found_records'] = []
        
    tool_context.state['current_subject']['found_records'].extend(records)
    return {"status": "success", "message": f"{len(records)} records added to state."}
