# Integración FEL para boletos de Auto Safari Chapín

Documento de la issue [#349](https://github.com/sihaysistema/factura_electronica_gt/issues/349). El texto de las secciones 1 a 7 se contrastó con `production-v16` en `a4e564aa` (versión 8.0.4). No está verificado en el bench de autosafarichapin: la API pública de ese sitio indica que `factura_electronica` todavía no está instalada.

Flujo aprobado: borrador de Sales Invoice, emisión de boletos (códigos en la descripción de cada línea), submit, firma FEL y envío al cliente del PDF firmado más un PDF con QR que muestre serie y número FEL. Hace falta firmar cada venta, en web y en mostrador (`is_pos=1`, efectivo o tarjeta), y saber cuándo la factura quedó firmada.

## 1. ¿Firma síncrona o asíncrona?

La firma no ocurre en el `on_submit` de una Sales Invoice normal. En `factura_electronica/hooks.py`, `doc_events` de Sales Invoice es:

- `on_submit`: `factura_electronica.api.pos_calculations`, `factura_electronica.api.generate_access_number`, `factura_electronica.buscar_nit.buscar_nombre`
- `after_insert`: `factura_electronica.api.generate_access_number` (número de acceso de factura cambiaria; no firma)

La firma para un integrador en el mismo bench es `factura_electronica.fel_api.api_interface(invoice_code, naming_series)`. Es síncrona: no usa `frappe.enqueue`. En éxito devuelve `(True, serie_para_factura)`. Ese segundo valor es el nombre nuevo de la Sales Invoice (serie SAT sin `*` más el número). Lo obtiene leyendo `Envio FEL.serie_para_factura` donde el nombre del Envio FEL es el UUID. En falla devuelve `(False, mensaje)` y además llama `frappe.msgprint`.

`api_interface` no tiene `@frappe.whitelist()`. Otra app de Frappe debe llamarla en Python, en el mismo proceso. El método expuesto a `frappe.call` es `factura_electronica.fel_api.api_facelec(invoice_name, naming_serie)`.

`api_facelec` también es síncrono. En éxito devuelve `{"status": "OK", "id_factura": invoice_name, "uuid": uuid}`. `id_factura` es el nombre que se le pasó (el original), no el nombre ya renombrado. `uuid` es el UUID de la autorización. En falla de negocio devuelve `{"status": "NO PROCESADO", "id_factura": invoice_name, "msj": mensaje}`. Si hay una excepción no capturada dentro del `try`, devuelve `{"status": "ERROR", "id_factura": invoice_name, "msj": ...}`.

Excepción de mostrador: si `Sales Invoice.is_pos=1` y `Configuracion Factura Electronica.factura_electronica_fel_pos=1`, `pos_calculations` llama `api_interface(doc.name, sales_invoice.naming_series)` dentro del `on_submit`. También es síncrono. Para el parque (boletos antes de firmar) ese check debe quedar apagado y `api_interface` debe llamarse después del submit.

`pos_calculations` solo entra a esa rama si `is_pos` es verdadero, y lo primero que hace ahí es leer `sales_invoice.taxes[0]`. Una factura POS sin fila de impuestos lanza excepción y puede impedir el submit. Con el check apagado esa llamada a `api_interface` no ocurre.

Requisitos reales de `generate_electronic_invoice` (`factura_electronica/fel_api.py`):

- Una `Configuracion Factura Electronica` de la compañía con `docstatus=1` (`validate_configuration` → `factura_electronica.utils.fel_config.get_active_config_for_company`).
- La `naming_series` de la factura presente en la tabla hija `Configuracion Series FEL` de esa configuración.

El campo `factura_venta_fel` no lo revisa `api_interface`. Solo lo revisa `factura_electronica.fel_api.is_valid_to_fel`, que decide si el escritorio muestra el botón. El XML manda en `@Tipo` el valor de `Configuracion Series FEL.tipo_documento` de esa serie (`ElectronicInvoice.general_data` en `factura_electronica/fel/fel.py`). Para un boleto normal esa fila debe decir `FACT`. La función no rechaza otro valor.

`generate_electronic_invoice` tampoco revisa `docstatus`. El flujo del parque debe enviar la factura antes de firmar; la función, por sí sola, no se niega a un borrador.

## 2. Dónde quedan serie, número y UUID; PDF

Se crea un `Envio FEL` cuyo nombre es el UUID (`autoname` `field:uuid` en `envio_fel.json`). Campos que llena `ElectronicInvoice.save_answers`:

- `uuid`, `serie`, `numero`
- `serie_factura_original`: nombre de la Sales Invoice antes de firmar
- `serie_para_factura`: serie SAT sin `*` concatenada con el número (el mismo texto con el que se renombra la factura)
- `xml_certificado`: el XML armado para la firma (`__xml_string` de `sign_invoice`), no un PDF
- `certificador`: lo escribe `factura_electronica.utils.fel_config.stamp_envio_fel`
- `status`: el texto `Valid`
- `tipo_documento`: el texto `Factura Electronica`

En la Sales Invoice, `upgrade_records` hace un `UPDATE` SQL: el `name` pasa a ser serie sin `*` más número (no el UUID); `numero_autorizacion_fel` queda con el UUID; `serie_original_del_documento` queda con el nombre original. La serie y el número sueltos no están en la factura. Están en `Envio FEL.serie` y `Envio FEL.numero`.

`factura_electronica.utils.rename_invoice.rename_invoice_links` actualiza hijas de la factura y enlaces de ledger estándar (pagos, stock, asientos, retenciones GT de la propia app, entre otros). No recorre doctypes ajenos. Los boletos de `park_entry` no se renombran solos: el integrador debe guardar el nombre devuelto por `api_interface`.

PDF oficial de INFILE, el mismo que va dentro del QR (`factura_electronica/fel/qrcode.py` y los botones de `sales_invoice.js`):

`https://report.feel.com.gt/ingfacereport/ingfacereport_documento?uuid=<numero_autorizacion_fel>`

En formatos de impresión, Jinja puede usar `create_fel_svg_qrcode(doc.numero_autorizacion_fel)` o el alias `fel_qr_svg`. Están registrados en `hooks.py`. El único formato que trae la app es `POS Si Hay Sistema` (`doc_type` Sales Invoice). Imprime `doc.name` como número de recibo y el UUID en texto (`doc.numero_autorizacion_fel`). No llama a las funciones del QR y no arma un PDF de QR con serie y número en cada página. Ese formato lo tiene que crear el sitio o la app del parque. Después de la firma, `doc.name` ya es la serie más el número.

## 3. Señal de «firmada»

No hay hook ni `publish_realtime` al terminar la firma. `upgrade_records` actualiza la factura con SQL, así que `on_update` y `on_update_after_submit` de Sales Invoice no corren.

Lo usable hoy: llamar `api_interface` y usar la tupla de retorno. Después se puede leer `Envio FEL` por `name` igual al UUID, por `serie_para_factura` o por `uuid`.

Otra vía: `doc_events` `after_insert` de `Envio FEL`. En ese momento `save_answers` ya guardó el envío y `upgrade_records` todavía no renombró la factura, así que el enlace sigue siendo `serie_factura_original`.

Sigue pendiente, y no está en este código, un hook opcional `on_fel_signed` que corra después del renombrado.

## 4. Falla y reintento

Si la firma falla, `api_interface` devuelve `(False, mensaje)`. La Sales Invoice sigue enviada, con el mismo nombre y sin `numero_autorizacion_fel`. No hace falta cancelarla para reintentar. `Envio FEL` se inserta en `save_answers`, que corre dentro de `response_validator` solo cuando INFILE respondió bien. Un rechazo de SAT no crea ese documento.

Esta ruta no llama `frappe.log_error`. El `log_error` de `sign_invoice` está comentado. El mensaje vuelve en la tupla y, en `api_interface`, también en `msgprint`.

Reintento: volver a llamar `api_interface` con el mismo nombre y la misma serie. `check_invoice_records` busca `Envio FEL` por `serie_para_factura` igual al nombre que se le pasa. Después de un éxito, ese nombre ya es el nombre nuevo, así que un segundo intento con el nombre nuevo se detiene.

Riesgo: si SAT certificó y `upgrade_records` falló al renombrar, el `Envio FEL` ya existe con `serie_para_factura` igual al nombre nuevo y `serie_factura_original` igual al nombre viejo. Reintentar con el nombre original no encuentra esa fila y puede pedir otra certificación. La guarda no mira `serie_factura_original`. Endurecerla queda pendiente de aprobación.

## 5. POS Invoice

No se puede firmar una POS Invoice de forma confiable. `ElectronicInvoice.sender` lee `Sales Invoice` por el nombre que recibe. Si ese nombre no es una Sales Invoice, `build_invoice` responde que no encontró la factura.

`factura_electronica/pos_fel_api.py` tiene su propio `api_interface` (ese sí está en whitelist) y un `is_valid_to_fel` que contempla `POS Invoice`, pero igual instancia `ElectronicInvoice` y por lo tanto busca una Sales Invoice. Además ERPNext, al cerrar la caja, consolida las POS Invoice en una Sales Invoice: un FEL sobre esa consolidación sería uno por cierre, no uno por venta.

Para el mostrador hay que usar Sales Invoice con `is_pos=1`, no la pantalla POS Invoice de ERPNext tal como está.

## 6. Sales Invoice con is_pos=1

Se firma con la misma clase `ElectronicInvoice` que una factura normal. El constructor del XML no lee la tabla de pagos. El total sale de `grand_total` y las líneas. Efectivo, tarjeta y vuelto no entran al XML.

## 7. Consumidor final (CF)

El campo `Customer.nit_face_customer` tiene default `C/F`. La Sales Invoice copia ese valor con `fetch_from` `customer.nit_face_customer` hacia `Sales Invoice.nit_face_customer`. El XML de `ElectronicInvoice.receiver` lee el campo de la factura, no el del cliente directamente. Si el texto, en mayúsculas, es `C/F`, quita `/` y `-` y lo pasa a mayúsculas: `IDReceptor` queda `CF`.

`NombreReceptor` lo arma `factura_electronica.utils.receptor_name.nombre_receptor_for_row`: `nombre_segun_sat` si tiene texto, si no `Sales Invoice.customer_name`, si no `Customer.customer_name`. No emite el texto `None`.

La app no impide un CF por monto. Un total alto, por ejemplo a partir de Q2,500, puede rechazarlo SAT aunque la app haya armado el XML.

## Correcciones respecto a la issue 349

- `api_interface` no es un método whitelist. La llamada de navegador o `frappe.call` es `api_facelec`. `api_interface` es para Python en el mismo sitio.
- El éxito de `api_interface` es `(True, serie_para_factura)`, el nombre nuevo. El UUID es el `name` del `Envio FEL`, no el segundo elemento de esa tupla.
- El éxito de `api_facelec` usa `status` `OK` y deja en `id_factura` el nombre original. La falla usa `NO PROCESADO` o `ERROR`, no un booleano.
- `factura_venta_fel=1` no es requisito de `api_interface`. Es requisito del botón del escritorio (`is_valid_to_fel`). `@Tipo` sale de `Configuracion Series FEL.tipo_documento`; la función no comprueba que sea `FACT`.
- La firma directa no comprueba que la factura esté enviada.
- Con `factura_electronica_fel_pos` encendido, una POS sin impuestos puede romper el `on_submit` en `taxes[0]` antes de firmar.
- `Envio FEL.status` se guarda como `Valid`. `xml_certificado` es el XML de la petición, no el PDF.
- El formato `POS Si Hay Sistema` muestra el UUID en texto y no genera el QR. Las funciones Jinja existen, pero ese formato no las llama.
- El NIT que viaja al XML es `Sales Invoice.nit_face_customer`. El default `C/F` está en el cliente y se copia a la factura.

## Integration API summary

Verified against `production-v16` at `a4e564aa` (app version 8.0.4). This is not a live check of erp.autosafarichapin.com.

Sign one submitted Sales Invoice per sale. Do not sign ERPNext POS Invoice documents. For the counter, use a Sales Invoice with `is_pos=1` and leave `Configuracion Factura Electronica.factura_electronica_fel_pos` unchecked, then call the signer after tickets are written into the line descriptions.

Server-side call, same site process, not whitelisted:

`factura_electronica.fel_api.api_interface(invoice_code, naming_series)`

- Success: `(True, new_invoice_name)`. `new_invoice_name` is SAT series with `*` removed, plus the DTE number. It matches `Envio FEL.serie_para_factura` and the renamed Sales Invoice `name`.
- Failure: `(False, message)`. The invoice stays submitted under the old name and `numero_autorizacion_fel` stays empty. Call again with the same arguments to retry.
- The function also calls `frappe.msgprint`. Use the return value, not the desk message.

Whitelisted call for `frappe.call`:

`factura_electronica.fel_api.api_facelec(invoice_name, naming_serie)`

- Success: `{status: "OK", id_factura: <original name>, uuid: <authorization UUID>}`.
- Business failure: `{status: "NO PROCESADO", id_factura, msj}`.
- Unexpected exception: `{status: "ERROR", id_factura, msj}`.

Read the signed result from `Envio FEL` (`autoname` is `field:uuid`):

| Field | Meaning |
| --- | --- |
| `name` / `uuid` | SAT authorization UUID |
| `serie` | SAT series, as returned |
| `numero` | DTE number |
| `serie_factura_original` | Sales Invoice name before rename |
| `serie_para_factura` | New Sales Invoice name |
| `status` | `Valid` after a successful SAT response |
| `numero_autorizacion_fel` on Sales Invoice | Same UUID, written by SQL |

Official PDF and QR target:

`https://report.feel.com.gt/ingfacereport/ingfacereport_documento?uuid=<numero_autorizacion_fel>`

Print-format Jinja helpers, registered in `hooks.py`: `create_fel_svg_qrcode(authorization_number)` and `fel_qr_svg(authorization_number)` in `factura_electronica.fel.qrcode`.

There is no `on_fel_signed` hook and no realtime event. `upgrade_records` renames the invoice with SQL, so Sales Invoice update hooks do not run. `rename_invoice_links` does not update `park_entry` ticket records. Store the name returned by `api_interface`.

`check_invoice_records` blocks a second call only when `Envio FEL.serie_para_factura` equals the name you pass. A retry with the original name is not blocked if SAT already certified and the rename failed.

Consumer final: `Customer.nit_face_customer` defaults to `C/F`, copied onto `Sales Invoice.nit_face_customer`. The XML `IDReceptor` becomes `CF`. Receiver name order is `nombre_segun_sat`, then `customer_name` on the invoice, then `Customer.customer_name`. The app does not block CF by amount.
