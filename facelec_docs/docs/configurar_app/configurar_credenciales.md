# Credenciales y configuración de escenarios

En el modulo Factura Electrónica en la sección `Configuración` encontrara la opción **Configuración Factura Electrónica** puede crear múltiples configuraciones se tomara en cuenta solamente aquella configuración que se encuentre validada.

<img src="../.vuepress/public/images/modulo_facelec.png" alt="modulo_facelec" style="zoom:100%;" />

## Paso 1 - Cree una nueva configuración

E ingrese los valores que se describen:

| Campo                 | Descripción                                                  |
| --------------------- | ------------------------------------------------------------ |
| Regimen               | Por default esta configurado para FEL                        |
| URL descarga pdf      | URL proporcionada por INFILE, esta url se usa para redireccionar al documento en PDF electrónico recién generado. |
| Compañía              | Seleccione la compañía que usara el servicio                 |
| Usar datos de prueba  | Márquelo si usara las credenciales de prueba                 |
| Nombre empresa prueba | Si marco el campo anterior, aparecerá este campo, ingrese el nombre de empresa prueba proporcionado por INFILE |

### Activación de generadores electrónicos

Marque los tipos de documentos que desea generar.

<img src="../.vuepress/public/images/generadores.png" alt="generadores" style="zoom:100%;" />

Guarde el documento antes de continuar.

## Campos generales

| Campo            | Descripción                                                  |
| ---------------- | ------------------------------------------------------------ |
| Correo Copia     | En caso el cliente/proveedor no dio un correo electrónico se usa este correo como respaldo para enviar la url del documento electrónico generado. |
| Llave PFX        | Llave proporcionada por INFILE                               |
| Es Anulación     | N = no                                                       |
| Alias            | Alias proporcionado por INFILE                               |
| URL Firma        | URL proporcionada por INFILE                                 |
| URL DTE          | URL proporcionada por INFILE                                 |
| URL de Anulación | URL proporcionada por INFILE                                 |
| Llave WS         | Llave proporcionada por INFILE                               |
| Afiliación IVA   | Seleccione su afiliación                                     |

## PASO 2 - Configuración series para escenarios venta y compra

En el mismo doctype encontrara la sección `CONFIGURACION SERIES FEL` **cada fila aplica para una serie y escenario**

### Escenario Factura FEL

::: tip

Cada vez que cree una factura de venta usando la serie aquí configurada, tras validar su factura de venta se habilitara un botón para generar factura electrónica.

:::

Ver video ejemplo

| Campo                                | Descripción                                                  |
| ------------------------------------ | ------------------------------------------------------------ |
| Serie                                | Seleccione la serie que desea configurar para factura electrónica |
| Tipo Documento                       | Seleccione el tipo de documento electrónico que generara con la serie ya seleccionada |
| Serie SAT                            | Seleccione la abreviatura relacionada con Tipo Documento solo aplica para el reporte AsisteLibros |
| Código INCOTERM                      | Seleccione el código si es una serie para exportaciones      |
| Tipo Frase                           | Seleccione el tipo de serie que aplica. Consulte con su contador o financiero para esta selección. |
| Código Escenario                     | Seleccione el código de escenario que aplica. Consulte con su contador o financiero para esta selección. |
| Tipo Frase Factura Exportación       | Seleccione la frase que aplique para exportaciones. Consulte con su contador o financiero para esta selección. |
| Código Escenario Factura Exportación | Seleccione el código de escenario que aplica. Consulte con su contador o financiero para esta selección. |
| Tipo Frase Factura Exenta            | NOTA: AUN EN DESARROLLO. Seleccione el tipo de frase para facturas exentas. Consulte con su contador o financiero para esta selección. |
| Código Escenario Factura Exenta      | NOTA: AUN EN DESARROLLO. Seleccione el código de escenario que aplica. Consulte con su contador o financiero para esta selección. |

**Ejemplo:**

<img src="../.vuepress/public/images/config1.png" alt="config1" style="zoom:100%;" />

### Escenario Nota de Crédito FEL

::: tip

Cada vez que cree una nota de crédito usando la serie aquí configurada tras validar se habilitara el botón para generar la nota de crédito electrónica

::: 

**Ejemplo**

<img src="../.vuepress/public/images/config2.png" alt="config2" style="zoom:100%;" />

### Escenario Factura Cambiaria FEL

::: tip

Cada vez que cree una factura cambiaria usando la serie aquí configurada tras validar se habilitara el botón para generar la factura cambiaria electrónica

::: 

**Ejemplo**

<img src="../.vuepress/public/images/config3.png" alt="config3" style="zoom:100%;" />

### Escenario Factura Exportación FEL

::: tip

Cada vez que cree una factura venta usando la serie aquí configurada tras validar se habilitara el botón para generar la factura exportación electrónica

::: 

Es importante que ingrese su código INCOTERM y Frases para factura exportación.

**Ejemplo**

<img src="../.vuepress/public/images/config4.png" alt="config4" style="zoom:100%;" />

::: tip

Recuerde guardar cada vez que agregue una fila, si tiene problemas con alguna fila elimínela y vuelvala a crear

:::

Tras ingresar todas las serie que necesite quedara algo así:

![config5](../.vuepress/public/images/config5.png)

Ahora en la sección **Configuración series para facturas de compra**

### Escenario Nota de debito

> Aplica para el doctype Factura de compra (Purchase Invoice)

::: tip

Cada vez que cree una nota de debito usando la serie aquí configurada tras validar se habilitara el botón para generar la nota de debito electrónica

::: 

**Ejemplo:**

<img src="../.vuepress/public/images/config6.png" alt="config6" style="zoom:100%;" />

### Escenario Factura Especial

> Aplica para el doctype Factura de compra (Purchase Invoice)

::: tip

Cada vez que cree una factura compra usando la serie aquí configurada tras validar se habilitara el botón para generar la factura especial electrónica

::: 

**Ejemplo:**

<img src="../.vuepress/public/images/config7.png" alt="config7" style="zoom:100%;" />

## Paso 3 - Otras Configuraciones

En el mismo doctype encontrara esta sección, seleccione la opción que desee

<img src="../.vuepress/public/images/config8.png" alt="config8" style="zoom:100%;" />