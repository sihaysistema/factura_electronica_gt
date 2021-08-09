# App Factura Electrónica

Aplicación para la generación de facturas electrónicas en Guatemala, basado en el modulo de Cuentas y Almacén de ERPNext y el DocType de Factura de Ventas.

Requiere de un servicio contratado por separado para conectar a su API.

https://github.com/sihaysistema/factura_electronica_gt

## Características

1. Envío de datos de Factura de Venta validada a servicio de facturación electrónica. Envía todos los campos requeridos por la SAT.
2. Estima automáticamente el valor de cualquier otro impuesto unitario como: IDP, Tabaco, Licor, Cemento, Timbres, etc. y realiza los cálculos automáticos, totalizando el IVA y los demás impuestos y colocándolos en la tabla de impuestos existente de ERPNext con la cuenta contable designada para cada impuesto, en cada Producto (Artículo o Item) del módulo de Almacén.
3. El impuesto unitario se configura en cada Producto, indicando el valor por Unidad de Medida, y la cuenta contable a donde desea cargar el impuesto. Si es un producto para la venta, indique una cuenta de Impuesto por Pagar (Pasivo). Si es un producto para la compra, indique la cuenta de Gasto del impuesto (Cuentas de Gastos). Al cargar el articulo en la factura de venta, automáticamente estimará el valor del impuesto, tomando en cuenta ese valor previo a calcular el IVA.
4. Para cumplir con los códigos de Unidades de Medida correctos, es necesario modificar la Unidad de Medida presente en su instalación de ERPNext para colocar el código de tres letras en mayúscula. Por ej. "Unidad" ahora le aparece un campo en donde debe colocar "UNI".
5. Automáticamente captura el **cae** o Validador Digital, que es un número único que le da validez legal a la factura. El programa revisa la existencia de una transacción de envió y recepción de datos.
6. En caso de no poder generar la factura electrónica, el programa le indica cual es el error para determinar si es de comunicación, del software interno, o del proveedor de servicio.
7. Agrega una sección a la Factura de Venta que totaliza el IVA de la cantidad de artículos en la factura, a tres categorías separadas requeridas para eventual uso en el Libro de Compras de la SAT.
