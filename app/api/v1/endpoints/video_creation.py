# app/api/v1/endpoints/video_creation.py
from fastapi import APIRouter, HTTPException, Body
# from typing import Optional # Ya deberías tenerlo
import uuid # Lo usamos si el project_id se genera aquí, pero ahora lo recibimos

# --- Importar la nueva tarea Celery ---
from app.workers.tasks.video_processing_tasks import assemble_video_from_project_id_task # <--- NUEVA IMPORTACIÓN

# --- Importar modelos Pydantic ---
from app.api.v1.schemas import AssembleVideoRequest, VideoAssemblyQueuedResponse # <--- USA EL NUEVO RESPONSE MODEL

# (video_assembly_service ya no se importa aquí directamente, la tarea lo usa)

router = APIRouter()

@router.post(
    "/assemble-video/",
    response_model=VideoAssemblyQueuedResponse, # <--- USA EL NUEVO RESPONSE MODEL
    summary="Encola una tarea para ensamblar el video final a partir de un project_id."
)
async def enqueue_assemble_video_task( # Renombrado para claridad
    request_data: AssembleVideoRequest = Body(...)
):
    """
    Toma un project_id y encola una tarea Celery para ensamblar el video final.
    Responde inmediatamente con un ID de tarea.
    """
    project_id = request_data.project_id
    # output_filename = request_data.output_filename or f"{project_id}_final_video.mp4" # Si lo hiciste configurable
    output_filename = f"{project_id}_final_video.mp4"


    print(f"Recibida solicitud para encolar ensamblaje de video para el proyecto: {project_id}")

    try:
        task = assemble_video_from_project_id_task.delay(
            project_id=project_id,
            output_filename=output_filename
        )
        
        print(f"Tarea Celery de ensamblaje de video encolada con ID: {task.id} para project_id: {project_id}")
        
        return VideoAssemblyQueuedResponse(
            project_id=project_id,
            task_id=task.id,
            status="QUEUED",
            message="La tarea de ensamblaje de video ha sido encolada."
        )
    except Exception as e:
        print(f"Error al intentar encolar la tarea Celery de ensamblaje: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno al encolar la tarea de ensamblaje: {str(e)}")