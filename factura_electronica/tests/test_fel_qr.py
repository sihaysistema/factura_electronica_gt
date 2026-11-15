# Copyright (c) 2026, Si Hay Sistema and contributors
# See license.txt

"""FEL QR is the original reportlab SVG, inside an img data URI.

No Frappe site is required.
"""

from __future__ import unicode_literals

import base64
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
        frappe.log_error = lambda *args, **kwargs: None
        frappe.get_traceback = lambda: "traceback"
        sys.modules["frappe"] = frappe
    if "numinwords" not in sys.modules:
        numinwords = types.ModuleType("numinwords")
        numinwords.numinwords = lambda *args, **kwargs: ""
        sys.modules["numinwords"] = numinwords


_ensure_import_stubs()

import frappe  # noqa: E402
from factura_electronica.fel import qrcode as fel_qr  # noqa: E402

_IMG = re.compile(
    r'^<img src="data:image/svg\+xml;base64,([A-Za-z0-9+/=]+)" alt="FEL QR" width="120" height="120">$'
)
_SAMPLE = "A1B2C3D4-E5F6-7890-ABCD-EF1234567890"
_URL = (
    "https://report.feel.com.gt/ingfacereport/ingfacereport_documento?uuid=" + _SAMPLE
)


def _svg_from_img(html):
    match = _IMG.match(html or "")
    if match is None:
        raise AssertionError("not an SVG data-URI image: {0}".format((html or "")[:80]))
    return base64.b64decode(match.group(1)).decode("utf-8")


def _quiet_zone_modules(svg):
    rects = re.findall(
        r'<rect x="([^"]+)" y="([^"]+)" width="([^"]+)" height="([^"]+)" style="([^"]+)"',
        svg,
    )
    dark = []
    for x, _y, width, _height, style in rects:
        if "rgb(15%,49%,100%)" not in style:
            continue
        dark.append((float(x), float(width)))
    if not dark:
        raise AssertionError("SVG has no blue modules")
    module = min(item[1] for item in dark)
    return min(item[0] for item in dark) / module


class TestFelQrSvgImage(unittest.TestCase):
    def test_public_names_return_the_original_blue_svg(self):
        html = fel_qr.create_fel_svg_qrcode(_SAMPLE)
        self.assertEqual(html, fel_qr.fel_qr_svg(_SAMPLE))
        svg = _svg_from_img(html)
        self.assertTrue(svg.lstrip().startswith("<svg"))
        self.assertIn('width="120"', svg)
        self.assertIn('height="120"', svg)
        self.assertIn("rgb(15%,49%,100%)", svg)
        self.assertAlmostEqual(_quiet_zone_modules(svg), 4, places=4)
        self.assertNotIn("renderPM", html)

    def test_image_wrapping_failure_returns_the_inline_svg(self):
        original = fel_qr._svg_img

        def broken(svg):
            raise RuntimeError("encode failed")

        fel_qr._svg_img = broken
        logged = []

        def log_error(*args, **kwargs):
            logged.append((args, kwargs))

        frappe.log_error = log_error
        try:
            html = fel_qr.create_fel_svg_qrcode(_SAMPLE)
        finally:
            fel_qr._svg_img = original
        self.assertTrue(html.lstrip().startswith("<svg"))
        self.assertIn('width="120"', html)
        self.assertIn("rgb(15%,49%,100%)", html)
        self.assertTrue(logged)

    def test_svg_failure_returns_plain_text_and_does_not_raise(self):
        original = fel_qr._svg_markup

        def broken(url):
            raise RuntimeError("reportlab failed")

        fel_qr._svg_markup = broken
        logged = []
        frappe.log_error = lambda *args, **kwargs: logged.append(kwargs.get("title"))
        try:
            text = fel_qr.create_fel_svg_qrcode(_SAMPLE)
        finally:
            fel_qr._svg_markup = original
        self.assertIn(_SAMPLE, text)
        self.assertIn(_URL, text)
        self.assertNotIn("<svg", text)
        self.assertNotIn("<img", text)
        self.assertIn("FEL QR SVG", logged)


if __name__ == "__main__":
    unittest.main()
