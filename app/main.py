from fastapi import FastAPI
from typing import Optional # Importa Optional
from app.api.v1.endpoints import reddit_content 

from app.workers.tasks.example_tasks import example_task, another_task
from app.api.v1.endpoints import script_orchestrator 
from app.api.v1.endpoints import video_creation
from app.api.v1.endpoints import tasks_status
# Crear una instancia de la aplicación FastAPI
app = FastAPI(title="Video Generator API")


# Este es nuestro primer endpoint
@app.get("/")
async def read_root():
    return {"message": "Hola desde la API de Automatización de YouTube!"}

app.include_router(reddit_content.router, prefix="/api/v1/reddit", tags=["Reddit Content"])
app.include_router(script_orchestrator.router, prefix="/api/v1/scripts", tags=["2. Script Generation (Async)"]) # Actualizado tag
app.include_router(video_creation.router, prefix="/api/v1/videos", tags=["3. Video Creation (Async)"]) # Actualizado tag
app.include_router(tasks_status.router, prefix="/api/v1/tasks", tags=["4. Task Status"])



