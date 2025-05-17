# app/services/script_generation_service.py
import nltk
from typing import List, Dict, Any, Optional
import os
import uuid

# Importar nuestros otros servicios
from app.services import tts_service
from app.services import ai_text_enhancer_service # Asumiendo que ya está creado y funciona

# (Tu función segment_text_into_sentences(...) permanece igual)
def segment_text_into_sentences(text: str) -> List[str]:
    if not text: return []
    # Asegúrate que 'punkt' esté disponible como lo configuramos en Dockerfile
    sentences = nltk.sent_tokenize(text, language='spanish') 
    return [s.strip() for s in sentences if s.strip()]

def create_script_segments(
    reddit_data: Dict[str, Any], 
    project_id: str = "default_project",
    target_narration_language: str = "español"
) -> List[Dict[str, Any]]:
    script_segments = []
    global_segment_counter = 0

    # --- Helper anidado para segmentar, hacer TTS y crear info de segmento ---
    # Esta función ahora recibe texto que YA HA SIDO MEJORADO POR IA (si aplica)
    def process_block_to_segments(
        text_block_enhanced: str, # Texto del bloque ya mejorado por IA
        original_text_block: str, # Texto del bloque original (para referencia)
        source_type_tag: str,     # ej. "title", "selftext", "comment_1"
        type_subfolder_for_tts: str, # ej. "title", "selftext", "comments/comment_1"
        current_project_id: str
    ):
        nonlocal global_segment_counter
        nonlocal script_segments

        sentences = segment_text_into_sentences(text_block_enhanced)
        if not sentences:
            print(f"[INFO] No se generaron frases para el bloque '{source_type_tag}' después de la mejora y segmentación.")
            return

        for i, sentence_chunk in enumerate(sentences):
            # El sentence_chunk ya es del texto mejorado
            print(f"\nProcesando frase mejorada ({source_type_tag} - frase {i+1}): '{sentence_chunk[:50]}...'")
            
            global_segment_counter += 1
            audio_filename = f"segment_{global_segment_counter:03d}.mp3"
            
            generated_path = tts_service.synthesize_text_to_audio_file(
                text_to_speak=sentence_chunk, # Texto mejorado y segmentado
                output_filename=audio_filename,
                project_id=current_project_id,
                type_subfolder=type_subfolder_for_tts
            )

            if not generated_path:
                print(f"[ERROR] No se pudo generar audio para la frase: '{sentence_chunk[:50]}...'")
                continue 

            duration_ms = tts_service.get_audio_duration_ms(generated_path) or 0
            print(f"Audio generado: {generated_path}, Duración: {duration_ms}ms")

            script_segments.append({
                "id": f"seg_{current_project_id}_{global_segment_counter:03d}",
                "segment_order": global_segment_counter,
                "text_chunk": sentence_chunk, # Este es el chunk de la frase ya mejorada
                # "original_text_block": original_text_block, # Podríamos guardar el bloque original si es útil
                "actual_tts_audio_url": generated_path,
                "actual_tts_duration_ms": duration_ms,
                "source_type": source_type_tag,
                "visual_type": "static_video",
                "visual_prompt_or_keyword": sentence_chunk[:200],
                "visual_asset_url": "assets/videos/Video_Cosmico_flash.mp4", # Placeholder, puedes cambiarlo
                "visual_duration_ms": duration_ms,
                "transition_to_next": "cut",
                "subtitles_enabled": True,
                "voice_options": None,
                "visual_asset_url_is_loopable": True
            })
    # --- Fin del helper anidado ---

    # 1. Procesar el TÍTULO
    if reddit_data.get("title"):
        original_title = reddit_data["title"]
        print(f"\nMejorando TÍTULO con IA: '{original_title[:100]}...'")
        enhanced_title = ai_text_enhancer_service.enhance_text_for_tts(
            original_title, target_language=target_narration_language
        )
        if not enhanced_title: 
            print(f"[WARN] Falló la mejora del título con IA, usando original.")
            enhanced_title = original_title
        else:
            print(f"Título mejorado por IA: '{enhanced_title[:100]}...'")
        
        process_block_to_segments(enhanced_title, original_title, "title", "title", project_id)

    # 2. Procesar el SELFTEXT
    if reddit_data.get("selftext"):
        original_selftext = reddit_data["selftext"]
        if original_selftext and original_selftext.strip(): # Solo procesar si hay contenido
            print(f"\nMejorando SELFTEXT con IA: '{original_selftext[:100]}...'")
            enhanced_selftext = ai_text_enhancer_service.enhance_text_for_tts(
                original_selftext, target_language=target_narration_language
            )
            if not enhanced_selftext:
                print(f"[WARN] Falló la mejora del selftext con IA, usando original.")
                enhanced_selftext = original_selftext
            else:
                print(f"Selftext mejorado por IA (primeros 100): '{enhanced_selftext[:100]}...'")

            process_block_to_segments(enhanced_selftext, original_selftext, "selftext", "selftext", project_id)
        else:
            print("[INFO] Selftext está vacío, omitiendo.")


    # 3. Procesar los COMENTARIOS
    if reddit_data.get("top_comments"):
        for comment_idx, comment in enumerate(reddit_data["top_comments"]):
            if comment.get("body"):
                original_comment_body = comment["body"]
                comment_tag = f"comment_{comment_idx+1}"
                comment_tts_subfolder = os.path.join("comments", comment_tag)

                print(f"\nMejorando {comment_tag.upper()} con IA: '{original_comment_body[:100]}...'")
                enhanced_comment_body = ai_text_enhancer_service.enhance_text_for_tts(
                    original_comment_body, target_language=target_narration_language
                )
                if not enhanced_comment_body:
                    print(f"[WARN] Falló la mejora del {comment_tag.upper()} con IA, usando original.")
                    enhanced_comment_body = original_comment_body
                else:
                    print(f"{comment_tag.upper()} mejorado por IA: '{enhanced_comment_body[:100]}...'")
                
                process_block_to_segments(enhanced_comment_body, original_comment_body, comment_tag, comment_tts_subfolder, project_id)
    
    print(f"\nProceso de generación de guion completado. Se generaron {len(script_segments)} segmentos en total.")
    return script_segments

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