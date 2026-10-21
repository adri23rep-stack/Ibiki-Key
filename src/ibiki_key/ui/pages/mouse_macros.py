from __future__ import annotations

from .macros import MacrosPage


class MouseMacrosPage(MacrosPage):
    def __init__(self, controller: object, bus: object):
        super().__init__(
            controller,
            bus,
            scope="mouse",
            page_title="Macros del mouse",
            page_subtitle=(
                "Graba movimientos, clics y ruedas; edita los tiempos y asigna la secuencia "
                "directamente a cualquier botón."
            ),
        )
