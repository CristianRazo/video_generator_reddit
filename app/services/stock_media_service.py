# app/services/stock_media_service.py
import requests
import os
import random
import uuid
from typing import Optional, List, Dict, Any
from app.core.config import PEXELS_API_KEY # Asume que está en tu config.py

PEXELS_SEARCH_VIDEO_URL = "https://api.pexels.com/videos/search"
# Podríamos añadir PEXELS_POPULAR_VIDEO_URL = "https://api.pexels.com/videos/popular"

def search_and_download_pexels_video(
    keywords: str, 
    project_id: str, # Para crear una carpeta de assets específica del proyecto
    video_filename: str = "stock_video.mp4", # Nombre base del archivo descargado
    orientation: str = "landscape", # 'landscape', 'portrait', 'square'
    size: str = "medium", # 'small', 'medium', 'large' (para calidad/resolución)
    per_page: int = 5 # Cuántos videos buscar para elegir uno
) -> Optional[str]:
    """
    Busca un video en Pexels basado en keywords, descarga el primero relevante
    y devuelve la ruta local al archivo descargado.
    """
    if not PEXELS_API_KEY or PEXELS_API_KEY == "TU_CLAVE_API_DE_PEXELS_AQUI":
        print("[Stock Media Service] PEXELS_API_KEY no configurada. No se puede buscar video.")
        return None

    headers = {"Authorization": PEXELS_API_KEY}
    params = {
        "query": keywords,
        "orientation": orientation,
        "size": size,
        "per_page": per_page
    }

    try:
        print(f"[Stock Media Service - {project_id}] Buscando video en Pexels con keywords: '{keywords}'...")
        response = requests.get(PEXELS_SEARCH_VIDEO_URL, headers=headers, params=params, timeout=15)
        response.raise_for_status() # Lanza una excepción para errores HTTP 4xx/5xx
        data = response.json()

        if not data.get("videos"):
            print(f"[Stock Media Service - {project_id}] No se encontraron videos en Pexels para: '{keywords}'")
            return None

        # Elegir un video (ej. el primero o uno al azar de los resultados)
        # Podrías implementar lógica más sofisticada para elegir el mejor video.
        selected_video_info = random.choice(data["videos"]) # Elegir uno al azar de los resultados

        # Encontrar un link de descarga de buena calidad pero no excesivamente grande
        # Pexels devuelve varios 'video_files' con diferentes calidades/resoluciones
        video_link = None
        target_quality = "hd" # Intentar obtener HD (usualmente ~1280 o ~1920 de ancho)
                              # Las calidades comunes en Pexels son sd, hd, uhd

        for vf in selected_video_info.get("video_files", []):
            if vf.get("quality") == target_quality and vf.get("link"): # Buscar calidad HD
                # Preferir archivos mp4
                if vf.get('file_type') == 'video/mp4':
                    video_link = vf["link"]
                    break

        # Si no se encontró HD, tomar el primer link disponible de mp4
        if not video_link:
            for vf in selected_video_info.get("video_files", []):
                 if vf.get("link") and vf.get('file_type') == 'video/mp4':
                    video_link = vf["link"]
                    break

        if not video_link: # Si aún no hay link (ej. no hay mp4)
            print(f"[Stock Media Service - {project_id}] No se encontró un link de video MP4 adecuado para: '{keywords}'")
            return None

        print(f"[Stock Media Service - {project_id}] Video seleccionado de Pexels: {selected_video_info.get('url')}")
        print(f"[Stock Media Service - {project_id}] Descargando desde: {video_link}...")

        # Crear directorio para assets descargados de este proyecto si no existe
        # WORKDIR es /usr/src/app. Guardaremos en outputs/temp_assets/<project_id>/videos/
        project_assets_dir = os.path.join("/usr/src/app/outputs/temp_assets", project_id, "videos")
        os.makedirs(project_assets_dir, exist_ok=True)

        local_video_path = os.path.join(project_assets_dir, video_filename)

        # Descargar el video
        video_response = requests.get(video_link, stream=True, timeout=60) # Timeout más largo para descargas
        video_response.raise_for_status()
        with open(local_video_path, 'wb') as f:
            for chunk in video_response.iter_content(chunk_size=8192):
                f.write(chunk)

        print(f"[Stock Media Service - {project_id}] Video descargado exitosamente en: {local_video_path}")

        # Devolver la ruta relativa al WORKDIR para que sea consistente con otras rutas de assets
        return os.path.relpath(local_video_path, "/usr/src/app") # ej. outputs/temp_assets/...

    except requests.exceptions.RequestException as e_req:
        print(f"[Stock Media Service - {project_id}] Error de red al contactar Pexels API o descargar video: {e_req}")
        return None
    except Exception as e:
        print(f"[Stock Media Service - {project_id}] Error inesperado en el servicio Pexels: {e}")
        import traceback; traceback.print_exc()
        return None

# Ejemplo de uso para probar este servicio aisladamente
if __name__ == "__main__":
    if not PEXELS_API_KEY or PEXELS_API_KEY == "TU_CLAVE_API_DE_PEXELS_AQUI":
        print("Configura tu PEXELS_API_KEY en app/core/config.py para probar.")
    else:
        test_project_id = f"project_pexels_test_{uuid.uuid4().hex[:6]}"
        keywords_test = "nature forest peaceful" # Palabras clave de ejemplo

        # Crear carpeta outputs para la prueba si no existe (a nivel de raíz del proyecto)
        if not os.path.exists("outputs"): os.makedirs("outputs")

        downloaded_video_path = search_and_download_pexels_video(
            keywords=keywords_test, 
            project_id=test_project_id,
            video_filename="forest_bg.mp4"
        )
        if downloaded_video_path:
            print(f"\nPrueba del servicio Pexels exitosa.")
            print(f"Video descargado y guardado en (ruta relativa al WORKDIR): {downloaded_video_path}")
            print(f"Ruta completa en host (asumiendo que 'outputs' está montado): ./outputs/temp_assets/{test_project_id}/videos/forest_bg.mp4")
        else:
            print("\nFalló la prueba del servicio Pexels.")