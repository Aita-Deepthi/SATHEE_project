import uuid
import io
import zipfile
from datetime import date
from html import escape

from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import agent
import session_store
from study_plan import get_today_task
from rag_pipeline import search_knowledge

app = FastAPI(title="SATHEE Guidance Agent")


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ResetRequest(BaseModel):
    session_id: str


@app.post("/api/chat")
async def chat(req: ChatRequest):
    reply = agent.chat(req.session_id, req.message)
    return {"reply": reply}


@app.post("/api/reset")
async def reset(req: ResetRequest):
    session_store.reset_session(req.session_id)
    return {"status": "ok"}


@app.get("/api/session/new")
async def new_session():
    return {"session_id": str(uuid.uuid4())}


@app.get("/api/study-plan/{session_id}")
async def get_study_plan(session_id: str):
    profile = session_store.get_profile(session_id)
    plan = profile.get("study_plan")
    if not plan:
        return {"plan": None}
    return {"plan": plan, "today": get_today_task(plan)}


@app.get("/api/study-plan/{session_id}/today")
async def get_today(session_id: str):
    profile = session_store.get_profile(session_id)
    plan = profile.get("study_plan")
    if not plan:
        return {"today": None, "message": "No plan generated yet."}
    today_task = get_today_task(plan)
    if not today_task:
        return {"today": None, "message": "Today is outside the plan's date range."}
    return {"today": today_task}


@app.get("/api/study-plan/{session_id}/download")
async def download_study_plan(session_id: str):
    profile = session_store.get_profile(session_id)
    plan = profile.get("study_plan")
    if not plan:
        return HTMLResponse("No study plan has been generated yet.", status_code=404)

    exam = escape(profile.get("exam_type") or "Entrance Exam")
    exam_date = escape(profile.get("exam_date") or plan[-1]["date"])

    def paragraph(text: str, bold: bool = False) -> str:
        value = escape(str(text))
        run_properties = "<w:rPr><w:b/></w:rPr>" if bold else ""
        return f"<w:p><w:r>{run_properties}<w:t xml:space=\"preserve\">{value}</w:t></w:r></w:p>"

    document_parts = [paragraph(f"{exam} Study Plan", True), paragraph(f"Complete plan from {plan[0]['date']} to {exam_date}.")]
    for day in plan:
        topics = "; ".join(
            f"{item['subject']}: {item['topic']} ({item['practice_problems']} topic problems)"
            for item in day["subjects"]
        ) or "Revision and practice"
        practice = "; ".join(
            f"{item['task']} - {item['problems']} problems, {item['duration_minutes']} minutes"
            for item in day.get("daily_practice", [])
        )
        document_parts.append(paragraph(f"Day {day['day']} | {day['date']} | {day['phase']}", True))
        document_parts.append(paragraph(f"Topics: {topics}"))
        document_parts.append(paragraph(f"Daily practice: {practice}"))
        document_parts.append(paragraph(f"Resources: {'; '.join(day['resources'])}"))

    document_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>{''.join(document_parts)}<w:sectPr/></w:body></w:document>"""
    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>"""
    relationships = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>"""
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", relationships)
        archive.writestr("word/document.xml", document_xml)
    filename = (profile.get("exam_type") or "exam").replace(" ", "_") + "_study_plan.docx"
    return Response(
        content=output.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/knowledge/search")
async def knowledge_search(q: str, limit: int = 4):
    """Inspect the passages the agent can retrieve for a question."""
    return {"results": search_knowledge(q, max(1, min(limit, 10)))}


app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    return FileResponse("static/index.html")
