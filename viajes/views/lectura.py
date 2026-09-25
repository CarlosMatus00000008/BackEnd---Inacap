"""READ: consultar viajes (línea de tiempo, compartidos y detalle)."""

from django.db.models import Count, Q
from django.utils import timezone
from django.views.generic import DetailView, ListView

from ..forms import FiltroViajesForm
from ..mixins import AccesoMixin, PaginacionTolerante
from ..models import EstadoViaje, Viaje


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
    """Detalle de un viaje: fechas, estado, notas y con quién se comparte. Dueño y compartidos pueden verlo."""

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
        )
        return contexto
