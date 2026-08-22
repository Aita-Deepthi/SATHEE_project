"""
Core conversational logic for the SATHEE Guidance AI Agent.

Flow (mirrors the flowcharts in the project brief):
  1. Figure out if the user is a Student or a Well-Wisher.
  2. Collect a small profile (exam, class, language, ...) as it comes up
     naturally in conversation -- not as a rigid form.
  3. Explain SATHEE, help with registration/course choice, build a study
     plan, recommend resources, answer doubts, motivate, or (for
     well-wishers) hand over the forwardable message + steps.

Profile fields are captured via a "tool" (function call) so we get
structured data out of a normal conversation instead of regex-parsing text.
"""

import os
import json
from typing import List, Dict

import google.generativeai as genai
from dotenv import load_dotenv

from knowledge_base import get_knowledge_base_text
from session_store import get_history, get_profile, update_profile, append_message

# Load environment variables
load_dotenv()

MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
API_KEY = os.environ.get("GEMINI_API_KEY")

if not API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY is not set. Create a .env file in backend/ and add your Gemini key "
        "from https://aistudio.google.com"
    )

# Configure Gemini client
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel(MODEL)

UPDATE_PROFILE_TOOL = {
    "type": "function",
    "function": {
        "name": "update_user_profile",
        "description": (
            "Save any new facts the user has revealed about themselves. Only "
            "include fields that were actually stated or clearly implied in "
            "the latest message -- never guess or invent values."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "user_type": {"type": "string", "enum": ["student", "well_wisher"]},
                "exam": {"type": "string", "description": "e.g. JEE, NEET, Other"},
                "class_level": {"type": "string", "description": "e.g. 9, 10, 11, 12, Dropper"},
                "language": {"type": "string", "description": "Preferred language, e.g. Hindi, English"},
                "hours_per_day": {"type": "string", "description": "Study hours available per day"},
                "weak_subjects": {"type": "string"},
                "strong_subjects": {"type": "string"},
                "exam_year": {"type": "string"},
            },
            "additionalProperties": False,
        },
    },
}


def _system_prompt(profile: Dict) -> str:
    known = {k: v for k, v in profile.items() if v}
    known_text = json.dumps(known, ensure_ascii=False) if known else "(nothing known yet)"

    return f"""You are the SATHEE Guidance AI Agent: a warm, patient, 24x7 guide that helps
economically disadvantaged students (Class 9-12 and droppers) preparing for JEE/NEET and
similar exams, and well-wishers who want to help such a student, discover and use SATHEE --
a completely free platform built by IIT Kanpur.

KNOWLEDGE BASE (facts about SATHEE -- only use these facts, never invent links or features):
{get_knowledge_base_text()}

WHAT YOU ALREADY KNOW ABOUT THIS USER: {known_text}

HOW TO BEHAVE:
- If you don't yet know whether they are a Student or a Well-Wisher, find that out first,
  in a friendly, non-interrogating way.
- Ask at most one or two questions per message -- this is a conversation, not a form.
- For STUDENTS: explain SATHEE simply, help them pick a course (JEE/NEET, full vs crash
  course), guide registration (sign up with Gmail), and once you know enough (class, exam,
  hours available, weak/strong subjects) offer a simple weekly study plan with daily slots
  for lectures, DPPs, revision, and mocks. Recommend specific next actions, not vague advice.
- For WELL-WISHERS: briefly confirm the child's exam/language if known, then give the
  forwardable family message, a short registration walkthrough, and simple ways to support
  (e.g. checking daily DPP completion).
- Always explain DPPs (Daily Practice Problems) when relevant: short daily practice sets
  that build speed and accuracy, and should not be skipped.
- Keep replies concise, encouraging, and in simple language (roughly Class 8-10 reading
  level). Match the user's language if they write in Hindi or another language.
- Never ask for money, OTPs, passwords or personal financial details. Never promise a
  rank, seat, or result. If asked something outside SATHEE/exam-prep guidance, gently
  redirect back to how you can help with SATHEE.
- When you learn a new fact about the user (exam, class, language, hours/day, weak/strong
  subjects, or whether they're a student/well-wisher), call update_user_profile with just
  that new information.
"""


def _extract_tool_updates(tool_calls) -> Dict[str, str]:
    updates: Dict[str, str] = {}
    if not tool_calls:
        return updates
    for call in tool_calls:
        if call.get("function", {}).get("name") != "update_user_profile":
            continue
        try:
            args = json.loads(call["function"]["arguments"])
        except (json.JSONDecodeError, KeyError):
            continue
        updates.update({k: v for k, v in args.items() if v})
    return updates


def get_reply(session_id: str, user_message: str) -> str:
    append_message(session_id, "user", user_message)
    profile = get_profile(session_id)
    history = get_history(session_id)

    messages: List[Dict] = [{"role": "system", "content": _system_prompt(profile)}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    # Generate response from Gemini
    response = model.generate_content(messages)
    reply_text = response.text or ""

    append_message(session_id, "assistant", reply_text)
    return reply_text
