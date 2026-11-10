"""
Deterministic (non-LLM) study plan generator for the SATHEE Guidance Agent.

Why deterministic instead of asking the LLM to invent the plan:
- Day counts, phase splits and topic coverage must be arithmetically
  correct against the real exam date every time — an LLM will drift
  on this over a long plan.
- The LLM's job is to *present* this plan conversationally, answer
  follow-ups about it, and adjust tone/language — not compute it.

Usage:
    from study_plan import generate_study_plan
    plan = generate_study_plan("JEE Main", date(2027, 1, 24))
    today_task = get_today_task(plan)
"""

from datetime import date, timedelta
from syllabus_data import SYLLABUS, DEFAULT_RESOURCES


def _phase_split(total_days: int):
    """Return list of (phase_name, num_days) covering total_days exactly."""
    if total_days >= 90:
        phases = [("Foundation", 0.55), ("Revision", 0.25),
                  ("Practice & Mocks", 0.15), ("Final Revision", 0.05)]
    elif total_days >= 45:
        phases = [("Coverage", 0.40), ("Revision", 0.30),
                  ("Practice & Mocks", 0.25), ("Final Revision", 0.05)]
    elif total_days >= 14:
        phases = [("Rapid Revision", 0.55), ("Practice & Mocks", 0.35),
                  ("Final Revision", 0.10)]
    else:
        # Very close to exam: no new topics, pure high-yield revision + mocks
        phases = [("Final Sprint", 0.7), ("Final Revision", 0.3)]

    # A very short window cannot contain every phase; keep the earliest phases
    # and give each remaining phase at least one day.
    phases = phases[:total_days]

    # Give each phase a proportional share, then distribute remaining days.
    # This keeps the sum exact even for one- and two-week timelines.
    counts = [max(1, int(total_days * frac)) for _, frac in phases]
    while sum(counts) > total_days:
        reducible = [i for i, count in enumerate(counts) if count > 1]
        if not reducible:
            break
        index = max(reducible, key=lambda i: counts[i])
        counts[index] -= 1
    for index in range(total_days - sum(counts)):
        counts[index % len(counts)] += 1
    return [[name, count] for (name, _), count in zip(phases, counts)]


def _flatten_topics(exam_type: str):
    syllabus = SYLLABUS[exam_type]
    topics = []
    for subject, subject_topics in syllabus.items():
        for t in subject_topics:
            topics.append({"subject": subject, "name": t["name"], "weightage": t["weightage"]})
    # Highest-weightage topics first so they land earliest in the coverage phase
    topics.sort(key=lambda t: -t["weightage"])
    return topics


def generate_study_plan(exam_type: str, exam_date: date, start_date: date = None, topics_per_day: int = 3):
    """
    Returns a list of day dicts:
    {
      "day": int, "date": "YYYY-MM-DD", "phase": str,
      "subjects": [{"subject": str, "topic": str, "practice_problems": int}, ...],
      "practice": [str, ...],   # extra practice instructions (PYQs, mocks)
      "resources": [str, ...]
    }
    """
    if exam_type not in SYLLABUS:
        raise ValueError(f"Unknown exam_type '{exam_type}'. Options: {list(SYLLABUS.keys())}")

    start_date = start_date or date.today()
    total_days = (exam_date - start_date).days
    if total_days <= 0:
        raise ValueError("exam_date must be after start_date")

    phase_plan = _phase_split(total_days)
    all_topics = _flatten_topics(exam_type)
    subjects = list(SYLLABUS[exam_type].keys())

    plan = []
    day_number = 0
    topic_idx = 0

    for phase_name, ndays in phase_plan:
        for _ in range(ndays):
            day_number += 1
            current_date = start_date + timedelta(days=day_number - 1)
            day = {
                "day": day_number,
                "date": current_date.isoformat(),
                "phase": phase_name,
                "subjects": [],
                "practice": [],
                "resources": list(DEFAULT_RESOURCES),
            }

            if phase_name in ("Foundation", "Coverage", "Rapid Revision"):
                day["practice"].append("10 practice problems per topic covered today (SATHEE topic test)")
            elif phase_name == "Revision":
                subj = subjects[day_number % len(subjects)]
                day["subjects"].append({
                    "subject": subj,
                    "topic": f"Revise {subj}: redo formula sheet + weak topics",
                    "practice_problems": 20,
                })
                day["practice"].append("15 mixed Previous Year Questions (PYQs) across all subjects, timed")

            elif phase_name in ("Practice & Mocks", "Final Sprint"):
                if day_number % 7 == 0:
                    day["practice"].append("Full-length mock test (SATHEE test series), then a full error-analysis pass")
                else:
                    day["practice"].append("25-30 mixed PYQs across subjects, timed like exam conditions")
                    day["practice"].append("Review yesterday's mistakes for 20 minutes before starting new problems")

            elif phase_name == "Final Revision":
                day["practice"].append("Revise formula/concept sheets only — no new topics")
                day["practice"].append("1 sectional or full mock test + review")

            plan.append(day)

    # Assign every syllabus topic to a concrete day. On short timelines this
    # intentionally creates longer days instead of hiding topics in one note.
    topic_days = [
        day for day in plan
        if day["phase"] != "Final Revision"
    ] or plan
    for index, topic in enumerate(all_topics):
        day = topic_days[index % len(topic_days)]
        day["subjects"].append({
            "subject": topic["subject"],
            "topic": topic["name"],
            "practice_problems": 15,
        })

    return plan


def get_today_task(plan: list, today: date = None):
    """Given a generated plan, return the entry matching today's date (or None if outside range)."""
    today = today or date.today()
    iso = today.isoformat()
    for day in plan:
        if day["date"] == iso:
            return day
    return None


def summarize_plan(plan: list):
    """Short human-readable summary of the phases and their date ranges — useful for a first overview message."""
    if not plan:
        return "No plan generated."
    phases = []
    current_phase = None
    phase_start = None
    for day in plan:
        if day["phase"] != current_phase:
            if current_phase is not None:
                phases.append((current_phase, phase_start, prev_date))
            current_phase = day["phase"]
            phase_start = day["date"]
        prev_date = day["date"]
    phases.append((current_phase, phase_start, prev_date))

    lines = [f"Total days: {len(plan)} (from {plan[0]['date']} to {plan[-1]['date']})"]
    for name, start, end in phases:
        lines.append(f"- {name}: {start} to {end}")
    return "\n".join(lines)
