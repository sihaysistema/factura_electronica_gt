# Copyright (c) 2020, Si Hay Sistema and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import requests
import xmltodict

import frappe
from frappe import _, _dict

from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.graphics.shapes import *
from reportlab.graphics import renderPDF
from reportlab.graphics import renderSVG

import xml.etree.ElementTree as ET

#----------------------------------------------------------------------
@frappe.whitelist()
def create_fel_svg_qrcode(authorization_number):
    """
    Create QR Code example and return it as an svg string.
    Takes in variables for QR Code assembly on-the-fly
    Debug function can also save the SVG file, PDF, PNG
    """
    label_width_mm = 105
    label_height_mm = 155
    # c = canvas.Canvas("QRCodes.svg")
    # c.setPageSize((label_width_mm*mm, label_height_mm*mm))

    #track_no = 2999
    # track_url = 'https://tunart.biz/track?mytuna=' + str(track_no)
    qr_code_url = 'https://report.feel.com.gt/ingfacereport/ingfacereport_documento?uuid=' + str(authorization_number)

    # We create a list with possible content options for the QR code.
    # This helps with quick changes during first production run.
    qr_contents = ['https://fogliasana.com/','https://sihaysistema.com',qr_code_url]

    # en_US: We specify the position of the QR code element in mm from the left and bottom of page.
    # en_US: We also provide a percentage scale for quick and easy adjustment when draing on the page. Default = 100.0  Larger numbers will enlarge the QR.
    qr_code_x_pos_mm = 20.00
    qr_code_y_pos_mm = 70.00

    # Assign the colors
    # We use CMYK color assignment for print
    FSBluecmyk = colors.PCMYKColor(84.29,50.99,0,0)
    FSGreenCMYK = colors.PCMYKColor(60.83,0,95.9,0)

    scaling_percent = 20.0
    unit = 100.0
    # en_US:  First, we draw a QR code with the selected contents. For now it is a URL. Plan is to call a webpage which calls a Python method delivering data for that specific shipment.
    qr_code = qr.QrCodeWidget(qr_contents[2],barFillColor=FSBluecmyk)
    # en_US: We get the bounds of the drawn QR Code. This will help resize.
    bounds = qr_code.getBounds() # Returns position x, position y, size x, size y
    # en_US: We set the width of the QR code drawing to the width bounds returned
    width = bounds[2] - bounds[0]
    # en_US: We set the width of the QR code drawing to the width bounds returned
    height = bounds[3] - bounds[1]
    # en_US: We create a drawing container with a specified size. We adjust the container to fit the QR Code, using the object size and a percentage amount
    qr1 = Drawing(unit, unit, transform=[(scaling_percent/width)*mm,0,0,(scaling_percent/height)*mm,0,0])

    # en_US: We add the QR code to the code container
    qr1.add(qr_code)

    # en_US: We draw contents of d container with QR Code, on canvas c, at x position, y position
    # renderSVG.draw(d, c, qr_code_x_pos_mm*mm, qr_code_y_pos_mm*mm)

    # We now draw the SVG to an SVG XML-based string
    svg_as_string = renderSVG.drawToString(qr1)
    # DEBUG ONLY, Save to a file.
    #renderSVG.drawToFile(qr1, 'QRCode.svg')

    # We now parse to XML, by passing to a string again, without the extra tags
    myroot = ET.fromstring(svg_as_string)
    #print(svg_as_string)
    # print(myroot.tag)
    # print(myroot)
    qr_svg_string = ET.tostring(myroot, encoding="utf-8", method="xml")
    # print(qr_svg_string)
    return qr_svg_string
