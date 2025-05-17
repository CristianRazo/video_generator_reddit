# video_generator_reddit/app/api/v1/endpoints/script_orchestrator.py
from fastapi import APIRouter, HTTPException, Body
import uuid
import json 
import os

# --- Importar la tarea Celery ---
from app.workers.tasks.video_processing_tasks import generate_script_and_audio_for_post_task # <--- NUEVA IMPORTACIÓN

# --- Importar modelos Pydantic ---
from app.api.v1.schemas import (
    GenerateScriptRequest,
    # GenerateScriptResponse, # Ya no la usamos para la respuesta de este endpoint
    ScriptGenerationQueuedResponse # <--- NUEVO MODELO DE RESPUESTA
)
# (No necesitamos importar los servicios scraping_service y script_generation_service aquí directamente,
#  ya que la tarea Celery los llamará internamente)

router = APIRouter()

@router.post(
    "/generate-full-script/", 
    response_model=ScriptGenerationQueuedResponse, # <--- USA EL NUEVO MODELO DE RESPUESTA
    summary="Encola una tarea para generar un guion completo con TTS a partir de una URL de Reddit"
)
async def enqueue_generate_full_script_task( # Renombrado para claridad (opcional)
    request_data: GenerateScriptRequest = Body(...)
):
    """
    Recibe una URL de Reddit y encola una tarea Celery para:
    1. Extraer contenido del post y comentarios (PRAW).
    2. Mejorar texto con IA.
    3. Segmentar los textos.
    4. Generar audio TTS para cada segmento.
    5. Medir la duración de cada audio.
    6. Guardar el guion estructurado como JSON y los archivos de audio.
    
    Responde inmediatamente con un ID de tarea.
    """
    print(f"Recibida solicitud para encolar generación de guion para URL: {request_data.reddit_url}")

    current_project_id = request_data.project_id
    if not current_project_id:
        current_project_id = f"project_{uuid.uuid4().hex[:12]}"
    print(f"Usando project_id: {current_project_id}")

    # --- LLAMAR A LA TAREA CELERY ---
    try:
        # Usamos .delay() que es un atajo para .apply_async()
        # Pasamos los argumentos que espera nuestra tarea Celery
        task = generate_script_and_audio_for_post_task.delay(
            reddit_url=str(request_data.reddit_url),
            num_comments=request_data.num_comments,
            project_id=current_project_id
            # target_narration_language podrías añadirlo al request_data y pasarlo aquí si quieres
        )
        
        print(f"Tarea Celery encolada con ID: {task.id} para project_id: {current_project_id}")
        
        return ScriptGenerationQueuedResponse(
            project_id=current_project_id,
            task_id=task.id,
            status="QUEUED", # O "PENDING", Celery maneja el estado exacto
            message="La tarea de generación de guion y audio ha sido encolada."
        )

    except Exception as e:
        # Esto capturaría errores al *intentar encolar* la tarea (ej. si Redis no está disponible)
        # Los errores *dentro* de la tarea Celery se manejarán en el worker y se registrarán allí.
        print(f"Error al intentar encolar la tarea Celery: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error interno al encolar la tarea de generación: {str(e)}")