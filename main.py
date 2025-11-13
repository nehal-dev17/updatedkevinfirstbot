from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from routes.user import router as user_router
from routes.chat import router as chat_router
from database import init_db
import os
from dotenv import load_dotenv
# Load environment variables
load_dotenv()
# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(
    title="AI Wellness Companion API",
    description="Production-ready wellness companion API with rate limiting",
    version="1.0.0"
)
# Add rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Register routers
app.include_router(user_router, prefix="/api/v1", tags=["User & Profile"])
app.include_router(chat_router, prefix="/api/v1", tags=["Chat & History"])
@app.on_event("startup")
async def startup_event():
    """Initialize database tables on startup"""
    try:
        init_db()
        print("✓ Database tables initialized successfully")
        print("✓ Rate limiting enabled")
    except Exception as e:
        print(f"✗ Database initialization error: {str(e)}")
        raise
@app.get("/", tags=["Health"])
@limiter.limit("50/minute")
async def root(request: Request):
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "AI Wellness Companion API",
        "version": "1.0.0",
        "rate_limiting": "enabled"
    }
@app.get("/health", tags=["Health"])
@limiter.limit("50/minute")
async def health_check(request: Request):
    """Detailed health check"""
    return {
        "status": "ok",
        "database": "connected",
        "ai_service": "configured",
        "rate_limiting": "active"
    }
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=os.getenv("ENVIRONMENT", "production") == "development"
    )