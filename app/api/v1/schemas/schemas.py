# video_generator_reddit/app/api/v1/schemas.py
from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional, Dict, Any
import uuid # Lo quitamos de aquí si project_id se genera solo en el endpoint

class GenerateScriptRequest(BaseModel):
    reddit_url: HttpUrl
    num_comments: Optional[int] = Field(
        5, 
        ge=0,
        description="Número de comentarios principales a incluir en el guion."
    )
    project_id: Optional[str] = Field(
        None, 
        description="ID de proyecto opcional. Si no se provee, se generará uno en el endpoint."
    )

class ScriptSegmentOutput(BaseModel):
    id: str
    segment_order: int
    text_chunk: str
    actual_tts_audio_url: str # Ruta al archivo de audio local por ahora
    actual_tts_duration_ms: int
    source_type: str
    visual_type: str
    visual_prompt_or_keyword: str
    visual_asset_url: Optional[str] = None
    visual_duration_ms: int
    transition_to_next: Optional[str] = "cut"
    subtitles_enabled: Optional[bool] = True
    voice_options: Optional[Dict[str, Any]] = None

class GenerateScriptResponse(BaseModel):
    project_id: str
    message: str
    total_segments: int
    script: List[ScriptSegmentOutput]

class AssembleVideoRequest(BaseModel):
    project_id: str = Field(..., description="El ID del proyecto para el cual ensamblar el video. Se asume que el guion y los audios ya existen.")
    # Opcionalmente, podrías pasar output_filename, resolution, fps aquí si quieres que sean configurables por API
    # output_filename: Optional[str] = "final_video.mp4" 

class AssembleVideoResponse(BaseModel):
    project_id: str
    message: str
    video_url: Optional[str] = None # Ruta al video generado (relativa al servidor o una URL completa si se sube a la nube)
    # Podríamos añadir más detalles, como la duración del video final, etc.

class ScriptGenerationQueuedResponse(BaseModel):
    project_id: str
    task_id: str
    status: str # ej. "QUEUED", "PENDING"
    message: str

class VideoAssemblyQueuedResponse(BaseModel):
    project_id: str
    task_id: str
    status: str
    message: str

class TaskStatusResponse(BaseModel):
    task_id: str
    status: str  # Ej: "PENDING", "STARTED", "SUCCESS", "FAILURE", "RETRY", "REVOKED"
    result: Optional[Any] = None # El resultado de la tarea si está lista y fue exitosa (puede ser un dict, string, etc.)
    error_info: Optional[str] = None # Información del error si la tarea falló