import logging
import os

APP_NAME = "LineageAI"
MODEL_SMART = "gemini-2.5-pro" # Expensive and slow
MODEL_MIXED = "gemini-2.5-flash" # Cheaper but faster
MODEL_FAST = "gemini-2.5-flash-lite-preview-06-17" # Cheapest but fastest

# --- Configure Logging ---
filename = os.path.join(os.path.dirname(os.path.realpath(__file__)), f'{APP_NAME}.log') # doesn't work??
logging.basicConfig(filename=filename, level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.info("Invocation start")
