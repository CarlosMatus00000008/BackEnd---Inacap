"""
Crea el usuario de demostración «JuanPablo»: sus datos de registro (nombre, correo,
teléfono y consentimiento), 10 viajes completados en 10 países (con presupuesto, gastos
en moneda local y 10 fotos cada uno) y 2 viajes planificados.

Las fotos son de Wikimedia Commons (licencias CC BY y CC BY-SA): se descargan en 1920 px
de ancho y pasan por el mismo proceso que las que suben los usuarios (sin EXIF). El
crédito de cada foto (autor y licencia) queda en las notas de su viaje. La lista está en
juanpablo_fotos.json.

Uso:
    python manage.py cargar_juanpablo                 # crea el usuario, o completa su perfil y las fotos que falten
    python manage.py cargar_juanpablo --contrasena "OtraClave.2026"
    python manage.py cargar_juanpablo --eliminar      # borra el usuario, sus viajes y sus fotos
"""

import json
import secrets
import time
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from cuentas.models import PerfilUsuario
from viajes.forms import VariasFotosField
from viajes.models import CategoriaGasto, EstadoViaje, FotoViaje, Gasto, Pais, Viaje
from viajes.senales import GRUPO_VIAJEROS

Usuario = get_user_model()
NOMBRE_USUARIO = "JuanPablo"
# Datos de registro inventados. El correo usa example.com (dominio reservado para ejemplos) y el
# teléfono es el de ejemplo del formulario de registro, así no pertenecen a una persona real.
REGISTRO = {
    "first_name": "Juan Pablo",
    "last_name": "Rojas Valenzuela",
    "email": "juanpablo.rojas@example.com",
    "telefono": "+56912345678",
    "alta": datetime(2021, 4, 20, 19, 32),  # antes de su primer viaje
}
FOTOS = json.loads((Path(__file__).with_name("juanpablo_fotos.json")).read_text(encoding="utf-8"))
AGENTE = "DiarioDeViajes-demo/1.0 (proyecto educativo)"  # Wikimedia pide identificarse

T, A, C, AC, CO, O = (
    CategoriaGasto.TRANSPORTE,
    CategoriaGasto.ALOJAMIENTO,
    CategoriaGasto.COMIDA,
    CategoriaGasto.ACTIVIDADES,
    CategoriaGasto.COMPRAS,
    CategoriaGasto.OTROS,
)

# País → viaje. «cambio» = pesos chilenos por unidad de la moneda local en esas fechas.
# Gastos: (descripción, categoría, monto en moneda local, día del viaje); el pasaje va en pesos.
VIAJES = {
    "PE": {
        "destino": "Cusco, Machu Picchu y Titicaca",
        "fechas": (date(2021, 5, 8), date(2021, 5, 18)),
        "calificacion": 5,
        "favorito": True,
        "presupuesto": 1_300_000,
        "pasaje": 420_000,
        "moneda": "PEN",
        "cambio": 240,
        "gastos": [
            ("Hostal en San Blas", A, 1_050, 0),
            ("Tren a Aguas Calientes", T, 520, 3),
            ("Entrada a Machu Picchu y Huayna Picchu", AC, 200, 4),
            ("Lomo saltado y chicha morada", C, 95, 5),
            ("Excursión a las islas de los Uros", AC, 120, 8),
            ("Chompa de alpaca", CO, 180, 9),
        ],
        "notas": "Aclimatarse en Cusco fue clave. Machu Picchu al amanecer superó todo lo que imaginaba, "
        "y las islas flotantes de los Uros en el Titicaca parecen de otro mundo.",
    },
    "AR": {
        "destino": "Patagonia e Iguazú",
        "fechas": (date(2022, 2, 2), date(2022, 2, 14)),
        "calificacion": 5,
        "favorito": True,
        "presupuesto": 1_600_000,
        "pasaje": 380_000,
        "moneda": "ARS",
        "cambio": 8.5,
        "gastos": [
            ("Cabaña en El Calafate", A, 68_000, 0),
            ("Minitrekking en el Perito Moreno", AC, 32_000, 2),
            ("Bus a El Chaltén", T, 9_500, 4),
            ("Cordero patagónico", C, 7_800, 5),
            ("Vuelo a Puerto Iguazú", T, 41_000, 8),
            ("Parque Nacional Iguazú", AC, 6_500, 9),
        ],
        "notas": "El Perito Moreno se escucha antes de verlo: los bloques de hielo caen con un estruendo. "
        "Subí a la Laguna de los Tres para ver el Fitz Roy y cerré el viaje empapado en la Garganta del Diablo.",
    },
    "BR": {
        "destino": "Río de Janeiro",
        "fechas": (date(2022, 11, 10), date(2022, 11, 17)),
        "calificacion": 4,
        "favorito": False,
        "presupuesto": 900_000,
        "pasaje": 350_000,
        "moneda": "BRL",
        "cambio": 170,
        "gastos": [
            ("Departamento en Copacabana", A, 1_900, 0),
            ("Teleférico al Pan de Azúcar", AC, 150, 2),
            ("Tren al Corcovado", AC, 110, 3),
            ("Feijoada del sábado", C, 90, 4),
            ("Caipiriñas en Ipanema", C, 60, 5),
        ],
        "notas": "Atardecer aplaudido en Arpoador, el Cristo entre nubes y samba en Lapa. "
        "El Pan de Azúcar tiene la mejor vista de la bahía.",
    },
    "CO": {
        "destino": "Eje Cafetero y Villa de Leyva",
        "fechas": (date(2023, 3, 15), date(2023, 3, 25)),
        "calificacion": 5,
        "favorito": False,
        "presupuesto": 1_100_000,
        "pasaje": 390_000,
        "moneda": "COP",
        "cambio": 0.2,
        "gastos": [
            ("Hotel en Cartagena", A, 780_000, 0),
            ("Finca cafetera en Salento", A, 540_000, 3),
            ("Jeep Willys al Valle de Cocora", T, 24_000, 4),
            ("Ajiaco santafereño", C, 38_000, 8),
            ("Tour de café", AC, 90_000, 5),
            ("Café de origen para la casa", CO, 120_000, 6),
        ],
        "notas": "Empecé con el atardecer en las murallas de Cartagena. En Cocora las palmas de cera "
        "se pierden entre la niebla, y Villa de Leyva tiene una de las plazas más grandes de América.",
    },
    "MX": {
        "destino": "Riviera Maya y San Miguel de Allende",
        "fechas": (date(2023, 8, 4), date(2023, 8, 15)),
        "calificacion": 4,
        "favorito": False,
        "presupuesto": 1_500_000,
        "pasaje": 610_000,
        "moneda": "MXN",
        "cambio": 49,
        "gastos": [
            ("Hotel en Tulum", A, 9_800, 0),
            ("Entrada a Chichén Itzá", AC, 614, 2),
            ("Cenote Ik Kil", AC, 350, 2),
            ("Tacos al pastor (varias noches)", C, 780, 4),
            ("Autobús a San Miguel de Allende", T, 1_450, 6),
            ("Artesanía de barro", CO, 900, 8),
        ],
        "notas": "Chichén Itzá temprano, antes del calor y los buses. Tulum frente al Caribe es una postal. "
        "San Miguel de Allende de noche, con la Parroquia iluminada, fue lo mejor del viaje.",
    },
    "ES": {
        "destino": "Barcelona y Granada",
        "fechas": (date(2024, 4, 10), date(2024, 4, 20)),
        "calificacion": 5,
        "favorito": False,
        "presupuesto": 1_900_000,
        "pasaje": 890_000,
        "moneda": "EUR",
        "cambio": 1_030,
        "gastos": [
            ("Piso en el Eixample", A, 620, 0),
            ("Sagrada Familia con torres", AC, 36, 1),
            ("Park Güell", AC, 18, 2),
            ("Tapas en el Albaicín", C, 45, 7),
            ("Alhambra y Generalife", AC, 19, 8),
            ("Tren Barcelona-Granada", T, 89, 6),
        ],
        "notas": "La luz que entra por los vitrales de la Sagrada Familia no se puede explicar. "
        "En Granada vi el atardecer sobre la Alhambra desde el mirador de San Nicolás.",
    },
    "FR": {
        "destino": "París",
        "fechas": (date(2024, 4, 21), date(2024, 4, 26)),
        "calificacion": 4,
        "favorito": False,
        "presupuesto": 900_000,
        "pasaje": 0,
        "moneda": "EUR",
        "cambio": 1_030,
        "gastos": [
            ("Hotel en el Barrio Latino", A, 540, 0),
            ("Vuelo Granada-París", T, 95, 0),
            ("Museo del Louvre", AC, 22, 1),
            ("Croissants y café cada mañana", C, 60, 2),
            ("Libro de un bouquiniste", CO, 15, 3),
        ],
        "notas": "Caminé París de punta a punta: los libreros del Sena, el Jardín de Luxemburgo "
        "y el Arco del Triunfo iluminado. Notre-Dame de noche desde el río.",
    },
    "IT": {
        "destino": "Roma, Florencia y Venecia",
        "fechas": (date(2024, 10, 1), date(2024, 10, 12)),
        "calificacion": 5,
        "favorito": True,
        "presupuesto": 2_300_000,
        "pasaje": 950_000,
        "moneda": "EUR",
        "cambio": 1_020,
        "gastos": [
            ("Hoteles (3 ciudades)", A, 890, 0),
            ("Coliseo y Foro Romano", AC, 18, 1),
            ("Tren de alta velocidad Roma-Florencia-Venecia", T, 95, 4),
            ("Cúpula de Brunelleschi", AC, 30, 5),
            ("Pasta, pizza y gelato", C, 210, 6),
            ("Góndola por el Gran Canal", AC, 90, 10),
        ],
        "notas": "Tiré la moneda en la Fontana di Trevi, así que tengo que volver. Subí los 463 escalones "
        "de la cúpula de Florencia y en Venecia me perdí a propósito.",
    },
    "JP": {
        "destino": "Kioto, Himeji y el monte Fuji",
        "fechas": (date(2025, 3, 28), date(2025, 4, 8)),
        "calificacion": 5,
        "favorito": True,
        "presupuesto": 2_500_000,
        "pasaje": 1_150_000,
        "moneda": "JPY",
        "cambio": 6.4,
        "gastos": [
            ("Ryokan en Kioto", A, 96_000, 0),
            ("Japan Rail Pass (7 días)", T, 50_000, 0),
            ("Templo Kiyomizu-dera", AC, 500, 2),
            ("Castillo de Himeji", AC, 1_000, 5),
            ("Ramen, sushi y onigiri", C, 28_000, 6),
            ("Hotel con vista al Fuji", A, 32_000, 9),
        ],
        "notas": "Llegué justo para los cerezos. El castillo de Himeji es el más bonito de Japón "
        "y el Fuji se dejó ver despejado al atardecer desde el lago Kawaguchi.",
    },
    "IS": {
        "destino": "Reikiavik y la costa sur",
        "fechas": (date(2025, 8, 12), date(2025, 8, 20)),
        "calificacion": 5,
        "favorito": False,
        "presupuesto": 2_000_000,
        "pasaje": 980_000,
        "moneda": "ISK",
        "cambio": 7,
        "gastos": [
            ("Arriendo de auto", T, 72_000, 0),
            ("Guesthouses por la costa sur", A, 118_000, 1),
            ("Kayak en la laguna glaciar Jökulsárlón", AC, 14_900, 4),
            ("Sopa de cordero y hot dogs", C, 21_000, 3),
            ("Bencina", T, 26_000, 5),
        ],
        "notas": "Paré en cada cascada de la ruta 1: Seljalandsfoss se recorre por detrás. La playa negra "
        "de Reynisfjara y los témpanos de Jökulsárlón fueron lo más impresionante.",
    },
}

PLANIFICADOS = [
    ("Bangkok y Chiang Mai", "TH", 120, 14, "Templos, mercados flotantes y un curso de cocina tailandesa."),
    ("Queenstown", "NZ", 400, 16, "Ruta de Milford Sound y, si me atrevo, el bungee del puente Kawarau."),
]


class Command(BaseCommand):
    help = "Crea el usuario demo «JuanPablo» con 10 viajes, gastos y 10 fotos por país."

    def add_arguments(self, parser):
        parser.add_argument("--contrasena", help="Contraseña del usuario (por defecto se genera una segura).")
        parser.add_argument("--eliminar", action="store_true", help="Borra el usuario, sus viajes y sus fotos.")

    def handle(self, *args, **opciones):
        if opciones["eliminar"]:
            return self._eliminar()
        if not settings.FOTOS_HABILITADAS:
            raise CommandError("Las fotos no están habilitadas (falta configurar Supabase Storage).")

        usuario = Usuario.objects.filter(username=NOMBRE_USUARIO).first()
        if usuario:
            self.stdout.write(f"«{NOMBRE_USUARIO}» ya existe: se completan su perfil y las fotos que falten.")
        else:
            contrasena = opciones["contrasena"] or secrets.token_urlsafe(12)
            with transaction.atomic():
                usuario = self._crear_usuario(contrasena)
                self._crear_viajes(usuario)
            self.stdout.write(self.style.SUCCESS(f"Usuario «{NOMBRE_USUARIO}» creado con sus viajes y gastos."))
            self.stdout.write(f"  Contraseña: {contrasena}")

        self._completar_registro(usuario)
        self._cargar_fotos(usuario)

    # ------------------------------------------------------------------
    def _crear_usuario(self, contrasena):
        usuario = Usuario.objects.create_user(NOMBRE_USUARIO, password=contrasena)
        usuario.groups.add(Group.objects.get_or_create(name=GRUPO_VIAJEROS)[0])
        return usuario

    def _completar_registro(self, usuario):
        """Los datos que pide el registro (y el perfil), como si se hubiera registrado en el sitio."""
        alta = timezone.make_aware(REGISTRO["alta"])
        usuario.first_name = REGISTRO["first_name"]
        usuario.last_name = REGISTRO["last_name"]
        usuario.email = REGISTRO["email"]
        usuario.date_joined = alta
        usuario.last_login = usuario.last_login or timezone.now()
        usuario.full_clean(exclude=["password"])
        usuario.save()
        PerfilUsuario.objects.update_or_create(
            usuario=usuario,
            defaults={"telefono": REGISTRO["telefono"], "acepta_datos": True, "fecha_consentimiento": alta},
        )
        self.stdout.write(
            f"  Perfil: {usuario.get_full_name()} · {usuario.email} · +56 9 1234 5678 · alta {alta:%d-%m-%Y}"
        )

    def _guardar(self, objeto):
        objeto.full_clean()  # los datos demo pasan por las mismas validaciones que la web
        objeto.save()
        return objeto

    def _crear_viajes(self, usuario):
        paises = {pais.codigo_iso: pais for pais in Pais.objects.all()}
        for codigo, datos in VIAJES.items():
            inicio, regreso = datos["fechas"]
            viaje = self._guardar(
                Viaje(
                    usuario=usuario,
                    destino=datos["destino"],
                    pais=paises[codigo],
                    fecha_inicio=inicio,
                    fecha_fin=regreso,
                    estado=EstadoViaje.COMPLETADO,
                    favorito=datos["favorito"],
                    calificacion=datos["calificacion"],
                    presupuesto=datos["presupuesto"],
                    notas=f"{datos['notas']}\n\n{self._creditos(codigo)}",
                )
            )
            if datos["pasaje"]:
                self._guardar(
                    Gasto(viaje=viaje, descripcion="Pasajes de avión", categoria=T, monto=datos["pasaje"], fecha=inicio)
                )
            for descripcion, categoria, monto_local, dia in datos["gastos"]:
                self._guardar(
                    Gasto(
                        viaje=viaje,
                        descripcion=descripcion,
                        categoria=categoria,
                        monto=round(monto_local * datos["cambio"]),
                        moneda=datos["moneda"],
                        monto_moneda=monto_local,
                        fecha=inicio + timedelta(days=dia),
                    )
                )

        hoy = timezone.localdate()
        for destino, codigo, dias, duracion, notas in PLANIFICADOS:
            inicio = hoy + timedelta(days=dias)
            self._guardar(
                Viaje(
                    usuario=usuario,
                    destino=destino,
                    pais=paises[codigo],
                    fecha_inicio=inicio,
                    fecha_fin=inicio + timedelta(days=duracion - 1),
                    estado=EstadoViaje.PLANIFICADO,
                    notas=notas,
                )
            )

    @staticmethod
    def _creditos(codigo):
        """Crédito de las fotos, como piden las licencias Creative Commons."""
        lineas = ["📷 Fotos de Wikimedia Commons:"]
        for foto in FOTOS[codigo]:
            titulo = foto["titulo"].removeprefix("File:").rsplit(".", 1)[0]
            lineas.append(f"· {titulo} — {foto['autor'] or 'autor en Commons'} ({foto['licencia']})")
        return "\n".join(lineas)

    # ------------------------------------------------------------------
    def _cargar_fotos(self, usuario):
        campo = VariasFotosField()  # el mismo proceso que las fotos subidas desde la web
        viajes = {viaje.pais.codigo_iso: viaje for viaje in usuario.viajes.select_related("pais")}
        subidas = fallidas = 0
        for codigo, fotos in FOTOS.items():
            viaje = viajes.get(codigo)
            if viaje is None:
                continue
            faltan = fotos[viaje.fotos.count():FotoViaje.MAXIMO_POR_VIAJE]
            for foto in faltan:
                try:
                    contenido = self._descargar(foto["thumb"])
                    [preparada] = campo.clean(SimpleUploadedFile("foto.jpg", contenido, "image/jpeg"))
                    FotoViaje.objects.create(viaje=viaje, imagen=preparada)
                    subidas += 1
                except (OSError, forms.ValidationError) as error:
                    fallidas += 1
                    self.stderr.write(f"  No se pudo cargar «{foto['titulo']}»: {error}")
            self.stdout.write(f"  {viaje.destino}: {viaje.fotos.count()} fotos")
        estilo = self.style.SUCCESS if not fallidas else self.style.WARNING
        self.stdout.write(estilo(f"Fotos subidas: {subidas} · con error: {fallidas}"))
        if fallidas:
            self.stdout.write("Vuelve a ejecutar el comando para reintentar las que faltan.")

    @staticmethod
    def _descargar(url):
        pedido = urllib.request.Request(url, headers={"User-Agent": AGENTE})
        for intento in range(3):
            try:
                with urllib.request.urlopen(pedido, timeout=60) as respuesta:
                    return respuesta.read()
            except OSError:
                if intento == 2:
                    raise
                time.sleep(3 * (intento + 1))

    def _eliminar(self):
        usuario = Usuario.objects.filter(username=NOMBRE_USUARIO).first()
        if not usuario:
            self.stdout.write(f"No existe el usuario «{NOMBRE_USUARIO}».")
            return
        fotos = FotoViaje.objects.filter(viaje__usuario=usuario).count()
        with transaction.atomic():
            usuario.delete()  # al borrar cada foto también se borra su archivo (viajes/senales.py)
        self.stdout.write(self.style.SUCCESS(f"Usuario «{NOMBRE_USUARIO}» eliminado con {fotos} fotos."))
