# app/services/script_generation_service.py
import nltk
from typing import List, Dict, Any, Optional
import os
import uuid

# Importar nuestros otros servicios
from app.services import tts_service
from app.services import ai_text_enhancer_service # Asumiendo que ya está creado y funciona
from app.services import stock_media_service

# (Tu función segment_text_into_sentences(...) permanece igual)
def segment_text_into_sentences(text: str) -> List[str]:
    if not text: return []
    # Asegúrate que 'punkt' esté disponible como lo configuramos en Dockerfile
    sentences = nltk.sent_tokenize(text, language='spanish') 
    return [s.strip() for s in sentences if s.strip()]

def create_script_segments(
    reddit_data: Dict[str, Any], 
    project_id: str = "default_project",
    target_narration_language: str = "español",
    default_visual_type: str = "static_image",
    default_visual_asset_url: str = "assets/images/default_background.jpg"
) -> List[Dict[str, Any]]:
    print(f"\n[SCRIPT_GEN - {project_id}] Iniciando para project_id: {project_id}")
    script_segments_for_json = []
    global_segment_counter = 0

    # --- Helper anidado ---
    def process_sentences_to_segments(
        sentences: List[str],
        source_type_tag: str,
        scene_visual_type: str,
        scene_visual_asset_url: str,
        scene_visual_is_loopable: bool,
        block_keywords_str: Optional[str], # <--- NUEVO PARÁMETRO para las keywords del bloque
        current_project_id: str
    ):
        nonlocal global_segment_counter
        nonlocal script_segments_for_json

        if not sentences: # ... (sin cambios) ...
            return

        print(f"    [SCRIPT_GEN_HELPER - {current_project_id}] Procesando {len(sentences)} frases para '{source_type_tag}' con visual '{scene_visual_type}'. Keywords del bloque: '{block_keywords_str}'")
        for i, sentence_chunk in enumerate(sentences):
            global_segment_counter += 1
            # ... (lógica de TTS, audio_filename, generated_path, duration_ms - sin cambios) ...
            tts_type_subfolder = source_type_tag
            audio_filename = f"segment_{global_segment_counter:03d}.mp3"
            generated_path = tts_service.synthesize_text_to_audio_file(
                text_to_speak=sentence_chunk, output_filename=audio_filename,
                project_id=current_project_id, type_subfolder=tts_type_subfolder
            )
            if not generated_path: continue
            duration_ms = tts_service.get_audio_duration_ms(generated_path) or 0
            
            # Usar las keywords del bloque, o el chunk como fallback
            prompt_keyword_to_store = block_keywords_str if block_keywords_str else sentence_chunk[:200]

            segment_dict_data = {
                "id": f"seg_{current_project_id}_{global_segment_counter:03d}",
                "segment_order": global_segment_counter, 
                "text_chunk": sentence_chunk,
                "actual_tts_audio_url": generated_path, 
                "actual_tts_duration_ms": duration_ms,
                "source_type": source_type_tag,
                "visual_type": scene_visual_type,
                "visual_asset_url": scene_visual_asset_url,
                "visual_asset_url_is_loopable": scene_visual_is_loopable,
                "visual_prompt_or_keyword": prompt_keyword_to_store, # <--- CAMBIO AQUÍ
                "visual_duration_ms": duration_ms, 
                "transition_to_next": "cut", "subtitles_enabled": True, "voice_options": None,
            }
            script_segments_for_json.append(segment_dict_data)
            print(f"        [SCRIPT_GEN_HELPER] Segmento #{global_segment_counter} AÑADIDO. Prompt/KW: '{prompt_keyword_to_store[:50]}...'")
    # --- Fin del helper anidado ---

    text_blocks_to_process = []
    # ... (lógica para llenar text_blocks_to_process con title, selftext, comments - sin cambios) ...
    if reddit_data.get("title"):
        text_blocks_to_process.append({"type": "title", "text": reddit_data["title"], "comment_idx": None})
    if reddit_data.get("selftext") and reddit_data["selftext"].strip():
        text_blocks_to_process.append({"type": "selftext", "text": reddit_data["selftext"], "comment_idx": None})
    if reddit_data.get("top_comments"):
        for idx, comment in enumerate(reddit_data["top_comments"]):
            if comment.get("body") and comment["body"].strip():
                text_blocks_to_process.append({"type": "comment", "text": comment["body"], "comment_idx": idx + 1})


    for block_info in text_blocks_to_process:
        original_text = block_info["text"]
        source_type = block_info["type"]
        comment_idx = block_info["comment_idx"]
        current_source_tag = source_type
        if source_type == "comment":
            current_source_tag = f"comment_{comment_idx}"
        
        print(f"\n[SCRIPT_GEN - {project_id}] Procesando bloque: {current_source_tag.upper()} (Original: '{original_text[:70]}...')")

        enhanced_text, keywords_list = ai_text_enhancer_service.enhance_text_and_extract_keywords(
            original_text, target_language=target_narration_language
        )
        if not enhanced_text: enhanced_text = original_text
        
        keywords_query_for_stock_video = None # String de keywords para Pexels
        if keywords_list:
            keywords_query_for_stock_video = ", ".join(keywords_list) # Unir lista en string
            print(f"  [SCRIPT_GEN - {project_id}] Keywords extraídas para {current_source_tag}: '{keywords_query_for_stock_video}'")
        else:
            print(f"  [SCRIPT_GEN - {project_id}] No se extrajeron keywords para {current_source_tag}.")

        scene_visual_type_to_use = default_visual_type
        scene_visual_asset_to_use = default_visual_asset_url
        scene_visual_loopable = False 

        if keywords_query_for_stock_video: # Solo buscar si tenemos keywords
            print(f"  Buscando video de stock para '{keywords_query_for_stock_video}'...")
            stock_video_filename = f"{current_source_tag}_bg_video.mp4"
            downloaded_video_path = stock_media_service.search_and_download_pexels_video(
                keywords=keywords_query_for_stock_video, project_id=project_id,
                video_filename=stock_video_filename
            )
            if downloaded_video_path:
                print(f"  Video de stock encontrado para {current_source_tag}: {downloaded_video_path}")
                scene_visual_type_to_use = "static_video"
                scene_visual_asset_to_use = downloaded_video_path
                scene_visual_loopable = True 
            else:
                print(f"  No se encontró video de stock para {current_source_tag}. Usando visual por defecto.")
        else: # Si no hubo keywords, usar visual por defecto
             print(f"  No hay keywords para buscar video de stock para {current_source_tag}. Usando visual por defecto.")
            
        sentences_for_block = segment_text_into_sentences(enhanced_text)
        
        process_sentences_to_segments(
            sentences_for_block,
            current_source_tag,
            scene_visual_type_to_use,
            scene_visual_asset_to_use,
            scene_visual_loopable,
            keywords_query_for_stock_video, # <--- PASAR LAS KEYWORDS DEL BLOQUE
            project_id
        )

    print(f"\n[SCRIPT_GEN - {project_id}] FINALIZADO. Total segmentos para JSON: {len(script_segments_for_json)}")
    return script_segments_for_json

# --- Bloque if __name__ == "__main__": para probar ---
if __name__ == "__main__":
    # from app.services import scraping_service # Descomentar para usar datos reales de PRAW
    import uuid 

    print("Iniciando prueba de generación de guion (Bloque de texto mejorado por IA -> Segmentación -> TTS)...")
    
    print("Usando datos mock de Reddit para la prueba...")
    reddit_content_data = {
        "id": "mock_post_block_enhanced",
        "title": "Este es un título con un herror y talves algunas cosas que mejorar.",
        "selftext": "El cuerpo del post. Necesita buena ortografia y gramatica. Una segunda frase para probar el flujo completo.",
        "top_comments": [
            {"body": "Primer comentario. Ola k ase.", "author": "c1"},
            {"body": "Segndo comentario, un poco mas largo para ver como se segmenta, y como la IA lo mejora antes de segmentar y luego generar el audio.", "author": "c2"},
        ]
    }

    if reddit_content_data:
        project_unique_id = f"test_project_block_ai_{uuid.uuid4().hex[:8]}"
        print(f"\nGenerando segmentos para el proyecto: {project_unique_id}")
        
        # Asegúrate de que tus API keys (OpenAI y Google TTS) estén en config.py y sean válidas
        generated_script = create_script_segments(
            reddit_content_data, 
            project_id=project_unique_id,
            target_narration_language="español"
        )
        
        if generated_script:
            print(f"\n--- Guion Generado Final (Total {len(generated_script)} segmentos) ---")
            for segment in generated_script:
                print(f"  Segmento ID: {segment.get('id')}, Orden: {segment.get('segment_order')}, Fuente: {segment.get('source_type')}")
                # "text_chunk" ahora es una frase del texto ya mejorado por IA
                print(f"    Texto (frase mejorada): '{segment.get('text_chunk', '')[:70]}...'") 
                print(f"    Audio: {segment.get('actual_tts_audio_url')}")
                print(f"    Duración: {segment.get('actual_tts_duration_ms')}ms")
                print("-" * 20)
        else:
            print("No se generó ningún segmento de guion.")
    else:
        print("No se pudieron obtener los datos de Reddit para la prueba (o el mock falló).")