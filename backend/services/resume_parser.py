import asyncio
import json
from uuid import uuid4
from datetime import datetime, timezone
from backend.services.event_bus import event_bus
from backend.models.resume_intelligence import ResumeFeatures

async def parse_and_analyze_resume(user_id: str, file_name: str, file_content: bytes):
    """
    Simulates a heavy ATS parser and scoring engine.
    Emits real-time state updates via EventBus.
    """
    channel = f"user_{user_id}"
    
    # 1. Start Analysis
    await event_bus.publish(channel, {"type": "START", "message": f"Initializing parsing for {file_name}..."})
    await asyncio.sleep(1.5)
    
    # 2. Extract Text
    await event_bus.publish(channel, {"type": "PROGRESS", "message": "Extracting text and structure...", "progress": 20})
    await asyncio.sleep(2)
    
    # 3. Evaluate ATS
    await event_bus.publish(channel, {"type": "PROGRESS", "message": "Evaluating ATS structural compatibility...", "progress": 40})
    await asyncio.sleep(1.5)
    
    # 4. Detect Keywords
    await event_bus.publish(channel, {"type": "PROGRESS", "message": "Detecting keyword density and skills...", "progress": 60})
    await asyncio.sleep(2)
    
    # 5. Quantify Achievements
    await event_bus.publish(channel, {"type": "PROGRESS", "message": "Analyzing measurable impact and achievements...", "progress": 80})
    await asyncio.sleep(1.5)
    
    # 6. Finalizing
    await event_bus.publish(channel, {"type": "PROGRESS", "message": "Finalizing correlation models...", "progress": 95})
    await asyncio.sleep(1)
    
    # Generate mock features (this should be an LLM or deterministic pipeline in reality)
    features = ResumeFeatures(
        ats_score=78.5,
        keyword_density=0.65,
        quantified_achievements=3,
        project_complexity_score=0.72,
        skill_diversity=0.8,
        education_strength=0.9,
        experience_depth=0.6,
        readability_score=0.85,
        formatting_consistency=0.95,
        action_verb_usage=0.7,
        backend_keywords=12,
        frontend_keywords=4,
        data_keywords=2,
        technical_depth=0.75,
        communication_indicators=0.6
    )
    
    weaknesses = [
        {
            "id": "w1",
            "category": "Impact",
            "severity": "high",
            "description": "Projects lack measurable impact.",
            "recommendation": "Add quantified outcomes such as performance improvements or scale handled.",
            "expected_improvement": "ATS relevance +12%",
            "confidence": 0.88
        },
        {
            "id": "w2",
            "category": "Keywords",
            "severity": "medium",
            "description": "Missing modern framework terminology.",
            "recommendation": "Include specific versions and associated tools (e.g., React 18, Next.js).",
            "expected_improvement": "Searchability +8%",
            "confidence": 0.92
        }
    ]
    
    result = {
        "file_name": file_name,
        "features": features.model_dump(),
        "weaknesses": weaknesses,
        "confidence": 0.85,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    await event_bus.publish(channel, {"type": "COMPLETE", "message": "Analysis complete.", "data": result})
    return result
