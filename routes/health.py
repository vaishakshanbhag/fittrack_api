from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check():
    """Health check endpoint — returns service status."""
    return {"status": "ok"}
