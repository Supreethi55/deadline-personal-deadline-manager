import json
import logging
import os
from datetime import datetime

from dotenv import load_dotenv
from google import genai

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=API_KEY)
logger = logging.getLogger(__name__)

ALLOWED_CATEGORIES = {
    "Assignments",
    "Exams",
    "Applications",
    "Placements",
    "Projects",
    "Study",
    "Other",
}
ALLOWED_PRIORITIES = {"High", "Medium", "Low"}


def analyze_text(text: str) -> dict:
    """Ask Gemini for structured data and validate every returned field."""
    now = datetime.now().astimezone().isoformat()
    prompt = f"""
Convert the natural-language student reminder below into structured deadline information.
Current date and time: {now}

Reminder: {text}

Return only valid JSON with exactly these keys and no markdown:
"title", "category", "priority", "deadline", "description"

Rules:
- category must be one of: Assignments, Exams, Applications, Placements, Projects, Study, Other
- priority must be one of: High, Medium, Low
- deadline must be an ISO-8601 datetime with timezone when the reminder gives a date or time; otherwise null
- Use the current date and time supplied by the application to resolve relative dates.
- Never invent a date or exact time.
- title should be concise and title-cased.
- description should preserve the reminder's meaning.
"""
    response_format = {
        "type": "text",
        "mime_type": "application/json",
        "schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "category": {"type": "string", "enum": sorted(ALLOWED_CATEGORIES)},
                "priority": {"type": "string", "enum": sorted(ALLOWED_PRIORITIES)},
                "deadline": {"type": ["string", "null"]},
                "description": {"type": "string"},
            },
            "required": ["title", "category", "priority", "deadline", "description"],
            "additionalProperties": False,
        },
    }

    try:
        interaction = client.interactions.create(
            model="gemini-3.6-flash",
            input=prompt,
            response_format=[response_format],
        )
    except Exception:
        logger.exception("Gemini interaction failed")
        raise

    raw = (interaction.output_text or "").strip()
    if not raw:
        raise ValueError("Gemini returned an empty response.")
    try:
        result = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("Gemini returned invalid JSON.") from exc

    return validate_result(result, text)


def validate_result(result: dict, original_text: str) -> dict:
    if not isinstance(result, dict):
        raise ValueError("AI response must be a JSON object.")

    required = {"title", "category", "priority", "deadline", "description"}
    if set(result) != required:
        raise ValueError("AI response is missing or adding unexpected fields.")

    title = result["title"]
    category = result["category"]
    priority = result["priority"]
    description = result["description"]
    deadline = result["deadline"]

    if not all(isinstance(value, str) and value.strip() for value in (title, category, priority, description)):
        raise ValueError("Title, category, priority, and description must be non-empty text.")
    if category not in ALLOWED_CATEGORIES or priority not in ALLOWED_PRIORITIES:
        raise ValueError("AI returned an unsupported category or priority.")
    if deadline is not None:
        if not isinstance(deadline, str) or not deadline.strip():
            raise ValueError("Deadline must be an ISO-8601 string or null.")
        try:
            datetime.fromisoformat(deadline.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("AI returned an invalid deadline format.") from exc

    return {
        "title": title.strip()[:160],
        "category": category,
        "priority": priority,
        "deadline": deadline,
        "description": description.strip()[:1000],
        "source_text": original_text,
    }
