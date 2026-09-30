# Diario de Viajes

Aplicación web para registrar los viajes de una persona en una línea de tiempo: destinos, fechas,
estado (planificado, en progreso o completado), notas, itinerario día a día, presupuesto y gastos
(también en moneda extranjera), fotos, y la opción de compartirlos con otras personas.

- **Producción:** https://midiariodeviajes.onrender.com
- **Repositorio:** https://github.com/CarlosMatus00000008/BackEnd---Inacap
- **Integrantes:** Carlos Matus y Benjamin Ortiz
- **Asignatura:** Programación Back End (TI3V41) — INACAP
- **Evaluación:** Evaluación 2 — Caso 4: Diario de Viajes

## Funcionalidades principales

- **Cuentas:** registro con consentimiento de datos personales (Ley N° 19.628 y N° 21.719),
  inicio y cierre de sesión, perfil y cambio de contraseña.
- **CRUD de viajes:** crear, ver, editar y eliminar viajes, con validaciones de fechas y estado.
  Línea de tiempo con filtros (estado, año, búsqueda, favoritos) y paginación.
- **Itinerario:** actividades por día y hora, marcadas como realizadas o pendientes.
- **Dashboard del viaje:** en el detalle, días que faltan (planificado) o que quedan (en progreso),
  actividades pendientes y el porcentaje del presupuesto usado.
- **Acompañantes:** con quién se viajó (nombre, relación y correo opcional). El dueño los agrega y
  quita; quienes ven el viaje compartido ven solo nombre y relación.
- **Presupuesto y gastos:** gastos por categoría comparados con el presupuesto (barra de colores por
  categoría). Cada gasto puede registrar la moneda extranjera en que se pagó y el sitio calcula el
  cambio promedio.
- **Fotos:** hasta 10 por viaje, guardadas en Supabase Storage (bucket privado con enlaces firmados).
  Al subirlas se enderezan, se achican y se les quitan los metadatos EXIF (ubicación GPS).
- **Compartir:** un viaje se comparte en modo solo lectura con otros usuarios. Las fotos se pueden
  enviar por WhatsApp con un enlace privado que vence o se revoca.
- **Viajes públicos:** el dueño puede publicar un viaje; cualquier usuario con cuenta lo ve en
  «Viajes públicos» en solo lectura (portada, notas, itinerario y fotos; sin gastos, presupuesto,
  acompañantes ni con quién se compartió).
- **Estadísticas:** países y continentes visitados, días viajados, viajes por año, gráfico de torta
  (SVG) de gastos por categoría, gasto promedio por día y avance de los itinerarios.
- **Mapa mundi:** países visitados pintados en el mapa, con una tarjeta de los viajes de cada país.
- **Panel de administración:** columnas de presupuesto, gastos totales, días totales y público;
  filtros por temporalidad, estado y público; acciones masivas (marcar como completados,
  favoritos, exportar CSV) y edición de actividades, acompañantes, gastos y fotos dentro del viaje.

## Tecnologías

| Tecnología | Uso |
|---|---|
| Django 5.2 (Python) | Framework web: modelos, vistas, formularios, plantillas y admin |
| PostgreSQL en Supabase | Base de datos de producción (SQLite en desarrollo) |
| Supabase Storage | Almacenamiento de las fotos (compatible con S3, vía `django-storages` y `boto3`) |
| Render | Hosting de la aplicación (`render.yaml` y `build.sh`) |
| WhiteNoise | Sirve los archivos estáticos (CSS, JS, imágenes) en producción |
| Gunicorn | Servidor WSGI en producción |
| Pillow | Validación y procesamiento de las fotos |

## Modelo de datos

```
Pais ──< Viaje >── Usuario (dueño)
              ├──<< compartido_con (usuarios que pueden verlo, solo lectura)
              ├──< Actividad   (itinerario día a día)
              ├──< Acompanante (con quién viajó: nombre, relación y correo opcional)
              ├──< Gasto       (gastos del viaje, comparados con Viaje.presupuesto)
              ├──< FotoViaje   (fotos guardadas en Supabase Storage)
              └──< EnlaceFotos (enlaces privados para ver solo las fotos, enviados por WhatsApp)

Usuario ── PerfilUsuario (teléfono y consentimiento de datos personales)

«──<» = uno a muchos (ForeignKey) · «>>──<<» = muchos a muchos · «──» = uno a uno
```

| Tabla | Qué guarda |
|---|---|
| `Pais` | Catálogo de países (código ISO y continente), cargado por las migraciones |
| `Viaje` | Destino, país, fechas, estado, notas, favorito, calificación, presupuesto, si es público y con quién se comparte |
| `Actividad` | Actividad del itinerario: día, hora, lugar y si ya se realizó |
| `Acompanante` | Persona que acompañó el viaje: nombre, relación (pareja, familia, amistad, trabajo u otra) y correo opcional |
| `Gasto` | Descripción, categoría, monto en pesos, fecha y, opcionalmente, moneda y monto extranjeros |
| `FotoViaje` | Archivo de la foto y su crédito (si no es propia) |
| `EnlaceFotos` | Enlace privado a las fotos de un viaje: código, contacto, teléfono y vencimiento |
| `PerfilUsuario` | Teléfono y registro del consentimiento de datos personales |

**Decisión de diseño — sin modelo `Dia`:** el itinerario no necesita una tabla de días. Cada
`Actividad` tiene su fecha, y la vista las agrupa por día (`Actividad.numero_dia` da el número de
día dentro del viaje). Así no hay datos duplicados ni días vacíos que mantener.

**Mejora futura — acompañantes por actividad:** hoy los acompañantes son del viaje completo. Una
relación muchos a muchos `Actividad.acompanantes` permitiría registrar quién participó en cada
actividad; se dejó fuera para mantener el cambio acotado.

## Instalación local

Requisitos: Python 3.10 o superior y Git.

```bash
# 1. Clonar el repositorio y entrar a la carpeta
git clone https://github.com/CarlosMatus00000008/BackEnd---Inacap.git
cd BackEnd---Inacap

# 2. Crear y activar el entorno virtual
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# 3. Instalar las dependencias
pip install -r requirements.txt

# 4. Crear el archivo .env (ver la tabla de variables más abajo).
#    Sin DB_HOST se usa SQLite local (db.sqlite3).

# 5. Crear las tablas y cargar el catálogo de países
python manage.py migrate

# 6. Crear un superusuario para el panel de administración
python manage.py createsuperuser

# 7. Levantar el servidor
python manage.py runserver
```

El sitio queda en http://127.0.0.1:8000 y el admin en http://127.0.0.1:8000/admin/.

### Comandos útiles

| Comando | Qué hace |
|---|---|
| `python manage.py verificar_bd` | Comprueba la conexión a la base de datos: motor, versión, latencia, migraciones y cantidad de registros |
| `python manage.py cargar_demo` | Crea los usuarios de prueba `viajero` y `pareja` con viajes de ejemplo, dos de ellos públicos (`--contrasena` fija la contraseña; `--reiniciar` los vuelve a crear) |
| `python manage.py cargar_juanpablo` | Crea el usuario demo `JuanPablo` con 12 viajes, gastos y fotos, dos viajes públicos (`--eliminar` lo borra) |
| `python manage.py cargar_viajeros_demo` | Crea los usuarios demo `Valentina` (5 viajes) y `Matias` (8 viajes) con todo relleno y dos viajes públicos cada uno (`--eliminar` los borra) |

## Variables de entorno (`.env`)

El archivo `.env` **no se sube al repositorio** (está en `.gitignore`). Esta tabla solo describe las
variables; nunca escribas valores reales en el README ni en el código.

| Variable | Descripción |
|---|---|
| `SECRET_KEY` | Clave secreta de Django (obligatoria en producción) |
| `DEBUG` | `True` en desarrollo, `False` en producción |
| `ALLOWED_HOSTS` | Dominios permitidos, separados por coma |
| `CSRF_TRUSTED_ORIGINS` | Orígenes confiables para formularios (con `https://`), separados por coma |
| `RENDER_EXTERNAL_HOSTNAME` | Dominio que entrega Render; se agrega solo a los hosts permitidos |
| `DB_HOST` | Servidor de PostgreSQL (Supabase). Si falta, se usa SQLite local |
| `DB_NAME` | Nombre de la base de datos |
| `DB_USER` | Usuario de la base de datos |
| `DB_PASSWORD` | Contraseña de la base de datos |
| `DB_PORT` | Puerto de la base de datos |
| `SUPABASE_S3_ENDPOINT` | Endpoint S3 de Supabase Storage |
| `SUPABASE_S3_ACCESS_KEY_ID` | Llave de acceso S3 de Supabase |
| `SUPABASE_S3_SECRET_ACCESS_KEY` | Llave secreta S3 de Supabase |
| `SUPABASE_S3_BUCKET` | Bucket donde se guardan las fotos |
| `SUPABASE_S3_REGION` | Región del bucket |
| `ADMIN_URL` | Ruta del panel de administración (permite ocultarla) |
| `COOKIES_SEGURAS` | Si las cookies de sesión y CSRF solo viajan por HTTPS |
| `SECURE_SSL_REDIRECT` | Si se redirige todo el tráfico a HTTPS |
| `SECURE_HSTS_SECONDS` | Duración de la política HSTS |
| `DJANGO_LOG_LEVEL` | Nivel de los registros (logs) |

## Seguridad implementada

- **Autenticación:** todo el sitio exige iniciar sesión (`LoginRequiredMiddleware`), salvo el
  inicio, el login, el registro y la página de fotos compartidas por enlace privado. «Viajes
  públicos» también exige sesión: «público» significa visible para usuarios con cuenta. El cierre de
  sesión es por POST, con token CSRF.
- **Permisos por grupo:** los usuarios nuevos entran al grupo «Viajeros», que tiene los permisos de
  Django para ver, crear, editar y eliminar sus datos. Sin ese permiso se muestra una página 403.
- **Permisos por dueño:** cada consulta se filtra por el usuario conectado. Si alguien cambia el
  número en la URL para ver un viaje ajeno, recibe 404. Los viajes compartidos son de solo lectura.
  Los viajes públicos se ven con vistas propias de solo lectura; editar, eliminar, gastos,
  acompañantes y fotos siguen siendo solo del dueño.
- **CSRF:** todos los formularios POST llevan `{% csrf_token %}`. Las cookies de CSRF son
  `HttpOnly` y `SameSite=Strict`.
- **Validación y sanitización:** los formularios validan tipos y reglas del negocio (fechas
  coherentes, estados, montos). El texto se limpia antes de guardarlo: se quitan etiquetas HTML y
  caracteres invisibles. Las fotos se validan con Pillow y se les quitan los metadatos EXIF.
- **ORM de Django:** todas las consultas usan el ORM, que parametriza los valores (sin SQL armado
  a mano), así que no hay inyección SQL.
- **Content-Security-Policy estricta:** `script-src 'self'; style-src 'self'`, sin scripts ni
  estilos en línea. También `X-Frame-Options: DENY`, `nosniff` y `Permissions-Policy`.
- **HTTPS en producción:** redirección a HTTPS, HSTS y cookies seguras.
- **Enlaces de fotos:** código aleatorio de 43 caracteres, con vencimiento, revocables, sin indexar
  en buscadores y sin caché.

## Tests

```bash
python manage.py test        # todos los tests (usa una base temporal)
ruff check .                 # revisión de estilo y errores comunes
```

Si tu `.env` apunta a Supabase, corre los tests con `DB_HOST` vacío para usar SQLite:

```bash
DB_HOST= python manage.py test
```
