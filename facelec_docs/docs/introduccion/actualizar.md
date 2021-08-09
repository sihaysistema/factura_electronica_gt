# Actualización app

::: tip
Recuerda estar pendiente a los [releases](https://github.com/sihaysistema/factura_electronica_gt/releases) y a las instrucciones de esta wiki
:::

Si quieres actualizar específicamente el app, ve al directorio `frappe-bench/apps/factura_electronica`  y alli ejecuta:

```bash
git fetch --all
```
y
```bash	
git pull --all
```

**Migra y reconstruye**

```bash
bench migrate && bench build --app factura_electronica
```

::: tip

SI DESEAS ACTUALIZAR TODO DE ERPNEXT/FRAPPE Y CUSTOM APPS

:::

> Hace un `git reset --hard` en cada repositorio y luego actualiza todas las apps

```bash
bench update --reset
```



