import io
import json
import base64
import urllib.request
import urllib.error
import re
from reportlab.lib.pagesizes import A5
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader


def handler(request):
    if request.method == "OPTIONS":
        return Response("", 200, {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
        })

    if request.method != "POST":
        return Response("Method not allowed", 405)

    try:
        body = json.loads(request.body)
    except Exception:
        return Response(json.dumps({"error": "Invalid JSON"}), 400,
                        {"Content-Type": "application/json"})

    name      = body.get("name", "Unknown")
    pid       = body.get("id", "")
    tags      = body.get("tags", [])
    photo_url = body.get("photo_url", "")

    photo_bytes = fetch_photo(photo_url)
    pdf_bytes   = draw_terminal_card(name, pid, tags, photo_bytes)
    filename    = f"terminal2k26_{pid}.pdf"

    return Response(pdf_bytes, 200, {
        "Content-Type": "application/pdf",
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Access-Control-Allow-Origin": "*",
    })


def fetch_photo(url):
    if not url:
        return None
    url = normalise_drive_url(url)
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        })
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.read()
    except Exception:
        return None


def normalise_drive_url(url):
    m = re.search(r"/d/([a-zA-Z0-9_-]+)", url)
    if m:
        fid = m.group(1)
        return f"https://drive.google.com/uc?export=download&id={fid}&confirm=t"
    return url


def draw_terminal_card(name, pid, tags, photo_bytes=None):
    buf = io.BytesIO()
    W, H = A5
    c = canvas.Canvas(buf, pagesize=A5)

    c.setFillColor(colors.HexColor("#020d04"))
    c.rect(0, 0, W, H, fill=1, stroke=0)

    c.setStrokeColor(colors.HexColor("#00ff41"))
    c.setStrokeAlpha(0.03)
    for y in range(0, int(H), 4):
        c.line(0, y, W, y)
    c.setStrokeAlpha(1)

    c.setStrokeColor(colors.HexColor("#0a3d12"))
    c.setLineWidth(0.8)
    c.rect(10, 10, W-20, H-20, fill=0, stroke=1)

    b, m = 16, 16
    c.setStrokeColor(colors.HexColor("#00ff41"))
    c.setLineWidth(1.5)
    for x1,y1,x2,y2,x3,y3 in [
        (m,H-m, m+b,H-m, m,H-m-b),
        (W-m,H-m, W-m-b,H-m, W-m,H-m-b),
        (m,m, m+b,m, m,m+b),
        (W-m,m, W-m-b,m, W-m,m+b),
    ]:
        c.line(x1,y1,x2,y2); c.line(x1,y1,x3,y3)

    c.setFillColor(colors.HexColor("#3a7a42"))
    c.setFont("Courier", 6)
    c.drawRightString(W-18, H-18, "TERMINAL 2K26")

    photo_size = 68*mm
    photo_x = (W - photo_size) / 2
    photo_y = H - 30*mm - photo_size

    c.setStrokeColor(colors.HexColor("#0a3d12"))
    c.setLineWidth(0.8)
    c.rect(photo_x-1, photo_y-1, photo_size+2, photo_size+2, fill=0, stroke=1)

    photo_drawn = False
    if photo_bytes:
        try:
            ir = ImageReader(io.BytesIO(photo_bytes))
            c.drawImage(ir, photo_x, photo_y, photo_size, photo_size,
                       preserveAspectRatio=True, anchor="c", mask="auto")
            photo_drawn = True
        except Exception:
            pass

    if not photo_drawn:
        ini = "".join(w[0] for w in name.split() if w).upper()[:2]
        c.setFillColor(colors.HexColor("#071a0a"))
        c.rect(photo_x, photo_y, photo_size, photo_size, fill=1, stroke=0)
        c.setFillColor(colors.HexColor("#00ff41"))
        c.setFont("Courier-Bold", 40)
        c.drawCentredString(photo_x+photo_size/2, photo_y+photo_size/2-14, ini)

    c.setFillColor(colors.HexColor("#000000"))
    c.setFillAlpha(0.05)
    for y in range(int(photo_y), int(photo_y+photo_size), 4):
        c.rect(photo_x, y, photo_size, 1.5, fill=1, stroke=0)
    c.setFillAlpha(1)

    name_y = photo_y - 12*mm
    c.setFillColor(colors.HexColor("#00ff41"))
    fs = 26
    c.setFont("Courier-Bold", fs)
    while c.stringWidth(name, "Courier-Bold", fs) > W-32 and fs > 13:
        fs -= 1
    c.setFont("Courier-Bold", fs)
    c.drawCentredString(W/2, name_y, name)

    c.setFillColor(colors.HexColor("#3a7a42"))
    c.setFont("Courier", 8)
    c.drawCentredString(W/2, name_y-7*mm, f"[ {pid} ]")

    div_y = name_y - 12*mm
    c.setStrokeColor(colors.HexColor("#0a3d12"))
    c.setLineWidth(0.5)
    c.line(22, div_y, W-22, div_y)

    tag_x, tag_y = 20, div_y-5*mm
    tag_h, pad_x, gap = 6*mm, 3.5*mm, 2.5*mm

    c.setFont("Courier", 7.5)
    for tag in tags:
        tw = c.stringWidth(tag, "Courier", 7.5) + pad_x*2
        if tag_x + tw > W-20:
            tag_x = 20
            tag_y -= tag_h + 2*mm
            if tag_y < 20: break
        c.setStrokeColor(colors.HexColor("#0a3d12"))
        c.setFillColor(colors.HexColor("#020d04"))
        c.setLineWidth(0.5)
        c.rect(tag_x, tag_y-tag_h+2*mm, tw, tag_h, fill=1, stroke=1)
        c.setFillColor(colors.HexColor("#3a7a42"))
        c.drawString(tag_x+pad_x, tag_y-tag_h+4*mm, tag)
        tag_x += tw + gap

    c.save()
    buf.seek(0)
    return buf.read()


class Response:
    def __init__(self, body, status=200, headers=None):
        self.body    = body
        self.status  = status
        self.headers = headers or {}
