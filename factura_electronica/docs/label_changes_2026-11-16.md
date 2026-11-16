# Custom field label changes, 2026-11-16

English is the label. Spanish comes from `translations/es.csv`. The shared source `Is Exempt` stays `Es exento` in Translation fixture `fb33b8c6b4`, so Sales Invoice Item `facelec_si_is_exempt` and Purchase Invoice Item `facelec_pr_is_exempt` keep that Spanish. Sales Invoice `es_extempta` uses the separate source `Exempt Invoice`, translated `Es exenta` in `es.csv`.

Revert instruction: revert commit `1d0e4b43709f0abf451db99221ff356dc824fc39`, then `bench migrate`. That commit is the English label conversion. The exempt checkbox uses `Exempt Invoice` in commit `05d6f3fe428da72bd928c7fa98ad287056b4bf3e`.

| Record name | Fieldname | Old label | New English label | Spanish translation |
| --- | --- | --- | --- | --- |
| Sales Invoice-es_extempta | es_extempta | Es extempta | Exempt Invoice | Es exenta |
| UOM-faceleccodigo_unidad_de_medida | faceleccodigo_unidad_de_medida | Codigo Unidad de Medida | Unit of Measurement Code | Código Unidad de Medida |
| Supplier-facelec_nit_proveedor | facelec_nit_proveedor | NIT Proveedor | Supplier NIT | NIT Proveedor |
| Purchase Invoice-facelec_nit_fproveedor | facelec_nit_fproveedor | NIT Proveedor | Supplier NIT | NIT Proveedor |
| Purchase Receipt-facelec_nit_prproveedor | facelec_nit_prproveedor | NIT Proveedor | Supplier NIT | NIT Proveedor |
| Purchase Invoice-es_factura_especial | es_factura_especial | Es Factura Especial | Is Special Invoice | Es Factura Especial |
| Sales Invoice-es_nota_de_debito | es_nota_de_debito | Es Nota de Debito | Is Debit Note | Es Nota de Débito |
| Sales Invoice-es_dpi | es_dpi | Es dpi | Is DPI | Es DPI |
| Sales Invoice-es_pasaporte | es_pasaporte | Es Pasaporte | Is Passport | Es Pasaporte |
| Sales Invoice-facelec_factura_asociada | facelec_factura_asociada | Factura Asociada para Nota de Debito | Associated Invoice for Debit Note | Factura Asociada para Nota de Débito |
| Sales Invoice-serie_original_del_documento | serie_original_del_documento | Serie Original del Documento | Original Document Series | Serie Original del Documento |
| Purchase Invoice-serie_original_del_documento | serie_original_del_documento | Serie Original Del Documento | Original Document Series | Serie Original del Documento |
| Sales Invoice-shs_numero_resolucion | shs_numero_resolucion | Numero Resolucion | Resolution Number | Número Resolución |
| Sales Invoice-numero_autorizacion_fel | numero_autorizacion_fel | Numero Autorizacion FEL | FEL Authorization Number | Número Autorización FEL |
| Purchase Invoice-numero_autorizacion_fel | numero_autorizacion_fel | Numero Autorizacion FEL | FEL Authorization Number | Número Autorización FEL |
| Sales Invoice-cae_factura_electronica | cae_factura_electronica | CAE Factura Electronica | Electronic Invoice CAE | CAE Factura Electrónica |
| Sales Invoice-cae_nota_de_credito | cae_nota_de_credito | CAE Nota de Credito | Credit Note CAE | CAE Nota de Crédito |
| Sales Invoice-cae_nota_de_debito | cae_nota_de_debito | CAE Nota de Debito | Debit Note CAE | CAE Nota de Débito |
| Sales Invoice Item-shs_amount_for_back_calc | shs_amount_for_back_calc | Monto Para Redondeo | Amount for Rounding | Monto Para Redondeo |
| Delivery Note Item-shs_amount_for_back_calc | shs_amount_for_back_calc | Monto Para Redondeo | Amount for Rounding | Monto Para Redondeo |
| Purchase Invoice Item-shs_amount_for_back_calc | shs_amount_for_back_calc | Monto Para Redondeo | Amount for Rounding | Monto Para Redondeo |
| Purchase Receipt Item-shs_amount_for_back_calc | shs_amount_for_back_calc | Monto Para Redondeo | Amount for Rounding | Monto Para Redondeo |
| Supplier Quotation-shs_spq_total_iva | shs_spq_total_iva | Total IVA | Total VAT | Total IVA |
| Quotation-facelec_qt_total_iva | facelec_qt_total_iva | Total IVA | Total VAT | Total IVA |
| Sales Order-shs_so_total_iva | shs_so_total_iva | Total IVA | Total VAT | Total IVA |
| Delivery Note-shs_dn_total_iva | shs_dn_total_iva | Total IVA | Total VAT | Total IVA |
| Purchase Order-facelec_po_total_iva | facelec_po_total_iva | Total IVA | Total VAT | Total IVA |
| Purchase Receipt-facelec_pr_total_iva | facelec_pr_total_iva | Total IVA | Total VAT | Total IVA |
| Purchase Invoice-facelec_p_total_iva | facelec_p_total_iva | Total IVA | Total VAT | Total IVA |
| Sales Invoice-shs_total_iva_fac | shs_total_iva_fac | Total IVA Factura | Invoice Total VAT | Total IVA Factura |
| Customer-codigo_comprador | codigo_comprador | Codigo Comprador | Buyer Code | Código Comprador |
| Customer-codigo_consignatario_comprador | codigo_consignatario_comprador | Codigo Consignatario Comprador | Buyer Consignee Code | Código Consignatario Comprador |
| Company-codigo_exportador | codigo_exportador | Codigo Exportador | Exporter Code | Código Exportador |
| Purchase Invoice-other_tax_facelec | other_tax_facelec | Otros Impuestos Tabla | Other Taxes Table | Otros Impuestos Tabla |
| Sales Invoice-other_tax_facelec | other_tax_facelec | Otro Impuesto Tabla | Other Tax Table | Otro Impuesto Tabla |
