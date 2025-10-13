import json
import requests
from requests.adapters import HTTPAdapter, Retry

def _session():
    s = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=1.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["POST"]
    )
    s.mount("https://", HTTPAdapter(max_retries=retries))
    s.mount("http://", HTTPAdapter(max_retries=retries))
    return s

def post_batch(endpoint: str, token: str, rows: list[str]):
    """
    rows: list of JSON strings (each an InsightEnvelope)
    Sends a JSON array to endpoint. Raises on failure.
    """
    payload = "[" + ",".join(rows) + "]"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    resp = _session().post(endpoint, data=payload, headers=headers, timeout=20)
    resp.raise_for_status()
    return resp
