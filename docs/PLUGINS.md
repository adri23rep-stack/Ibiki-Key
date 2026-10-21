# Plugins locales

Cada plugin vive en una carpeta dentro de la carpeta de datos `plugins` y necesita:

```text
mi_plugin/
  plugin.json
  plugin.py
```

Manifest mínimo:

```json
{
  "id": "mi_plugin",
  "name": "Mi plugin",
  "version": "1.0.0",
  "entry": "plugin.py"
}
```

Entrada mínima:

```python
def register(context):
    def ejecutar(value, options, phase, profile):
        if phase == "press":
            context.notify("info", str(value))

    context.register_action("aviso", "Mostrar aviso", ejecutar)
```

El tipo de acción resultante será `plugin.mi_plugin.aviso`. Copia `examples/plugins/sample_toast` a la carpeta de plugins para probar el sistema.

Los plugins corren con los mismos permisos que Ibiki Key. La aplicación valida su estructura, pero no puede garantizar que el código de terceros sea seguro.
