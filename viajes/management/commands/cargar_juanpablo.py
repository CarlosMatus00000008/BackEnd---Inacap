"""
Crea el usuario de demostración «JuanPablo»: sus datos de registro (nombre, correo,
teléfono y consentimiento), 10 viajes completados en 10 países (con presupuesto, gastos
en moneda local y 10 fotos cada uno) y 2 viajes planificados.

Las fotos son de Wikimedia Commons (licencias CC BY y CC BY-SA): se descargan en 1920 px
de ancho y pasan por el mismo proceso que las que suben los usuarios (sin EXIF). El
crédito de cada foto (autor y licencia) queda guardado en la foto (se ve en el admin).
La lista está en juanpablo_fotos.json.

Uso:
    python manage.py cargar_juanpablo                 # crea el usuario, o lo pone al día (contraseña Juanpablo123)
    python manage.py cargar_juanpablo --contrasena "OtraClave.2026"
    python manage.py cargar_juanpablo --eliminar      # borra el usuario, sus viajes y sus fotos
"""

import json
from datetime import date, datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from viajes.demo import CargadorDemo
from viajes.models import CategoriaGasto

# Datos de registro inventados. El sitio no envía correos, así que el correo es solo un dato;
# el teléfono es el de ejemplo del formulario de registro.
REGISTRO = {
    "first_name": "Juan Pablo",
    "last_name": "Rojas Valenzuela",
    "email": "juanpablo.rojas.viajes@gmail.com",
    "telefono": "+56912345678",
    "alta": datetime(2021, 4, 20, 19, 32),  # antes de su primer viaje
}
FOTOS = json.loads((Path(__file__).with_name("juanpablo_fotos.json")).read_text(encoding="utf-8"))

T, A, C, AC, CO = (
    CategoriaGasto.TRANSPORTE,
    CategoriaGasto.ALOJAMIENTO,
    CategoriaGasto.COMIDA,
    CategoriaGasto.ACTIVIDADES,
    CategoriaGasto.COMPRAS,
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
        "notas": (
            "Fui con mi hermano. Los dos primeros días en Cusco fueron solo para acostumbrarnos a la altura: caminar "
            "lento y mucho mate de coca.\n"
            "Lo mejor: llegar a Machu Picchu en el primer bus, a las 6 de la mañana, cuando todavía hay neblina.\n"
            "Un dato: las entradas a Machu Picchu se agotan. Las compramos con un mes de anticipación.\n"
            "¿Volvería? Sí, pero con más días para el lago Titicaca."
        ),
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
        "notas": (
            "Doce días entre El Calafate, El Chaltén e Iguazú. En la Patagonia hizo frío hasta en febrero, así que "
            "lleven cortaviento.\n"
            "Lo mejor: caminar sobre el glaciar Perito Moreno. Se escucha cómo cruje el hielo.\n"
            "Un dato: la caminata a la Laguna de los Tres toma unas 8 horas ida y vuelta, pero vale cada paso.\n"
            "¿Volvería? Mil veces. Iguazú fue el cierre perfecto."
        ),
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
        "notas": (
            "Una semana en Río, alojado en Copacabana.\n"
            "Lo mejor: subir al Pan de Azúcar al atardecer y quedarse hasta que se prenden las luces de la ciudad.\n"
            "Un dato: al Cristo Redentor hay que ir temprano. A mediodía se llena y a veces lo tapan las nubes.\n"
            "¿Volvería? Sí, para el Carnaval."
        ),
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
        "notas": (
            "Partí en Cartagena y después me fui al Eje Cafetero, con una pasada por Bogotá y Villa de Leyva.\n"
            "Lo mejor: el Valle de Cocora, entre palmas de cera de 40 metros. Llegamos en Jeep Willys desde Salento.\n"
            "Un dato: en Salento hay tours por las fincas de café. Se aprende harto y el café es buenísimo.\n"
            "¿Volvería? Sí, la gente es de lo más amable que he conocido."
        ),
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
        "notas": (
            "Once días: primero la Riviera Maya y después San Miguel de Allende.\n"
            "Lo mejor: San Miguel de Allende de noche, con la Parroquia iluminada.\n"
            "Un dato: a Chichén Itzá conviene llegar a la hora de apertura. Después hace mucho calor y llegan los "
            "buses.\n"
            "¿Volvería? Sí, me faltó Ciudad de México."
        ),
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
        "notas": (
            "Diez días entre Barcelona y Granada. De ahí seguí a París.\n"
            "Lo mejor: la Sagrada Familia por dentro, con el sol entrando por los vitrales.\n"
            "Un dato: la Alhambra hay que reservarla con tiempo. Las entradas del día se acaban rápido.\n"
            "¿Volvería? Sí, y me quedaría más días en Granada."
        ),
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
        "notas": (
            "Seis días en París, llegando desde Granada.\n"
            "Lo mejor: caminar por la orilla del Sena y ver Notre-Dame iluminada de noche.\n"
            "Un dato: el Louvre es enorme. Es mejor elegir dos o tres salas que intentar verlo todo.\n"
            "¿Volvería? Sí, pero fuera de temporada alta."
        ),
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
        "notas": (
            "Doce días en tren: Roma, Florencia y Venecia.\n"
            "Lo mejor: subir a la cúpula del Duomo de Florencia. Son 463 escalones, pero la vista es increíble.\n"
            "Un dato: el tren rápido entre ciudades es cómodo y sale más barato si se compra con anticipación.\n"
            "¿Volvería? Sí. Tiré la moneda en la Fontana di Trevi, así que tengo que volver."
        ),
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
        "notas": (
            "Doce días con el Japan Rail Pass: Kioto, Himeji y el lago Kawaguchi.\n"
            "Lo mejor: ver el monte Fuji despejado al atardecer desde el lago.\n"
            "Un dato: llegamos en temporada de cerezos y todo estaba lleno. Reservamos los hoteles con meses de "
            "anticipación.\n"
            "¿Volvería? Es el mejor viaje que he hecho."
        ),
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
        "notas": (
            "Ocho días en auto por la costa sur, saliendo desde Reikiavik.\n"
            "Lo mejor: los témpanos de la laguna glaciar Jökulsárlón y la playa de arena negra de Reynisfjara.\n"
            "Un dato: el clima cambia cada hora. Hay que andar siempre con ropa impermeable.\n"
            "¿Volvería? Sí, en invierno para ver auroras."
        ),
    },
}

PLANIFICADOS = [
    ("Bangkok y Chiang Mai", "TH", 120, 14, "Templos, mercados flotantes y un curso de cocina tailandesa."),
    ("Queenstown", "NZ", 400, 16, "Ruta de Milford Sound y, si me atrevo, el bungee del puente Kawarau."),
]


DATOS = {
    "usuario": "JuanPablo",
    "registro": REGISTRO,
    "viajes": VIAJES,
    "planificados": PLANIFICADOS,
    "fotos": FOTOS,
    "publicos": ["JP", "IT"],
}
CONTRASENA = "Juanpablo123"  # proyecto de prueba: contraseña simple a propósito


class Command(BaseCommand):
    help = "Crea el usuario demo «JuanPablo» con 10 viajes, gastos y 10 fotos por país."

    def add_arguments(self, parser):
        parser.add_argument(
            "--contrasena", default=CONTRASENA, help=f"Contraseña del usuario (por defecto {CONTRASENA})."
        )
        parser.add_argument("--eliminar", action="store_true", help="Borra el usuario, sus viajes y sus fotos.")

    def handle(self, *args, **opciones):
        cargador = CargadorDemo(self, DATOS)
        if opciones["eliminar"]:
            return cargador.eliminar()
        if not settings.FOTOS_HABILITADAS:
            raise CommandError("Las fotos no están habilitadas (falta configurar Supabase Storage).")
        cargador.cargar(opciones["contrasena"])
