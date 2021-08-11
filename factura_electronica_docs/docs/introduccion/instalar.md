# Instalación

> Las versiones estables son:
>
> *  `version-12` para ERPNext/Frappe version-12 
> *  `version-13` para ERPNext/Frappe version-13

## Prerrequisitos

> Frappe + ERPNext

## Obtener aplicación

Desde la terminal de tu servidor de producción/desarrollo, desde el directorio `frappe-bench` clona la aplicación con el comando:

```bash
bench get-app --branch version-13 https://github.com/sihaysistema/factura_electronica_gt.git
```

Con la bandera `--branch [nombre-rama]` puedes especificar la rama que quieras clonar.

::: tip

La ultima versión estable es la rama `version-13`

:::

## Instala la aplicación

Ubicando en el directorio `frappe-bench` ejecuta:

```bash
bench install-app factura_electronica
```

### Ejecuta la migración, parches, reconstrucción de assets de factura electrónica

**Actualiza los parches:**

```bash
bench update --patch
```

**Migra los cambios a la base de datos**

En este paso se insertan los custom fields, datos por default que necesita el app.

```bash
bench migrate
```

**Reconstruye assets js/css**

```bash
bench build --app factura_electronica
```

**Reinicia el bench y limpia el cache**

```bash
bench restart && bench clear-cache
```

