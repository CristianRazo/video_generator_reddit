# app/services/video_assembly_service.py
from moviepy import (AudioFileClip, ColorClip, TextClip, ImageClip, VideoFileClip,
                     CompositeVideoClip, CompositeAudioClip, vfx,concatenate_videoclips) # concatenate_videoclips ya no se usa para la composición principal de segmentos
# Asegúrate que fx.all.loop y tools.cuts.subclip estén disponibles si los usas
# from moviepy.video.fx.all import loop # Si fx.all.loop es la forma de loopear
# from moviepy.video.tools.cuts import subclip # Si subclip es una función importada

import os
import uuid
import json
from typing import List, Dict, Optional
from collections import OrderedDict

transition_video_relative_path = "assets/videos/transi-5.mp4" 
transition_video_full_path_in_container = os.path.join("/usr/src/app/", transition_video_relative_path)


    
    
# Para la función loop, si fx.all.loop no existe, y .loop() tampoco,
# podríamos necesitar una función helper para loopear manualmente con concatenate_videoclips,
# o confiar en que el video de fondo sea suficientemente largo o que .with_duration() congele el último frame.
# Por ahora, intentaremos usar un .loop() si existe o .with_duration() como fallback para extender.

def assemble_video_from_script(
    project_id: str,
    output_filename: str = "final_video.mp4",
    video_resolution: tuple = (1920, 1080),
    fps: int = 24,
    transition_duration_s: float = 1.0
) -> Optional[str]:
    transition_clip = get_transition_clip() # Obtener el video de transición
    print(f"\n[Video Assembly] Iniciando ensamblaje con FONDO CONTINUO para el proyecto: {project_id}")
    # 1. Cargar script_segments desde el archivo JSON
    script_file_path_container = os.path.join("/usr/src/app/outputs/scripts", project_id, "script_data.json")
    if not os.path.exists(script_file_path_container):
        print(f"[ERROR] No se encontró el archivo de guion: {script_file_path_container}")
        return None
    try:
        with open(script_file_path_container, 'r', encoding='utf-8') as f:
            script_segments = json.load(f)
        if not script_segments:
            print("[ERROR] El guion JSON está vacío.")
            return None
        print(f"[INFO] Guion cargado: {len(script_segments)} segmentos.")
    except Exception as e_load:
        print(f"[ERROR] Error al cargar o parsear el archivo de guion JSON: {e_load}")
        return None
    # --- Agrupar segmentos por 'source_type' para crear "escenas" ---
    # Usamos OrderedDict para intentar mantener un orden de aparición lógico
    scenes_dict = OrderedDict()
    for seg in script_segments:
        source_type = seg.get("source_type", f"unknown_scene_{seg.get('segment_order', 0)}")
        if source_type not in scenes_dict:
            scenes_dict[source_type] = {
                "segments": [],
                "visual_type": seg.get("visual_type"), # Tomar del primer segmento de la escena
                "visual_asset_url": seg.get("visual_asset_url"),
                "is_loopable": seg.get("visual_asset_url_is_loopable", False)
            }
        scenes_dict[source_type]["segments"].append(seg)
    if not scenes_dict:
        print("[ERROR] No se pudieron agrupar segmentos en escenas.")
        return None

    all_final_scene_clips_with_audio = [] # Aquí guardaremos los clips de cada escena completa
    font_to_use = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' # O tu fuente
    target_w, target_h = video_resolution
    # --- Iterar sobre cada ESCENA ---
    for scene_name, scene_data in scenes_dict.items():
        current_scene_individual_segments = scene_data["segments"]
        print(f"\n  Procesando Escena: '{scene_name}' con {len(current_scene_individual_segments)} segmentos de texto.")

        scene_narration_duration_s = sum(s.get('actual_tts_duration_ms', 0) for s in current_scene_individual_segments) / 1000.0
        if scene_narration_duration_s <= 0:
            print(f"    Escena '{scene_name}' no tiene duración de narración, omitiendo.")
            continue

        # --- Crear la pista de narración para ESTA escena (TextClips + Audio) ---
        scene_text_audio_overlays = []
        current_time_in_scene_s = 0.0
        for i, segment_data in enumerate(current_scene_individual_segments):
            text_content = segment_data.get('text_chunk', '')
            audio_relative_path = segment_data.get('actual_tts_audio_url')
            actual_audio_duration_s = segment_data.get('actual_tts_duration_ms', 0) / 1000.0

            if not audio_relative_path or not text_content or actual_audio_duration_s <= 0: continue
            full_audio_path = os.path.join("/usr/src/app", audio_relative_path)
            if not os.path.exists(full_audio_path): continue
            
            try:
                audio_clip = AudioFileClip(full_audio_path)
                # Asegurar que la duración del audio_clip sea la correcta (actual_audio_duration_s)
                # Esto es importante si el archivo es ligeramente diferente o para consistencia
                if hasattr(audio_clip, 'with_duration'):
                    audio_clip = audio_clip.with_duration(actual_audio_duration_s)
                else:
                    audio_clip.duration = actual_audio_duration_s

                original_audio_duration_s = audio_clip.duration
                
                epsilon = 0.01
                
                effective_segment_duration_s = max(0.001, original_audio_duration_s - epsilon) # 1ms de margen para evitar problemas con los límites
                

                # Log de comparación (opcional)
                json_duration_s = segment_data.get('actual_tts_duration_ms', 0) / 1000.0
                if abs(original_audio_duration_s - json_duration_s) > 0.05: 
                    print(f"    [INFO] Discrepancia de duración para : "
                          f"Archivo Real Original: {original_audio_duration_s:.4f}s, JSON: {json_duration_s:.3f}s.")
                print(f"    Usando duración efectiva para el segmento (con epsilon): {effective_segment_duration_s:.4f}s.")
                
                # Creamos un subclip con esta duración efectiva ligeramente reducida
                audio_segment_for_textclip = audio_clip.subclipped(0, effective_segment_duration_s)

                
                txt_clip_raw = TextClip(
                    font=font_to_use, text=text_content, font_size=100, color='white',
                    size=(int(target_w * 0.80), None), method='caption', text_align='center',
                    interline=-5, stroke_color='black', stroke_width=4,
                    duration=actual_audio_duration_s
                )
                
                text_actual_width, text_actual_height = txt_clip_raw.size
                
                # --- 2. Crear el Panel de Fondo Semi-Transparente para el Texto ---
                # Hacemos el panel un poco más grande que el texto para tener padding.
                padding_x = 60 # Padding horizontal para el panel (30px a cada lado)
                padding_y = 40 # Padding vertical para el panel (20px arriba/abajo)
                
                panel_width = text_actual_width + padding_x
                panel_height = text_actual_height + padding_y

                # Asegurarse que el panel no exceda el ancho del video
                panel_width = min(panel_width, video_resolution[0])
                # (Podríamos añadir lógica similar para la altura si fuera necesario)

                panel_clip = ColorClip(
                    size=(panel_width, panel_height), 
                    color=(0, 0, 0), # Color negro para el panel
                    is_mask=False, 
                    duration=actual_audio_duration_s
                ).with_opacity(0.6) # <--- Opacidad del panel (0.0 transparente, 1.0 opaco). 0.5-0.7 suele funcionar bien.
                
                 # --- 3. Componer el Texto sobre el Panel ---
                # Primero, posicionar el texto raw en el centro del panel_clip
                txt_clip_on_panel = txt_clip_raw
                txt_clip_on_panel.pos = lambda t: ('center','center')
                 # Componer el panel y el texto. El texto va encima.
                txt_clip = CompositeVideoClip(
                    [panel_clip, txt_clip_on_panel], 
                    size=(panel_width, panel_height) # El tamaño del clip compuesto es el del panel
                )
                
                txt_clip.pos = lambda t: ('center','center')
                txt_clip = txt_clip.with_start(current_time_in_scene_s) # Inicio RELATIVO a esta escena
                txt_clip.audio = audio_segment_for_textclip # Asignar audio al TextClip
                txt_clip.layer = 1 # Para superponer sobre el fondo de la escena
                if hasattr(txt_clip, 'duration') and txt_clip.duration is not None: # Asegurar .end
                    txt_clip.end = txt_clip.start + txt_clip.duration

                scene_text_audio_overlays.append(txt_clip)
                current_time_in_scene_s += actual_audio_duration_s
            except Exception as e_seg: print(f"    [ERROR] Procesando overlay para escena '{scene_name}': {e_seg}"); traceback.print_exc()
        
        if not scene_text_audio_overlays:
            print(f"    [WARN] No se generaron overlays de texto/audio para la escena '{scene_name}'.")
            # Podríamos decidir crear un clip de silencio o un ColorClip de la duración de la escena si es necesario,
            # o simplemente no añadir esta escena si no tiene contenido narrado.
            # Por ahora, si no hay overlays, no se añadirá a all_final_scene_clips_with_audio.
            continue


        # --- Preparar el fondo para ESTA escena ---
        scene_bg_type = scene_data["visual_type"]
        scene_bg_asset_url = scene_data["visual_asset_url"]
        scene_bg_is_loopable = scene_data["is_loopable"]
        
        scene_background_final = None
        if scene_bg_type == "static_image" and scene_bg_asset_url:
            # ... (Tu lógica para cargar, redimensionar y recortar ImageClip) ...
            # ... Al final: scene_background_final = img_clip_processed.set_duration(scene_narration_duration_s)
            full_image_path = os.path.join("/usr/src/app", scene_bg_asset_url)
            if os.path.exists(full_image_path):
                try:
                    img_clip_orig = ImageClip(full_image_path)
                    current_w, current_h = img_clip_orig.size; ratio = max(target_w / current_w, target_h / current_h)
                    img_clip_resized = img_clip_orig.resized((int(current_w * ratio), int(current_h * ratio)))
                    w, h = img_clip_resized.size; x_offset = (w - target_w) // 2; y_offset = (h - target_h) // 2
                    img_clip_cropped = img_clip_resized.cropped(x1=x_offset, y1=y_offset, x2=x_offset + target_w, y2=y_offset + target_h)
                    scene_background_final = img_clip_cropped.set_duration(scene_narration_duration_s)
                except Exception as e: print(f"    [WARN] Error procesando imagen para escena '{scene_name}': {e}")

        elif scene_bg_type == "static_video" and scene_bg_asset_url:
            # ... (Tu lógica para cargar, redimensionar, recortar y LOOPEAR/SUBCLIPEAR VideoFileClip) ...
            # ... Al final: scene_background_final = video_clip_processed (con duración = scene_narration_duration_s)
            full_video_path = os.path.join("/usr/src/app", scene_bg_asset_url)
            if os.path.exists(full_video_path):
                try:
                    video_clip_orig = VideoFileClip(full_video_path, audio=False)
                    current_w, current_h = video_clip_orig.size; ratio = max(target_w / current_w, target_h / current_h)
                    video_clip_resized = video_clip_orig.resized((int(current_w * ratio), int(current_h * ratio)))
                    w, h = video_clip_resized.size; x_offset = (w - target_w) // 2; y_offset = (h - target_h) // 2
                    video_clip_cropped = video_clip_resized.cropped(x1=x_offset, y1=y_offset, x2=x_offset + target_w, y2=y_offset + target_h)

                    if video_clip_cropped.duration < scene_narration_duration_s and scene_bg_is_loopable:
                        if video_clip_cropped.duration > 0:
                            num_loops = int(scene_narration_duration_s / video_clip_cropped.duration) + 1
                            concatenated_loop = concatenate_videoclips([video_clip_cropped] * num_loops)
                            scene_background_final = concatenated_loop.subclipped(0, scene_narration_duration_s)
                            del concatenated_loop # Liberar
                        else: scene_background_final = video_clip_cropped.set_duration(scene_narration_duration_s) if hasattr(video_clip_cropped, 'set_duration') else video_clip_cropped
                    else:
                        scene_background_final = video_clip_cropped.subclipped(0, min(video_clip_cropped.duration, scene_narration_duration_s))
                    
                    # Asegurar duración final
                    if hasattr(scene_background_final, 'set_duration'): scene_background_final = scene_background_final.set_duration(scene_narration_duration_s)
                    else: scene_background_final.duration = scene_narration_duration_s

                except Exception as e: print(f"    [WARN] Error procesando video para escena '{scene_name}': {e}")

        if scene_background_final is None: # Fallback para esta escena
            scene_background_final = ColorClip(size=video_resolution, color=(30,30,30), duration=scene_narration_duration_s)
        
        scene_background_final.layer = 0 # O .layer_index = 0
        if not hasattr(scene_background_final, 'start'): scene_background_final.start = 0.0 # Start relativo a su propia composición
        if hasattr(scene_background_final, 'duration') and scene_background_final.duration is not None:
            scene_background_final.end = scene_background_final.start + scene_background_final.duration
        else: # Si la duración es None por alguna razón
            scene_background_final.duration = scene_narration_duration_s
            scene_background_final.end = scene_background_final.start + scene_narration_duration_s


        # --- Componer ESTA escena ---
        # El audio vendrá de los scene_text_audio_overlays. El fondo no tiene audio.
        scene_text_audio_overlays_concatenated = concatenate_videoclips(scene_text_audio_overlays, method="compose")
        scene_text_audio_overlays_concatenated.pos = lambda t: ('center','center')
        scene_text_audio_overlays_concatenated_array = []
        scene_text_audio_overlays_concatenated_array.append(scene_text_audio_overlays_concatenated)
        final_scene_clip = CompositeVideoClip([scene_background_final] + scene_text_audio_overlays_concatenated_array, 
                                              size=video_resolution, 
                                              use_bgclip=True)
        # El audio de final_scene_clip será la composición de los audios de scene_text_audio_overlays
        # Asegurar que la duración de la escena compuesta sea correcta
        final_scene_clip = final_scene_clip.set_duration(scene_narration_duration_s) if hasattr(final_scene_clip, 'set_duration') else final_scene_clip # o .with_duration

        all_final_scene_clips_with_audio.append(final_scene_clip)

    # --- Fin del bucle de escenas ---

    if not all_final_scene_clips_with_audio:
        print("[ERROR] No se generaron clips de escena finales.")
        return None

    # --- Añadir Transiciones (clips espaciadores negros) y Concatenar Escenas ---
    video_parts_with_transitions = []
    if transition_duration_s > 0 and len(all_final_scene_clips_with_audio) > 1:
        transition_spacer_clip = ColorClip(size=video_resolution, color=(0,0,0), duration=transition_duration_s)
        for i, scene_clip_item in enumerate(all_final_scene_clips_with_audio):
            video_parts_with_transitions.append(scene_clip_item)
            if i < len(all_final_scene_clips_with_audio) - 1:
                video_parts_with_transitions.append(transition_spacer_clip)
        print(f"\n[Video Assembly] Clips de escena y transiciones preparadas. Total partes: {len(video_parts_with_transitions)}")
    else: # Sin transiciones o solo una escena
        video_parts_with_transitions = all_final_scene_clips_with_audio
        print(f"\n[Video Assembly] Clips de escena preparados (sin transiciones). Total partes: {len(video_parts_with_transitions)}")
    
     # --- BLOQUE DE DEPURACIÓN PARA video_parts_with_transitions ---
    print(f"\n[DEBUG] Revisando 'video_parts_with_transitions' antes de concatenación final:")
    print(f"  Total de partes a concatenar: {len(video_parts_with_transitions)}")
    for idx, part_clip in enumerate(video_parts_with_transitions):
        clip_type = type(part_clip).__name__
        duration = getattr(part_clip, 'duration', 'N/A')
        size = getattr(part_clip, 'size', 'N/A')
        start_time = getattr(part_clip, 'start', 'N/A') # Los clips para concatenar usualmente tienen start=0
        
        print(f"  --- Parte {idx + 1} ---")
        print(f"    Tipo de Clip: {clip_type}")
        print(f"    Duración: {duration}s")
        print(f"    Tamaño: {size}")
        print(f"    Tiempo de Inicio (relativo al clip mismo): {start_time}")
    
    final_video = concatenate_videoclips(video_parts_with_transitions,method="compose")  

   # Escribir el video final
    # ... (tu código para output_video_dir_container, write_videofile, y finally block) ...
    # ... (asegúrate de usar final_video.write_videofile(...)) ...
    output_video_dir_container = os.path.join("/usr/src/app", "outputs", "videos", project_id)
    os.makedirs(output_video_dir_container, exist_ok=True)
    output_video_path_container = os.path.join(output_video_dir_container, output_filename)
    temp_audio_filename_only = f"temp_audio_{project_id}_{uuid.uuid4().hex[:8]}.m4a"
    temp_audio_filepath_in_tmp = os.path.join("/tmp", temp_audio_filename_only)
    final_generated_path = None
    try:
        print(f"[Video Assembly] Escribiendo video final en: {output_video_path_container} ...")
        final_video.write_videofile(
            output_video_path_container, codec="libx264", audio_codec="aac",
            fps=fps, threads=8, preset="medium",
            temp_audiofile=temp_audio_filepath_in_tmp
        )
        print(f"[Video Assembly] ¡Video final generado exitosamente!")
        final_generated_path = output_video_path_container
    except Exception as e:
        print(f"[ERROR] Error al escribir el archivo de video final: {e}")
        import traceback; traceback.print_exc()
    finally:
        if os.path.exists(temp_audio_filepath_in_tmp):
            try: os.remove(temp_audio_filepath_in_tmp)
            except Exception as e_remove: print(f"[WARN] No se pudo eliminar temp audio: {e_remove}")
    return final_generated_path

# funcion para obtener transition_clip
def get_transition_clip():
    ######################transition#################
    transition_clip = None
    if os.path.exists(transition_video_full_path_in_container):
        try:
            print(f"Cargando video de transition desde: {transition_video_full_path_in_container}")
            transition_clip = VideoFileClip(transition_video_full_path_in_container)
            end_time = min(transition_clip.duration, 5.0)
            transition_clip = transition_clip.subclipped(3, end_time)
            
            video_resolution: tuple = (1920, 1080)
            target_w, target_h = video_resolution
            
            current_w, current_h = transition_clip.size
            ratio = max(target_w / current_w, target_h / current_h)
            new_size = (int(current_w * ratio), int(current_h * ratio))
            transition_clip = transition_clip.resized(new_size)
            
            w_resized, h_resized = transition_clip.size
            x_offset = (w_resized - target_w) // 2
            y_offset = (h_resized - target_h) // 2
            
            transition_clip = transition_clip.cropped(
                x1=x_offset, y1=y_offset, 
                x2=x_offset + target_w, y2=y_offset + target_h
            )
            
            print(f"Intro cargada: duración={transition_clip.duration}s, tamaño={transition_clip.size}")
        except Exception as e:
            print(f"Error al cargar el video de transition '{transition_video_full_path_in_container}': {e}")
    else:
        print(f"[WARN] Video de transition no encontrado en: {transition_video_full_path_in_container}")
    ####################fin transition###############
    return transition_clip


# El bloque if __name__ == "__main__":
if __name__ == "__main__":
    # (Misma lógica de prueba que antes, asegúrate de que el project_id tenga un script_data.json
    #  que ahora especifique un visual_type="static_video", un visual_asset_url válido,
    #  y visual_asset_url_is_loopable=True si quieres probar el loop)
    test_project_id_for_continuous_bg = "PRUEBA_FONDO_VIDEO" 
    # ... (resto de tu bloque de prueba como lo tenías, llamando a assemble_video_from_script) ...
    print(f"Iniciando prueba de ensamblaje de video CON FONDO CONTINUO para el proyecto: {test_project_id_for_continuous_bg}")
    expected_script_path = os.path.join("/usr/src/app/outputs/scripts", test_project_id_for_continuous_bg, "script_data.json")
    if not os.path.exists(expected_script_path):
        print(f"[ALERTA DE PRUEBA] No se encontró el archivo de guion JSON en: {expected_script_path}")
        print("                 Asegúrate de que el 'test_project_id_for_continuous_bg' sea correcto,")
        print("                 que hayas generado el guion para él, y que ese guion especifique")
        print("                 visual_type='static_video' y un visual_asset_url válido en 'assets/videos/'.")
        print("                 Y la bandera 'visual_asset_url_is_loopable': True si el video es corto.")
        print("                 También, asegúrate de que tu Dockerfile copie la carpeta 'assets/' al contenedor.")
    else:
        output_video_file = assemble_video_from_script(
            project_id=test_project_id_for_continuous_bg,
            output_filename="video_fondo_continuo.mp4"
        )
        if output_video_file:
            print(f"\nPrueba de ensamblaje completada.")
            print(f"Video generado en (dentro del contenedor): {output_video_file}")
        else:
            print("\nFalló el ensamblaje del video de prueba.")