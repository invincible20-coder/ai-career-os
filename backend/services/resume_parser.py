from datetime import datetime, timezone

from backend.services.event_bus import EventBus
from backend.services.resume_correlation_service import ResumeCorrelationService
from backend.storage.repository import HuntRepository


async def parse_and_analyze_resume(
    *,
    user_id: str,
    file_name: str,
    file_content: bytes,
    repository: HuntRepository,
    event_bus: EventBus,
    target_role: str | None = None,
) -> dict:
    """
    Parse, score, persist, and stream deterministic resume intelligence.
    """
    channel = f"user_{user_id}"
    await event_bus.publish(
        channel,
        {"type": "resume_analysis_started", "message": f"Initializing parsing for {file_name}..."},
    )
    text = file_content.decode("utf-8", errors="ignore")
    if not text.strip():
        text = f"Binary resume upload: {file_name}"
    await event_bus.publish(
        channel,
        {"type": "resume_analysis_progress", "message": "Extracted text and structure.", "progress": 25},
    )
    service = ResumeCorrelationService(repository)
    report = await service.analyze_resume_report(
        user_id=user_id,
        resume_id=file_name,
        resume_version=file_name,
        content=text,
        target_role=target_role,
    )
    await event_bus.publish(
        channel,
        {"type": "resume_analysis_progress", "message": "Computed ATS, weaknesses, and predictions.", "progress": 85},
    )
    result = {
        "file_name": file_name,
        "report": report.model_dump(mode="json"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    await event_bus.publish(
        channel,
        {"type": "resume_analysis_completed", "message": "Analysis complete.", "data": result, "progress": 100},
    )
    return result
