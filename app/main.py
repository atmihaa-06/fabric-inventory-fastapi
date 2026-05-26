from fastapi import FastAPI
from app.database import engine
from app.models import Base
from app.routers import fabric

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Fabric Inventory API"
)

@app.get("/")
def home():
    return {"message": "Fabric Inventory API"}

app.include_router(fabric.router)