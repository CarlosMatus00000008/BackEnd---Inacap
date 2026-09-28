"""READ: consultar viajes (línea de tiempo, compartidos y detalle)."""

from itertools import groupby

from django.conf import settings
from django.db.models import Count, Q, Sum
from django.utils import timezone
from django.views.generic import DetailView, ListView

from ..forms import ActividadForm, FiltroViajesForm, FotosForm, GastoForm
from ..mixins import AccesoMixin, PaginacionTolerante
from ..models import Actividad, CategoriaGasto, EstadoViaje, FotoViaje, Gasto, Viaje
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
        contexto["paises_visitados"] = (
            mis_viajes.exclude(estado=EstadoViaje.PLANIFICADO).values("pais").distinct().count()
        )
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
        etiquetas = dict(CategoriaGasto.choices)
        por_categoria = [
            (etiquetas[fila["categoria"]], fila["total"])
            for fila in viaje.gastos.values("categoria").annotate(total=Sum("monto")).order_by("-total")
        ]
        resumen = {"gastos": gastos, "total_gastado": total, "gastos_por_categoria": por_categoria}
        if viaje.presupuesto:
            saldo = viaje.presupuesto - total
            resumen.update(
                saldo=max(saldo, 0),
                exceso=max(-saldo, 0),
                porcentaje_usado=round(total * 100 / viaje.presupuesto),
            )
        return resumen
