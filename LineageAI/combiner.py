from zoneinfo import ZoneInfo
from google.adk.agents import LlmAgent
from .constants import PRINT, GEMINI_MODEL

combiner_agent = LlmAgent(
    name="RecordCombiner",
    model=GEMINI_MODEL,
    instruction="""
        You are an Record Combiner Assistant specializing in identifying the relationship between
        genealogical results.

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
    """,
    description="Combines genealogical results from multiple records.",
    output_key="genealogy_result"
 )
