# app/services/scraping_service.py
import praw
from app.core.config import REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT

# (la función get_reddit_instance() permanece igual)
def get_reddit_instance():
    reddit = praw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        user_agent=REDDIT_USER_AGENT,
        # read_only=True
    )
    # print(f"PRAW instance is read-only: {reddit.read_only}") # Descomentar para depurar
    return reddit

def get_post_data_from_url(reddit_url: str, num_top_comments: int = 5): # Añadimos num_top_comments
    """
    Obtiene datos de un post de Reddit (título, selftext, y N top comments) usando su URL.
    """
    reddit = get_reddit_instance()
    try:
        submission = reddit.submission(url=reddit_url)
        
        title = submission.title
        selftext = submission.selftext 
        post_id = submission.id
        score = submission.score
        num_total_comments = submission.num_comments # Renombrado para claridad
        permalink = submission.permalink
        created_utc = submission.created_utc

        # --- Extracción de Comentarios ---
        top_comments_data = []
        # submission.comment_sort = "top" # Opcional: asegurar que los comentarios están ordenados por 'top'
                                        # PRAW suele devolverlos así por defecto para .comments
        
        # Reemplazar los placeholders "more comments". 
        # limit=0 intenta cargar todos los comentarios de nivel superior.
        # Para un número limitado de reemplazos de "more", usa un entero. 
        # Si solo quieres N comentarios y hay muchos, esto podría ser costoso.
        # Una estrategia es primero obtener una lista y luego ordenarla si es necesario,
        # o usar replace_more con un límite más conservador.
        submission.comments.replace_more(limit=0) 

        # Iterar sobre los comentarios de nivel superior cargados
        # y tomar los 'num_top_comments' primeros.
        # Filtraremos por si algún comentario fue eliminado y no tiene autor.
        loaded_comments = submission.comments.list()
        
        comment_count = 0
        for comment in loaded_comments:
            if comment_count >= num_top_comments:
                break
            # Asegurarnos de que el comentario no sea un objeto MoreComments residual y tenga autor
            if isinstance(comment, praw.models.MoreComments) or not comment.author:
                continue
            
            top_comments_data.append({
                "id": comment.id,
                "author": str(comment.author.name) if comment.author else "[eliminado]",
                "body": comment.body,
                "score": comment.score,
                "created_utc": comment.created_utc
            })
            comment_count += 1
        # --- Fin Extracción de Comentarios ---

        return {
            "id": post_id,
            "title": title,
            "selftext": selftext,
            "score": score,
            "num_total_comments": num_total_comments, 
            "permalink": permalink,
            "created_utc": created_utc,
            "top_comments": top_comments_data 
        }

    except Exception as e:
        print(f"Error al obtener datos del post de Reddit con PRAW: {e}")
        import traceback
        print(traceback.format_exc()) # Para más detalle del error durante la depuración
        return None

# Ejemplo de uso (puedes probarlo si ejecutas este archivo directamente)
if __name__ == "__main__":
    # test_url = "https://www.reddit.com/r/AskReddit/comments/10c6f8q/what_is_a_piece_of_advice_that_seems_obvious_but/" # Muchos comentarios
    test_url = "https://www.reddit.com/r/AskReddit/comments/1klu2i6/what_non_sex_profession_has_the_freakiest/" 
    
    print(f"Intentando obtener datos para: {test_url}")
    post_data = get_post_data_from_url(test_url, num_top_comments=3) # Pedimos 3 comentarios
    if post_data:
        print("\n--- Datos del Post ---")
        for key, value in post_data.items():
            if key == "top_comments":
                print(f"Top_comments ({len(value)}):")
                for c_idx, comment_data in enumerate(value):
                    print(f"  Comment {c_idx + 1}:")
                    for c_key, c_value in comment_data.items():
                        if c_key == "body":
                            print(f"    {c_key.capitalize()}: {c_value[:100]}...") # Acortar cuerpo del comentario
                        else:
                            print(f"    {c_key.capitalize()}: {c_value}")
            elif key == "selftext":
                 print(f"Selftext (primeros 200 chars): {value[:200] if value else 'N/A'}")
            else:
                print(f"{key.capitalize()}: {value}")
    else:
        print("No se pudieron obtener los datos del post.")