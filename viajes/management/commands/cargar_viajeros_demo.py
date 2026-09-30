"""
Crea dos usuarios de demostración más, con todo relleno (ver viajes/demo.py):

- «Valentina» (Valentina Soto Rivas): 5 viajes, 4 completados y 1 planificado.
- «Matias» (Matías Fuentes Araya): 8 viajes, 6 completados, 1 en progreso y 1 planificado.

Cada viaje hecho o en curso tiene notas, calificación, presupuesto, gastos (en moneda local),
itinerario y 10 fotos de Wikimedia Commons (lista en viajeros_demo_fotos.json). Además se
comparten un viaje entre ellos, para que se vea la sección «Compartidos conmigo».

Proyecto de prueba: las contraseñas son simples a propósito y los datos son inventados
(el sitio no envía correos).

Uso:
    python manage.py cargar_viajeros_demo              # crea los usuarios, o los pone al día (también su contraseña)
    python manage.py cargar_viajeros_demo --eliminar   # borra ambos usuarios con sus viajes y fotos
"""

import json
from datetime import date, datetime, timedelta
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from viajes.demo import CargadorDemo
from viajes.models import CategoriaGasto, EstadoViaje

FOTOS = json.loads((Path(__file__).with_name("viajeros_demo_fotos.json")).read_text(encoding="utf-8"))
T, A, C, AC, CO = (
    CategoriaGasto.TRANSPORTE,
    CategoriaGasto.ALOJAMIENTO,
    CategoriaGasto.COMIDA,
    CategoriaGasto.ACTIVIDADES,
    CategoriaGasto.COMPRAS,
)
HOY = timezone.localdate()

# ---------------------------------------------------------------------------
# Valentina: 5 viajes
# ---------------------------------------------------------------------------
VALENTINA = {
    "usuario": "Valentina",
    "contrasena": "Valentina123",
    "registro": {
        "first_name": "Valentina",
        "last_name": "Soto Rivas",
        "email": "valentina.soto.viajes@gmail.com",
        "telefono": "+56922223333",
        "alta": datetime(2022, 3, 10, 21, 5),
    },
    "viajes": {
        "PT": {
            "destino": "Lisboa",
            "fechas": (date(2022, 6, 10), date(2022, 6, 17)),
            "calificacion": 5,
            "favorito": True,
            "presupuesto": 1_400_000,
            "pasaje": 790_000,
            "moneda": "EUR",
            "cambio": 900,
            "gastos": [
                ("Departamento en Alfama", A, 480, 0),
                ("Tranvía 28 y metro (una semana)", T, 40, 1),
                ("Pasteles de Belém", C, 12, 2),
                ("Monasterio de los Jerónimos", AC, 10, 2),
                ("Cena con fado en Alfama", C, 75, 4),
                ("Azulejos pintados a mano", CO, 45, 6),
            ],
            "itinerario": [
                (0, "16:00", "Paseo por Alfama y el mirador de Santa Luzia", "Alfama"),
                (1, "10:00", "Tranvía 28 de punta a punta", "Praça Martim Moniz"),
                (2, "09:30", "Torre de Belém y los Jerónimos", "Belém"),
                (4, "21:00", "Noche de fado", "Alfama"),
                (6, "18:30", "Atardecer en el Miradouro da Senhora do Monte", "Graça"),
            ],
            "notas": (
                "Mi primer viaje sola. Una semana en Lisboa, alojada en Alfama.\n"
                "Lo mejor: la noche de fado en un restaurante chiquitito de Alfama.\n"
                "Un dato: el tranvía 28 se llena; conviene tomarlo temprano en la parada de Martim Moniz.\n"
                "¿Volvería? Sí, y esta vez iría a Oporto."
            ),
        },
        "GR": {
            "destino": "Atenas y Santorini",
            "fechas": (date(2023, 9, 4), date(2023, 9, 13)),
            "calificacion": 5,
            "favorito": True,
            "presupuesto": 2_200_000,
            "pasaje": 1_050_000,
            "moneda": "EUR",
            "cambio": 960,
            "gastos": [
                ("Hotel en Plaka", A, 260, 0),
                ("Entrada a la Acrópolis", AC, 20, 1),
                ("Ferry Atenas-Santorini", T, 90, 3),
                ("Hotel con vista a la caldera", A, 540, 3),
                ("Paseo en velero al atardecer", AC, 120, 5),
                ("Gyros, souvlaki y ensalada griega", C, 140, 6),
            ],
            "itinerario": [
                (1, "08:00", "Acrópolis temprano, antes del calor", "Atenas"),
                (2, "11:00", "Barrio de Plaka y el Ágora", "Atenas"),
                (3, "07:30", "Ferry a Santorini", "Puerto del Pireo"),
                (5, "17:00", "Velero por la caldera", "Ammoudi"),
                (6, "19:30", "Atardecer en Oia", "Oia"),
                (8, None, "Playa roja y playa negra", "Akrotiri y Perissa"),
            ],
            "notas": (
                "Tres días en Atenas y seis en Santorini.\n"
                "Lo mejor: el paseo en velero por la caldera y bañarnos en las aguas termales.\n"
                "Un dato: el atardecer en Oia se repleta; lo vimos desde Imerovigli, igual de lindo y sin gente.\n"
                "¿Volvería? Sí, a otras islas: Milos o Naxos."
            ),
        },
        "MA": {
            "destino": "Marrakech y el desierto",
            "fechas": (date(2024, 3, 15), date(2024, 3, 22)),
            "calificacion": 4,
            "favorito": False,
            "presupuesto": 1_600_000,
            "pasaje": 980_000,
            "moneda": "MAD",
            "cambio": 95,
            "gastos": [
                ("Riad en la medina", A, 2_400, 0),
                ("Tour de 3 días al Sahara", AC, 1_800, 3),
                ("Tajine y jugo de naranja en Jemaa el-Fnaa", C, 350, 1),
                ("Jardín Majorelle", AC, 150, 2),
                ("Lámpara de bronce del zoco", CO, 600, 6),
            ],
            "itinerario": [
                (1, "19:00", "Plaza Jemaa el-Fnaa de noche", "Marrakech"),
                (2, "09:00", "Jardín Majorelle y los zocos", "Marrakech"),
                (3, "07:00", "Salida al desierto por el Atlas", "Aït Benhaddou"),
                (4, "18:00", "Camellos al atardecer en las dunas", "Merzouga"),
                (5, "05:30", "Amanecer en el Erg Chebbi", "Merzouga"),
            ],
            "notas": (
                "Una semana entre la medina de Marrakech y las dunas de Merzouga.\n"
                "Lo mejor: dormir en el campamento del desierto y ver el cielo lleno de estrellas.\n"
                "Un dato: en los zocos todo se regatea; partir ofreciendo la mitad es normal.\n"
                "¿Volvería? Sí, a Chefchaouen y Fez."
            ),
        },
        "TR": {
            "destino": "Estambul y Capadocia",
            "fechas": (date(2025, 5, 8), date(2025, 5, 17)),
            "calificacion": 5,
            "favorito": True,
            "presupuesto": 2_100_000,
            "pasaje": 1_120_000,
            "moneda": "TRY",
            "cambio": 25,
            "gastos": [
                ("Hotel en Sultanahmet", A, 9_500, 0),
                ("Vuelo Estambul-Capadocia", T, 3_200, 4),
                ("Globo aerostático al amanecer", AC, 7_500, 5),
                ("Hotel cueva en Göreme", A, 8_800, 4),
                ("Baklava, kebab y té turco", C, 4_200, 2),
                ("Alfombra pequeña del Gran Bazar", CO, 6_000, 3),
            ],
            "itinerario": [
                (1, "09:00", "Santa Sofía y la Mezquita Azul", "Sultanahmet"),
                (2, "15:00", "Crucero por el Bósforo", "Eminönü"),
                (3, "11:00", "Gran Bazar y Bazar de las Especias", "Estambul"),
                (5, "05:00", "Vuelo en globo", "Göreme"),
                (6, None, "Valle Rojo y ciudad subterránea", "Capadocia"),
            ],
            "notas": (
                "Cuatro días en Estambul y cinco en Capadocia.\n"
                "Lo mejor: volar en globo al amanecer, con otros cien globos alrededor.\n"
                "Un dato: los vuelos en globo se cancelan si hay viento; mejor dejarlos para los primeros días.\n"
                "¿Volvería? Sí, sin pensarlo."
            ),
        },
    },
    "planificados": [
        ("Bangkok y Chiang Mai", "TH", 75, 12, "Templos, mercados nocturnos y un santuario de elefantes."),
    ],
    "fotos": FOTOS,
    "publicos": ["GR", "PT"],
}

# ---------------------------------------------------------------------------
# Matías: 8 viajes (uno en curso)
# ---------------------------------------------------------------------------
INICIO_SIDNEY = HOY - timedelta(days=4)

MATIAS = {
    "usuario": "Matias",
    "contrasena": "Matias123",
    "registro": {
        "first_name": "Matías",
        "last_name": "Fuentes Araya",
        "email": "matias.fuentes.viajes@gmail.com",
        "telefono": "+56933334444",
        "alta": datetime(2021, 10, 5, 12, 40),
    },
    "viajes": {
        "US": {
            "destino": "Nueva York",
            "fechas": (date(2021, 12, 18), date(2021, 12, 26)),
            "calificacion": 4,
            "favorito": False,
            "presupuesto": 2_300_000,
            "pasaje": 980_000,
            "moneda": "USD",
            "cambio": 850,
            "gastos": [
                ("Hotel en Midtown", A, 1_100, 0),
                ("MetroCard de 7 días", T, 33, 0),
                ("Mirador del Empire State", AC, 44, 2),
                ("Pizza, bagels y hot dogs", C, 180, 3),
                ("Musical en Broadway", AC, 150, 4),
                ("Regalos de Navidad", CO, 220, 5),
            ],
            "itinerario": [
                (1, "10:00", "Cruzar el puente de Brooklyn caminando", "Brooklyn"),
                (2, "18:00", "Mirador del Empire State", "Midtown"),
                (3, "11:00", "Central Park con nieve", "Central Park"),
                (4, "19:30", "Musical en Broadway", "Times Square"),
                (6, None, "Navidad en el Rockefeller Center", "Midtown"),
            ],
            "notas": (
                "Navidad en Nueva York con mi familia.\n"
                "Lo mejor: Central Park nevado y el árbol del Rockefeller Center.\n"
                "Un dato: hace muchísimo frío en diciembre; hay que llevar gorro, guantes y primera capa.\n"
                "¿Volvería? Sí, pero en primavera."
            ),
        },
        "CL": {
            "destino": "Torres del Paine",
            "fechas": (date(2022, 2, 10), date(2022, 2, 16)),
            "calificacion": 5,
            "favorito": True,
            "presupuesto": 1_300_000,
            "pasaje": 280_000,
            "moneda": None,  # en Chile: todo en pesos
            "cambio": 1,
            "gastos": [
                ("Refugios del circuito W", A, 540_000, 1),
                ("Bus Puerto Natales-Torres del Paine", T, 30_000, 1),
                ("Entrada al parque", AC, 49_000, 1),
                ("Comida para el trekking", C, 85_000, 0),
                ("Catamarán del lago Pehoé", T, 45_000, 3),
            ],
            "itinerario": [
                (1, "08:00", "Subida a la base de las Torres", "Sector Central"),
                (2, None, "Caminata al refugio Los Cuernos", "Circuito W"),
                (3, "09:00", "Valle del Francés", "Circuito W"),
                (4, "10:00", "Mirador del glaciar Grey", "Sector Grey"),
                (5, "15:00", "Catamarán por el lago Pehoé", "Pudeto"),
            ],
            "notas": (
                "Hicimos el circuito W completo en cinco días con dos amigos.\n"
                "Lo mejor: llegar a la base de las Torres al amanecer, después de dos horas de subida.\n"
                "Un dato: el viento en la Patagonia es brutal; los bastones de trekking salvan las rodillas.\n"
                "¿Volvería? Sí, a hacer el circuito O."
            ),
        },
        "EC": {
            "destino": "Galápagos y Quito",
            "fechas": (date(2022, 10, 1), date(2022, 10, 10)),
            "calificacion": 5,
            "favorito": True,
            "presupuesto": 3_000_000,
            "pasaje": 690_000,
            "moneda": "USD",
            "cambio": 930,
            "gastos": [
                ("Crucero de 4 días por las islas", AC, 1_800, 3),
                ("Tasa de ingreso al Parque Galápagos", AC, 100, 2),
                ("Hotel en el centro histórico de Quito", A, 180, 0),
                ("Vuelo Quito-Galápagos", T, 420, 2),
                ("Ceviche y encebollado", C, 90, 1),
            ],
            "itinerario": [
                (0, "15:00", "Centro histórico e iglesia de La Compañía", "Quito"),
                (1, "09:00", "Mitad del Mundo", "San Antonio de Pichincha"),
                (2, None, "Vuelo a Galápagos", "Isla Baltra"),
                (3, "10:00", "Tortugas gigantes en la reserva El Chato", "Santa Cruz"),
                (5, "08:00", "Snorkel con lobos marinos", "Isla Bartolomé"),
                (6, "16:00", "Piqueros de patas azules", "Isla Seymour Norte"),
            ],
            "notas": (
                "Dos días en Quito y el resto recorriendo las islas en crucero.\n"
                "Lo mejor: nadar con lobos marinos que se acercan a jugar.\n"
                "Un dato: los animales no le tienen miedo a la gente, pero hay que mantener dos metros de distancia.\n"
                "¿Volvería? Es el mejor viaje que he hecho."
            ),
        },
        "GB": {
            "destino": "Londres y Edimburgo",
            "fechas": (date(2023, 6, 5), date(2023, 6, 13)),
            "calificacion": 4,
            "favorito": False,
            "presupuesto": 2_600_000,
            "pasaje": 1_150_000,
            "moneda": "GBP",
            "cambio": 1_050,
            "gastos": [
                ("Hotel en South Kensington", A, 620, 0),
                ("Oyster card", T, 60, 0),
                ("Tren Londres-Edimburgo", T, 95, 5),
                ("Castillo de Edimburgo", AC, 20, 6),
                ("Fish and chips y pubs", C, 160, 3),
            ],
            "itinerario": [
                (1, "10:00", "Torre de Londres y Tower Bridge", "Londres"),
                (2, "11:00", "Museo Británico", "Bloomsbury"),
                (3, "17:00", "Westminster y el Big Ben al atardecer", "Westminster"),
                (5, "09:00", "Tren a Edimburgo", "King's Cross"),
                (6, "10:00", "Castillo de Edimburgo y la Royal Mile", "Edimburgo"),
                (7, "15:00", "Subida al Arthur's Seat", "Edimburgo"),
            ],
            "notas": (
                "Cinco días en Londres y tres en Edimburgo, en tren.\n"
                "Lo mejor: la vista de Edimburgo desde el Arthur's Seat.\n"
                "Un dato: casi todos los museos de Londres son gratis.\n"
                "¿Volvería? Sí, a recorrer las Highlands."
            ),
        },
        "NL": {
            "destino": "Ámsterdam",
            "fechas": (date(2023, 6, 14), date(2023, 6, 17)),
            "calificacion": 4,
            "favorito": False,
            "presupuesto": 800_000,
            "pasaje": 0,  # siguió desde Edimburgo
            "moneda": "EUR",
            "cambio": 1_000,
            "gastos": [
                ("Vuelo Edimburgo-Ámsterdam", T, 110, 0),
                ("Hotel junto al canal", A, 390, 0),
                ("Arriendo de bicicleta", T, 36, 1),
                ("Rijksmuseum", AC, 22, 1),
                ("Stroopwafels y papas fritas", C, 70, 2),
            ],
            "itinerario": [
                (1, "09:00", "Paseo en bicicleta por los canales", "Jordaan"),
                (1, "14:00", "Rijksmuseum", "Museumplein"),
                (2, "10:00", "Molinos de Zaanse Schans", "Zaandam"),
                (3, "11:00", "Crucero por los canales", "Centro"),
            ],
            "notas": (
                "Cuatro días en Ámsterdam al final del viaje por el Reino Unido.\n"
                "Lo mejor: recorrer los canales en bicicleta como un local.\n"
                "Un dato: las bicicletas tienen preferencia; hay que mirar bien antes de cruzar la ciclovía.\n"
                "¿Volvería? Sí, en abril, para ver los tulipanes."
            ),
        },
        "CA": {
            "destino": "Banff y las Rocosas",
            "fechas": (date(2024, 8, 20), date(2024, 8, 29)),
            "calificacion": 5,
            "favorito": True,
            "presupuesto": 2_800_000,
            "pasaje": 1_240_000,
            "moneda": "CAD",
            "cambio": 690,
            "gastos": [
                ("Arriendo de auto", T, 780, 0),
                ("Cabaña en Canmore", A, 1_150, 0),
                ("Pase de Parques Nacionales", AC, 145, 0),
                ("Canoa en el lago Louise", AC, 140, 3),
                ("Poutine y pancakes con miel de maple", C, 260, 4),
            ],
            "itinerario": [
                (1, "06:00", "Amanecer en el lago Moraine", "Banff"),
                (2, "09:00", "Lago Louise y la casa de té Agnes", "Lake Louise"),
                (3, "15:00", "Canoa en el lago Louise", "Lake Louise"),
                (5, None, "Icefields Parkway hasta el lago Peyto", "Parkway 93"),
                (7, "10:00", "Góndola de Banff", "Sulphur Mountain"),
            ],
            "notas": (
                "Diez días en auto por Banff y la Icefields Parkway.\n"
                "Lo mejor: el lago Moraine al amanecer, con el agua turquesa y las diez montañas detrás.\n"
                "Un dato: al lago Moraine ya no se puede subir en auto; hay que reservar el bus del parque.\n"
                "¿Volvería? Sí, a Jasper."
            ),
        },
        "AU": {
            "destino": "Sídney y las Montañas Azules",
            "estado": EstadoViaje.EN_PROGRESO,
            "fechas": (INICIO_SIDNEY, INICIO_SIDNEY + timedelta(days=9)),
            "calificacion": 5,
            "favorito": False,
            "presupuesto": 3_200_000,
            "pasaje": 1_690_000,
            "moneda": "AUD",
            "cambio": 620,
            "gastos": [
                ("Departamento en Circular Quay", A, 1_600, 0),
                ("Tarjeta Opal (transporte)", T, 60, 0),
                ("Visita guiada a la Ópera de Sídney", AC, 45, 1),
                ("Tour a las Montañas Azules", AC, 180, 2),
                ("Brunch con palta en tostada", C, 110, 3),
            ],
            "itinerario": [
                (1, "10:00", "Visita guiada a la Ópera", "Bennelong Point"),
                (1, "18:00", "Atardecer desde el Harbour Bridge", "The Rocks"),
                (2, "07:30", "Tour a las Montañas Azules y las Tres Hermanas", "Katoomba"),
                (3, "11:00", "Caminata costera de Bondi a Coogee", "Bondi Beach"),
                (5, "09:00", "Ferry a Manly", "Circular Quay"),
                (7, "10:00", "Zoológico de Taronga", "Mosman"),
            ],
            "notas": (
                "Estoy en Sídney: diez días con base en Circular Quay.\n"
                "Lo mejor hasta ahora: el tour a las Montañas Azules y el mirador de las Tres Hermanas.\n"
                "Un dato: la tarjeta Opal sirve para buses, trenes y ferris, y los domingos el tope es muy barato.\n"
                "Pendiente: el ferry a Manly y el zoológico de Taronga."
            ),
        },
    },
    "planificados": [
        ("Queenstown", "NZ", 150, 14, "Milford Sound, el lago Wakatipu y, si me atrevo, el bungee de Kawarau."),
    ],
    "fotos": FOTOS,
    "publicos": ["CL", "CA"],
}

USUARIOS = (VALENTINA, MATIAS)
# (dueño, país del viaje, con quién lo comparte): para que se vea «Compartidos conmigo».
COMPARTIDOS = [("Valentina", "GR", "Matias"), ("Matias", "GB", "Valentina")]


class Command(BaseCommand):
    help = "Crea los usuarios demo Valentina (5 viajes) y Matias (8 viajes), con todo relleno."

    def add_arguments(self, parser):
        parser.add_argument("--eliminar", action="store_true", help="Borra ambos usuarios con sus viajes y fotos.")

    def handle(self, *args, **opciones):
        if opciones["eliminar"]:
            for datos in USUARIOS:
                CargadorDemo(self, datos).eliminar()
            return
        if not settings.FOTOS_HABILITADAS:
            raise CommandError("Las fotos no están habilitadas (falta configurar Supabase Storage).")

        usuarios = {datos["usuario"]: CargadorDemo(self, datos).cargar(datos["contrasena"]) for datos in USUARIOS}
        for dueno, pais, invitado in COMPARTIDOS:
            viaje = usuarios[dueno].viajes.get(pais__codigo_iso=pais)
            viaje.compartido_con.add(usuarios[invitado])
            self.stdout.write(f"  «{viaje.destino}» de {dueno} compartido con {invitado}.")
