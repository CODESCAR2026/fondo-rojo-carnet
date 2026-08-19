from fastapi import FastAPI, UploadFile, File
from fastapi.responses import Response, JSONResponse
from rembg import remove, new_session
from PIL import Image
import io

app = FastAPI()

# Color de fondo para el carnet (rojo sólido). Cambia estos valores si necesitas otro tono.
COLOR_FONDO = (200, 16, 30)  # rojo (R, G, B)

# Modelo liviano (~4-5 MB) para que funcione bien con poca memoria RAM (plan gratuito de Render).
# Si en el futuro alojas esto en un servidor con más memoria, puedes cambiar a "u2net_human_seg"
# (más pesado, pero más preciso recortando personas).
#
# OJO: la sesión se crea de forma DIFERIDA (solo cuando llega la primera foto), no al arrancar.
# Así el servicio abre el puerto de inmediato al iniciar (Render lo detecta rápido), y el costo
# de cargar el modelo en memoria se paga solo en la primera petición real, no en el arranque.
_session = None


def get_session():
    global _session
    if _session is None:
        _session = new_session("u2netp")
    return _session


@app.get("/")
def health():
    """Endpoint simple para verificar que el servicio está despierto."""
    return {"status": "ok"}


# Tamaño máximo (en px, del lado más largo) antes de procesar. Fotos de celular
# pueden pesar varios MB a resolución muy alta, lo que puede agotar los 512 MB
# de RAM del plan gratuito y hacer que el contenedor se caiga. Para una foto
# de carnet esta resolución es más que suficiente.
MAX_DIMENSION = 1200


@app.post("/remove-bg-red")
async def remove_bg_red(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        input_image = Image.open(io.BytesIO(contents)).convert("RGBA")

        # 0) Reducir tamaño si la foto es muy grande (ahorra memoria y tiempo)
        ancho, alto = input_image.size
        lado_mayor = max(ancho, alto)
        if lado_mayor > MAX_DIMENSION:
            ratio = MAX_DIMENSION / lado_mayor
            nuevo_tamano = (int(ancho * ratio), int(alto * ratio))
            input_image = input_image.resize(nuevo_tamano, Image.LANCZOS)

        # 1) Quitar el fondo original (rembg devuelve RGBA con canal alfa = transparencia)
        sin_fondo = remove(input_image, session=get_session())

        # 2) Crear lienzo rojo del mismo tamaño y pegar la persona encima usando el alfa como máscara
        fondo_rojo = Image.new("RGBA", sin_fondo.size, COLOR_FONDO + (255,))
        fondo_rojo.paste(sin_fondo, (0, 0), sin_fondo)

        # 3) Convertir a JPEG (sin canal alfa) para que el archivo pese menos
        final_image = fondo_rojo.convert("RGB")
        buf = io.BytesIO()
        final_image.save(buf, format="JPEG", quality=92)
        buf.seek(0)

        return Response(content=buf.getvalue(), media_type="image/jpeg")
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
