"""
Carga datos de demostración para probar y presentar el proyecto.

Crea dos usuarios normales (sin acceso al admin):
  - viajero: 16 viajes completados en 15 países, 1 en progreso y 6 planificados.
  - pareja:  sus propios viajes + los que «viajero» compartió con ella.

Uso:
    python manage.py cargar_demo
    python manage.py cargar_demo --contrasena "OtraClave.2026" --reiniciar
"""

from datetime import date, timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from viajes.models import EstadoViaje, Pais, Viaje
from viajes.senales import GRUPO_VIAJEROS

Usuario = get_user_model()
C, P, E = EstadoViaje.COMPLETADO, EstadoViaje.PLANIFICADO, EstadoViaje.EN_PROGRESO

# (destino, código país, inicio, regreso, favorito, calificación, notas)
VIAJES_COMPLETADOS = [
    (
        "Mendoza",
        "AR",
        date(2019, 3, 8),
        date(2019, 3, 12),
        False,
        4,
        "Ruta del vino en bicicleta y un asado inolvidable en Chacras de Coria.",
    ),
    (
        "Cusco",
        "PE",
        date(2019, 7, 14),
        date(2019, 7, 22),
        True,
        5,
        "Camino Inca de 4 días hasta Machu Picchu. El mal de altura pegó el primer día.",
    ),
    (
        "Río de Janeiro",
        "BR",
        date(2020, 2, 1),
        date(2020, 2, 9),
        False,
        4,
        "Carnaval, Pan de Azúcar y atardecer en Arpoador.",
    ),
    (
        "Cartagena",
        "CO",
        date(2021, 12, 10),
        date(2021, 12, 17),
        False,
        4,
        "Ciudad amurallada preciosa; tour en lancha a Islas del Rosario.",
    ),
    (
        "Ciudad de México",
        "MX",
        date(2022, 4, 5),
        date(2022, 4, 13),
        False,
        5,
        "Tacos al pastor, Teotihuacán al amanecer y el Museo de Antropología.",
    ),
    (
        "Nueva York",
        "US",
        date(2022, 9, 18),
        date(2022, 9, 26),
        False,
        4,
        "Caminata por el puente de Brooklyn y musical en Broadway.",
    ),
    (
        "Barcelona",
        "ES",
        date(2023, 5, 2),
        date(2023, 5, 7),
        False,
        4,
        "Sagrada Familia (reservar con anticipación) y tapas en El Born.",
    ),
    (
        "París",
        "FR",
        date(2023, 5, 8),
        date(2023, 5, 14),
        True,
        5,
        "Viaje de aniversario. Picnic frente a la Torre Eiffel y el Louvre de noche.",
    ),
    (
        "Roma",
        "IT",
        date(2023, 10, 20),
        date(2023, 10, 27),
        True,
        5,
        "El Coliseo, la Fontana di Trevi y el mejor gelato de la vida.",
    ),
    (
        "Lisboa",
        "PT",
        date(2024, 3, 11),
        date(2024, 3, 16),
        False,
        4,
        "Tranvía 28, pasteles de Belém y fado en Alfama.",
    ),
    (
        "Tokio",
        "JP",
        date(2024, 8, 3),
        date(2024, 8, 15),
        True,
        5,
        "Shibuya, Akihabara y excursión a Kioto en shinkansen.",
    ),
    (
        "Bangkok",
        "TH",
        date(2024, 12, 5),
        date(2024, 12, 12),
        False,
        3,
        "Templos increíbles, pero demasiado calor y tráfico.",
    ),
    (
        "Bali",
        "ID",
        date(2025, 4, 10),
        date(2025, 4, 20),
        True,
        5,
        "Arrozales de Tegallalang, clase de surf en Canggu y amanecer en el Batur.",
    ),
    (
        "Sídney",
        "AU",
        date(2025, 10, 2),
        date(2025, 10, 12),
        False,
        4,
        "Ópera, Bondi-Coogee a pie y ferry a Manly.",
    ),
    (
        "Marrakech",
        "MA",
        date(2025, 12, 1),
        date(2025, 12, 7),
        False,
        4,
        "Zocos, noche en el desierto de Agafay y mucho té de menta.",
    ),
    (
        "Buenos Aires",
        "AR",
        date(2026, 2, 13),
        date(2026, 2, 17),
        False,
        4,
        "Segunda vez en Argentina: San Telmo, tango y parrilla.",
    ),
]

# (destino, código país, días desde hoy, duración en días o None, notas)
VIAJES_PLANIFICADOS = [
    ("Reikiavik", "IS", 45, 10, "Auroras boreales y ruta por el Círculo Dorado."),
    ("Queenstown", "NZ", 120, 12, "Milford Sound y bungee jumping (¿me atreveré?)."),
    ("El Cairo", "EG", 200, 8, "Pirámides de Giza y crucero por el Nilo."),
    ("Santorini", "GR", 260, 6, "Atardecer en Oia."),
    ("Banff", "CA", 330, 9, "Lago Louise y Moraine en verano."),
    ("Hanói", "VN", 400, None, "Bahía de Ha Long. Fechas por confirmar."),
]

COMPARTIR_CON_PAREJA = {"París", "Roma", "Tokio", "Bali", "Buenos Aires", "Reikiavik"}


class Command(BaseCommand):
    help = "Carga usuarios y viajes de demostración (viajero y pareja)."

    def add_arguments(self, parser):
        parser.add_argument("--contrasena", default="Viajes.2026", help="Contraseña de los usuarios demo.")
        parser.add_argument(
            "--reiniciar", action="store_true", help="Borra los viajes demo existentes y los vuelve a crear."
        )
        parser.add_argument("--forzar", action="store_true", help="Permite ejecutarlo con DEBUG=False.")

    def handle(self, *args, **opciones):
        if not settings.DEBUG and not opciones["forzar"]:
            raise CommandError(
                "Por seguridad este comando solo se ejecuta con DEBUG=True (usa --forzar si estás seguro)."
            )
        if not Pais.objects.exists():
            raise CommandError("No hay países cargados. Ejecuta primero «python manage.py migrate».")

        with transaction.atomic():
            viajero = self._usuario("viajero", "Benja", "viajero@example.com", opciones["contrasena"])
            pareja = self._usuario("pareja", "Cami", "pareja@example.com", opciones["contrasena"])

            if viajero.viajes.exists() and not opciones["reiniciar"]:
                self.stdout.write(
                    self.style.WARNING("Los datos demo ya existen. Usa --reiniciar para volver a crearlos.")
                )
                return
            for usuario in (viajero, pareja):
                usuario.viajes.all().delete()

            self._crear_viajes_de_viajero(viajero, pareja)
            self._crear_viajes_de_pareja(pareja, viajero)

        self.stdout.write(self.style.SUCCESS("Datos de demostración cargados."))
        self.stdout.write(f"  Usuarios: viajero / pareja   ·   Contraseña: {opciones['contrasena']}")
        total_viajes, compartidos = viajero.viajes.count(), pareja.viajes_compartidos.count()
        self.stdout.write(f"  Viajes de viajero: {total_viajes}   ·   Compartidos con pareja: {compartidos}")

    # ------------------------------------------------------------------
    def _usuario(self, nombre, nombre_pila, correo, contrasena):
        usuario, creado = Usuario.objects.get_or_create(
            username=nombre, defaults={"first_name": nombre_pila, "email": correo}
        )
        if creado:
            usuario.set_password(contrasena)
            usuario.save()
        usuario.groups.add(Group.objects.get_or_create(name=GRUPO_VIAJEROS)[0])
        return usuario

    def _guardar(self, viaje):
        viaje.full_clean()  # los datos demo pasan por las mismas validaciones que la web
        viaje.save()
        return viaje

    def _crear_viajes_de_viajero(self, viajero, pareja):
        paises = {pais.codigo_iso: pais for pais in Pais.objects.all()}
        hoy = timezone.localdate()

        for destino, codigo, inicio, regreso, favorito, nota, notas in VIAJES_COMPLETADOS:
            viaje = self._guardar(
                Viaje(
                    usuario=viajero,
                    destino=destino,
                    pais=paises[codigo],
                    fecha_inicio=inicio,
                    fecha_fin=regreso,
                    estado=C,
                    favorito=favorito,
                    calificacion=nota,
                    notas=notas,
                )
            )
            self._completar(viaje, pareja)

        actual = self._guardar(
            Viaje(
                usuario=viajero,
                destino="Montevideo",
                pais=paises["UY"],
                fecha_inicio=hoy - timedelta(days=2),
                fecha_fin=hoy + timedelta(days=5),
                estado=E,
                notas="Escapada de una semana. ¡Probar el chivito!",
            )
        )
        self._completar(actual, pareja)

        for destino, codigo, dias, duracion, notas in VIAJES_PLANIFICADOS:
            inicio = hoy + timedelta(days=dias)
            viaje = self._guardar(
                Viaje(
                    usuario=viajero,
                    destino=destino,
                    pais=paises[codigo],
                    fecha_inicio=inicio,
                    fecha_fin=inicio + timedelta(days=duracion - 1) if duracion else None,
                    estado=P,
                    notas=notas,
                )
            )
            self._completar(viaje, pareja)

    def _crear_viajes_de_pareja(self, pareja, viajero):
        hoy = timezone.localdate()
        floripa = self._guardar(
            Viaje(
                usuario=pareja,
                destino="Florianópolis",
                pais=Pais.objects.get(codigo_iso="BR"),
                fecha_inicio=date(2024, 1, 15),
                fecha_fin=date(2024, 1, 24),
                estado=C,
                calificacion=5,
                favorito=True,
                notas="Playas de Joaquina y Lagoa da Conceição.",
            )
        )
        floripa.compartido_con.add(viajero)
        self._guardar(
            Viaje(
                usuario=pareja,
                destino="Madrid",
                pais=Pais.objects.get(codigo_iso="ES"),
                fecha_inicio=hoy + timedelta(days=90),
                fecha_fin=hoy + timedelta(days=97),
                estado=P,
                notas="Congreso de trabajo + fin de semana en Toledo.",
            )
        )

    def _completar(self, viaje, pareja):
        """Comparte con la pareja algunos de los viajes (solo lectura)."""
        if viaje.destino in COMPARTIR_CON_PAREJA:
            viaje.compartido_con.add(pareja)
