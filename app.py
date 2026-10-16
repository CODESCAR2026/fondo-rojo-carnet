from fastapi import FastAPI, UploadFile, File
from fastapi.responses import Response, JSONResponse
from rembg import remove, new_session
from PIL import Image
import io, gc

app = FastAPI()
COLOR_FONDO = (200, 16, 30)
SESSION = new_session("u2netp")

def procesar_seguro(image_bytes: bytes):
    img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    if max(img.size) > 1024:
        w, h = img.size
        ratio = 1024 / max(w, h)
        img = img.resize((int(w*ratio), int(h*ratio)), Image.LANCZOS)
    sin_fondo = remove(img, session=SESSION)
    fondo = Image.new("RGBA", sin_fondo.size, COLOR_FONDO + (255,))
    fondo.paste(sin_fondo, (0,0), sin_fondo)
    final = fondo.convert("RGB")
    lado = min(final.size)
    left = (final.width - lado)//2
    top = (final.height - lado)//2
    final = final.crop((left, top, left+lado, top+lado))
    final = final.resize((472, 472), Image.LANCZOS)
    buf = io.BytesIO()
    final.save(buf, format="JPEG", quality=90)
    del img, sin_fondo, fondo, final
    gc.collect()
    return buf.getvalue()

@app.get("/")
def home():
    return {"status": "OK"}

@app.post("/procesar")
async def procesar(file: UploadFile = File(...)):
    try:
        data = await file.read()
        resultado = procesar_seguro(data)
        return Response(content=resultado, media_type="image/jpeg")
    except Exception as e:
        gc.collect()
        return JSONResponse(status_code=500, content={"error": str(e)})
