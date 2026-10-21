from __future__ import annotations


def register(context):
    def show_toast(value, options, phase, profile):
        if phase == "press":
            context.notify("info", str(value or "Hola desde un plugin"))

    context.register_action("show", "Mostrar aviso", show_toast)
