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
from openai import OpenAI

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

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "update_user_profile",
            "description": "Record the student's exam type or exam date.",
            "parameters": {
                "type": "object",
                "properties": {
                    "exam_type": {"type": "string", "enum": ["JEE Main", "JEE Advanced", "NEET"]},
                    "exam_date": {"type": "string", "description": "Date in YYYY-MM-DD format."},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_study_plan",
            "description": "Generate a plan after exam details are known and the student agrees.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_study_plan_day",
            "description": "Fetch the exact plan entry for a date.",
            "parameters": {
                "type": "object",
                "properties": {"requested_date": {"type": "string", "description": "Date in YYYY-MM-DD format."}},
                "required": ["requested_date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "record_practice_result",
            "description": "Record practice results and return accuracy-based review guidance.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string"},
                    "attempted": {"type": "integer", "minimum": 1},
                    "correct": {"type": "integer", "minimum": 0},
                    "notes": {"type": "string"},
                },
                "required": ["topic", "attempted", "correct"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "adjust_study_plan",
            "description": "Regenerate the plan after missed days or an exam-date change.",
            "parameters": {
                "type": "object",
                "properties": {
                    "exam_date": {"type": "string", "description": "Optional YYYY-MM-DD date."},
                    "reason": {"type": "string"},
                },
                "required": ["reason"],
            },
        },
    },
]


def _handle_tool_call(session_id: str, name: str, args: dict) -> str:
    profile = session_store.get_profile(session_id)

    if name == "update_user_profile":
        session_store.update_profile(session_id, args)
        return f"Profile updated: {json.dumps(args)}"

    if name == "generate_study_plan":
        profile = session_store.get_profile(session_id)
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

    if name == "record_practice_result":
        attempted = args.get("attempted", 0)
        correct = args.get("correct", 0)
        if correct > attempted:
            return "The correct count cannot be greater than attempted. Ask the student to correct the result."
        result = {
            "topic": args.get("topic", "General practice"),
            "attempted": attempted,
            "correct": correct,
            "accuracy": round(correct / attempted * 100, 1) if attempted else 0,
            "notes": args.get("notes", ""),
            "date": date.today().isoformat(),
        }
        log = list(profile.get("practice_log") or [])
        log.append(result)
        session_store.update_profile(session_id, {"practice_log": log[-50:]})
        accuracy = result["accuracy"]
        if accuracy >= 80:
            review = "Strong work. Keep this topic in maintenance revision and move to mixed timed practice."
        elif accuracy >= 60:
            review = "You have a useful base. Revisit the mistakes, then retry a smaller timed set tomorrow."
        else:
            review = "Treat this as a revision signal: review the concept, solve worked examples, and retry 10 easier questions."
        return f"Practice result saved: {json.dumps(result)}. Review recommendation: {review}"

    if name == "adjust_study_plan":
        profile = session_store.get_profile(session_id)
        exam_type = profile.get("exam_type")
        exam_date_str = args.get("exam_date") or profile.get("exam_date")
        if not exam_type or not exam_date_str:
            return "Cannot adjust the plan until the exam type and exam date are known."
        try:
            plan = generate_study_plan(exam_type, date.fromisoformat(exam_date_str))
        except ValueError as exc:
            return f"Could not adjust plan: {exc}"
        session_store.update_profile(
            session_id,
            {"exam_date": exam_date_str, "study_plan": plan},
        )
        return f"Plan adjusted from today because {args.get('reason')}. {summarize_plan(plan)}"

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
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=TOOLS,
    )
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
        final = client.chat.completions.create(model=MODEL, messages=messages)
        reply = final.choices[0].message.content
    else:
        reply = choice.message.content

    session_store.append_message(session_id, "assistant", reply)
    return reply
