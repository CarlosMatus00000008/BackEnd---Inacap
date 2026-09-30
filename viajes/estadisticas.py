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


def dona_por_categoria(totales: dict) -> list[dict]:
    """
    Tramos del gráfico de torta de gastos, en el orden fijo de las categorías (cada una conserva
    el color que tiene en la barra del presupuesto). El círculo mide 100 de largo (radio 15,9155),
    así «largo» y «desfase» son directamente porcentajes. Los porcentajes mostrados se redondean
    por el método del resto mayor, para que siempre sumen 100.
    """
    gastado = sum(totales.values())
    if not gastado:
        return []
    filas = [(clave, etiqueta, totales[clave]) for clave, etiqueta in CategoriaGasto.choices if totales.get(clave)]
    exactos = [monto * 100 / gastado for *_, monto in filas]
    porcentajes = [int(exacto) for exacto in exactos]
    por_repartir = 100 - sum(porcentajes)
    for i in sorted(range(len(filas)), key=lambda i: exactos[i] - porcentajes[i], reverse=True)[:por_repartir]:
        porcentajes[i] += 1

    separacion = 0.6 if len(filas) > 1 else 0  # hueco del color del fondo entre tramos
    tramos, inicio = [], 0.0
    for (clave, etiqueta, monto), exacto, porcentaje in zip(filas, exactos, porcentajes, strict=True):
        largo = max(exacto - separacion, 0.1)
        tramos.append(
            {
                "clave": clave,
                "etiqueta": etiqueta,
                "nombre": etiqueta.split(" ", 1)[-1],  # sin el emoji, para el texto accesible
                "total": monto,
                "porcentaje": porcentaje,
                # Van como texto con punto decimal: se usan directo en los atributos del SVG.
                "largo": f"{largo:.3f}",
                "resto": f"{100 - largo:.3f}",
                "desfase": f"{(25 - inicio) % 100:.3f}",  # 25 = empezar arriba, a las 12
            }
        )
        inicio += exacto
    return tramos


def promedio_diario(mis_viajes) -> dict | None:
    """
    Gasto promedio por día = suma de gastos ÷ suma de días, solo de los viajes que tienen
    duración y gastos (así un viaje sin fechas completas o sin gastos no baja el promedio).
    """
    viajes = [
        viaje
        for viaje in mis_viajes.annotate(gastado=Sum("gastos__monto")).filter(gastado__gt=0)
        if viaje.duracion_dias
    ]
    dias = sum(viaje.duracion_dias for viaje in viajes)
    if not dias:
        return None
    return {"monto": round(sum(viaje.gastado for viaje in viajes) / dias), "viajes": len(viajes), "dias": dias}


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
    totales_por_categoria = dict(mis_gastos.values_list("categoria").annotate(total=Sum("monto")))

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
        "dona_gastos": dona_por_categoria(totales_por_categoria),
        "promedio_diario": promedio_diario(mis_viajes),
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
