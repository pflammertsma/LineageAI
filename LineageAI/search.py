from google.adk.agents import Agent
from google.adk.tools import google_search
from google.adk.tools.agent_tool import AgentTool
from .constants import logger, MODEL_SMART, MODEL_MIXED, MODEL_FAST

search_agent = Agent(
    model=MODEL_FAST,
    name="search_agent",
    instruction="""
    You're a specialist in Google Search.
    """,
    tools=[google_search],
)

search_tool = AgentTool(search_agent)
