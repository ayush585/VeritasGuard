import os
import re
import json
from dotenv import load_dotenv
from mistralai import Mistral

load_dotenv()

_client = None

def get_mistral_client():
    global _client
    if _client is None:
        api_key = os.getenv("MISTRAL_API_KEY")
        if not api_key:
            raise ValueError("MISTRAL_API_KEY environment variable is required")
        _client = Mistral(api_key=api_key)
    return _client

def parse_json_safe(text: str) -> dict | list:
    """Parse JSON from LLM response, handling markdown fences and malformed output."""
    if not text:
        return {}

    # Strip markdown code fences
    cleaned = re.sub(r'```(?:json)?\s*\n?', '', text)
    cleaned = cleaned.strip()

    # Try direct parse
    try:
        return json.loads(cleaned)
    except (json.JSONDecodeError, TypeError):
        pass

    # Try to find JSON object
    obj_match = re.search(r'\{[\s\S]*\}', cleaned)
    if obj_match:
        try:
            return json.loads(obj_match.group())
        except (json.JSONDecodeError, TypeError):
            pass

    # Try to find JSON array
    arr_match = re.search(r'\[[\s\S]*\]', cleaned)
    if arr_match:
        try:
            return json.loads(arr_match.group())
        except (json.JSONDecodeError, TypeError):
            pass

    return {}
