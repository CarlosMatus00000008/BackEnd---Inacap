"""READ: consultar viajes (línea de tiempo, compartidos y detalle)."""

from collections import defaultdict
from decimal import Decimal
from itertools import groupby

from django.conf import settings
from django.db.models import Count, Q, Sum
from django.utils import timezone
from django.views.generic import DetailView, ListView

from ..forms import ActividadForm, CompartirFotosForm, FiltroViajesForm, FotosForm, GastoForm
from ..mixins import AccesoMixin, PaginacionTolerante
from ..models import Actividad, CategoriaGasto, EstadoViaje, FotoViaje, Gasto, Pais, Viaje
from ..monedas import nombre_moneda
from .itinerario import dia_sugerido


class LineaTiempoView(AccesoMixin, PaginacionTolerante, ListView):
    """Línea de tiempo de MIS viajes, del más reciente al más antiguo, con filtros y paginación."""

    permission_required = "viajes.view_viaje"
    template_name = "viajes/linea_tiempo.html"
    context_object_name = "viajes"
    paginate_by = 8

    def get_queryset(self):
        mis_viajes = Viaje.objects.de_usuario(self.request.user)
        anios = mis_viajes.dates("fecha_inicio", "year", order="DESC")
        self.filtros = FiltroViajesForm(self.request.GET or None, anios=[fecha.year for fecha in anios])
        consulta = self.filtros.filtrar(mis_viajes.con_resumen())
        return consulta.order_by("-fecha_inicio", "-creado")

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        mis_viajes = Viaje.objects.de_usuario(self.request.user)
        contexto["filtros"] = self.filtros
        contexto["paises_mapa"] = self.paises_mapa(mis_viajes)
        contexto["paises_visitados"] = len(contexto["paises_mapa"])
        contexto["total_paises"] = Pais.objects.count()
        contexto["proximo_viaje"] = (
            mis_viajes.planificados().filter(fecha_inicio__gte=timezone.localdate()).order_by("fecha_inicio").first()
        )
        contexto["viaje_actual"] = mis_viajes.en_progreso().first()
        contexto["resumen"] = mis_viajes.aggregate(
            total=Count("pk"),
            completados=Count("pk", filter=Q(estado=EstadoViaje.COMPLETADO)),
            en_progreso=Count("pk", filter=Q(estado=EstadoViaje.EN_PROGRESO)),
            pendientes=Count("pk", filter=Q(estado=EstadoViaje.PLANIFICADO)),
        )
        return contexto

    @staticmethod
    def paises_mapa(mis_viajes):
        """
        Países de viajes completados o en progreso: se cuentan y se pintan en el mapa mundi.
        Cada país lleva sus viajes (del más reciente al más antiguo) para la tarjeta que se
        muestra al pasar el mouse.
        """
        visitados = (
            mis_viajes.exclude(estado=EstadoViaje.PLANIFICADO)
            .annotate(gastado=Sum("gastos__monto"))
            .order_by("-fecha_inicio")
        )
        por_pais = defaultdict(list)
        for viaje in visitados:
            por_pais[viaje.pais_id].append(viaje)
        paises = list(Pais.objects.filter(pk__in=por_pais))
        for pais in paises:
            pais.viajes_mapa = por_pais[pais.pk]
        return paises


class CompartidosView(AccesoMixin, PaginacionTolerante, ListView):
    """Viajes que otras personas compartieron conmigo (solo lectura)."""

    permission_required = "viajes.view_viaje"
    template_name = "viajes/compartidos.html"
    context_object_name = "viajes"
    paginate_by = 8

    def get_queryset(self):
        return Viaje.objects.compartidos_con(self.request.user).con_resumen().order_by("-fecha_inicio")


class ViajeDetalleView(AccesoMixin, DetailView):
    """
    Detalle de un viaje: fechas, estado, notas, itinerario, presupuesto y gastos, fotos y con quién se comparte.
    Dueño y compartidos pueden verlo; solo el dueño ve los formularios para modificarlo.
    """

    permission_required = "viajes.view_viaje"
    template_name = "viajes/viaje_detalle.html"
    context_object_name = "viaje"

    def get_queryset(self):
        return Viaje.objects.visibles_para(self.request.user).con_resumen()

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        viaje = self.object
        contexto.update(
            es_propietario=viaje.es_de(self.request.user),
            compartido_con=viaje.compartido_con.order_by("username"),
            opciones_estado=[(valor, etiqueta, Viaje.ICONOS_ESTADO[valor]) for valor, etiqueta in EstadoViaje.choices],
            **self.itinerario(viaje),
            fotos=viaje.fotos.all(),
            maximo_fotos=FotoViaje.MAXIMO_POR_VIAJE,
            fotos_habilitadas=settings.FOTOS_HABILITADAS,
            **self.resumen_gastos(viaje),
        )
        if contexto["es_propietario"]:
            contexto["actividad_form"] = ActividadForm(
                instance=Actividad(viaje=viaje), initial={"fecha": dia_sugerido(viaje)}
            )
            contexto["gasto_form"] = GastoForm(instance=Gasto(viaje=viaje))
            contexto["fotos_form"] = FotosForm(viaje=viaje)
            contexto["compartir_form"] = CompartirFotosForm()
        return contexto

    @staticmethod
    def itinerario(viaje):
        """Actividades agrupadas por día: [{"fecha", "numero", "actividades"}, …]."""
        actividades = list(viaje.actividades.all())
        dias = [
            {"fecha": fecha, "numero": (fecha - viaje.fecha_inicio).days + 1, "actividades": list(grupo)}
            for fecha, grupo in groupby(actividades, key=lambda actividad: actividad.fecha)
        ]
        return {
            "itinerario": dias,
            "total_actividades": len(actividades),
            "actividades_realizadas": sum(actividad.realizada for actividad in actividades),
        }

    @staticmethod
    def resumen_gastos(viaje):
        gastos = list(viaje.gastos.all())
        total = sum(gasto.monto for gasto in gastos)
        resumen = {
            "gastos": gastos,
            "total_gastado": total,
            **tramos_por_categoria(gastos, viaje.presupuesto),
            "gastos_en_monedas": gastos_en_monedas(gastos, viaje.presupuesto),
        }
        if viaje.presupuesto:
            saldo = viaje.presupuesto - total
            resumen.update(
                saldo=max(saldo, 0),
                exceso=max(-saldo, 0),
                porcentaje_usado=round(total * 100 / viaje.presupuesto),
            )
        return resumen


def tramos_por_categoria(gastos, presupuesto):
    """
    La barra del presupuesto, en tramos de color por categoría (siempre en el mismo orden,
    así cada categoría conserva su color). El 100 % es el presupuesto, o lo gastado si se
    pasó (o si no hay presupuesto); en ese caso «limite» marca dónde termina el presupuesto.
    Las posiciones van como texto con punto decimal: van directo a los atributos del SVG.
    """
    totales = defaultdict(int)
    for gasto in gastos:
        totales[gasto.categoria] += gasto.monto
    gastado = sum(totales.values())
    if not gastado:
        return {"tramos": [], "limite_presupuesto": None}
    base = max(presupuesto or 0, gastado)
    tramos, inicio = [], 0.0
    for clave, etiqueta in CategoriaGasto.choices:
        if monto := totales.get(clave):
            ancho = monto * 100 / base
            tramos.append(
                {
                    "clave": clave,
                    "etiqueta": etiqueta,
                    "total": monto,
                    "porcentaje": round(monto * 100 / gastado),
                    "x": f"{inicio:.3f}",
                    "ancho": f"{ancho:.3f}",
                }
            )
            inicio += ancho
    limite = f"{presupuesto * 100 / base:.3f}" if presupuesto and gastado > presupuesto else None
    return {"tramos": tramos, "limite_presupuesto": limite}


def gastos_en_monedas(gastos, presupuesto):
    """
    Lo gastado en cada moneda extranjera: «gastaste 1.400.000 pesos colombianos (≈ $310.000)».
    El cambio promedio sale de los mismos gastos (lo que pagaste allá ÷ lo que te costó en pesos).
    """
    totales = defaultdict(lambda: [Decimal(0), 0])
    for gasto in gastos:
        if gasto.moneda:
            totales[gasto.moneda][0] += gasto.monto_moneda
            totales[gasto.moneda][1] += gasto.monto
    resumen = []
    for codigo, (total_moneda, total_pesos) in sorted(totales.items(), key=lambda fila: -fila[1][1]):
        por_peso = total_moneda / total_pesos  # cuántas unidades de esa moneda da $1
        presupuesto_en_moneda = round(presupuesto * por_peso) if presupuesto else None
        resumen.append(
            {
                "codigo": codigo,
                "nombre": nombre_moneda(codigo, total_moneda),
                "total": total_moneda,
                "total_pesos": total_pesos,
                # Se muestra el lado del cambio que no queda en decimales chicos:
                # «$1 = 4,52 COP» o «1 USD = $950»
                "unidades_por_peso": por_peso if por_peso >= 1 else None,
                "pesos_por_unidad": total_pesos / total_moneda if por_peso < 1 else None,
                "presupuesto": presupuesto_en_moneda,
                "nombre_presupuesto": nombre_moneda(codigo, presupuesto_en_moneda) if presupuesto else "",
            }
        )
    return resumen
