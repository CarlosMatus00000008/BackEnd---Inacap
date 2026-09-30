"""
Vistas del diario de viajes, separadas por operación CRUD:

    lectura.py       READ   → línea de tiempo, compartidos y detalle
    estadisticas.py  READ   → estadísticas de mis viajes
    crear.py         CREATE → nuevo viaje
    editar.py        UPDATE → editar viaje y cambio rápido de estado
    eliminar.py      DELETE → eliminar viaje (con confirmación)
    itinerario.py    agregar, marcar como realizadas y eliminar actividades del itinerario
    gastos.py        agregar y eliminar gastos de un viaje (se comparan con su presupuesto)
    fotos.py         subir y eliminar fotos de un viaje (Supabase Storage)
    compartir.py     enlaces privados para ver solo las fotos de un viaje (se envían por WhatsApp)

Las piezas comunes (permisos, guardado seguro, paginación) están en viajes/mixins.py.
"""
