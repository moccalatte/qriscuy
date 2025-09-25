"""QR image renderer with qriscuy branding."""
from __future__ import annotations

import base64
import io
from typing import Any

import qrcode
from PIL import Image, ImageDraw, ImageFont


def generate_qr_image(data: str, title: str = "qriscuy") -> Image.Image:
    """Generate QR image with branded frame and label."""

    qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=10, border=4)
    qr.add_data(data)
    qr.make(fit=True)

    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGBA")
    width, height = qr_img.size

    label_height = 40
    margin = 40
    canvas_width = width + margin * 2
    canvas_height = height + margin * 2 + label_height

    canvas = Image.new("RGBA", (canvas_width, canvas_height), color="#F5F7FA")
    canvas.paste(qr_img, (margin, margin))

    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default()
    text = title.upper()
    text_width, text_height = draw.textsize(text, font=font)
    text_x = (canvas_width - text_width) // 2
    text_y = margin + height + (label_height - text_height) // 2
    draw.rectangle(
        [(margin // 2, margin + height), (canvas_width - margin // 2, margin + height + label_height)],
        fill="#FFFFFF",
    )
    draw.text((text_x, text_y), text, fill="#1F2937", font=font)

    return canvas


def qr_image_to_png_bytes(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def render_qr_payload(payload: str, title: str = "qriscuy") -> dict[str, Any]:
    """Render payload into PNG bytes and base64 string."""

    image = generate_qr_image(payload, title=title)
    png_bytes = qr_image_to_png_bytes(image)
    return {
        "png_bytes": png_bytes,
        "png_base64": base64.b64encode(png_bytes).decode("ascii"),
    }
