# Copyright (c) 2020, Si Hay Sistema and contributors
# For license information, please see license.txt

"""FEL authorization QR for print formats.

The drawing is the original reportlab SVG: QrCodeWidget, CMYK blue
(84.29, 50.99, 0, 0), a 100 by 100 code inside a 120 by 120 drawing,
error correction L, and a 4-module quiet zone. wkhtmltopdf 0.12.6 drops
inline SVG, so the same markup is delivered as an SVG data-URI image.

renderPM is not used. reportlab 4 needs rlPyCairo for that backend, and
a missing library must not break printing.
"""

from __future__ import unicode_literals

import base64
import logging

import frappe

_FEL_QR_URL = (
    "https://report.feel.com.gt/ingfacereport/ingfacereport_documento?uuid="
)
_DISPLAY_SIZE = 120
_QR_DRAW_SIZE = 100
_QUIET_ZONE = 4

_log = logging.getLogger(__name__)


def fel_qr_url(authorization_number):
    """SAT/INFILE document URL encoded in the QR."""
    return _FEL_QR_URL + str(authorization_number)


def _log_failure(title, exc):
    """Record a QR failure without letting the logger break the print."""
    try:
        message = "{0}".format(exc)
        if hasattr(frappe, "get_traceback"):
            message = frappe.get_traceback()
        frappe.log_error(message=message, title=title)
    except Exception:
        _log.warning("%s: %s", title, exc)


def _svg_markup(url):
    """Original inline SVG, without the XML declaration or the debug print."""
    from reportlab.graphics.barcode import qr
    from reportlab.graphics.shapes import Drawing
    from reportlab.graphics import renderSVG
    from reportlab.lib.colors import PCMYKColor

    widget = qr.QrCodeWidget(
        url,
        barFillColor=PCMYKColor(84.29, 50.99, 0, 0),
        x=0,
        y=0,
        barWidth=_QR_DRAW_SIZE,
        barHeight=_QR_DRAW_SIZE,
        barBorder=_QUIET_ZONE,
    )
    drawing = Drawing(_DISPLAY_SIZE, _DISPLAY_SIZE)
    drawing.add(widget)
    svg_as_string = renderSVG.drawToString(drawing)
    first = svg_as_string.find(">", 0)
    second = svg_as_string.find(">", first + 1)
    return svg_as_string[second + 2:]


def _svg_img(svg):
    encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return (
        '<img src="data:image/svg+xml;base64,{encoded}" alt="FEL QR" '
        'width="{size}" height="{size}">'
    ).format(encoded=encoded, size=_DISPLAY_SIZE)


def _plain_fallback(authorization_number, url):
    return "{0}\n{1}".format(authorization_number, url)


def fel_qr_markup(authorization_number):
    """SVG data-URI image, inline SVG, or plain text. Does not raise."""
    url = fel_qr_url(authorization_number)
    try:
        svg = _svg_markup(url)
    except Exception as exc:
        _log_failure("FEL QR SVG", exc)
        return _plain_fallback(authorization_number, url)
    try:
        return _svg_img(svg)
    except Exception as exc:
        _log_failure("FEL QR image", exc)
        return svg


@frappe.whitelist()
def create_fel_svg_qrcode(authorization_number):
    """Jinja/whitelist name kept for existing print formats."""
    return fel_qr_markup(authorization_number)


def fel_qr_svg(authorization_number):
    """Jinja alias kept from v13 (``fel_qr_svg``), used by the FEL print format."""
    return create_fel_svg_qrcode(authorization_number)
