import io
import json
from pathlib import Path

import cv2
import numpy as np
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from PIL import Image, ImageFilter, ImageOps, UnidentifiedImageError

ROOT = Path(__file__).parent
app = FastAPI(title='White Room')
app.mount('/static', StaticFiles(directory=ROOT / 'static'), name='static')

@app.get('/')
def index():
    return FileResponse(ROOT / 'static/index.html')

def refine_alpha(mask, rgb, cleanup):
    """Remove isolated dust and use image edges to refine the selection boundary."""
    binary = np.where((mask == 1) | (mask == 3), 255, 0).astype('uint8')
    count, labels, stats, _ = cv2.connectedComponentsWithStats(binary)
    protected = set(np.unique(labels[mask == cv2.GC_FGD]))
    threshold = max(4, binary.size * 0.00008)
    for label in range(1, count):
        if stats[label, cv2.CC_STAT_AREA] < threshold and label not in protected:
            binary[labels == label] = 0
    # A conservative inward trim removes old background fringes. Zero keeps fine details.
    if cleanup:
        binary = cv2.erode(binary, np.ones((3, 3), np.uint8), iterations=cleanup)
    guide = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255
    source = binary.astype(np.float32) / 255
    mean = lambda v: cv2.boxFilter(v, -1, (5, 5), borderType=cv2.BORDER_REFLECT)
    mu_i, mu_p = mean(guide), mean(source)
    a = (mean(guide * source) - mu_i * mu_p) / (mean(guide * guide) - mu_i * mu_i + 0.001)
    b = mu_p - a * mu_i
    alpha = np.clip((mean(a) * guide + mean(b) - 0.05) / 0.90, 0, 1)
    # Manual brush instructions override automatic edge cleanup.
    alpha[mask == cv2.GC_FGD] = 1
    alpha[mask == cv2.GC_BGD] = 0
    return Image.fromarray(np.rint(alpha * 255).astype('uint8'))


def brighten_product(image, brightness):
    """Lift midtones with a gamma curve; leave black and white endpoints intact."""
    if brightness == 0:
        return image
    gamma = 1 / (1 + brightness / 100)
    lut = [round(255 * (v / 255) ** gamma) for v in range(256)]
    return image.point(lut * 3)


@app.post('/api/process')
async def process(file: UploadFile = File(...), selection: str = Form(...), strokes: str = Form('[]'), shadow: int = Form(28), brightness: int = Form(15, ge=0, le=50), cleanup: int = Form(1, ge=0, le=3)):
    data = await file.read(21 * 1024 * 1024)
    if len(data) > 20 * 1024 * 1024:
        raise HTTPException(413, '20MB 이하의 사진을 올려 주세요.')
    try:
        image = ImageOps.exif_transpose(Image.open(io.BytesIO(data)))
        if image.width * image.height > 40_000_000:
            raise ValueError('사진은 4천만 화소 이하로 올려 주세요.')
        image = image.convert('RGB')
        box = json.loads(selection)
        marks = json.loads(strokes)
        if not isinstance(marks, list) or len(marks) > 1000:
            raise ValueError('브러시 횟수가 너무 많습니다.')
        coords = [float(box[k]) for k in ('x', 'y', 'w', 'h')]
        if not all(np.isfinite(v) for v in coords):
            raise ValueError('올바른 제품 영역을 선택해 주세요.')
    except (UnidentifiedImageError, ValueError, KeyError, TypeError, Image.DecompressionBombError):
        raise HTTPException(400, '사진 또는 선택 영역을 확인해 주세요.')
    w, h = image.size
    scale = min(1, 1200 / max(w, h))
    sw, sh = round(w * scale), round(h * scale)
    rgb = np.array(image.resize((sw, sh), Image.Resampling.LANCZOS))
    x, y = max(0, min(sw - 2, round(coords[0] * sw))), max(0, min(sh - 2, round(coords[1] * sh)))
    rw, rh = min(sw - x - 1, round(coords[2] * sw)), min(sh - y - 1, round(coords[3] * sh))
    if rw < 5 or rh < 5:
        raise HTTPException(400, '제품을 감싸는 영역을 조금 더 크게 선택해 주세요.')
    mask = np.zeros((sh, sw), np.uint8)
    mask[y:y + rh, x:x + rw] = cv2.GC_PR_FGD
    try:
        for mark in marks:
            points = mark['points']
            radius = max(1, min(80, round(float(mark['size']) * sw / 2)))
            color = cv2.GC_FGD if mark['mode'] == 'keep' else cv2.GC_BGD
            pts = [(int(max(0,min(1,float(p[0]))) * (sw-1)), int(max(0,min(1,float(p[1]))) * (sh-1))) for p in points]
            for p in pts:
                cv2.circle(mask, p, radius, color, -1)
            for p, q in zip(pts, pts[1:]):
                cv2.line(mask, p, q, color, radius * 2)
        cv2.grabCut(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR), mask, None, np.zeros((1,65),np.float64), np.zeros((1,65),np.float64), 8, cv2.GC_INIT_WITH_MASK)
    except (cv2.error, KeyError, TypeError, ValueError, OverflowError):
        raise HTTPException(400, '제품 영역을 다시 선택해 주세요. 배경이 테두리에 포함되어야 합니다.')
    alpha = refine_alpha(mask, rgb, cleanup).resize((w,h), Image.Resampling.LANCZOS)
    if not alpha.getbbox():
        raise HTTPException(422, '제품을 찾지 못했습니다. 포함 브러시로 제품 안쪽을 표시해 주세요.')
    output = Image.new('RGBA', (w,h), 'white')
    strength = max(0,min(60,shadow))
    if strength:
        layer = Image.new('RGBA',(w,h),(0,0,0,0))
        shade = alpha.filter(ImageFilter.GaussianBlur(max(w,h)*0.012)).point(lambda a: round(a*strength/100))
        layer.paste((0,0,0), (0,0,w,h), shade)
        output.alpha_composite(layer, (0,round(h*0.008)))
    product = brighten_product(image, brightness).convert('RGBA')
    product.putalpha(alpha)
    output.alpha_composite(product)
    buf = io.BytesIO()
    output.convert('RGB').save(buf, format='PNG')
    return Response(buf.getvalue(), media_type='image/png', headers={'Content-Disposition':'attachment; filename="white-room.png"'})
