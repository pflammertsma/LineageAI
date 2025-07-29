from .constants import logger, MODEL_SMART, MODEL_MIXED, MODEL_FAST
from zoneinfo import ZoneInfo
from google.adk.agents import LlmAgent
from google.genai import types

combiner_agent = LlmAgent(
    name="RecordCombiner",
    model=MODEL_MIXED,  # Use a mixed model for cost efficiency
    generate_content_config=types.GenerateContentConfig(
        temperature=0.2, # More deterministic output
        max_output_tokens=100
    ),
    description="""
    You are the Record Combiner Agent specializing in identifying the relationship between
    genealogical results and recombining them into a single coherent record that is focused on
    a single individual that is the subject of the query.
    """,
    instruction="""
    You are provided with a query and a set of genealogical results from multiple agents.
    Your task is to inspect these results and, if it concerns multiple individuals, select the
    most relevant one to the initial query and combine all relevant information a single,
    coherent record.

    You are diligent to not confuse records from different individuals, even if they share
    similar names or approximate dates, merging information with the following rules:
    - Variations in spelling are permitted;
    - Omitted middle names are permitted;
    - Patronymic names (derived from the father's given name) were used prior to 1811, having 
        been replaced by fixed surnames.
    
    However, if there's a strong signal that there is no relevance, irrelevant irrelevant
    records should be discarded.

    Output in plain text:
    - A short explanation of why you chose one individual if previous data suggested there
        were multiple individuals to choose from;
    - A succint biography describing all the relevant details about the person you chose.

    You should try to transfer back to the orchestrator agent and encourage it to finalize the
    update biography, if any new information was found.

    IMPORTANT NOTES
    ---------------

    Once you're finished, you must transfer back to the LineageAiOrchestrator.
    """,
    output_key="genealogy_result"
 )
