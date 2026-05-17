from fastapi import APIRouter, UploadFile, File, BackgroundTasks, Request
from fastapi.responses import StreamingResponse
import uuid

from backend.services.resume_parser import parse_and_analyze_resume
from backend.services.event_bus import event_bus

router = APIRouter(prefix="/resume", tags=["resume"])

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
    background_tasks.add_task(
        parse_and_analyze_resume,
        user_id,
        file.filename,
        content
    )
    
    return {"message": "Upload successful. Analysis started.", "channel": f"user_{user_id}"}

@router.get("/stream/{user_id}")
async def stream_resume_events(user_id: str):
    channel = f"user_{user_id}"
    return StreamingResponse(
        event_bus.subscribe(channel),
        media_type="text/event-stream"
    )
