# video_generator_reddit/app/services/ai_text_enhancer_service.py
from openai import OpenAI # Nueva forma de importar
from typing import Optional, Tuple, List

# Intentar importar la clave API desde config. Es mejor si el cliente la toma de variables de entorno
# o se le pasa explícitamente al instanciarlo.
try:
    from app.core.config import OPENAI_API_KEY
except ImportError:
    OPENAI_API_KEY = None
    print("[WARN] OPENAI_API_KEY no encontrada en app.core.config. El servicio podría no funcionar.")

def enhance_text_and_extract_keywords(
    text_to_process: str, 
    target_language: str = "español",
    model_name: str = "gpt-4o-mini"
) -> Tuple[Optional[str], Optional[List[str]]]:
    if not OPENAI_API_KEY or OPENAI_API_KEY.startswith("sk-TU_CLAVE"):
        print("[ERROR] La clave API de OpenAI no está configurada correctamente.")
        return text_to_process, None

    try:
        client = OpenAI(api_key=OPENAI_API_KEY)

        system_prompt = (
            "Eres un asistente experto en edición y pulido de textos para ser narrados por una voz TTS. "
            "Tu objetivo es que el texto final sea gramaticalmente perfecto, claro, conciso y que fluya de manera natural. "
            "Además, identificarás las palabras clave más relevantes del texto original."
        )
        user_prompt = ( # <--- PROMPT REFINADO ---
            f"1. Revisa y mejora el siguiente texto para una narración TTS en '{target_language}'. "
            f"Corrige todos los errores de gramática, ortografía y puntuación. Asegura una excelente fluidez. "
            f"Si el texto original está predominantemente en un idioma diferente al '{target_language}' y es un fragmento corto, "
            f"tradúcelo al '{target_language}' manteniendo el significado esencial. Si son nombres propios, marcas o citas directas "
            f"en otro idioma que deben conservarse, mantenlos. "
            f"IMPORTANTE: El texto mejorado debe comenzar inmediatamente, sin ningún prefijo, saludo, o introducción como 'Texto mejorado:'.\n" # Instrucción más explícita
            f"2. Después del texto mejorado, en una NUEVA LÍNEA y comenzando EXACTAMENTE con 'KEYWORDS:', " # Mantenemos exactitud aquí
            f"proporciona de 3 a 5 palabras clave relevantes del texto original, separadas por comas.\n\n"
            f"Texto original:\n---\n{text_to_process}\n---"
        )

        print(f"[AI Text Enhancer] Enviando texto (primeros 50 chars): '{text_to_process[:50]}...' al modelo {model_name}")

        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
        )
        
        full_response_content = response.choices[0].message.content.strip()
        
        enhanced_text_part = full_response_content
        keywords_list = None # Cambiado a keywords_list para claridad
        
        # Parsear la respuesta para separar texto mejorado y keywords
        keyword_marker = "\nKEYWORDS:"
        if keyword_marker in full_response_content:
            parts = full_response_content.split(keyword_marker, 1)
            enhanced_text_part = parts[0].strip()
            if len(parts) > 1 and parts[1].strip():
                keywords_list = [kw.strip() for kw in parts[1].strip().split(',') if kw.strip()]
        else:
            # Si no encontramos el marcador KEYWORDS, asumimos que toda la respuesta es el texto mejorado
            # y no hay keywords parseables de esta forma.
            print(f"[AI Text Enhancer] Marcador 'KEYWORDS:' no encontrado en la respuesta. Asumiendo toda la respuesta como texto.")
        
        # --- NUEVO: Limpieza de Prefijos Comunes del Texto Mejorado ---
        preambles_to_strip = [
            "Texto mejorado:\n---\n",
            "Texto mejorado:\n",
            "Aquí está el texto mejorado:\n---\n",
            "Aquí está el texto mejorado:\n",
            "Enhanced text:\n---\n", # Por si acaso la IA responde en inglés el prefijo
            "Enhanced text:\n"
            # Puedes añadir más prefijos comunes si los observas
        ]
        for preamble in preambles_to_strip:
            if enhanced_text_part.startswith(preamble):
                enhanced_text_part = enhanced_text_part[len(preamble):].strip()
                print(f"[AI Text Enhancer] Prefijo '{preamble.strip()}' eliminado del texto mejorado.")
                break # Eliminar solo el primer prefijo que coincida
        # --- FIN LIMPIEZA DE PREFIJOS ---

        print(f"[AI Text Enhancer] Texto final para TTS (primeros 50): '{enhanced_text_part[:50]}...'")
        if keywords_list:
            print(f"[AI Text Enhancer] Keywords extraídas: {keywords_list}")
        
        return enhanced_text_part, keywords_list

    except Exception as e:
        print(f"[ERROR] Error al llamar a la API de OpenAI: {e}")
        import traceback; traceback.print_exc()
        return text_to_process, None

# (El bloque if __name__ == "__main__": permanece igual para probar)
if __name__ == "__main__":
    if not OPENAI_API_KEY or OPENAI_API_KEY == "sk-TU_CLAVE_API_SECRETA_DE_OPENAI_AQUI":
        print("Configura tu OPENAI_API_KEY en app/core/config.py para probar este script.")
    else:
        sample_text_1 = "Este es un texto con algunos herrores ortograficos y talves mala redaccion para probar la extraccion de palabras clave como herrores y ortografia."
        print(f"\nTexto original 1: {sample_text_1}")
        enhanced_text, keywords = enhance_text_and_extract_keywords(sample_text_1)
        print(f"Texto mejorado 1: {enhanced_text}")
        print(f"Keywords para texto 1: {keywords}")

        sample_text_2 = "A very interesting topic about space exploration and new planets discovered by telescopes."
        print(f"\nTexto original 2 (inglés): {sample_text_2}")
        enhanced_text_es, keywords_es = enhance_text_and_extract_keywords(sample_text_2, target_language="español")
        print(f"Texto mejorado 2 (español): {enhanced_text_es}")
        print(f"Keywords para texto 2: {keywords_es}")