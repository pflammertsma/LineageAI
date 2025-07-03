import logging
import os

AGENT_NAME = "lineage_agent"
APP_NAME = "LineageAI"
GEMINI_MODEL = "gemini-2.5-pro"
PRINT = False

# --- Configure Logging ---
filename = os.path.join(os.path.dirname(os.path.realpath(__file__)), '{APP_NAME}.log') # doesn't work??
logging.basicConfig(filename=filename, level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info("Invocation start")
