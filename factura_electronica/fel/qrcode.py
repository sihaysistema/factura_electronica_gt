# Copyright (c) 2020, Si Hay Sistema and contributors
# For license information, please see license.txt

"""FEL authorization QR for print formats.

wkhtmltopdf 0.12.6 (the PDF button and ``frappe.get_pdf``) drops inline
SVG, so the QR is a PNG embedded as a data-URI ``<img>``. The public
names stay ``create_fel_svg_qrcode`` and ``fel_qr_svg`` because existing
print formats call those Jinja methods.
"""

from __future__ import unicode_literals

import base64
import io

import frappe

_FEL_QR_URL = (
    "https://report.feel.com.gt/ingfacereport/ingfacereport_documento?uuid="
)
_QR_SIZE = 120


def fel_qr_url(authorization_number):
    """SAT/INFILE document URL encoded in the QR."""
    return _FEL_QR_URL + str(authorization_number)


def _png_with_renderpm(url):
    """Draw the QR with reportlab renderPM. Raises if that backend is missing."""
    from reportlab.graphics import renderPM
    from reportlab.graphics.barcode import qr
    from reportlab.graphics.shapes import Drawing

    widget = qr.QrCodeWidget(url)
    bounds = widget.getBounds()
    width = bounds[2] - bounds[0]
    height = bounds[3] - bounds[1]
    if not width or not height:
        raise ValueError("QR drawing has no size")
    drawing = Drawing(
        _QR_SIZE,
        _QR_SIZE,
        transform=[float(_QR_SIZE) / width, 0, 0, float(_QR_SIZE) / height, 0, 0],
    )
    drawing.add(widget)
    png = renderPM.drawToString(drawing, fmt="PNG")
    if isinstance(png, str):
        png = png.encode("latin-1")
    if not png.startswith(b"\x89PNG"):
        raise ValueError("renderPM did not return a PNG")
    return png


def _png_with_qrcode(url):
    """Draw the QR with the qrcode package and Pillow."""
    import qrcode

    code = qrcode.QRCode(border=1, box_size=4)
    code.add_data(url)
    code.make(fit=True)
    image = code.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def fel_qr_png_bytes(authorization_number):
    """PNG bytes for the authorization QR.

    reportlab renderPM is used when it can actually draw. Sites without
    that backend (no Cairo/rlPyCairo) fall back to qrcode and Pillow.
    """
    url = fel_qr_url(authorization_number)
    try:
        return _png_with_renderpm(url)
    except Exception:
        return _png_with_qrcode(url)


def fel_qr_png_img(authorization_number, size=_QR_SIZE):
    """``<img>`` with a base64 PNG data URI."""
    encoded = base64.b64encode(fel_qr_png_bytes(authorization_number)).decode("ascii")
    return (
        '<img src="data:image/png;base64,{encoded}" alt="FEL QR" '
        'width="{size}" height="{size}">'
    ).format(encoded=encoded, size=int(size))


@frappe.whitelist()
def create_fel_svg_qrcode(authorization_number):
    """Jinja/whitelist name kept for existing print formats.

    Returns a PNG data-URI image. The previous SVG string does not survive
    wkhtmltopdf 0.12.6.
    """
    return fel_qr_png_img(authorization_number)


def fel_qr_svg(authorization_number):
    """Jinja alias kept from v13 (``fel_qr_svg``), used by the FEL print format."""
    return create_fel_svg_qrcode(authorization_number)
