# app/services/video_assembly_service.py
from moviepy import (AudioFileClip, ColorClip, TextClip, ImageClip, VideoFileClip,
                            CompositeVideoClip, concatenate_videoclips)

# Para redimensionar imágenes
#importar uuid
import uuid
import json

# Asegúrate de importar todo lo que necesites de moviepy.editor
# Para TextClip, necesitarás fuentes instaladas en el contenedor, lo veremos después.
# Por ahora, nos enfocaremos en ColorClip y AudioFileClip.

import os
from typing import List, Dict, Optional

def assemble_video_from_script( 
    project_id: str,
    output_filename: str = "final_video.mp4",
    video_resolution: tuple = (1920, 1080), # Full HD
    fps: int = 24
) -> Optional[str]:
    """
    Ensambla un video a partir de una lista de segmentos de guion.
    Cada segmento tiene un archivo de audio y su duración.
    Por ahora, usa un fondo de color simple para cada segmento.

    Args:
        script_segments: Lista de diccionarios, cada uno representando un segmento.
                         Debe contener 'actual_tts_audio_url' y 'actual_tts_duration_ms'.
        project_id: ID del proyecto para la ruta de salida del video.
        output_filename: Nombre del archivo de video de salida.
        video_resolution: Tupla (ancho, alto) para la resolución del video.
        fps: Frames por segundo para el video.

    Returns:
        La ruta al archivo de video generado, o None si falla.
    """
    # --- NUEVO: Cargar script_segments desde el archivo JSON ---
    script_file_path_container = os.path.join("/usr/src/app/outputs/scripts", project_id, "script_data.json")

    if not os.path.exists(script_file_path_container):
        print(f"[ERROR] No se encontró el archivo de guion: {script_file_path_container}")
        return None
    try:
        with open(script_file_path_container, 'r', encoding='utf-8') as f:
            script_segments = json.load(f)
        print(f"[INFO] Guion cargado exitosamente desde: {script_file_path_container} ({len(script_segments)} segmentos)")
    except Exception as e_load:
        print(f"[ERROR] Error al cargar o parsear el archivo de guion JSON: {script_file_path_container}")
        print(f"Detalle: {e_load}")
        return None
    
    if not script_segments:
        print("[ERROR] La lista de segmentos de guion está vacía. No se puede generar el video.")
        return None
    
    video_clips = []
    print(f"[VIDEO_ASSEMBLY - {project_id}] Lista 'video_clips' inicializada. Tamaño: {len(video_clips)}")
    
    base_audio_path_in_container = "/usr/src/app/" # WORKDIR de Docker. Asumimos que las rutas de audio son relativas a esto.

    print(f"\n[Video Assembly] Iniciando ensamblaje para el proyecto: {project_id}")

    for i, segment_data in enumerate(script_segments):
        print(f"  [VIDEO_ASSEMBLY - {project_id}] Segmento {i+1} (orden: {segment_data.get('segment_order')}, fuente: {segment_data.get('source_type')})")
        print(f"    Texto del segmento: '{segment_data.get('text_chunk', 'N/A')[:50]}...'")
        print(f"    Preparando para añadir segment_video_clip a video_clips.")

        audio_relative_path = segment_data.get('actual_tts_audio_url')
        duration_ms = segment_data.get('actual_tts_duration_ms')

        if not audio_relative_path or duration_ms is None:
            print(f"[WARN] Segmento {i+1} no tiene ruta de audio o duración. Omitiendo.")
            continue
        
        # Las rutas en 'actual_tts_audio_url' son como 'outputs/audio/project_id/segment_N.mp3'
        # Estas son relativas al WORKDIR (/usr/src/app) dentro del contenedor.
        full_audio_path_container = os.path.join(base_audio_path_in_container, audio_relative_path)

        if not os.path.exists(full_audio_path_container):
            print(f"[ERROR] Archivo de audio no encontrado en el contenedor: {full_audio_path_container}. Omitiendo segmento.")
            continue
            
        duration_seconds = duration_ms / 1000.0

        try:        
            # 1. Cargar el clip de audio
            audio_clip = AudioFileClip(full_audio_path_container)

            visual_type = segment_data.get("visual_type")
            visual_asset_url = segment_data.get("visual_asset_url")

            background_clip = None

            # 2. Cargar el clip de fondo según el tipo visual
            if visual_type == "static_image" and visual_asset_url:
                full_image_path_container = os.path.join("/usr/src/app", visual_asset_url)
                if os.path.exists(full_image_path_container):
                    print(f"    Usando imagen de fondo: {full_image_path_container}")
                    background_clip = ImageClip(full_image_path_container, duration=duration_seconds)
                    # 1. Redimensionar manteniendo la relación de aspecto
                    current_w, current_h = background_clip.size
                    target_w, target_h = video_resolution

                    # Calculamos la proporción
                    width_ratio = target_w / current_w
                    height_ratio = target_h / current_h
                    resize_ratio = max(width_ratio, height_ratio)

                    # Redimensionamos usando .resized()
                    new_size = (int(current_w * resize_ratio), int(current_h * resize_ratio))
                    background_clip = background_clip.resized(new_size)

                    # 2. Centramos y recortamos el exceso
                    w, h = background_clip.size
                    x_center = (w - target_w) // 2
                    y_center = (h - target_h) // 2

                    background_clip = background_clip.cropped(
                        x1=x_center,
                        y1=y_center,
                        x2=x_center + target_w,
                        y2=y_center + target_h
                    )

                    # 3. Centramos el clip (aunque ya está recortado)
                    background_clip = background_clip.with_position(("center", "center"))
                else:
                    print(f"    [WARN] Imagen no encontrada en {full_image_path_container}, usando fondo de color.")
                    visual_type = "color_background"

            elif visual_type == "static_video" and visual_asset_url:
                full_video_path_container = os.path.join("/usr/src/app", visual_asset_url)
                if os.path.exists(full_video_path_container):
                    print(f"    Usando video de fondo: {full_video_path_container}")
                    try:
                        video_bg_original = VideoFileClip(full_video_path_container, audio=False) # Cargamos sin su audio original

                        # Estrategia para el video de fondo:
                        # 1. Redimensionar para cubrir (aspect fill) como con las imágenes.
                        current_w, current_h = video_bg_original.size
                        target_w, target_h = video_resolution
                        width_ratio = target_w / current_w
                        height_ratio = target_h / current_h
                        resize_ratio = max(width_ratio, height_ratio)
                        new_size = (int(current_w * resize_ratio), int(current_h * resize_ratio))

                        resized_video_bg = video_bg_original.resized(new_size)

                        # 2. Recortar al centro
                        w, h = resized_video_bg.size
                        x_offset = (w - target_w) // 2
                        y_offset = (h - target_h) // 2
                        cropped_video_bg = resized_video_bg.cropped(
                            x1=x_offset, y1=y_offset,
                            x2=x_offset + target_w, y2=y_offset + target_h
                        )

                        if cropped_video_bg.duration < duration_seconds and segment_data.get("visual_asset_url_is_loopable", False):
                            background_clip = cropped_video_bg.loop(duration=duration_seconds)
                            print(f"    Video de fondo loopeado a {duration_seconds}s.")
                        elif cropped_video_bg.duration >= duration_seconds:
                            background_clip = cropped_video_bg.subclipped(0, duration_seconds)
                            print(f"    Subclip de video de fondo tomado ({duration_seconds}s).")
                        else: # No es loopeable (porque .get() devolvió False) y es más corto
                            print(f"    [WARN] Video de fondo es más corto ({cropped_video_bg.duration}s) que el audio ({duration_seconds}s) y no es loopeable. Se usará su duración original.")
                            background_clip = cropped_video_bg

                    except Exception as e_vid_load:
                        print(f"    [WARN] Error al cargar o procesar video de fondo {full_video_path_container}: {e_vid_load}. Usando fondo de color.")
                        visual_type = "color_background" # Forzar fallback
            else:
                print(f"    [WARN] Video de fondo no encontrado en {full_video_path_container}. Usando fondo de color.")
                visual_type = "color_background" # Forzar fallback

            # Si no se cargó imagen o el tipo no era static_image
            if background_clip is None: 
                bg_color = (50, 50, 150) if i % 2 == 0 else (150, 50, 50)
                background_clip = ColorClip(size=video_resolution, color=bg_color, duration=duration_seconds)
            # --- AÑADIR TextClip ---
            text_content = segment_data.get('text_chunk', '')

            # Configuración del TextClip (puedes experimentar con estos valores)
            # Usamos 'DejaVu-Sans' que deberías tener instalada con fonts-dejavu-core
            txt_clip = TextClip(
                    font='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',    # Argumento posicional para la fuente
                    text=text_content,   # Argumento nombrado para el texto
                    font_size=120,        # Usamos font_size
                    color='white',
                    # Para method='caption', el fondo es transparente por defecto si no se especifica bg_color.
                    # O podemos ser explícitos si bg_color y transparent están en la firma:
                    # bg_color=None, # (ya es el default)
                    # transparent=True, # (ya es el default)
                    size=(int(video_resolution[0] * 0.75), None), # Ancho 90%, altura auto
                    method='caption',
                    horizontal_align='center', 
                    vertical_align='center',
                    text_align='center',        # Alineación para method='caption' (prueba 'West' o 'East' si 'center' no es lo que quieres)
                    interline=-2,          # Ajusta el interlineado (prueba valores)
                    stroke_color='black',
                    stroke_width=15,        # Grosor del borde
                    duration=duration_seconds # Pasamos la duración al constructor
            )

            # Posicionar el TextClip y establecer su duración
            txt_clip.pos = lambda t: ('center', 'center') 
            # ('center', 0.7) con relative=True significa: centrado horizontalmente, y al 70% desde la parte superior del video.
            # Puedes probar 'center' para centrarlo completamente, o ('center', 'bottom') para abajo, etc.

            # 3. Componer el fondo con el texto
            # El orden es importante: el último en la lista va encima.
            visual_composite_clip = CompositeVideoClip([background_clip, txt_clip], size=video_resolution)

            # 4. Asignar el audio al clip visual compuesto
            visual_composite_clip.audio = audio_clip
            segment_video_clip = visual_composite_clip
            # --- FIN AÑADIR TextClip ---

            video_clips.append(segment_video_clip)
            print(f"    Segmento {i+1} procesado. Duración: {duration_seconds:.2f}s. Audio: {full_audio_path_container}")

        except Exception as e:
            print(f"[ERROR] Error procesando segmento {i+1} con MoviePy: {e}")
            import traceback
            traceback.print_exc()
            continue # Saltar al siguiente segmento si este falla

    if not video_clips:
        print("[ERROR] No se generaron clips de video válidos. Abortando ensamblaje.")
        return None

    # 4. Concatenar todos los clips de segmento
    try:
        print("\n[Video Assembly] Concatenando clips...")
        final_clip = concatenate_videoclips(video_clips, method="compose")
    except Exception as e:
        print(f"[ERROR] Error al concatenar clips de video: {e}")
        return None

    # 5. Escribir el video final a un archivo
    output_video_dir = os.path.join(base_audio_path_in_container, "outputs", "videos", project_id)
    os.makedirs(output_video_dir, exist_ok=True)
    output_video_path = os.path.join(output_video_dir, output_filename)

    # --- MANEJO DEL ARCHIVO DE AUDIO TEMPORAL ---
    # Crear un nombre de archivo único para el audio temporal en /tmp/
    # /tmp/ es generalmente escribible por cualquier usuario en contenedores Linux.
    temp_audio_filename_only = f"temp_audio_{project_id}_{uuid.uuid4().hex[:8]}.m4a" # Nombre único
    temp_audio_filepath_in_tmp = os.path.join("/tmp", temp_audio_filename_only)
    # ---------------------------------------------

    try:
        print(f"[Video Assembly] Escribiendo video final en: {output_video_path} ...")
        print(f"[Video Assembly] Usando archivo de audio temporal en: {temp_audio_filepath_in_tmp}")
        # Usar codecs comunes para MP4. 'libx264' para video, 'aac' para audio.
        # 'threads' y 'preset' pueden ajustarse para velocidad vs calidad.
        final_clip.write_videofile(
            output_video_path, 
            codec="libx264", 
            audio_codec="aac",
            fps=fps,
            threads=4, # Ajusta según los cores de tu CPU
            preset="medium", # ultrafast, superfast, veryfast, faster, fast, medium, slow, slower, veryslow
            temp_audiofile=temp_audio_filepath_in_tmp
        )
        print(f"[Video Assembly] ¡Video final generado exitosamente en {output_video_path}!")
        return output_video_path # Devolver la ruta relativa al WORKDIR del contenedor
    except Exception as e:
        print(f"[ERROR] Error al escribir el archivo de video final: {e}")
        import traceback
        traceback.print_exc()
        return None

# Al final de app/services/video_assembly_service.py
if __name__ == "__main__":
    # --- IMPORTANTE: Configura este ID de proyecto ---
    # Este debe ser un project_id para el cual ya hayas generado el guion
    # y los archivos de audio usando el Módulo 2 (script_generation_service.py o el endpoint).
    # Por ejemplo, el 'PRUEBA GUARDADO JSON' o el 'test_project_block_ai_e975ee21' de tus pruebas anteriores.

    test_project_id_with_script_and_audio = "prueba muy corta" # <--- CAMBIA ESTO AL ID DE TU PROYECTO DE PRUEBA REAL

    print(f"Iniciando prueba de ensamblaje de video para el proyecto: {test_project_id_with_script_and_audio}")

    # Verificar si el script JSON existe como una primera comprobación
    expected_script_path = os.path.join("/usr/src/app/outputs/scripts", test_project_id_with_script_and_audio, "script_data.json")
    if not os.path.exists(expected_script_path):
        print(f"[ALERTA DE PRUEBA] No se encontró el archivo de guion JSON en: {expected_script_path}")
        print("                 Asegúrate de que el 'test_project_id_with_script_and_audio' sea correcto y")
        print("                 que hayas generado el guion y los audios para este project_id previamente.")
    else:
        output_video_file = assemble_video_from_script(
            project_id=test_project_id_with_script_and_audio,
            output_filename="video_desde_json.mp4" # Puedes cambiar el nombre del video de salida
        )

        if output_video_file:
            print(f"\nPrueba de ensamblaje completada.")
            print(f"Video generado en (dentro del contenedor): {output_video_file}")
            print(f"Deberías encontrarlo en tu máquina host en: outputs/videos/{test_project_id_with_script_and_audio}/video_desde_json.mp4")
        else:
            print("\nFalló el ensamblaje del video de prueba.")