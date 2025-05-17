# app/api/v1/endpoints/tasks_status.py
from fastapi import APIRouter, HTTPException, Path
from celery.result import AsyncResult # Para obtener el resultado de una tarea Celery
from typing import Any, Optional # Para manejar tipos opcionales
from app.workers.celery_app import celery_app # Importamos nuestra instancia de Celery
from app.api.v1.schemas import TaskStatusResponse # Importamos el nuevo schema

router = APIRouter()

@router.get(
    "/status/{task_id}",
    response_model=TaskStatusResponse,
    summary="Consulta el estado y resultado de una tarea Celery."
)
async def get_task_status(
    task_id: str = Path(..., description="El ID de la tarea Celery a consultar.")
):
    """
    Obtiene el estado actual de una tarea Celery.
    Si la tarea fue exitosa, también devuelve su resultado.
    Si la tarea falló, devuelve información del error.
    """
    # Creamos un objeto AsyncResult para la tarea específica usando su ID
    # y nuestra instancia de la aplicación Celery.
    task_result = AsyncResult(task_id, app=celery_app)

    result_data: Any = None
    error_data: Optional[str] = None

    if task_result.successful():
        result_data = task_result.result # Obtener el resultado (lo que devolvió la función de la tarea)
    elif task_result.failed():
        # Intentar obtener el traceback o la excepción como string
        try:
            # El traceback puede ser muy largo. Podríamos querer solo el mensaje de error.
            # task_result.get(propagate=False) podría dar más detalles de la excepción.
            error_data = str(task_result.info) if task_result.info else "Error desconocido en la tarea."
            if isinstance(task_result.info, Exception):
                 error_data = f"{type(task_result.info).__name__}: {str(task_result.info)}"
            # El traceback completo está en task_result.traceback
            # print(f"Traceback para tarea fallida {task_id}: {task_result.traceback}")
        except Exception as e:
            error_data = f"Error al obtener detalles del fallo de la tarea: {str(e)}"

    # El estado puede ser: PENDING, STARTED, RETRY, FAILURE, SUCCESS, REVOKED
    return TaskStatusResponse(
        task_id=task_result.id,
        status=task_result.status,
        result=result_data,
        error_info=error_data
    )