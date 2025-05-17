# video_generator_reddit/app/services/ai_text_enhancer_service.py
from openai import OpenAI # Nueva forma de importar
from typing import Optional

# Intentar importar la clave API desde config. Es mejor si el cliente la toma de variables de entorno
# o se le pasa explícitamente al instanciarlo.
try:
    from app.core.config import OPENAI_API_KEY
except ImportError:
    OPENAI_API_KEY = None
    print("[WARN] OPENAI_API_KEY no encontrada en app.core.config. El servicio podría no funcionar.")

# Se recomienda instanciar el cliente una vez si es posible (ej. a nivel de módulo o app),
# o pasar la clave directamente al crear la instancia.
# Para un servicio simple, instanciarlo por llamada también funciona pero puede ser menos eficiente.
# El cliente buscará la variable de entorno OPENAI_API_KEY por defecto si no se le pasa la clave.
# Por eso, configurar la variable de entorno en docker-compose.yml sería lo ideal.

def enhance_text_for_tts(
    text_to_enhance: str, 
    target_language: str = "español",
    model_name: str = "gpt-4o-mini" # Usamos el modelo que decidiste
) -> Optional[str]:
    """
    Usa la API de OpenAI para corregir, mejorar y opcionalmente traducir texto para TTS.
    """
    if not OPENAI_API_KEY:
        print("[ERROR] La clave API de OpenAI no está configurada. No se puede mejorar el texto.")
        return text_to_enhance # Devolver el texto original si no hay clave

    try:
        client = OpenAI(api_key=OPENAI_API_KEY) # Instanciamos el cliente con la clave

        # Prompt detallado para guiar al modelo
        # Puedes experimentar y refinar mucho este prompt
        system_prompt = (
            "Eres un asistente experto en edición y pulido de textos para ser narrados por una voz TTS. "
            "Tu objetivo es que el texto final sea gramaticalmente perfecto, claro, conciso y que fluya de manera natural."
        )
        user_prompt = (
            f"Revisa y mejora el siguiente texto para una narración TTS en '{target_language}'. "
            f"Corrige todos los errores de gramática, ortografía y puntuación. "
            f"Asegura una excelente fluidez y naturalidad. "
            f"Si el texto original parece estar predominantemente en un idioma diferente al '{target_language}' y es un fragmento corto, "
            f"tradúcelo al '{target_language}' manteniendo el significado esencial. "
            f"Si son nombres propios, marcas o citas directas en otro idioma que deben conservarse, mantenlos. "
            f"Por favor, devuelve únicamente el texto final mejorado, sin ningún comentario, saludo o explicación adicional. Solo el texto puro y listo para TTS.\n\n"
            f"Texto original:\n---\n{text_to_enhance}\n---"
        )

        print(f"[AI Text Enhancer] Enviando texto (primeros 50 chars): '{text_to_enhance[:50]}...' al modelo {model_name}")

        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3, # Más bajo para respuestas más factuales y menos "creativas"
            # max_tokens: OpenAI recomienda no especificarlo para chat completions y dejar que el modelo decida,
            # o calcularlo con cuidado si es necesario. Para correcciones, suele ser similar a la longitud de entrada.
        )

        enhanced_text = response.choices[0].message.content.strip()
        print(f"[AI Text Enhancer] Texto mejorado (primeros 50 chars): '{enhanced_text[:50]}...'")
        return enhanced_text

    except Exception as e:
        print(f"[ERROR] Error al llamar a la API de OpenAI para mejorar texto: {e}")
        # En caso de error, podríamos devolver el texto original para no interrumpir el flujo
        return text_to_enhance 

# Ejemplo de uso para prueba directa (cuando configures todo y reconstruyas)
if __name__ == "__main__":
    if not OPENAI_API_KEY or OPENAI_API_KEY == "sk-TU_CLAVE_API_SECRETA_DE_OPENAI_AQUI":
        print("Por favor, configura tu OPENAI_API_KEY en app/core/config.py para probar este script.")
    else:
        sample_text_1 = "Este es un texto con algunos herrores ortograficos y talves mala redaccion para probar."
        print(f"\nTexto original 1: {sample_text_1}")
        enhanced_1 = enhance_text_for_tts(sample_text_1)
        print(f"Texto mejorado 1: {enhanced_1}")

        sample_text_2 = "This is a short english text. We want it in spanish."
        print(f"\nTexto original 2: {sample_text_2}")
        enhanced_2 = enhance_text_for_tts(sample_text_2, target_language="español")
        print(f"Texto mejorado 2 (esperado en español): {enhanced_2}")

        sample_text_3 = "Reddit user u/example_user said: 'LOL, that's hilarious!' How do you react?"
        print(f"\nTexto original 3: {sample_text_3}")
        enhanced_3 = enhance_text_for_tts(sample_text_3, target_language="español")
        print(f"Texto mejorado 3 (esperado en español, conservando u/example_user y 'LOL...'): {enhanced_3}")