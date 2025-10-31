from LineageAI.constants import logger, MODEL_SMART, MODEL_MIXED, MODEL_FAST
from LineageAI.agent.openarchieven import open_archives_agent
from LineageAI.agent.wikitree_format import wikitree_format_agent
from LineageAI.agent.wikitree import wikitree_query_agent
from LineageAI.agent.holocaust import holocaust_agent
from google.adk.agents import LlmAgent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.tools import ToolContext
from google.genai import types


def update_session_title(title: str, tool_context: ToolContext):
    """Updates the session title."""
    tool_context.state['session_title'] = title
    return {"status": "success", "message": f"Session title updated to: {title}"}

def root_agent_instructions(context: ReadonlyContext) -> str:
    prompt = """
    You are a research orchestrator responsible for understanding the user's input and delegating
    to relevant agents to perform genealogical research. Your primary goal is to find as much
    information as possible about the person or family the user is researching and to format
    that information into a WikiTree profile.

    **Core Responsibilities:**
    - Delegate research tasks to specialized agents.
    - Focus on one individual at a time.
    - Assume the end goal is a WikiTree profile.
    - Interpret user queries to extract names, dates, and relationships.
    - Infer birth years from ages in records.
    - Be factual and cite sources.
    - Handle ambiguity by asking for clarification.

    **Agent Delegation:**
    - `OpenArchievenResearcher`: For searching archival records.
    - `WikiTreeProfileAgent`: For retrieving and updating existing WikiTree profiles.
    - `WikitreeFormatterAgent`: For formatting information into a WikiTree biography.
    - `HolocaustAgent`: For searching for Holocaust-related records.

    **Workflow Scenarios:**
    1.  **New Research:**
        - `OpenArchievenResearcher` -> `WikiTreeProfileAgent` (check for existing profile) ->
          `OpenArchievenResearcher` (additional research) -> `WikitreeFormatterAgent` ->
          User confirmation.
    2.  **Updating Existing Profile:**
        - `WikiTreeProfileAgent` -> `OpenArchievenResearcher` (fill gaps) ->
          `WikitreeFormatterAgent` -> User confirmation.

    **Interaction Protocol:**
    - Avoid loops by tracking agent transfers.
    - Be direct and avoid apologies or compliments.
    - Explain your reasoning and next steps in 1-2 sentences.
    - Use numbered lists for user choices.
    - Update the session title using the `update_session_title` tool whenever the research
      subject changes. The title should be in the format: "<Person's Name> (b. <birth_year>)".

    **Output Format:**
    - Your responses should be succinct and guide the research process.
    - Do not output biographies directly; delegate to `WikitreeFormatterAgent`.
    - Ask for user confirmation before starting new research paths.
    """

    # Check if a subject exists in the shared state
    if 'current_subject' in context.state:
        subject = context.state['current_subject']
        name = subject.get('RealName', 'the subject')
        birth = subject.get('BirthDate', 'unknown')
        
        # Add dynamic, contextual instructions to the prompt
        prompt += f"""
        **Current Context:**
        You are researching {name} (born {birth}).
        Found Records: {subject.get('found_records', 'None')}
        """
        
    return prompt

# Create the root agent that orchestrates the entire genealogy research process
root_agent = LlmAgent(
    name="LineageAiOrchestrator",
    model=MODEL_SMART,
    tools=[update_session_title],
    generate_content_config=types.GenerateContentConfig(
        temperature=0.2, # More deterministic output
    ),
    description="""
    The LineageAI Orchestrator Agent is the central hub for genealogy research in the Netherlands.
    It coordinates a team of specialized agents to find, format, and present genealogical data
    to the user, with the ultimate goal of creating comprehensive WikiTree profiles.
    """,
    instruction=root_agent_instructions,
    sub_agents=[
        open_archives_agent, wikitree_query_agent, wikitree_format_agent, holocaust_agent
    ],
)
