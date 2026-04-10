from http.server import BaseHTTPRequestHandler
import json
import base64
import urllib.request
import io

from reportlab.lib.pagesizes import A5
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


def draw_card(person_name, person_id, tags, photo_b64=None):
    buf = io.BytesIO()
    W, H = A5  # 148 x 210 mm
    c = canvas.Canvas(buf, pagesize=A5)

    # ── Background ──────────────────────────────────────────────
    c.setFillColor(colors.HexColor("#020d04"))
    c.rect(0, 0, W, H, fill=1, stroke=0)

    # ── Scanline texture (thin horizontal lines) ─────────────────
    c.setStrokeColor(colors.HexColor("#00ff41"))
    c.setStrokeAlpha(0.04)
    for y in range(0, int(H), 4):
        c.line(0, y, W, y)
    c.setStrokeAlpha(1)

    # ── Outer border ─────────────────────────────────────────────
    c.setStrokeColor(colors.HexColor("#0a3d12"))
    c.setLineWidth(1)
    c.rect(8, 8, W - 16, H - 16, fill=0, stroke=1)

    # ── Corner brackets ──────────────────────────────────────────
    green = colors.HexColor("#00ff41")
    c.setStrokeColor(green)
    c.setLineWidth(1.5)
    bracket = 14
    margin = 14
    # TL
    c.line(margin, H - margin, margin + bracket, H - margin)
    c.line(margin, H - margin, margin, H - margin - bracket)
    # TR
    c.line(W - margin, H - margin, W - margin - bracket, H - margin)
    c.line(W - margin, H - margin, W - margin, H - margin - bracket)
    # BL
    c.line(margin, margin, margin + bracket, margin)
    c.line(margin, margin, margin, margin + bracket)
    # BR
    c.line(W - margin, margin, W - margin - bracket, margin)
    c.line(W - margin, margin, W - margin, margin + bracket)

    # ── Branding ─────────────────────────────────────────────────
    c.setFillColor(colors.HexColor("#3a7a42"))
    c.setFont("Courier-Bold", 6)
    c.drawRightString(W - 18, H - 18, "TERMINAL 2K26")

    # ── Photo ─────────────────────────────────────────────────────
    photo_size = 72 * mm
    photo_x = (W - photo_size) / 2
    photo_y = H - 28 * mm - photo_size

    # Border around photo
    c.setStrokeColor(colors.HexColor("#0a3d12"))
    c.setLineWidth(1)
    c.rect(photo_x - 1, photo_y - 1, photo_size + 2, photo_size + 2, fill=0, stroke=1)

    if photo_b64:
        try:
            img_data = base64.b64decode(photo_b64)
            img_buf = io.BytesIO(img_data)
            img_reader = ImageReader(img_buf)
            c.drawImage(img_reader, photo_x, photo_y, photo_size, photo_size,
                       preserveAspectRatio=True, anchor='c', mask='auto')
        except Exception:
            # Fallback: initials box
            _draw_initials(c, person_name, photo_x, photo_y, photo_size)
    else:
        _draw_initials(c, person_name, photo_x, photo_y, photo_size)

    # ── Scanline overlay on photo ─────────────────────────────────
    c.setFillColor(colors.HexColor("#000000"))
    c.setFillAlpha(0.06)
    for y in range(int(photo_y), int(photo_y + photo_size), 4):
        c.rect(photo_x, y, photo_size, 1.5, fill=1, stroke=0)
    c.setFillAlpha(1)

    # ── Name ──────────────────────────────────────────────────────
    name_y = photo_y - 12 * mm
    c.setFillColor(colors.HexColor("#00ff41"))
    # Scale font to fit
    font_size = 28
    c.setFont("Courier-Bold", font_size)
    while c.stringWidth(person_name, "Courier-Bold", font_size) > W - 28 and font_size > 14:
        font_size -= 1
        c.setFont("Courier-Bold", font_size)
    c.drawCentredString(W / 2, name_y, person_name)

    # ── ID ────────────────────────────────────────────────────────
    c.setFillColor(colors.HexColor("#3a7a42"))
    c.setFont("Courier", 8)
    c.drawCentredString(W / 2, name_y - 7 * mm, f"ID: {person_id}")

    # ── Divider ───────────────────────────────────────────────────
    div_y = name_y - 11 * mm
    c.setStrokeColor(colors.HexColor("#0a3d12"))
    c.setLineWidth(0.5)
    c.line(20, div_y, W - 20, div_y)

    # ── Tags ──────────────────────────────────────────────────────
    tag_area_y = div_y - 4 * mm
    tag_x = 18
    tag_y = tag_area_y
    tag_h = 6 * mm
    tag_pad_x = 4 * mm
    tag_gap = 3 * mm
    max_x = W - 18

    c.setFont("Courier", 8)

    for tag in tags:
        tag_w = c.stringWidth(tag, "Courier", 8) + tag_pad_x * 2
        if tag_x + tag_w > max_x:
            tag_x = 18
            tag_y -= tag_h + 2 * mm
            if tag_y < 18:
                break

        # Tag border
        c.setStrokeColor(colors.HexColor("#0a3d12"))
        c.setFillColor(colors.HexColor("#020d04"))
        c.setLineWidth(0.5)
        c.rect(tag_x, tag_y - tag_h + 2 * mm, tag_w, tag_h, fill=1, stroke=1)

        # Tag text
        c.setFillColor(colors.HexColor("#3a7a42"))
        c.drawString(tag_x + tag_pad_x, tag_y - tag_h + 4 * mm, tag)

        tag_x += tag_w + tag_gap

    c.save()
    buf.seek(0)
    return buf.read()


def _draw_initials(c, name, x, y, size):
    initials = ''.join(w[0] for w in name.split() if w).upper()[:2]
    c.setFillColor(colors.HexColor("#071a0a"))
    c.rect(x, y, size, size, fill=1, stroke=0)
    c.setFillColor(colors.HexColor("#00ff41"))
    c.setFont("Courier-Bold", 36)
    c.drawCentredString(x + size / 2, y + size / 2 - 12, initials)


def fetch_photo_as_b64(photo_url):
    if not photo_url:
        return None
    try:
        req = urllib.request.Request(photo_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = resp.read()
        return base64.b64encode(data).decode()
    except Exception:
        return None


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        body = json.loads(self.rfile.read(length))

        name = body.get('name', 'Unknown')
        pid = body.get('id', '')
        tags = body.get('tags', [])
        photo_url = body.get('photo_url', '')

        photo_b64 = fetch_photo_as_b64(photo_url)
        pdf_bytes = draw_card(name, pid, tags, photo_b64)

        self.send_response(200)
        self.send_header('Content-Type', 'application/pdf')
        self.send_header('Content-Disposition', f'attachment; filename="terminal2k26_{pid}.pdf"')
        self.send_header('Content-Length', str(len(pdf_bytes)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(pdf_bytes)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
