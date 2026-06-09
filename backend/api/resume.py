from fastapi import APIRouter, UploadFile, File, BackgroundTasks, Request
from fastapi.responses import StreamingResponse

from backend.services.resume_parser import parse_and_analyze_resume
from backend.storage.repository import HuntRepository

router = APIRouter(prefix="/resume", tags=["resume"])


async def _process_resume_upload(
    *,
    session_factory,
    event_bus,
    user_id: str,
    file_name: str,
    content: bytes,
) -> None:
    async with session_factory() as session:
        repository = HuntRepository(session)
        await parse_and_analyze_resume(
            user_id=user_id,
            file_name=file_name,
            file_content=content,
            repository=repository,
            event_bus=event_bus,
        )

@router.post("/upload")
async def upload_resume(
    background_tasks: BackgroundTasks,
    request: Request,
    file: UploadFile = File(...)
):
    # Determine a user or session identifier
    # In a real app with auth, we get this from the access_token/session
    user_id = request.headers.get("x-user-id", "anonymous")
    
    # Read the file content (can also stream if huge)
    content = await file.read()
    
    # Fire the heavy parsing logic in the background
    job_kwargs = {
        "session_factory": request.app.state.db.session_factory,
        "event_bus": request.app.state.event_bus,
        "user_id": user_id,
        "file_name": file.filename or "resume",
        "content": content,
    }
    if getattr(request.app.state.settings, "background_worker_enabled", False):
        await request.app.state.background_worker.enqueue(
            f"resume-analysis:{user_id}:{file.filename}",
            lambda: _process_resume_upload(**job_kwargs),
        )
    else:
        background_tasks.add_task(_process_resume_upload, **job_kwargs)
    
    return {"message": "Upload successful. Analysis started.", "channel": f"user_{user_id}"}

@router.get("/stream/{user_id}")
async def stream_resume_events(user_id: str, request: Request):
    channel = f"user_{user_id}"
    return StreamingResponse(
        request.app.state.event_bus.subscribe(channel),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
