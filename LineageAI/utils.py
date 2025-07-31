from .constants import logger
import logging
from http.client import HTTPConnection
import os
import requests
import json
import time
import threading

# --- Rate limiting logic usign rolling window counter ---
_api_lock = threading.Lock()
_api_window_start = 0
_api_request_count = 0
_API_RATE_LIMIT = 10  # requests during the window
_API_RATE_WINDOW = 60  # window duration in seconds
_API_INVOCATION_MIN_DURATION = 3  # minimum duration of requests to slow invocations
_API_INVOCATION_MAX_DURATION = 10 # maximum duration of requests before timing out
_API_SLEEP_INTERVAL = 1

HTTPConnection.debuglevel = 1

logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)
requests_log = logging.getLogger("requests.packages.urllib3")
requests_log.setLevel(logging.DEBUG)
requests_log.propagate = True


def rate_limited_get(url, params=None, timeout=_API_INVOCATION_MAX_DURATION, fast=False):
    """
    Helper for requests.get with rate limiting, bound by a max number of requests per minute
    through a rolling window.
    
    This function also suspends a minimum duration to pace API requests. To minimize this, provide
    `fast=True`, which will circumvent invocation quotas. Use this sparsely.
    
    This function suspends if limit exceeded and will output sleep countdowns while holding.
    """
    global _api_window_start, _api_request_count
    with _api_lock:
        start_time = time.time()
        if start_time - _api_window_start > _API_RATE_WINDOW:
            # Rolling window can be reset; it's been long enough ago
            _api_window_start = start_time
            _api_request_count = 0
        # Perform the request
        response = requests.get(url, params=params, timeout=timeout)
        if (not fast):
            elapsed = time.time() - start_time
            if elapsed < _API_INVOCATION_MIN_DURATION:
                # Ensure this function doesn't run too quickly as this quickly results in hitting quota
                sleep_time = _API_INVOCATION_MIN_DURATION - elapsed
                if sleep_time > 0:
                    logger.warning(f"API request is being paced")
                    while sleep_time > 0:
                        interval = min(_API_SLEEP_INTERVAL, sleep_time)
                        logger.info(f"Sleeping ({sleep_time:.0f}s remaining)...")
                        time.sleep(interval)
                        sleep_time -= interval
            if _api_request_count >= _API_RATE_LIMIT:
                # Ensure this function doesn't perform more requests than the maximum allowed in the
                # window
                sleep_time = _API_RATE_WINDOW - (start_time - _api_window_start)
                if sleep_time > 0:
                    logger.warning(f"API rate limit reached ({_API_RATE_LIMIT}/min); sleeping for {sleep_time:.0f}s")
                    while sleep_time > 0:
                        interval = min(_API_SLEEP_INTERVAL, sleep_time)
                        logger.info(f"Sleeping ({sleep_time:.0f}s remaining)...")
                        time.sleep(interval)
                        sleep_time -= interval
                _api_window_start = time.time()
                _api_request_count = 0
            _api_request_count += 1
    return response
