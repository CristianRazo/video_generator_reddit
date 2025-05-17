# /usr/src/app/app/api/v1/schemas/__init__.py

# Asumiendo que tus modelos Pydantic están en un archivo llamado 'models.py' 
# dentro de esta misma carpeta 'schemas/'
from .schemas import GenerateScriptRequest, GenerateScriptResponse, ScriptSegmentOutput, AssembleVideoRequest, AssembleVideoResponse, ScriptGenerationQueuedResponse, VideoAssemblyQueuedResponse, TaskStatusResponse

# O si tienes diferentes archivos para diferentes tipos de schemas:
# from .request_schemas import GenerateScriptRequest
# from .response_schemas import GenerateScriptResponse, ScriptSegmentOutput