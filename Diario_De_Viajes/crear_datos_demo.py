"""
Script de datos de ejemplo. Crea:
  - 1 superusuario (admin / admin12345) con acceso total.
  - 2 usuarios normales (pareja / pareja12345 y viajero / viajero12345)
    con distintos permisos, para poder mostrar el control de permisos.
  - 6+ viajes repartidos entre ellos, con fechas pasadas, presentes y
    futuras, para que el estado automático se vea con los 3 colores.

Ejecutar con:  ./venv/bin/python manage.py shell < crear_datos_demo.py
"""
import datetime
import io

from django.contrib.auth.models import User
from django.core.files.base import ContentFile

from viajes.models import FotoViaje, Mg, PerfilUsuario, Viaje

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    Image = None

hoy = datetime.date.today()

# --- Superusuario ---
if not User.objects.filter(username="admin").exists():
    admin = User.objects.create_superuser("admin", "admin@example.com", "admin12345")
else:
    admin = User.objects.get(username="admin")

# --- Usuario con permiso para crear y ver otros (el "viajero" dueño de la cuenta) ---
if not User.objects.filter(username="viajero").exists():
    viajero = User.objects.create_user("viajero", "viajero@example.com", "viajero12345")
else:
    viajero = User.objects.get(username="viajero")
PerfilUsuario.objects.update_or_create(
    usuario=viajero, defaults={"puede_crear_viajes": True, "puede_ver_otros": True}
)

# --- Usuario "pareja": solo puede VER los viajes de los demás, no crear ---
if not User.objects.filter(username="pareja").exists():
    pareja = User.objects.create_user("pareja", "pareja@example.com", "pareja12345")
else:
    pareja = User.objects.get(username="pareja")
PerfilUsuario.objects.update_or_create(
    usuario=pareja, defaults={"puede_crear_viajes": False, "puede_ver_otros": True}
)

# --- Usuario "nuevo": recién registrado, sin permisos todavía (para demostrar el flujo) ---
if not User.objects.filter(username="nuevo").exists():
    nuevo = User.objects.create_user("nuevo", "nuevo@example.com", "nuevo12345")
else:
    nuevo = User.objects.get(username="nuevo")
PerfilUsuario.objects.update_or_create(
    usuario=nuevo, defaults={"puede_crear_viajes": False, "puede_ver_otros": False}
)

viajes_demo = [
    dict(
        propietario=viajero, destino="Cartagena", pais="Colombia",
        fecha_inicio=hoy - datetime.timedelta(days=200),
        fecha_fin=hoy - datetime.timedelta(days=190),
        notas="Primer viaje internacional. El centro histórico es hermoso, comimos arepas de huevo todos los días.",
    ),
    dict(
        propietario=viajero, destino="Bali", pais="Indonesia",
        fecha_inicio=hoy - datetime.timedelta(days=60),
        fecha_fin=hoy - datetime.timedelta(days=45),
        notas="Templos increíbles, el arroz de Tegallalang vale totalmente la pena.",
    ),
    dict(
        propietario=viajero, destino="Buenos Aires", pais="Argentina",
        fecha_inicio=hoy - datetime.timedelta(days=3),
        fecha_fin=hoy + datetime.timedelta(days=4),
        notas="Viaje actual: recorriendo San Telmo y Palermo con la pareja.",
    ),
    dict(
        propietario=viajero, destino="París", pais="Francia",
        fecha_inicio=hoy + datetime.timedelta(days=90),
        fecha_fin=hoy + datetime.timedelta(days=100),
        notas="Pendiente: reservar el Louvre con anticipación.",
    ),
    dict(
        propietario=pareja, destino="Tokio", pais="Japón",
        fecha_inicio=hoy - datetime.timedelta(days=400),
        fecha_fin=hoy - datetime.timedelta(days=385),
        notas="Viaje en cerezos en flor, uno de los mejores recuerdos juntos.",
    ),
    dict(
        propietario=pareja, destino="Cancún", pais="México",
        fecha_inicio=hoy + datetime.timedelta(days=30),
        fecha_fin=hoy + datetime.timedelta(days=37),
        notas="",
    ),
]

creados = []
for datos in viajes_demo:
    v, _ = Viaje.objects.get_or_create(
        propietario=datos["propietario"], destino=datos["destino"], pais=datos["pais"],
        defaults=datos,
    )
    creados.append(v)

# Algunos "mg" cruzados entre usuarios
Mg.objects.get_or_create(viaje=creados[0], usuario=pareja)
Mg.objects.get_or_create(viaje=creados[1], usuario=pareja)
Mg.objects.get_or_create(viaje=creados[4], usuario=viajero)


def _imagen_de_ejemplo(texto, color_fondo):
    """Genera una imagen simple tipo postal (no es una foto real) solo para
    que la demo se vea completa. El usuario sube sus propias fotos reales."""
    img = Image.new("RGB", (900, 600), color_fondo)
    dibujo = ImageDraw.Draw(img)
    try:
        fuente = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 60
        )
    except OSError:
        fuente = ImageFont.load_default()
    caja = dibujo.textbbox((0, 0), texto, font=fuente)
    ancho, alto = caja[2] - caja[0], caja[3] - caja[1]
    dibujo.text(
        ((900 - ancho) / 2, (600 - alto) / 2), texto, fill="white", font=fuente
    )
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=85)
    return ContentFile(buffer.getvalue(), name=f"{texto.lower().replace(' ', '_')}.jpg")


# Un par de fotos de ejemplo, solo para que se vea la función funcionando.
if Image is not None:
    fotos_demo = [
        (creados[0], "Cartagena", (230, 126, 34)),
        (creados[1], "Bali", (22, 160, 133)),
        (creados[4], "Tokio", (192, 57, 43)),
    ]
    for viaje, texto, color in fotos_demo:
        if not viaje.fotos.exists():
            FotoViaje.objects.create(viaje=viaje, imagen=_imagen_de_ejemplo(texto, color))

print("Datos demo creados:")
print(" - admin / admin12345 (superusuario)")
print(" - viajero / viajero12345 (puede crear y ver otros)")
print(" - pareja / pareja12345 (solo puede ver otros)")
print(" - nuevo / nuevo12345 (sin permisos, para demostrar el flujo de aprobación)")
print(f" - {Viaje.objects.count()} viajes en total")
