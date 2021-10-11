**es-GT:**

**Disponible para `version-13` de Frappe/ERPNext**

## App Factura Electronica

Aplicacion para la generacion de facturas electronicas en Guatemala, basado en el modulo de Cuentas y Almacén de ERPNext y el DocType de Factura de Ventas.

Requiere de un servicio contratado por separado para conectar a su API.

**en-US:**
## Electronic Invoice App
Electronic invoice generator for Guatemala, based on the Accounts and Stock modules, plus the Sales Invoice DocType.

A hired service is required to connect to their API.

For installation details, features and more information please visit the [wiki](https://github.com/sihaysistema/factura_electronica_gt/wiki)

## Features

## Características
1. Envío de datos de Factura de Venta validada a servicio de facturación electronica.  Envía todos los campos requeridos por la SAT.
2.  Estima automaticamente el valor de cualquier otro impuesto unitario como: IDP, Tabaco, Licor, Cemento, Timbres, etc. y realiza los calculos automáticos, totalizando el IVA y los demás impuestos y colocandolos en la tabla de impuestos existente de ERPNext con la cuenta contable designada para cada impuesto, en cada Producto (Artículo o Item) del módulo de Almacén.
3. El impuesto unitario se configura en cada Producto, indicando el valor por Unidad de Medida, y la cuenta contable a donde desea cargar el impuesto. Si es un producto para la venta, indique una cuenta de Impuesto por Pagar (Pasivo).  Si es un producto para la compra, indique la cuenta de Gasto del impuesto (Cuentas de Gastos). Al cargar el articulo en la factura de venta, automáticamente estimará el valor del impuesto, tomando en cuenta ese valor previo a calcular el IVA.
4. Para cumplir con los codigos de Unidades de Medida correctos, es necesario modificar la Unidad de Medida presente en su instalación de ERPNext para colcoar el código de tres letras en mayúscula. Por ej.  "Unidad" ahora le aparece un campo en donde debe colocar "UNI".
5. Automáticamente captura el **cae** o Validador Digital, que es un número único que le dá validez legal a la factura. El programa revisa la existencia de una transacción de envio y recepcion de datos.
6. En caso de no poder generar la factura electrónica, el programa le indica cual es el error para determinar si es de comunicacion, del software interno, o del proveedor de servicio.
7. Agrega una sección a la Factura de Venta que totaliza el IVA de la cantidad de articulos en la factura, a tres categorias separadas requeridas para eventual uso en el Libro de Compras de la SAT.

**es-GT**
## Instalación

**en-US:**
## Installation
Currently, this application is only available for self-deployed instances of ERPNext. Source code will be proposed for merging into the core in a more generalized manner for supporting other countries regional requirements by mid-jun 2018.



## Electronic Invoice App
#### License

LGPL V3
=======

# factura_electronica_gt

Electronic Invoice support for Guatemala - Factura Electronica de Guatemala


