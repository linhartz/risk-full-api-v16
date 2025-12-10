# api/causal_server.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# routry
from api.routers.risk_router import router as risk_router

app = FastAPI(
    title="AIR-NUR-API v13",
    version="13.0",
    description="Full AI risk integration API (HHI + HOPE + NUR + RSZ + Chaotic Risk)"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------
# Routers
# -------------------------
app.include_router(risk_router, prefix="/risk", tags=["risk"])

# -------------------------
# Health & Root
# -------------------------
@app.get("/", tags=["default"])
def root():
    return {"message": "AIR-NUR-API v13 is running"}

@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}
