from fastapi import FastAPI
from routers import user_async, blog_async, authentication
import models.models as models
from database.database import engine

app = FastAPI()

# Run this at startup inside FastAPI's event loop
@app.on_event("startup")
async def init_models():
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)

# Include routers
app.include_router(user_async.router)
app.include_router(blog_async.router)
app.include_router(authentication.router)

@app.get("/")
async def index():
    return {"message": "Welcome to the FastAPI Blog App!"}
