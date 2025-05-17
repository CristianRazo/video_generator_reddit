import time
from app.workers.celery_app import celery_app # Importamos la instancia de Celery que creamos

@celery_app.task(name="create_example_task") # El decorador @celery_app.task convierte esta función en una tarea Celery
                                         # El argumento 'name' es opcional pero bueno para la claridad.
def example_task(a: int, b: int) -> int:
    """
    Una tarea de ejemplo simple que suma dos números después de una pequeña pausa.
    """
    print(f"Tarea de ejemplo iniciada con argumentos: a={a}, b={b}")
    time.sleep(5)  # Simulamos un trabajo que toma algo de tiempo
    result = a + b
    print(f"Tarea de ejemplo finalizada. Resultado: {result}")
    return result

@celery_app.task(name="another_simple_task")
def another_task(message: str) -> str:
    """
    Otra tarea simple que procesa un mensaje.
    """
    print(f"Another task recibió el mensaje: '{message}'")
    time.sleep(2)
    processed_message = f"Mensaje procesado: {message.upper()}!"
    print(f"Another task finalizó. Resultado: '{processed_message}'")
    return processed_message
