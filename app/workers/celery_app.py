from celery import Celery

# Definimos el nombre de nuestra aplicación Celery.
# El primer argumento para Celery es usualmente el nombre del módulo actual.
# El broker es la URL de nuestro servidor Redis.
# 'redis://redis:6379/0' -> 'redis' es el nombre del servicio Redis en docker-compose.yml
#                         -> '6379' es el puerto por defecto de Redis
#                         -> '/0' es la base de datos por defecto en Redis (puedes usar del 0 al 15)
# El backend es donde Celery almacenará los resultados de las tareas.
# Usaremos Redis también para esto por simplicidad en esta etapa.
celery_app = Celery(
    "worker", # Puedes darle un nombre más descriptivo si quieres, ej. "video_tasks_worker"
    broker="redis://redis:6379/0",
    result_backend="redis://redis:6379/0",
    include=["app.workers.tasks.video_processing_tasks"] # Lista de módulos donde Celery buscará tareas.
)

# Configuraciones opcionales de Celery (puedes añadir más según necesites)
celery_app.conf.update(
    task_serializer="json",         # Formato de serialización para las tareas
    result_serializer="json",       # Formato de serialización para los resultados
    accept_content=["json"],        # Tipos de contenido aceptados
    timezone="America/Mexico_City", # Ajusta a tu zona horaria
    enable_utc=True,                # Recomendado si usas zonas horarias
    # result_expires=3600,          # Tiempo en segundos antes de que los resultados de las tareas se borren (1 hora)
    task_track_started=True,      # Para que se registre el estado 'STARTED' de la tarea
)

# Si quieres que Celery cargue la configuración desde un archivo de settings de Django, por ejemplo:
# celery_app.config_from_object('django.conf:settings', namespace='CELERY')

# Este es un ejemplo de cómo podrías añadir más configuraciones:
# if __name__ == '__main__':
#     celery_app.start() # No es necesario para la forma en que lo usaremos con el worker CLI
