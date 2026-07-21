
from pydantic import BaseModel, Field
from typing import List, Optional


class RecommendationItem(BaseModel):
    artist_name: str
    score: float
    source: str


class RecommendationResponse(BaseModel):
    user_id: Optional[str]
    k: int
    recommendations: List[RecommendationItem]
    model_used: str


class SimilarArtistsRequest(BaseModel):
    artist_name: str
    k: int = Field(default=10, ge=1, le=50)


class UserRecommendationRequest(BaseModel):
    user_id: str
    k: int = Field(default=10, ge=1, le=50)
    mode: str = Field(default="hybrid", pattern="^(hybrid|svd|content|popularity)$")


class ColdStartRequest(BaseModel):
    k: int = Field(default=10, ge=1, le=50)


class HealthResponse(BaseModel):
    status: str
    models_loaded: List[str]
    total_artists: int
    total_users: int