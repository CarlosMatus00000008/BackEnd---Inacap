"""
Estadísticas de los viajes de una persona (solo los suyos, no los compartidos con ella).

«Visitado» = viaje completado o en progreso. Los planificados cuentan como pendientes.
Todo se calcula con consultas agregadas (Count, Sum, Max) para no traer viaje por viaje.
"""

from django.db.models import Count, Max, Q, Sum
from django.utils import timezone

from .models import Actividad, CategoriaGasto, Continente, EstadoViaje, Gasto, Pais, Viaje


def con_proporcion(filas, clave="total"):
    """Agrega «maximo» a cada fila para dibujar barras comparables (<progress max=… value=…>)."""
    maximo = max((fila[clave] for fila in filas), default=0)
    return [{**fila, "maximo": maximo} for fila in filas]


def calcular(usuario) -> dict:
    mis_viajes = Viaje.objects.de_usuario(usuario)
    visitados = mis_viajes.exclude(estado=EstadoViaje.PLANIFICADO)
    planificados = mis_viajes.planificados()

    resumen = mis_viajes.aggregate(
        total=Count("pk"),
        completados=Count("pk", filter=Q(estado=EstadoViaje.COMPLETADO)),
        en_progreso=Count("pk", filter=Q(estado=EstadoViaje.EN_PROGRESO)),
        planificados=Count("pk", filter=Q(estado=EstadoViaje.PLANIFICADO)),
    )

    # La duración depende de «hoy» en los viajes en progreso: se suma en Python.
    viajes_con_duracion = [viaje for viaje in visitados.select_related("pais") if viaje.duracion_dias]
    viaje_mas_largo = max(viajes_con_duracion, key=lambda viaje: viaje.duracion_dias, default=None)

    # «¿Cuándo fue la última vez que fui a…?»: una fila por país, del más reciente al más antiguo.
    ultima_vez = (
        Pais.objects.filter(viajes__in=visitados)
        .annotate(veces=Count("viajes"), ultima=Max("viajes__fecha_inicio"))
        .order_by("-ultima", "nombre")
    )
    paises_visitados = {pais.pk for pais in ultima_vez}

    nombres_continente = dict(Continente.choices)
    por_continente = [
        {"nombre": nombres_continente[fila["pais__continente"]], "total": fila["total"]}
        for fila in visitados.values("pais__continente").annotate(total=Count("pk")).order_by("-total")
    ]
    por_anio = [
        {"anio": fila["fecha_inicio__year"], "total": fila["total"]}
        for fila in mis_viajes.values("fecha_inicio__year").annotate(total=Count("pk")).order_by("-fecha_inicio__year")
    ]

    mis_gastos = Gasto.objects.filter(viaje__usuario=usuario)
    nombres_categoria = dict(CategoriaGasto.choices)
    gastos_por_categoria = [
        {"nombre": nombres_categoria[fila["categoria"]], "total": fila["total"]}
        for fila in mis_gastos.values("categoria").annotate(total=Sum("monto")).order_by("-total")
    ]

    actividades = Actividad.objects.filter(viaje__usuario=usuario).aggregate(
        total=Count("pk"), realizadas=Count("pk", filter=Q(realizada=True))
    )

    return {
        "resumen": resumen,
        "paises_visitados": len(paises_visitados),
        "continentes_visitados": len(por_continente),
        "dias_viajados": sum(viaje.duracion_dias for viaje in viajes_con_duracion),
        "viaje_mas_largo": viaje_mas_largo,
        "ultima_vez": ultima_vez,
        "por_anio": con_proporcion(por_anio),
        "por_continente": con_proporcion(por_continente),
        "total_gastado": sum(fila["total"] for fila in gastos_por_categoria),
        "gastos_por_categoria": con_proporcion(gastos_por_categoria),
        "actividades": actividades,
        "proximo_viaje": (
            planificados.filter(fecha_inicio__gte=timezone.localdate())
            .select_related("pais")
            .order_by("fecha_inicio")
            .first()
        ),
        "paises_pendientes": (
            Pais.objects.filter(viajes__in=planificados).exclude(pk__in=paises_visitados).distinct().order_by("nombre")
        ),
    }
