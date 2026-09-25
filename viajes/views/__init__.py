"""
Vistas del diario de viajes, separadas por operación CRUD:

    lectura.py       READ   → línea de tiempo, compartidos y detalle
    crear.py         CREATE → nuevo viaje
    editar.py        UPDATE → editar viaje y cambio rápido de estado
    eliminar.py      DELETE → eliminar viaje (con confirmación)

Las piezas comunes (permisos, guardado seguro, paginación) están en viajes/mixins.py.
"""
