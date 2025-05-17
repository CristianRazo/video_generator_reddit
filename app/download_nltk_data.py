import nltk
import os

def check_punkt_resource():
    print(f"[INFO] Rutas de búsqueda de NLTK activas: {nltk.data.path}")
    resource_name = 'tokenizers/punkt'
    resource_short_name = 'punkt'
    try:
        print(f"[INFO] Verificando si el recurso '{resource_short_name}' está disponible...")
        nltk.data.find(resource_name)
        print(f"[INFO] NLTK '{resource_short_name}' tokenizer ¡YA ESTÁ DISPONIBLE Y ENCONTRADO!")
    except LookupError:
        print(f"[ERROR] NLTK '{resource_short_name}' tokenizer NO ENCONTRADO. Esto no debería suceder si el Dockerfile lo descargó correctamente.")
    except Exception as e_general:
        print(f"[ERROR] Un error general ocurrió: {e_general}")

if __name__ == "__main__":
    check_punkt_resource()