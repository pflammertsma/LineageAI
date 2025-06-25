from zoneinfo import ZoneInfo
from google.adk.agents import Agent, BaseAgent, LlmAgent, SequentialAgent
from .constants import AGENT_NAME
from .openarchieven import open_archives_agent
from .reviewer import reviewer_agent
from .combiner import combiner_agent
from .wikitree import wikitree_agent

root_agent = SequentialAgent(
    name=AGENT_NAME,
    sub_agents=[
        open_archives_agent, reviewer_agent, combiner_agent, wikitree_agent
    ],
    description=(
        "Agent to answer questions about genealogy in the Netherlands."
    ),
)
