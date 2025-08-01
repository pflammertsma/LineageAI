import logging
import os
from http.client import HTTPConnection

APP_NAME = "LineageAI"
MODEL_SMART = "gemini-2.5-pro" # Expensive and slow
MODEL_MIXED = "gemini-2.5-flash" # Cheaper but faster
MODEL_FAST = "gemini-2.5-flash-lite-preview-06-17" # Cheapest but fastest

_REQUEST_LOGGING = False

# --- Configure Logging ---
filename = os.path.join(os.path.dirname(os.path.realpath(__file__)), f'{APP_NAME}.log') # doesn't work??
logging.basicConfig(filename=filename, level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.info("Invocation start")
logger.propagate = True

requests_log = logging.getLogger("requests.packages.urllib3")
if _REQUEST_LOGGING:
    requests_log.setLevel(logging.DEBUG)
    HTTPConnection.debuglevel = 1
else:
    requests_log.setLevel(logging.WARNING)
    HTTPConnection.debuglevel = 0
requests_log.propagate = True
