import io

import segno


def make_qr_png(data: str) -> bytes:
    """Turns text (the ticket code) into a QR code PNG image."""
    buffer = io.BytesIO()
    segno.make(data, error="m").save(buffer, kind="png", scale=8, border=2)
    return buffer.getvalue()
