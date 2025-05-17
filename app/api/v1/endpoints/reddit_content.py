from fastapi import APIRouter, HTTPException, Query, Body # Body puede ser útil si envías JSON
from app.services import scraping_service # Importamos nuestro módulo de servicio
from typing import Any, Optional # Para tipos

# Podríamos definir modelos Pydantic para request y response para mayor claridad y validación
# from pydantic import BaseModel, HttpUrl
# class RedditPostRequest(BaseModel):
#     reddit_url: HttpUrl
#     num_comments: Optional[int] = 5

# class Comment(BaseModel):
#     id: str
#     author: str
#     body: str
#     score: int
#     created_utc: float

# class RedditPostResponse(BaseModel):
#     id: str
#     title: str
#     selftext: Optional[str]
#     score: int
#     num_total_comments: int
#     permalink: str
#     created_utc: float
#     top_comments: list[Comment]

router = APIRouter()

@router.post(
    "/fetch-reddit-post/", 
    # response_model=RedditPostResponse # Usar el modelo Pydantic para la respuesta sería ideal
    response_model=Any # Por ahora, usamos Any para simplicidad, podemos refinar después
)
async def fetch_reddit_post_data(
    # Si prefieres enviar los datos en el cuerpo del POST como JSON:
    # request_data: RedditPostRequest
    # Y luego accederías a: request_data.reddit_url, request_data.num_comments

    # O como parámetros de query, que es más simple para este caso si lo llamas desde el navegador/docs:
    reddit_url: str = Query(
        ..., # El "..." indica que es un parámetro requerido
        description="La URL completa del post de Reddit a procesar.", 
        example="https://www.reddit.com/r/tifu/comments/1cfydr3/tifu_by_pranking_my_husband_and_accidentally/"
    ),
    num_comments: Optional[int] = Query(
        5, # Valor por defecto si no se proporciona
        description="El número de comentarios principales a extraer.",
        ge=0 # ge=0 significa "greater than or equal to 0" (mayor o igual a 0)
    )
):
    """
    Obtiene los datos principales de un post de Reddit (título, selftext, N comentarios)
    utilizando PRAW a través de su URL.
    """
    if not reddit_url: # FastAPI y Pydantic usualmente manejan esto si es un campo requerido.
        raise HTTPException(status_code=400, detail="La URL de Reddit no puede estar vacía.")
    
    # Aquí podrías añadir validación más robusta para la URL si Pydantic HttpUrl no se usa.

    try:
        # Llamamos a nuestro servicio, pasando ambos parámetros
        post_data = scraping_service.get_post_data_from_url(
            reddit_url=reddit_url, 
            num_top_comments=num_comments
        )
    except Exception as e:
        # Si el servicio mismo no maneja la excepción y la relanza, la capturamos aquí.
        # O si hay un error antes de llamar al servicio.
        print(f"Error en el endpoint al procesar {reddit_url}: {e}")
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error interno del servidor al procesar la URL de Reddit.")


    if not post_data:
        raise HTTPException(status_code=404, detail=f"No se pudieron obtener datos para la URL: {reddit_url}. Verifica la URL o los logs del servidor.")
    
    return post_data