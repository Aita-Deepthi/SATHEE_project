"""
Core agent logic. Uses Google's Gemini OpenAI-compatibility endpoint via
the OpenAI SDK, with two function-calling tools:
  - update_user_profile: structured extraction of exam_type/exam_date etc.
  - generate_study_plan: triggers the deterministic Python plan generator
    (study_plan.py) — the LLM never invents the plan itself.
"""

import os
import json
from datetime import date

from dotenv import load_dotenv
from openai import OpenAI, RateLimitError

import session_store
from knowledge_base import build_system_prompt
from rag_pipeline import retrieve_context
from study_plan import generate_study_plan, summarize_plan

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError(
        "OPENAI_API_KEY is missing. Create backend/.env from .env.example and add your Gemini API key."
    )

client = OpenAI(
    api_key=api_key,  # holds the Gemini API key
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
)
MODEL = os.environ.get("OPENAI_MODEL", "gemini-3.6-flash")

RESOURCE_SUGGESTIONS = (
    "\n\nUseful free resources:\n"
    "- SATHEE: https://sathee.iitk.ac.in/\n"
    "- NCERT textbooks: https://ncert.nic.in/textbook.php\n"
    "- NTA exam resources: https://www.nta.ac.in/"
)

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "update_user_profile",
            "description": "Record or update known facts about the student: exam type and/or exam date. Call this as soon as you learn either.",
            "parameters": {
                "type": "object",
                "properties": {
                    "exam_type": {
                        "type": "string",
                        "enum": ["JEE Main", "JEE Advanced", "NEET"],
                        "description": "The exam the student is preparing for.",
                    },
                    "exam_date": {
                        "type": "string",
                        "description": "The student's exam date in ISO format YYYY-MM-DD.",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_study_plan",
            "description": "Generate a day-by-day study plan for the student. Only call this once exam_type and exam_date are both known and the student has agreed to receive a plan.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_study_plan_day",
            "description": "Fetch the exact plan entry for a date after a study plan exists.",
            "parameters": {
                "type": "object",
                "properties": {"requested_date": {"type": "string", "description": "Date in YYYY-MM-DD format."}},
                "required": ["requested_date"],
            },
        },
    },
]


def _quota_reply() -> str:
    return (
        "Gemini's free API quota has been reached for this model today. "
        "Please wait for the quota to reset, use another Gemini API key, "
        "or select a model with available quota in backend/.env. "
        "Your study plan features will work again when the AI quota is available."
    )


def _handle_tool_call(session_id: str, name: str, args: dict) -> str:
    profile = session_store.get_profile(session_id)

    if name == "update_user_profile":
        session_store.update_profile(session_id, args)
        return f"Profile updated: {json.dumps(args)}"

    if name == "generate_study_plan":
        exam_type = profile.get("exam_type")
        exam_date_str = profile.get("exam_date")
        if not exam_type or not exam_date_str:
            return "Cannot generate plan yet — exam_type or exam_date is still missing. Ask the user for whichever is missing."
        try:
            plan = generate_study_plan(exam_type, date.fromisoformat(exam_date_str))
        except ValueError as e:
            return f"Could not generate plan: {e}. Ask the user to clarify their exam date."
        session_store.update_profile(session_id, {"study_plan": plan})
        return (
            "Plan generated successfully.\n"
            f"{summarize_plan(plan)}\n"
            "Tell the student the plan is ready, give a brief overview of the phases, "
            "and describe today's specific tasks (day 1)."
        )

    if name == "get_study_plan_day":
        plan = profile.get("study_plan")
        if not plan:
            return "No study plan exists yet. Ask whether the student wants one generated."
        requested_date = args.get("requested_date")
        task = next((day for day in plan if day["date"] == requested_date), None)
        if not task:
            return f"No plan entry exists for {requested_date}. The plan runs from {plan[0]['date']} to {plan[-1]['date']}."
        return f"Plan entry for {requested_date}: {json.dumps(task)}"

    return f"Unknown tool: {name}"


def chat(session_id: str, user_message: str) -> str:
    session_store.append_message(session_id, "user", user_message)
    profile = session_store.get_profile(session_id)

    context = retrieve_context(user_message)
    messages = [{"role": "system", "content": build_system_prompt(profile, context)}]
    messages += session_store.get_history(session_id)

    # First pass — model may respond directly or call tool(s)
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS,
        )
    except RateLimitError:
        reply = _quota_reply()
        session_store.append_message(session_id, "assistant", reply)
        return reply
    choice = response.choices[0]

    if choice.message.tool_calls:
        messages.append(choice.message)
        for tool_call in choice.message.tool_calls:
            args = json.loads(tool_call.function.arguments or "{}")
            result = _handle_tool_call(session_id, tool_call.function.name, args)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result,
                }
            )

        # Refresh system prompt with updated profile, then second pass for final reply
        profile = session_store.get_profile(session_id)
        messages[0] = {"role": "system", "content": build_system_prompt(profile, context)}
        try:
            final = client.chat.completions.create(model=MODEL, messages=messages)
        except RateLimitError:
            reply = _quota_reply()
            session_store.append_message(session_id, "assistant", reply)
            return reply
        reply = final.choices[0].message.content
    else:
        reply = choice.message.content

    resource_words = ("website", "websites", "resource", "resources", "material", "materials", "link")
    if any(word in user_message.lower() for word in resource_words) and "https://" not in reply:
        reply += RESOURCE_SUGGESTIONS

    session_store.append_message(session_id, "assistant", reply)
    return reply
