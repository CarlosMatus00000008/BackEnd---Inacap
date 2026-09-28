"""
Vistas del diario de viajes, separadas por operación CRUD:

    lectura.py       READ   → línea de tiempo, compartidos y detalle
    crear.py         CREATE → nuevo viaje
    editar.py        UPDATE → editar viaje y cambio rápido de estado
    eliminar.py      DELETE → eliminar viaje (con confirmación)
    gastos.py        agregar y eliminar gastos de un viaje (se comparan con su presupuesto)
    fotos.py         subir y eliminar fotos de un viaje (Supabase Storage)

Las piezas comunes (permisos, guardado seguro, paginación) están en viajes/mixins.py.
"""
