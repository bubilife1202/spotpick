from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    return {"status": "healthy"}


@router.get("/")
async def root():
    return {
        "name": "Builder Curation API",
        "version": "0.1.0",
        "docs": "/docs",
    }
