
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pathlib import Path
from src.api.schemas import (
    RecommendationResponse, RecommendationItem,
    SimilarArtistsRequest, UserRecommendationRequest,
    ColdStartRequest, HealthResponse
)
from src.api.recommender import RecommenderService

# Global service instance
service: RecommenderService = None
# Create log directory if it doesn't exist
project_root = Path(__file__).resolve().parents[2]
log_dir = project_root / "outputs" / "logs"
log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(log_dir / "api.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load all models once at startup, release at shutdown."""
    global service
    project_root = Path(__file__).resolve().parents[2]
    service = RecommenderService(config_path=project_root / "configs" / "config.yaml")
    yield
    service = None


app = FastAPI(
    title="Music Recommendation API",
    description="Hybrid music recommendation system — SVD + Content-Based + Popularity",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
def health():
    """Check API status and confirm models are loaded."""
    return HealthResponse(
        status="ok",
        models_loaded=["popularity", "svd", "content_based", "hybrid", "ranker"],
        total_artists=service.total_artists,
        total_users=service.total_users
    )


@app.post("/recommend/user", response_model=RecommendationResponse)
def recommend_for_user(request: UserRecommendationRequest):

    logger.info(
        "recommend/user | user=%s | mode=%s | k=%d",
        request.user_id,
        request.mode,
        request.k,
    )

    results, model_used = service.get_recommendations(
        user_id=request.user_id,
        k=request.k,
        mode=request.mode
    )

    if results.empty:
        logger.warning(
            "No recommendations found for user=%s",
            request.user_id
        )
        raise HTTPException(
            status_code=404,
            detail=f"No recommendations found for user '{request.user_id}'. "
                   f"User may not exist in the system."
        )

    logger.info(
        "Returned %d recommendations using %s",
        len(results),
        model_used,
    )

    return RecommendationResponse(
        user_id=request.user_id,
        k=request.k,
        recommendations=[
            RecommendationItem(
                artist_name=row["artist_name"],
                score=round(float(row["score"]), 4),
                source=model_used
            )
            for _, row in results.iterrows()
        ],
        model_used=model_used
    )


@app.post("/recommend/similar", response_model=RecommendationResponse)
def similar_artists(request: SimilarArtistsRequest):
    """
    Find artists similar to a given artist.
    Uses SVD latent space similarity, falls back to audio feature similarity.
    """
    logger.info(
    "recommend/similar | artist=%s | k=%d",
    request.artist_name,
    request.k,
    )

    results, model_used = service.get_similar_artists(
        artist_name=request.artist_name,
        k=request.k
    )

    if results.empty:
        logger.warning(
        "Similar artist search failed for artist=%s",
        request.artist_name
        )
        raise HTTPException(
            status_code=404,
            detail=f"Artist '{request.artist_name}' not found or has no similar artists."
        )
    logger.info(
    "Returned %d similar artists using %s",
    len(results),
    model_used,
    
    )
    return RecommendationResponse(
        user_id=None,
        k=request.k,
        recommendations=[
            RecommendationItem(
                artist_name=row["artist_name"],
                score=round(float(row["score"]), 4),
                source=model_used
            )
            for _, row in results.iterrows()
        ],
        model_used=model_used
    )


@app.post("/recommend/cold-start", response_model=RecommendationResponse)
def cold_start(request: ColdStartRequest):
    """
    Recommendations for new users with no listening history.
    Returns globally popular artists.
    """

    logger.info(
    "recommend/cold-start | k=%d",
    request.k,
    )
    results, model_used = service.get_cold_start(k=request.k)
    logger.info(
    "Returned %d cold-start recommendations",
    len(results),
    )
    return RecommendationResponse(
        user_id=None,
        k=request.k,
        recommendations=[
            RecommendationItem(
                artist_name=row["artist_name"],
                score=round(float(row["score"]), 4),
                source=model_used
            )
            for _, row in results.iterrows()
        ],
        model_used=model_used
    )


@app.get("/artists/{artist_name}/similar", response_model=RecommendationResponse)
def similar_artists_get(artist_name: str, k: int = 10):
    """
    GET version of similar artists — easier to call from a browser.
    Example: /artists/radiohead/similar?k=5
    """
    logger.info(
    "artists/%s/similar | k=%d",
    artist_name,
    k,
    )
    results, model_used = service.get_similar_artists(artist_name=artist_name, k=k)

    if results.empty:
        logger.warning(
        "Artist not found: %s",
        artist_name,
        )
        raise HTTPException(status_code=404, detail=f"Artist '{artist_name}' not found.")
    logger.info(
    "Returned %d similar artists using %s",
    len(results),
    model_used,
    )
    return RecommendationResponse(
        user_id=None,
        k=k,
        recommendations=[
            RecommendationItem(
                artist_name=row["artist_name"],
                score=round(float(row["score"]), 4),
                source=model_used
            )
            for _, row in results.iterrows()
        ],
        model_used=model_used
    )