# video_generator_reddit/app/workers/tasks/video_processing_tasks.py
import os
import uuid
import json # <--- AÑADIR IMPORTACIÓN DE JSON
from typing import Dict, Any # List, Optional (asegúrate que estén si los usas)

from app.workers.celery_app import celery_app
from app.services import script_generation_service, video_assembly_service, scraping_service

@celery_app.task(name="tasks.generate_script_and_audio_for_post", bind=True) # bind=True para poder reintentar
def generate_script_and_audio_for_post_task(
    self, # self es el contexto de la tarea cuando bind=True
    reddit_url: str, 
    num_comments: int, 
    project_id: str,
    target_narration_language: str = "español"
) -> Dict[str, Any]:
    print(f"[CELERY TASK - {project_id} - ID: {self.request.id}] Iniciando para URL: {reddit_url}")

    try:
        print(f"[CELERY TASK - {project_id}] Obteniendo datos de Reddit...")
        reddit_content = scraping_service.get_post_data_from_url(
            reddit_url=reddit_url,
            num_top_comments=num_comments
        )
        if not reddit_content:
            error_message = f"No se pudo obtener contenido de Reddit para la URL: {reddit_url}"
            print(f"[CELERY TASK - {project_id}] ERROR: {error_message}")
            # Para que Celery marque la tarea como FAILED y se pueda manejar:
            # raise ValueError(error_message) 
            return {"project_id": project_id, "status": "FAILURE", "message": error_message}

        print(f"[CELERY TASK - {project_id}] Datos de Reddit obtenidos. Título: {reddit_content.get('title', 'N/A')[:50]}...")
        
        print(f"[CELERY TASK - {project_id}] Generando segmentos de guion y audios...")
        script_segments_data = script_generation_service.create_script_segments(
            reddit_data=reddit_content,
            project_id=project_id,
            target_narration_language=target_narration_language
        )

        if not script_segments_data:
            message = f"No se generaron segmentos de guion para el project_id: {project_id}"
            print(f"[CELERY TASK - {project_id}] {message}")
            return {"project_id": project_id, "status": "COMPLETED_EMPTY", "message": message}

        # --- LÓGICA PARA GUARDAR EL SCRIPT JSON ---
        script_output_base_dir = "/usr/src/app/outputs/scripts"
        project_script_dir = os.path.join(script_output_base_dir, project_id)
        os.makedirs(project_script_dir, exist_ok=True)
        
        script_filepath = os.path.join(project_script_dir, "script_data.json")
        try:
            with open(script_filepath, 'w', encoding='utf-8') as f:
                json.dump(script_segments_data, f, ensure_ascii=False, indent=4)
            print(f"[CELERY TASK - {project_id}] Guion guardado exitosamente en: {script_filepath}")
            save_message = f"Guion y audios generados. Guion JSON guardado en {script_filepath}."
        except Exception as e_save:
            save_message = f"Guion y audios generados, pero falló al guardar el guion JSON: {e_save}"
            print(f"[CELERY TASK - {project_id}] ERROR al guardar JSON: {save_message}")
            # Considerar si esto debe hacer que la tarea falle
            # raise self.retry(exc=e_save, countdown=60) o devolver FAILURE
            return {"project_id": project_id, "status": "PARTIAL_SUCCESS", "message": save_message, "error_saving_script": str(e_save)}
        # --- FIN LÓGICA PARA GUARDAR ---
        
        audio_base_path = os.path.join("/usr/src/app/outputs/audio", project_id)
        success_message = f"Proceso completado para project_id: {project_id}. {len(script_segments_data)} segmentos creados. {save_message}"
        print(f"[CELERY TASK - {project_id}] ÉXITO: {success_message}")
        
        return {
            "project_id": project_id, 
            "status": "SUCCESS", 
            "message": success_message,
            "script_path": script_filepath,
            "audio_paths_base": audio_base_path
        }

    except Exception as e:
        error_message = f"Excepción crítica en la tarea Celery para project_id {project_id}: {str(e)}"
        print(f"[CELERY TASK - {project_id}] ERROR CRÍTICO: {error_message}")
        import traceback
        traceback.print_exc()
        # Para que Celery maneje el reintento o el fallo:
        # self.update_state(state='FAILURE', meta={'exc_type': type(e).__name__, 'exc_message': traceback.format_exc()})
        # raise Ignore() # Para evitar que se reintente si no quieres, o simplemente no relanzar y devolver un estado de fallo
        return {"project_id": project_id, "status": "FAILURE", "message": error_message, "error_details": traceback.format_exc()}

@celery_app.task(name="tasks.assemble_video_from_project_id", bind=True)
def assemble_video_from_project_id_task(
    self, # Contexto de la tarea Celery
    project_id: str, 
    output_filename: str = "final_video.mp4", # Podrías hacerlo configurable si quieres
    # Otros parámetros de video_assembly_service podrían pasarse aquí si es necesario
) -> Dict[str, Any]:
    """
    Tarea Celery para ensamblar el video final a partir de un project_id
    para el cual ya existe un script_data.json y los archivos de audio.
    """
    print(f"[CELERY TASK - {project_id} - ID: {self.request.id}] Iniciando: assemble_video_from_project_id_task")

    try:
        video_file_path = video_assembly_service.assemble_video_from_script(
            project_id=project_id,
            output_filename=output_filename
            # Pasar otros args como video_resolution, fps si se hicieron parámetros de la tarea
        )

        if video_file_path:
            message = f"Video ensamblado exitosamente para project_id: {project_id}"
            print(f"[CELERY TASK - {project_id}] ÉXITO: {message}. Video en: {video_file_path}")
            return {"project_id": project_id, "status": "SUCCESS", "message": message, "video_path": video_file_path}
        else:
            message = f"Falló el ensamblaje del video para project_id: {project_id} (el servicio no devolvió ruta)."
            print(f"[CELERY TASK - {project_id}] ERROR: {message}")
            return {"project_id": project_id, "status": "FAILURE", "message": message}

    except Exception as e:
        error_message = f"Excepción crítica en assemble_video_from_project_id_task para project_id {project_id}: {str(e)}"
        print(f"[CELERY TASK - {project_id}] ERROR CRÍTICO: {error_message}")
        import traceback
        traceback.print_exc()
        return {"project_id": project_id, "status": "FAILURE", "message": error_message, "error_details": traceback.format_exc()}