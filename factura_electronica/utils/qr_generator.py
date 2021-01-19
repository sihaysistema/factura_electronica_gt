# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import frappe
import qrcode
from frappe import _


@frappe.whitelist()
def qr_generator(img_name, input_data='https://sihaysistema.com', img_type='png', fill='black',
                 background_color='white', private=1):
    # Link for website
    # input_data = 'https://sihaysistema.com'

    # Creating an instance of qrcode
    qr = qrcode.QRCode(
        version=1,
        box_size=10,
        border=5
    )

    qr.add_data(input_data)
    qr.make(fit=True)

    img = qr.make_image(fill=fill, back_color=background_color)
    img.save(f'{img_name}.{img_type}')
