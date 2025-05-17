# app/services/tts_service.py
from typing import Optional
from google.cloud import texttospeech
import os # Para manejar rutas de archivos
from mutagen.mp3 import MP3
#from app.core.config import GOOGLE_APPLICATION_CREDENTIALS_PATH # Necesitaremos definir esta variable en config.py si no usamos la variable de entorno global

# Es recomendable que la librería cliente de Google use la variable de entorno
# GOOGLE_APPLICATION_CREDENTIALS automáticamente si está configurada.
# Si no, puedes especificar explícitamente el archivo de credenciales al crear el cliente,
# pero usar la variable de entorno es más limpio.

# Asegurémonos de que la variable de entorno esté configurada o que el cliente la encuentre.
# Si configuraste GOOGLE_APPLICATION_CREDENTIALS en docker-compose.yml,
# la librería debería encontrarlo automáticamente.

def synthesize_text_to_audio_file(
    text_to_speak: str, 
    output_filename: str, # Solo el nombre del archivo, ej. segment_001.mp3
    base_output_dir: str = "outputs/audio", # Directorio base donde se creará la subcarpeta del proyecto
    project_id: str = "default_project", # Para crear una subcarpeta
    type_subfolder: Optional[str] = None,
    voice_name: str = "es-US-Wavenet-A"
) -> Optional[str]:
    try:
        client = texttospeech.TextToSpeechClient()
        input_text = texttospeech.SynthesisInput(text=text_to_speak)
        voice = texttospeech.VoiceSelectionParams(
            language_code=voice_name.split('-')[0] + "-" + voice_name.split('-')[1],
            name=voice_name,
        )
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        )
        response = client.synthesize_speech(
            request={"input": input_text, "voice": voice, "audio_config": audio_config}
        )

        # Construir la ruta de salida
        path_parts = [base_output_dir, project_id]
        if type_subfolder: # Si se proporciona una subcarpeta de tipo, la añadimos
            path_parts.append(type_subfolder)

        current_output_dir = os.path.join(*path_parts) # Une todas las partes de la ruta
        os.makedirs(current_output_dir, exist_ok=True) # Crea el directorio final si no existe

        output_filepath = os.path.join(current_output_dir, output_filename)

        with open(output_filepath, "wb") as out_file:
            out_file.write(response.audio_content)
        return output_filepath
    except Exception as e:
        print(f"Error al sintetizar texto con Google Cloud TTS: {e}")
        import traceback
        print(traceback.format_exc())
        return None

def get_audio_duration_ms(audio_filepath: str) -> Optional[int]:
    """
    Obtiene la duración de un archivo de audio MP3 en milisegundos.
    Retorna None si hay un error o el archivo no es MP3 válido.
    """
    try:
        audio = MP3(audio_filepath)
        duration_seconds = audio.info.length
        duration_milliseconds = int(duration_seconds * 1000)
        return duration_milliseconds
    except Exception as e:
        print(f"Error al obtener la duración del audio de '{audio_filepath}': {e}")
        return None
    
if __name__ == "__main__":
    print("Probando síntesis de voz y obtención de duración...")
    
    sample_text_es = "Esta es una frase de prueba corta."
    output_file_es = "test_duration_es.mp3"
    
    # Generar el audio
    generated_audio_path = synthesize_text_to_audio_file(
        sample_text_es, 
        output_file_es, 
        voice_name="es-US-Wavenet-A"
    )
    
    if generated_audio_path:
        print(f"Audio de prueba guardado en: {generated_audio_path}")
        
        # Obtener y mostrar la duración
        duration_ms = get_audio_duration_ms(generated_audio_path)
        if duration_ms is not None:
            print(f"Duración del audio: {duration_ms} ms ({duration_ms / 1000:.2f} segundos)")
        else:
            print("No se pudo obtener la duración del audio.")
    else:
        print("Falló la generación del audio de prueba.")