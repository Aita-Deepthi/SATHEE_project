"""
Static knowledge base for the SATHEE Guidance AI Agent.

This is intentionally kept as plain Python data (not a vector DB) because
the corpus is small and fixed. If it grows, swap this module for a real
retrieval layer without touching agent.py's public interface
(get_knowledge_base_text()).
"""

SATHEE_FACTS = {
    "name": "SATHEE (Self Assessment, Test and Help for Entrance Exams)",
    "developer": "IIT Kanpur, under the Ministry of Education, Government of India",
    "cost": "100% free",
    "website": "https://sathee.iitk.ac.in",
    "app_name": "Sathee: AI Exam Prep Free",
    "exams_covered": [
        "JEE (Main & Advanced)", "NEET", "CUET", "CLAT", "ICAR", "SSC", "RRB", "IBPS",
    ],
    "content": [
        "Video lectures by IIT/IISc/AIIMS faculty",
        "NCERT-based modules",
        "Practice questions",
        "DPPs (Daily Practice Problems)",
        "PYQs (Previous Year Questions)",
        "Mock tests with analytics",
    ],
    "ai_tools": [
        "AI Tutor", "Visual Solver", "Mock Test Generator", "Performance analytics",
    ],
    "languages": "English, Hindi, and 12+ regional languages",
    "support": "Live doubt-clearing sessions and mentorship programs",
}

FORWARDABLE_FAMILY_MESSAGE = (
    "Good news! There is a completely FREE platform called SATHEE, made by IIT Kanpur "
    "(Govt. of India), to help students prepare for JEE, NEET and other exams. It has "
    "free video lectures, practice questions, mock tests, and even an AI tutor to solve "
    "doubts \u2014 in Hindi, English and other languages too. Website: sathee.iitk.ac.in, "
    "or search \"Sathee: AI Exam Prep Free\" on the Play Store. No fees, no scam \u2014 just "
    "sign up with a Gmail ID and start learning today."
)

SAFETY_RULES = [
    "Never ask for money, fees, OTPs, passwords, or bank details.",
    "Never guarantee ranks, admissions, or results.",
    "Always be honest about being an AI assistant, not a human tutor.",
    "Keep language simple (roughly Class 8-10 reading level).",
    "Prefer Hindi/English/regional language based on the user's stated preference.",
]


def get_knowledge_base_text() -> str:
    """Render the KB as a compact text block to inject into the system prompt."""
    f = SATHEE_FACTS
    lines = [
        f"Platform: {f['name']}",
        f"Developed by: {f['developer']} ({f['cost']})",
        f"Website: {f['website']}",
        f"Mobile app: {f['app_name']} (Android/iOS app stores)",
        f"Exams covered: {', '.join(f['exams_covered'])}",
        f"Content available: {', '.join(f['content'])}",
        f"Built-in AI tools: {', '.join(f['ai_tools'])}",
        f"Languages supported: {f['languages']}",
        f"Support: {f['support']}",
        "",
        "Forwardable message for well-wishers to share with a family:",
        FORWARDABLE_FAMILY_MESSAGE,
        "",
        "Safety rules the agent must always follow:",
        *[f"- {rule}" for rule in SAFETY_RULES],
    ]
    return "\n".join(lines)
