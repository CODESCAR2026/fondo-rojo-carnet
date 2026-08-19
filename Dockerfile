FROM python:3.10-slim

RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

# Descargar el modelo de IA (u2netp) DURANTE la compilación, no al arrancar,
# para que el servicio inicie rápido y no dependa de la red en cada arranque.
RUN python -c "from rembg import new_session; new_session('u2netp')"

# Render inyecta la variable de entorno PORT y espera que el servicio escuche ahí
EXPOSE 8080
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-8080}"]
