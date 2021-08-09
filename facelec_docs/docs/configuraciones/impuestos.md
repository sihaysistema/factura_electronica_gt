



# Configuración de tablas de impuestos

::: tip

Esta configuración es necesaria para llevar el registro de impuestos aplica para ventas y compras

::: 

> Si generará facturas con impuesto IVA 0, cree una tabla con impuesto 12 cambiando el valor a 0

Puedes encontrarlo en la ruta `/app/sales-taxes-and-charges-template` o puedes ingresar en la barra de búsqueda:

<img src="../.vuepress/public/images/impuestos1.png" alt="impuestos1" style="zoom:100%;" />



También puede ingresar a las tablas de impuesto desde compañía:

![impuestos2](../.vuepress/public/images/impuestos2.png)



## Tabla de impuesto para la venta

::: tip

Si ya existe una plantilla por default elimínela y cree una nueva.

:::

Desde el doctype plantilla de impuestos sobre ventas, cree una nueva plantilla, ejemplo:

<img src="../.vuepress/public/images/impuestos4.png" alt="impuestos4" style="zoom:100%;" />

Y marque los valores como se indican en la imagen y guarde:

<img src="../.vuepress/public/images/impuestos5.png" alt="impuestos5" style="zoom:100%;" />

Ahora agregue la descripción del impuesto como se muestra en la imagen:

::: tip

Si la tabla es para facturas exentas de IVA en el campo **Nombre Unidad Gravable** busque el valor Tasa 0 y en el campo **Precio** escriba 0.

:::

<img src="../.vuepress/public/images/iva1.png" alt="iva1" style="zoom:100%;" />

Haga click fuera del dialogo y guarde, quedando algo así:

<img src="../.vuepress/public/images/iva2.png" alt="iva2" style="zoom:100%;" />

::: tip

En el campo nombre puede ingresar el que desee.

:::

## Tabla de impuesto para la compra

El procedimiento es el mismo que para la venta.
