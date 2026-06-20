"""
RedevOps.io Social Autopilot - Agent API Server

Main entry point for the autonomous agent layer.
Provides REST API endpoints for content creation, scheduling optimization,
and engagement management.
"""

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List
import os
import logging

# Configure logging
logging.basicConfig(
    level=os.getenv("AGENT_LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# ============================================
# Authentication
# ============================================

API_SECRET_KEY = os.getenv("API_SECRET_KEY")

if not API_SECRET_KEY:
    logger.warning(
        "API_SECRET_KEY is not set. Agent endpoints are UNAUTHENTICATED; "
        "bind the service to localhost only and do not expose it publicly."
    )


async def require_api_key(x_api_key: Optional[str] = Header(None)) -> None:
    """Enforce the X-API-Key header against API_SECRET_KEY.

    If API_SECRET_KEY is unset, authentication is disabled and the service
    must be run on localhost only (see startup warning).
    """
    if not API_SECRET_KEY:
        return
    if x_api_key != API_SECRET_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

app = FastAPI(
    title="RedevOps.io Social Autopilot Agent API",
    description="Autonomous AI agents for social media management",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware for frontend integration.
# Origins are restricted via the ALLOWED_ORIGINS env var (comma-separated).
# Never combine a wildcard origin with credentials.
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================
# Pydantic Models
# ============================================

class ContentCreateRequest(BaseModel):
    """Request model for content creation."""
    topic: str = Field(..., description="The topic or theme for the content")
    platforms: List[str] = Field(
        default=["twitter", "linkedin"],
        description="Target social media platforms"
    )
    tone: Optional[str] = Field("professional", description="Content tone/style")
    include_hashtags: bool = Field(True, description="Include relevant hashtags")


class ContentCreateResponse(BaseModel):
    """Response model for content creation."""
    id: str
    topic: str
    platforms: dict  # platform -> content mapping
    suggested_post_times: List[str]
    created_at: str


class ScheduleOptimizeRequest(BaseModel):
    """Request model for schedule optimization."""
    platform: str = Field(..., description="Platform to optimize")
    audience_timezone: Optional[str] = Field(None, description="Target audience timezone")
    historical_data: Optional[dict] = Field(None, description="Historical engagement data")


class ScheduleOptimizeResponse(BaseModel):
    """Response model for schedule optimization."""
    platform: str
    optimal_times: List[str]
    confidence_score: float
    recommendations: List[str]


class EngagementRequest(BaseModel):
    """Request model for engagement management."""
    post_id: str = Field(..., description="ID of the post to manage")
    action: str = Field("monitor", description="Action: monitor, respond, escalate")
    response_draft: Optional[bool] = Field(True, description="Draft AI responses")


class EngagementResponse(BaseModel):
    """Response model for engagement management."""
    post_id: str
    mentions_count: int
    comments_count: int
    suggested_responses: List[dict]
    urgency_level: str  # low, medium, high, critical


# ============================================
# Health Check Endpoint
# ============================================

@app.get("/health")
async def health_check():
    """Health check endpoint for container orchestration."""
    return {
        "status": "healthy",
        "service": "social-autopilot-agent-api",
        "version": "1.0.0"
    }


# ============================================
# Agent Endpoints
# ============================================

@app.post("/agents/content/create", response_model=ContentCreateResponse)
async def create_content(request: ContentCreateRequest, _: None = Depends(require_api_key)):
    """
    Create social media content using AI agents.
    
    Generates platform-specific content variations based on the provided topic,
    with appropriate tone, length, and hashtag suggestions.
    """
    logger.info(f"Creating content for topic: {request.topic}")
    
    try:
        # Import agent harness here to avoid circular imports
        from agents.content_creator import ContentCreatorAgent
        
        agent = ContentCreatorAgent()
        result = await agent.create_content(
            topic=request.topic,
            platforms=request.platforms,
            tone=request.tone,
            include_hashtags=request.include_hashtags
        )
        
        return ContentCreateResponse(
            id=result.get("id", "generated"),
            topic=request.topic,
            platforms=result.get("platforms", {}),
            suggested_post_times=result.get("suggested_times", []),
            created_at=result.get("created_at", "")
        )
    except Exception as e:
        logger.error(f"Content creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/agents/schedule/optimize", response_model=ScheduleOptimizeResponse)
async def optimize_schedule(request: ScheduleOptimizeRequest, _: None = Depends(require_api_key)):
    """
    Optimize posting schedule using AI analysis.
    
    Analyzes historical engagement data and recommends optimal posting times
    for maximum reach and engagement.
    """
    logger.info(f"Optimizing schedule for platform: {request.platform}")
    
    try:
        from agents.scheduling_agent import SchedulingOptimizerAgent
        
        agent = SchedulingOptimizerAgent()
        result = await agent.optimize_schedule(
            platform=request.platform,
            timezone=request.audience_timezone,
            historical_data=request.historical_data
        )
        
        return ScheduleOptimizeResponse(
            platform=request.platform,
            optimal_times=result.get("optimal_times", []),
            confidence_score=result.get("confidence", 0.0),
            recommendations=result.get("recommendations", [])
        )
    except Exception as e:
        logger.error(f"Schedule optimization failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/agents/engagement/manage", response_model=EngagementResponse)
async def manage_engagement(request: EngagementRequest, _: None = Depends(require_api_key)):
    """
    Manage engagement for a specific post.
    
    Monitors comments and mentions, drafts responses, and escalates urgent matters.
    """
    logger.info(f"Managing engagement for post: {request.post_id}, action: {request.action}")
    
    try:
        from agents.engagement_agent import EngagementManagerAgent
        
        agent = EngagementManagerAgent()
        result = await agent.manage_engagement(
            post_id=request.post_id,
            action=request.action,
            draft_responses=request.response_draft
        )
        
        return EngagementResponse(
            post_id=request.post_id,
            mentions_count=result.get("mentions", 0),
            comments_count=result.get("comments", 0),
            suggested_responses=result.get("responses", []),
            urgency_level=result.get("urgency", "low")
        )
    except Exception as e:
        logger.error(f"Engagement management failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================
# Agent Status Endpoints
# ============================================

@app.get("/agents/status")
async def get_agent_status(_: None = Depends(require_api_key)):
    """Get status of all available agents."""
    return {
        "content_creator": {
            "status": "available",
            "description": "Generates social media content from topics"
        },
        "scheduling_optimizer": {
            "status": "available", 
            "description": "Optimizes posting schedules for engagement"
        },
        "engagement_manager": {
            "status": "available",
            "description": "Manages comments, mentions, and responses"
        }
    }


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "RedevOps.io Social Autopilot Agent API",
        "version": "1.0.0",
        "description": "Autonomous AI agents for social media management",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
