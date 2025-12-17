"""
Scholarship API Routes
All endpoints for scholarship discovery, matching, and management
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List
import structlog

from app.models import (
    DiscoverRequest,
    DiscoveryJobResponse,
    MatchedScholarshipsResponse,
    Scholarship,
    SaveScholarshipRequest,
    StartApplicationRequest,
    ErrorResponse
)
from app.services.matching_service import matching_service
from app.database import db

logger = structlog.get_logger()
router = APIRouter(prefix="/api/scholarships", tags=["scholarships"])


@router.post("/discover", response_model=DiscoveryJobResponse)
async def discover_scholarships(
    request: DiscoverRequest,
    background_tasks: BackgroundTasks
):
    """
    Initial scholarship discovery after onboarding
    Returns immediate cached results and starts background discovery
    """
    try:
        logger.info("Discovery request received", user_id=request.user_id)
        
        # Start discovery job (returns immediately)
        response = await matching_service.start_discovery_job(
            request.user_id,
            request.profile
        )
        
        # If processing, schedule background task
        if response.status == "processing" and response.job_id:
            background_tasks.add_task(
                matching_service.run_background_discovery,
                response.job_id,
                request.user_id,
                request.profile
            )
        
        return response
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        logger.error("Discovery failed", error=str(e), user_id=request.user_id)
        raise HTTPException(
            status_code=500,
            detail=f"Discovery failed: {str(e)}"
        )


@router.get("/discover/{job_id}", response_model=DiscoveryJobResponse)
async def get_discovery_progress(job_id: str):
    """
    Poll for discovery job progress
    Returns current status and any new scholarships found
    """
    try:
        result = await matching_service.get_job_status(job_id)
        
        if not result:
            raise HTTPException(
                status_code=404,
                detail="Discovery job not found"
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get discovery status", error=str(e), job_id=job_id)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get discovery status: {str(e)}"
        )


@router.get("/matched", response_model=MatchedScholarshipsResponse)
async def get_matched_scholarships(user_id: str):
    """
    Get all scholarships matched to a user
    Returns full list with match scores
    """
    try:
        logger.info("Fetching matched scholarships", user_id=user_id)
        
        scholarships = await db.get_user_matched_scholarships(user_id)
        
        total_value = sum(s.amount for s in scholarships)
        
        return MatchedScholarshipsResponse(
            scholarships=scholarships,
            total_value=total_value,
            last_updated=(scholarships[0].last_verified or "") if scholarships else ""
        )
        
    except Exception as e:
        logger.error("Failed to fetch matched scholarships", error=str(e), user_id=user_id)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch scholarships: {str(e)}"
        )


@router.get("/{scholarship_id}", response_model=Scholarship)
async def get_scholarship_by_id(scholarship_id: str):
    """
    Get detailed information about a specific scholarship
    Used for the opportunity detail page
    """
    try:
        scholarship = await db.get_scholarship(scholarship_id)
        
        if not scholarship:
            raise HTTPException(
                status_code=404,
                detail="Scholarship not found"
            )
        
        return scholarship
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to fetch scholarship", error=str(e), scholarship_id=scholarship_id)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch scholarship: {str(e)}"
        )


@router.post("/save")
async def save_scholarship(request: SaveScholarshipRequest):
    """
    Add scholarship to user's saved/favorites list
    """
    try:
        await db.save_user_scholarship(request.user_id, request.scholarship_id)
        return {"success": True, "message": "Scholarship saved to favorites"}
        
    except Exception as e:
        logger.error("Failed to save scholarship", error=str(e), user_id=request.user_id)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save scholarship: {str(e)}"
        )


@router.post("/unsave")
async def unsave_scholarship(request: SaveScholarshipRequest):
    """
    Remove scholarship from user's saved/favorites list
    """
    try:
        await db.unsave_user_scholarship(request.user_id, request.scholarship_id)
        return {"success": True, "message": "Scholarship removed from favorites"}
        
    except Exception as e:
        logger.error("Failed to unsave scholarship", error=str(e), user_id=request.user_id)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to unsave scholarship: {str(e)}"
        )
