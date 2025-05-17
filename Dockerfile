FROM python:3.9-slim 

WORKDIR /usr/src/app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Instalar dependencias de Python (incluyendo nltk)
COPY ./requirements.txt /usr/src/app/requirements.txt
COPY ./app/assets /usr/src/app/assets

RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# ---- Forzar reinstalación de MoviePy para asegurar que esté completo ----
    RUN echo "Attempting to uninstall moviepy if it exists..." && \
    pip uninstall -y moviepy || true && \
    echo "Installing moviepy with verbose output..." && \
    pip install --no-cache-dir moviepy --verbose
# --------------------------------------------------------------------

# ---- Instalar FFmpeg ----
# Actualizar la lista de paquetes e instalar ffmpeg y sus dependencias.
# El '&& rm -rf /var/lib/apt/lists/*' es para limpiar y mantener la imagen pequeña.
RUN apt-get update && \
    apt-get install -y ffmpeg libsm6 libxext6 && \
    rm -rf /var/lib/apt/lists/*
# -------------------------

# ---- Instalar Fuentes ----
    RUN apt-get update && \
    apt-get install -y fonts-dejavu-core && \
    fc-cache -fv && \ 
    rm -rf /var/lib/apt/lists/*
# -------------------------

# Descargar el recurso 'punkt' de NLTK
RUN python -c "import nltk; print('[INFO] Downloading punkt...'); nltk.download('punkt', download_dir='/usr/local/share/nltk_data', raise_on_error=True); print('[INFO] punkt downloaded.')"

# ---- INTENTAR DESCARGAR 'punkt_tab' ----
# Este comando fallará el build si 'punkt_tab' no es un ID de recurso conocido por NLTK.
RUN python -c "import nltk; print('[INFO] Attempting to download punkt_tab...'); nltk.download('punkt_tab', download_dir='/usr/local/share/nltk_data', raise_on_error=True); print('[INFO] punkt_tab download attempt finished.')"
# -----------------------------------------

# Asegurar permisos de lectura para todos en el directorio de datos de NLTK principal
RUN chmod -R a+r /usr/local/share/nltk_data || true # || true para que no falle si el dir no existe por alguna razón antes del download de punkt


# Crear el usuario y grupo
RUN groupadd -g 1000 appgroup && \
    useradd -u 1000 -g appgroup -s /sbin/nologin -d /usr/src/app appuser

# Copiar el código de la aplicación y darle permisos a appuser
COPY --chown=appuser:appgroup ./app /usr/src/app/app

# Cambiar al usuario no privilegiado
USER appuser

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]