# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
from frappe import _
import xmltodict
from datetime import datetime, date, time
import os


# es-GT: Guarda los datos recibidos de infile en la Tabla 'Facturas Electronicas'.
# en-US: Saves the data received from infile in the 'Electronic Invoices' Table.
# es-GT: Cada factura electronica que se genere exitosamente, deja este registro como constancia.
# en-US: Saves the data received from infile in the 'Electronic Invoices' Table.
# en-US: For every succesfully generated electronic invoice, a record is added to keep as confirmation.
def guardar_factura_electronica(datos_recibidos, serie_fact, tiempo_envio):
    '''Guarda los datos recibidos de infile en la tabla Envios Facturas Electronicas
       de la base de datos ERPNext

       Parametros:
       ----------
       * datos_recibidos (xml) : Respuesta de INFILE con la data de factura electronica
                                 generada
       * serie_fact (str) : Serie utilizada para la factura original
       * tiempo_envio (str) : timestamp capturado al momento de enviar
    '''
    try:
        # es-GT: documento: con la libreria xmltodict, se convierte de XML a Diccionario, para acceder a los datos atraves de sus llaves.
        # es-GT: Se asigna a la variable 'documento'

        # en-US: documento: with the xmltodict library, it is converted from XML to Dictionary, to access the data through the dictionary keys
        # en-US: All this is assigned to the 'document' variable.
        respuestaINFILE = xmltodict.parse(datos_recibidos)

        # es-GT: Crea un nuevo record de Envios Facturas Electronica en la base de datos.
        # en-US: Creates a new Electronic Invoice Sent record in the database
        tabFacturaElectronica = frappe.new_doc("Envios Facturas Electronicas")

        # es-GT: Obtiene y Guarda la serie de factura.
        # en-US: Obtains and Saves the invoice series.
        tabFacturaElectronica.serie_factura_original = serie_fact

        # es-GT: Obtiene y Guarda el CAE (Codigo de Autorización Electronico)
        # en-US: Obtains and Saves the CAE or literally translated: "Code of Electronic Authorization"
        tabFacturaElectronica.cae = str(respuestaINFILE['S:Envelope']['S:Body']['ns2:registrarDteResponse']['return']['cae'])
        cae_dato = str(respuestaINFILE['S:Envelope']['S:Body']['ns2:registrarDteResponse']['return']['cae'])

        # es-GT: Obtiene y Guarda el Numero de Documento que quedo registrada ante el Generador de Factura Electronica y la SAT
        # en-US: Obtains and Saves the Document Number that was registered with the Electronic Invoice Generator and SAT
        tabFacturaElectronica.numero_documento = str(respuestaINFILE['S:Envelope']['S:Body']['ns2:registrarDteResponse']['return']['numeroDocumento'])

        # es-GT: Obtiene y Guarda el Estado según GFACE (GFACE = Generador de Factura Electronica)
        # en-US: Obtains and Saves the current State of the document as per GFACE (Electronic Invoice Generator)
        tabFacturaElectronica.estado = str(respuestaINFILE['S:Envelope']['S:Body']['ns2:registrarDteResponse']['return']['estado'])

        # es-GT: Obtiene y Guarda las Anotaciones segun GFACE
        # en-US: Obtains and Saves the Annotations as per GFACE
        tabFacturaElectronica.anotaciones = str(respuestaINFILE['S:Envelope']['S:Body']['ns2:registrarDteResponse']['return']['anotaciones'])

        # es-GT: Obtiene y Guarda la Descripcion: En este campo estan todas las descripciones de errores y mensaje de generacion correcta
        # en-US: Obtains and Saves the Description: This field contains all the descriptions of errors and correct generation messages
        tabFacturaElectronica.descripcion = str(respuestaINFILE['S:Envelope']['S:Body']['ns2:registrarDteResponse']['return']['descripcion'])

        # es-GT: Obtiene y Guarda la Validez del documento
        # en-US: Obtains and Saves the Validity state of the document
        tabFacturaElectronica.valido = str(respuestaINFILE['S:Envelope']['S:Body']['ns2:registrarDteResponse']['return']['valido'])

        # es-GT: Obtiene y Guarda el Numero DTE
        # en-US: Obtains and Saves the DTE Number
        tabFacturaElectronica.numero_dte = str(respuestaINFILE['S:Envelope']['S:Body']['ns2:registrarDteResponse']['return']['numeroDte'])
        # numeroDTEINFILE: Guarda el numero DTE, sera utilizado para renombrar la serie original de la factura que lo origino
        numeroDTEINFILE = str(respuestaINFILE['S:Envelope']['S:Body']['ns2:registrarDteResponse']['return']['numeroDte'])

        # es-GT: Obtiene y Guarda el Rango Final Autorizado
        # en-US: Obtains and Saves the Authorized Final Range
        tabFacturaElectronica.rango_final_autorizado = str(respuestaINFILE['S:Envelope']['S:Body']['ns2:registrarDteResponse']['return']['rangoFinalAutorizado'])

        # es-GT: Obtiene y Guarda el Rango Inicial Autorizado
        # en-US: Obtains and Saves the Initial Authorized Range
        tabFacturaElectronica.rango_inicial_autorizado = str(respuestaINFILE['S:Envelope']['S:Body']['ns2:registrarDteResponse']['return']['rangoInicialAutorizado'])

        # es-GT: Obtiene y Guarda el Regimen de impuestos
        # en-US: Obtains and Saves the Legal Tax Structure, aka 'Regimen'
        tabFacturaElectronica.regimen = str(respuestaINFILE['S:Envelope']['S:Body']['ns2:registrarDteResponse']['return']['regimen'])

        # es-GT: Obtiene y Guarda el tiempo en que se recibieron los datos de INFILE
        # en-US: Obtains and Saves the timestamp of data reception from INFILE
        tabFacturaElectronica.recibido = datetime.now()

        # es-GT: Obtiene y Guarda el tiempo en que se enviaron los datos a INFILE
        # es-GT: Estos datos de tiempo se obtienen para poder monitorear el tiempo de transacción
        # en-US: Obtains and Saves the timestamp the data was sent to INFILE
        # en-US: These timestamps are obtained to keep track of transaction time
        tabFacturaElectronica.enviado = tiempo_envio

        # es-GT: Guarda todos los datos en la tabla llamada 'FACTURAS ELECTRONICAS' de la base de datos de ERPNext
        # en-US: Saves all the data in the table called 'ELECTRONIC INVOICES' of the ERPNext database
        tabFacturaElectronica.save()
        # es-GT: Al terminar de guardar el registro en la base de datos, retorna el CAE
        # en-US: When done saving the records to the database, it returns de CAE

        # return cae_dato
        # frappe.msgprint(_("Factura Electronica Generada!"))
    except:
        # es-GT: Si algo falla, muestra el error en el navegador.
        # es-GT: Este mensaje solo indica que no se guardo la confirmacion de la factura electronica.
        # en-US: If something fails, the exception shows this message in the browser
        # en-US: This message simply states that the Electronic Invoice Confirmation was not saved.
        frappe.msgprint(_("""Error: No se guardo correctamente la Factura Electronica. Por favor vuelva a presionar el
                             boton de Factura Electronica"""))
    else:
        # Si los datos se Guardan correctamente, se retornara el cae generado, que sera capturado por api.py
        # Puede utlizar para futuros cambios en el codigo
        return cae_dato


def actualizarTablas(serieOriginalFac):
    """Funcion permite actualizar tablas en la base de datos, despues de haber generado
       la factura electronica

       Parametros:
       ----------
       * serieOriginalFac (str) : Serie de factura original
    """
    # Verifica que exista un documento en la tabla Envios Facturas Electronicas con el nombre de la serie original
    if frappe.db.exists('Envios Facturas Electronicas', {'serie_factura_original': serieOriginalFac}):
        factura_guardada = frappe.db.get_values('Envios Facturas Electronicas',
                                                filters={'serie_factura_original': serieOriginalFac},
                                                fieldname=['numero_dte', 'cae', 'serie_factura_original'], as_dict=1)
        # Esta seccion se encarga de actualizar la serie, con una nueva que es el numero de DTE
        # buscara en las tablas donde exista una coincidencia actualizando con la nueva serie
        try:
            # serieDte: guarda el numero DTE retornado por INFILE, se utilizara para reemplazar el nombre de la serie de la
            # factura que lo generó.
            serieDte = str(factura_guardada[0]['numero_dte'])
            # serie_fac_original: Guarda la serie original de la factura.
            serie_fac_original = serieOriginalFac

            # Actualizacion de tablas que son modificadas directamente.
            # 01 - tabSales Invoice
            frappe.db.sql('''UPDATE `tabSales Invoice`
                             SET name=%(name)s,
                                 cae_factura_electronica=%(cae_correcto)s,
                                 serie_original_del_documento=%(serie_orig_correcta)s
                            WHERE name=%(serieFa)s
                            ''', {'name':serieDte, 'cae_correcto': factura_guardada[0]['cae'],
                                  'serie_orig_correcta': serie_fac_original, 'serieFa':serie_fac_original})

            # 02 - tabSales Invoice Item
            frappe.db.sql('''UPDATE `tabSales Invoice Item` SET parent=%(name)s
                            WHERE parent=%(serieFa)s''', {'name':serieDte, 'serieFa':serie_fac_original})

            # 03 - tabGL Entry
            frappe.db.sql('''UPDATE `tabGL Entry` SET voucher_no=%(name)s, against_voucher=%(name)s
                            WHERE voucher_no=%(serieFa)s AND against_voucher=%(serieFa)s''', {'name':serieDte, 'serieFa':serie_fac_original})

            frappe.db.sql('''UPDATE `tabGL Entry` SET voucher_no=%(name)s, docstatus=1
                            WHERE voucher_no=%(serieFa)s AND against_voucher IS NULL''', {'name':serieDte, 'serieFa':serie_fac_original})

            # Actualizacion de tablas que pueden ser modificadas desde Sales Invoice
            # Verificara tabla por tabla en busca de un valor existe, en caso sea verdadero actualizara,
            # en caso no encuentre nada no hara nada
            # 04 - tabSales Taxes and Charges
            if frappe.db.exists('Sales Taxes and Charges', {'parent': serie_fac_original}):
                frappe.db.sql('''UPDATE `tabSales Taxes and Charges` SET parent=%(name)s
                                WHERE parent=%(serieFa)s''', {'name':serieDte, 'serieFa':serie_fac_original})

            if frappe.db.exists('Otros Impuestos Factura Electronica', {'parent': serie_fac_original}):
                frappe.db.sql('''UPDATE `tabOtros Impuestos Factura Electronica` SET parent=%(name)s
                                WHERE parent=%(serieFa)s''', {'name':serieDte, 'serieFa':serie_fac_original})

            # else:
            #     frappe.msgprint(_('No hay registro en Sales Taxes and Charges'))

            # Pago programado
            # 05 - tabPayment Schedule
            if frappe.db.exists('Payment Schedule', {'parent': serie_fac_original}):
                frappe.db.sql('''UPDATE `tabPayment Schedule` SET parent=%(name)s
                                WHERE parent=%(serieFa)s''', {'name':serieDte, 'serieFa':serie_fac_original})
            # else:
            #     frappe.msgprint(_('No hay registro en Payment Schedule'))

            # subscripcion
            # 06 - tabSubscription
            if frappe.db.exists('Subscription', {'reference_document': serie_fac_original}):
                frappe.db.sql('''UPDATE `tabSubscription` SET reference_document=%(name)s
                                WHERE reference_document=%(serieFa)s''', {'name':serieDte, 'serieFa':serie_fac_original})
            # else:
            #     frappe.msgprint(_('No hay registro en Subscription'))

            # Entrada del libro mayor de inventarios
            # 07 - tabStock Ledger Entry
            if frappe.db.exists('Stock Ledger Entry', {'voucher_no': serie_fac_original}):
                frappe.db.sql('''UPDATE `tabStock Ledger Entry` SET voucher_no=%(name)s
                                WHERE voucher_no=%(serieFa)s''', {'name':serieDte, 'serieFa':serie_fac_original})
            # else:
            #     frappe.msgprint(_('No hay registro en Stock Ledger Entry'))

            # Hoja de tiempo de factura de ventas
            # 08 - tabSales Invoice Timesheet
            if frappe.db.exists('Sales Invoice Timesheet', {'parent': serie_fac_original}):
                frappe.db.sql('''UPDATE `tabSales Invoice Timesheet` SET parent=%(name)s
                                WHERE parent=%(serieFa)s''', {'name':serieDte, 'serieFa':serie_fac_original})
            # else:
            #     frappe.msgprint(_('No hay registro en Sales Invoice Timesheet'))

            # Equipo Ventas
            # 09 - tabSales Team
            if frappe.db.exists('Sales Team', {'parent': serie_fac_original}):
                frappe.db.sql('''UPDATE `tabSales Team` SET parent=%(name)s
                                WHERE parent=%(serieFa)s''', {'name':serieDte, 'serieFa':serie_fac_original})
            # else:
            #     frappe.msgprint(_('No hay registro en Sales Team'))

            # Packed Item
            # 10 - tabPacked Item
            if frappe.db.exists('Packed Item', {'parent': serie_fac_original}):
                frappe.db.sql('''UPDATE `tabPacked Item` SET parent=%(name)s
                                WHERE parent=%(serieFa)s''', {'name':serieDte, 'serieFa':serie_fac_original})
            # else:
            #     frappe.msgprint(_('No hay registro en tabPackedItem))

            # Sales Invoice Advance - Anticipos a facturas
            # 11 - tabSales Invoice Advance
            if frappe.db.exists('Sales Invoice Advance', {'parent': serie_fac_original}):
                frappe.db.sql('''UPDATE `tabSales Invoice Advance` SET parent=%(name)s
                                WHERE parent=%(serieFa)s''', {'name':serieDte, 'serieFa':serie_fac_original})
            # else:
            #     frappe.msgprint(_('No hay registro en tabSales Invoice Advance))

            # Sales Invoice Payment - Pagos sobre a facturas
            # 12 - tabSales Invoice Payment
            if frappe.db.exists('Sales Invoice Payment', {'parent': serie_fac_original}):
                frappe.db.sql('''UPDATE `tabSales Invoice Payment` SET parent=%(name)s
                                WHERE parent=%(serieFa)s''', {'name':serieDte, 'serieFa':serie_fac_original})
            # else:
            #     frappe.msgprint(_('No hay registro en tabSales Invoice Payment))

            # Payment Entry Reference -
            # 13 - tabPayment Entry Reference
            if frappe.db.exists('Payment Entry Reference', {'parent': serie_fac_original}):
                frappe.db.sql('''UPDATE `tabSales Invoice Payment` SET parent=%(name)s
                                WHERE parent=%(serieFa)s''', {'name':serieDte, 'serieFa':serie_fac_original})
            # else:
            #     frappe.msgprint(_('No hay registro en tabPayment Entry Reference))

            # Sales Order
            # 15 - tabSales Order
            if frappe.db.exists('Sales Order', {'parent': serie_fac_original}):
                frappe.db.sql('''UPDATE `tabSales Order` SET parent=%(name)s
                                WHERE parent=%(serieFa)s''', {'name':serieDte, 'serieFa':serie_fac_original})
            # else:
            #     frappe.msgprint(_('No hay registro en tabSales Order))

            # Parece que este no enlaza directamente con sales invoice es el sales invoice que enlaza con este.
            # Delivery Note
            # 16 - tabDelivery Note
            if frappe.db.exists('Delivery Note', {'parent': serie_fac_original}):
                frappe.db.sql('''UPDATE `tabDelivery Note` SET parent=%(name)s
                                WHERE parent=%(serieFa)s''', {'name':serieDte, 'serieFa':serie_fac_original})

            frappe.db.commit()
        except:
            # En caso exista un error al renombrar la factura retornara el mensaje con el error
            frappe.msgprint(_('Error al renombrar Factura. Por favor intente de nuevo presionando el boton Factura Electronica'))
        else:
            # Si los datos se Guardan correctamente, se retornara el Numero Dte generado, que sera capturado por api.py
            # para luego ser capturado por javascript, se utilizara para recargar la url con los cambios correctos
            return str(factura_guardada[0]['numero_dte'])
