# Desinstalar Factura Electrónica

El primer comando elimina toda relación del bench con la aplicación. Con la bandera `--site`  podemos especificar el site de la aplicación.

```bash
bench --site site1.local uninstall-app factura_electronica
```

o

```bash
bench uninstall-app factura_electronica
```

Tras ejecutar el comando anterior, con `remove-app` elimina las carpetas, archivos relacionados a la aplicación 

```bash
bench --site site1.local remove-app factura_electronica
```



