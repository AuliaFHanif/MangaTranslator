from fastapi import APIRouter
router = APIRouter()

@router.get("/status")
async def pipeline_status() -> dict:
    return {"queue_depth": 0, "active_jobs": [], "phase": "stub"}
