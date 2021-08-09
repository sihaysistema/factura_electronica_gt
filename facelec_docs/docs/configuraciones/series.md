## Configuración de series para facturas (Naming Series)

En la ruta `/app/naming-series/Naming%20Series` o si ingresas **secuencias e identificadores** en la barra de búsqueda:

<img src="../.vuepress/public/images/naming_series1.png" alt="naming_series1" style="zoom:;" />

::: tip

Las series se usan como secuenciadores temporales para sus documentos, hasta que se generan como electrónicos y la serie se cambia por la otorgada por la SAT

:::

En el campo **`Seleccione el tipo de transacción`** seleccione el doctype al cual le deseas una serie, puede ser para **Factura de venta (Sales Invoice)**  o **Factura de compra (Purchase Invoice)**

::: tip

Cada `#` en la serie significa hasta que numero se incrementara, ejemplo; la serie `FEL-.######` puede ir desde **FEL-.000000** a  **FEL-.999999**

:::

**Ejemplo:**

- FEL-.###### -> la puedes usar para Factura electrónicas normales
- FEL-EXPORT-.######  -> para factura electrónica de exportación
- FEL-NOTA-CRED=.######  -> para notas de crédito electrónicas
- FEL-FAC-CAMB=.######  -> para facturas cambiarias electrónicas

<img src="../.vuepress/public/images/naming_series2.png" alt="naming_series2" style="zoom:100%;" />