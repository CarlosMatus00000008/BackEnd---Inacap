# Diario de Viajes

Es una página web donde cada persona puede anotar sus viajes: a dónde fue, cuándo, qué hizo cada
día, cuánto gastó y sus fotos. Los viajes se ven en una línea de tiempo y se pueden compartir con
otras personas.

- **Página en línea:** https://midiariodeviajes.onrender.com
- **Repositorio:** https://github.com/CarlosMatus00000008/BackEnd---Inacap
- **Integrantes:** Carlos Matus y Benjamín Ortiz
- **Asignatura:** Programación Back End (TI3V41) — INACAP
- **Evaluación:** Evaluación 2 — Caso 4: Diario de Viajes

## Qué se puede hacer

- Crear una cuenta (aceptando el uso de datos personales), iniciar sesión y editar el perfil.
- Crear, ver, editar y eliminar viajes, con su estado: planificado, en progreso o completado.
- Buscar y filtrar los viajes por estado, año o favoritos.
- Armar el itinerario de cada día y marcar las actividades hechas.
- Anotar con quién se viajó.
- Registrar el presupuesto y los gastos, también en moneda extranjera.
- Subir hasta 10 fotos por viaje.
- Compartir un viaje con otro usuario, publicarlo en «Viajes públicos» o mandar las fotos por
  WhatsApp con un enlace privado que vence.
- Ver estadísticas: países visitados, días viajados, gastos por categoría y un mapa mundi.
- Administrar todo desde el panel de administración de Django.

## Con qué lo hicimos

- **Django 5.2** (Python) para la página.
- **PostgreSQL en Supabase** como base de datos (en local se puede usar SQLite).
- **Supabase Storage** para guardar las fotos.
- **Render** para publicar la página.
- **Pillow** para revisar y achicar las fotos.

## Cómo está organizado

El proyecto tiene tres apps:

- `cuentas`: registro, inicio de sesión y perfil.
- `viajes`: viajes, itinerario, acompañantes, gastos, fotos y estadísticas.
- `core`: lo común, como la página de inicio y la seguridad.

Las tablas principales son `Viaje`, `Pais`, `Actividad`, `Acompanante`, `Gasto`, `FotoViaje` y
`EnlaceFotos`. No hicimos una tabla de días: cada actividad guarda su fecha y la página las agrupa
por día.

## Cómo correrlo en tu computador

Necesitas Python 3.10 o más nuevo y Git.

```bash
git clone https://github.com/CarlosMatus00000008/BackEnd---Inacap.git
cd BackEnd---Inacap
python -m venv venv
venv\Scripts\activate              # en Mac o Linux: source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

La página queda en http://127.0.0.1:8000 y el panel de administración en http://127.0.0.1:8000/admin/.

Para tener datos de prueba puedes usar `python manage.py cargar_demo`.

## Archivo .env

Las claves van en un archivo `.env` que **no se sube a GitHub**. Si no lo creas, la página funciona
igual en local con SQLite. Las variables principales son:

- `SECRET_KEY` y `DEBUG`: configuración de Django.
- `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` y `DB_PORT`: conexión a la base de datos de Supabase.
- `SUPABASE_S3_ENDPOINT`, `SUPABASE_S3_ACCESS_KEY_ID`, `SUPABASE_S3_SECRET_ACCESS_KEY`,
  `SUPABASE_S3_BUCKET` y `SUPABASE_S3_REGION`: dónde se guardan las fotos.

## Seguridad

- Hay que iniciar sesión para usar la página, y cada usuario ve solo sus viajes (o los que le
  compartieron).
- Todos los formularios tienen protección CSRF.
- Los datos se validan antes de guardarse y a las fotos se les borra la ubicación GPS.
- La página solo ejecuta scripts propios (Content-Security-Policy) y en producción usa HTTPS.
- Las contraseñas y claves están en el `.env` o en Render, nunca en el código.

## Pruebas

```bash
python manage.py test
```

Si tu `.env` apunta a Supabase, deja `DB_HOST` vacío para que las pruebas usen SQLite.
