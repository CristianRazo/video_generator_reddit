# app/services/scraping_service.py
import praw
from app.core.config import REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT
from typing import Optional, List, Dict, Any # Asegúrate de tener estas importaciones

def get_reddit_instance():
    reddit = praw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        user_agent=REDDIT_USER_AGENT,
        # read_only=True # Puedes descomentar si solo lees contenido público
    )
    # print(f"PRAW instance is read-only: {reddit.read_only}")
    return reddit

def get_post_data_from_url(
    reddit_url: str, 
    num_top_comments: int = 5,
    max_replies_per_comment: int = 2, # NUEVO: Máximo de respuestas a añadir por comentario
    min_reply_score: int = 500          # NUEVO: Puntaje mínimo para que una respuesta sea "relevante"
) -> Optional[Dict[str, Any]]:       # Añadido el tipo de retorno
    """
    Obtiene datos de un post de Reddit (título, selftext, y N top comments) usando su URL.
    Para cada comentario principal, intenta añadir el texto de hasta 'max_replies_per_comment'
    respuestas "relevantes" a su cuerpo.
    """
    reddit = get_reddit_instance()
    print(f"[SCRAPING SERVICE] Obteniendo datos para URL: {reddit_url}")
    try:
        submission = reddit.submission(url=reddit_url)
        # Es buena práctica acceder a un atributo para "cargar" el submission si no se ha hecho
        _ = submission.title # Acceder a un atributo para asegurar que se cargue
        
        title = submission.title
        selftext = submission.selftext if submission.selftext else "" 
        post_id = submission.id
        score = submission.score
        num_total_comments_on_post = submission.num_comments # Nombre de variable que ya usabas
        permalink = submission.permalink
        created_utc = submission.created_utc
        # Obtener el nombre del autor del post para identificar respuestas del OP
        post_author_name = str(submission.author.name) if submission.author else None
        
        print(f"  Título: {title}")
        print(f"  Autor del Post: u/{post_author_name if post_author_name else '[desconocido]'}")


        top_comments_data = []
        submission.comment_sort = "top" # Asegurar que los comentarios estén ordenados por 'top'
        
        # Reemplazar los placeholders "more comments" para los comentarios de nivel superior
        print(f"  Expandiendo comentarios de nivel superior (submission.comments.replace_more(limit=0))...")
        submission.comments.replace_more(limit=0) # Intentar cargar todos

        loaded_comments = submission.comments.list()
        print(f"  Total de items en loaded_comments (después de replace_more): {len(loaded_comments)}")
        
        comment_count = 0
        for top_level_comment in loaded_comments:
            if comment_count >= num_top_comments:
                print(f"  Alcanzado el límite de {num_top_comments} comentarios principales.")
                break
            
            if isinstance(top_level_comment, praw.models.MoreComments):
                print("    Encontrado objeto MoreComments, omitiendo.")
                continue
            if not top_level_comment.author:
                print(f"    Comentario sin autor (ID: {top_level_comment.id}), omitiendo.")
                continue
            
            comment_author_name = str(top_level_comment.author.name)
            comment_body_original = top_level_comment.body # Guardamos el cuerpo original
            
            # Inicializar la variable que contendrá el cuerpo + respuestas
            final_comment_body = comment_body_original

             # --- NUEVO: Lógica para obtener y añadir respuestas relevantes (REVISADA) ---
            if max_replies_per_comment > 0:
                print(f"    Procesando comentario de u/{comment_author_name} (Score: {top_level_comment.score}). Buscando respuestas...")
                
                potential_replies = []
                try:
                    # Cargar "more replies" para este comentario específico.
                    # limit=0 para intentar obtener todas las respuestas de primer nivel.
                    top_level_comment.replies.replace_more(limit=0) 
                except Exception as e_replies_more:
                    print(f"      [WARN] Error al intentar expandir 'more replies' para el comentario {top_level_comment.id}: {e_replies_more}")

                for reply in top_level_comment.replies.list(): # Iterar sobre las respuestas de primer nivel
                    if isinstance(reply, praw.models.MoreComments) or not reply.author:
                        continue
                    potential_replies.append(reply) # Añadir todas las respuestas válidas a una lista temporal
                
                if potential_replies:
                    # Ordenar las respuestas potenciales por score (de mayor a menor)
                    # Si dos tienen el mismo score, se mantiene el orden original (usualmente cronológico inverso o "top")
                    sorted_replies = sorted(potential_replies, key=lambda r: r.score, reverse=True)
                    print(f"      Encontradas y ordenadas {len(sorted_replies)} respuestas potenciales.")

                    relevant_replies_texts_list = []
                    replies_added_for_this_comment = 0
                    
                    for reply in sorted_replies: # Iterar sobre las respuestas YA ORDENADAS POR SCORE
                        if replies_added_for_this_comment >= max_replies_per_comment:
                            break # Ya tenemos suficientes respuestas relevantes

                        reply_author_name_str = str(reply.author.name) # Ya filtramos not reply.author
                        is_reply_op = reply_author_name_str == post_author_name if post_author_name else False
                        
                        # Criterio de relevancia: es del OP del POST O tiene suficiente score
                        if is_reply_op or reply.score >= min_reply_score:
                            relevant_replies_texts_list.append(reply.body)
                            replies_added_for_this_comment += 1
                            print(f"        -> Respuesta relevante de u/{reply_author_name_str} (Score: {reply.score}, OP del Post: {is_reply_op}) añadida.")
                    
                    if relevant_replies_texts_list:
                        final_comment_body += "".join(relevant_replies_texts_list)
                else:
                    print(f"      No se encontraron respuestas válidas para el comentario de u/{comment_author_name}.")
            # --- FIN Lógica para obtener y añadir respuestas (REVISADA) ---
            
            top_comments_data.append({
                "id": top_level_comment.id,
                "author": comment_author_name,
                "body": final_comment_body, # Cuerpo del comentario con respuestas relevantes añadidas
                "score": top_level_comment.score,
                "created_utc": top_level_comment.created_utc,
                "is_op_of_post": comment_author_name == post_author_name if post_author_name else False # Si este comentarista es el OP del post
            })
            comment_count += 1
            
        print(f"  Total comentarios principales procesados y añadidos a la lista: {len(top_comments_data)}")

        return {
            "id": post_id,
            "title": title,
            "selftext": selftext,
            "score": score,
            "num_total_comments_on_post": num_total_comments_on_post, # Usar el nombre de la variable PRAW
            "permalink": permalink,
            "created_utc": created_utc,
            "author": post_author_name, # Autor del post
            "top_comments": top_comments_data 
        }

    except Exception as e:
        print(f"[SCRAPING SERVICE] Error al obtener datos del post de Reddit con PRAW: {e}")
        import traceback
        print(traceback.format_exc())
        return None

# Actualiza el bloque if __name__ == "__main__": para probar esto
if __name__ == "__main__":
    # Elige una URL de un post que sepas que tiene comentarios con respuestas interesantes
    # test_url = "https://www.reddit.com/r/AskReddit/comments/1klu2i6/what_non_sex_profession_has_the_freakiest/" # Este es bueno para muchos comentarios
    test_url = "https://www.reddit.com/r/AskReddit/comments/1koz7pi/whats_a_dead_feature_of_the_internet_you_still/" # Un post reciente de TIFU que podría tener respuestas
    # test_url = "https://www.reddit.com/r/MadeMeSmile/comments/1d3xxfx/after_3_years_of_hard_work_dedication_my_first/"

    print(f"Intentando obtener datos para: {test_url}")
    # Pedimos 2 comentarios principales, y para cada uno, hasta 1 respuesta relevante con score > 1
    post_data = get_post_data_from_url(
        reddit_url=test_url, 
        num_top_comments=3, # Obtener 3 comentarios principales
        max_replies_per_comment=2, # Para cada uno, hasta 2 respuestas
        min_reply_score=500 # Con puntaje mínimo de 2 (o si es del OP del post)
    )
    
    if post_data:
        print("\n\n--- RESULTADO FINAL DEL POST ---")
        print(f"Título: {post_data.get('title')}")
        print(f"Autor del Post: u/{post_data.get('author')}")
        # print(f"Selftext: {post_data.get('selftext')}") # Descomenta para ver el selftext completo

        print(f"\n--- COMENTARIOS PROCESADOS ({len(post_data.get('top_comments', []))}) ---")
        for i, comment in enumerate(post_data.get('top_comments', [])):
            print(f"\nComentario Principal #{i+1}:")
            print(f"  Autor: u/{comment.get('author')}")
            print(f"  Score: {comment.get('score')}")
            print(f"  ¿Es OP del Post?: {comment.get('is_op_of_post')}")
            print(f"  Cuerpo (con respuestas integradas):\n------------------------------------\n{comment.get('body')}\n------------------------------------")
    else:
        print("No se pudieron obtener los datos del post.")