from google.adk.tools import ToolContext
from typing import Dict, Any, List, Optional
from LineageAI.util.models import Subject

def set_current_subject(subject_data: Dict[str, Any], tool_context: ToolContext, title: Optional[str] = None):
    """Sets the primary individual being researched in the session state and optionally updates the session title."""
    if 'FirstName' in subject_data and 'RealName' not in subject_data:
        subject_data['RealName'] = subject_data.pop('FirstName')
    subject = Subject(**subject_data)
    tool_context.state['current_subject'] = subject
    if title:
        tool_context.state['session_title'] = title
    return {"status": "success", "message": "Current subject updated in state."}
def get_current_subject(tool_context: ToolContext) -> Subject:
    """Gets the primary individual being researched from the session state."""
    return tool_context.state.get('current_subject')

def add_records_to_subject(records: List[Dict[str, Any]], tool_context: ToolContext):
    """Adds a list of found records to the current subject in the session state."""
    if 'current_subject' not in tool_context.state:
        return {"status": "error", "message": "No current subject in state to add records to."}
    
    subject = get_current_subject(tool_context)
    subject.found_records.extend(records)
    
    return {"status": "success", "message": f"{len(records)} records added to state."}
