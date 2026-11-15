# Copyright (c) 2026, Si Hay Sistema and contributors
# See license.txt

"""FEL QR is a PNG data URI so wkhtmltopdf 0.12.6 can print it.

No Frappe site is required. pyzbar is used when it imports; without it
the test still checks that the image is a real PNG.
"""

from __future__ import unicode_literals

import base64
import io
import re
import sys
import types
import unittest


def _ensure_import_stubs():
    if "frappe" not in sys.modules:
        frappe = types.ModuleType("frappe")

        def whitelist(*args, **kwargs):
            if len(args) == 1 and callable(args[0]) and not kwargs:
                return args[0]

            def decorator(fn):
                return fn

            return decorator

        frappe.whitelist = whitelist
        sys.modules["frappe"] = frappe
    if "numinwords" not in sys.modules:
        numinwords = types.ModuleType("numinwords")
        numinwords.numinwords = lambda *args, **kwargs: ""
        sys.modules["numinwords"] = numinwords


_ensure_import_stubs()

from factura_electronica.fel import qrcode as fel_qr  # noqa: E402

_DATA_URI = re.compile(
    r'^<img src="data:image/png;base64,([A-Za-z0-9+/=]+)" alt="FEL QR" width="120" height="120">$'
)
_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
_SAMPLE = "A1B2C3D4-E5F6-7890-ABCD-EF1234567890"


def _png_from_img(html):
    match = _DATA_URI.match(html)
    if match is None:
        raise AssertionError("not a PNG data-URI image: {0}".format(html[:80]))
    return base64.b64decode(match.group(1))


def _decoded_payload(png_bytes):
    """Return the QR text, or None when pyzbar is not installed."""
    try:
        from PIL import Image
        from pyzbar.pyzbar import decode
    except Exception:
        return None
    found = decode(Image.open(io.BytesIO(png_bytes)))
    if not found:
        raise AssertionError("pyzbar installed but did not read the QR")
    return found[0].data.decode("utf-8")


class TestFelQrPng(unittest.TestCase):
    def test_url_uses_the_authorization_number(self):
        self.assertEqual(
            fel_qr.fel_qr_url(_SAMPLE),
            "https://report.feel.com.gt/ingfacereport/ingfacereport_documento?uuid=" + _SAMPLE,
        )

    def test_public_names_return_the_same_png_data_uri(self):
        svg_name = fel_qr.create_fel_svg_qrcode(_SAMPLE)
        alias = fel_qr.fel_qr_svg(_SAMPLE)
        self.assertEqual(svg_name, alias)
        png = _png_from_img(svg_name)
        self.assertTrue(png.startswith(_PNG_MAGIC))
        image = __import__("PIL").Image.open(io.BytesIO(png))
        image.load()
        self.assertGreater(image.size[0], 0)
        self.assertEqual(image.size[0], image.size[1])
        payload = _decoded_payload(png)
        if payload is not None:
            self.assertEqual(payload, fel_qr.fel_qr_url(_SAMPLE))

    def test_qrcode_pillow_fallback_is_a_png_of_the_same_url(self):
        png = fel_qr._png_with_qrcode(fel_qr.fel_qr_url(_SAMPLE))
        self.assertTrue(png.startswith(_PNG_MAGIC))
        payload = _decoded_payload(png)
        if payload is not None:
            self.assertEqual(payload, fel_qr.fel_qr_url(_SAMPLE))

    def test_missing_renderpm_uses_the_fallback(self):
        original = fel_qr._png_with_renderpm

        def broken(url):
            raise ImportError("renderPM missing")

        fel_qr._png_with_renderpm = broken
        try:
            png = _png_from_img(fel_qr.create_fel_svg_qrcode(_SAMPLE))
        finally:
            fel_qr._png_with_renderpm = original
        self.assertTrue(png.startswith(_PNG_MAGIC))
        payload = _decoded_payload(png)
        if payload is not None:
            self.assertEqual(payload, fel_qr.fel_qr_url(_SAMPLE))


if __name__ == "__main__":
    unittest.main()
