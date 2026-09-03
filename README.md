# Diario de Viajes

Proyecto para la Evaluación 1 de Programación Back End (Caso 4: Diario de Viajes y Destinos Pendientes). Es una app en Django donde cada usuario lleva un registro de los viajes que ha hecho o que planea hacer, con fecha, país, notas y hasta un par de fotos por viaje. El estado del viaje (completado, en progreso o planificado) no se elige a mano: se calcula solo, comparando las fechas con el día de hoy.

Además de lo mínimo que pedía la rúbrica le agregué un sistema de permisos (no cualquiera puede crear o ver viajes de otros), registro de usuarios, un "mg" tipo Instagram (me gusta, sin comentarios) y una vista de línea de tiempo por perfil. Más abajo explico cada cosa.

## Cómo levantarlo

cd proyecto
python3 -m venv venv
source venv/bin/activate          # en Windows: venv\Scripts\activate
pip install -r requirements.txt

python manage.py migrate
python manage.py runserver

Con eso ya queda funcionando en http://127.0.0.1:8000/. La base de datos (db.sqlite3) ya viene con datos de ejemplo cargados, así que se puede probar todo sin escribir nada a mano.

Si se prefiere partir de cero:

rm db.sqlite3
python manage.py migrate
python manage.py createsuperuser
python manage.py shell < crear_datos_demo.py   # opcional, carga usuarios y viajes de ejemplo

## Usuarios para probar

- admin / admin12345: Superusuario. Ve y edita todo, entra al admin de Django y al panel de permisos (/usuarios/)
- viajero / viajero12345: Puede crear y editar sus propios viajes, y ver los de los demás
- pareja / pareja12345: Solo puede ver los viajes de todos, no puede crear ni editar nada
- nuevo / nuevo12345: Se acaba de registrar y todavía no tiene ningún permiso, sirve para mostrar cómo funciona el flujo de aprobación

Al admin de Django se entra en /admin/ con admin / admin12345.

## Qué pide la rúbrica y dónde está

- Entorno (venv + Django 4.2): requirements.txt
- Proyecto + app: diario_viajes/ es el proyecto, viajes/ es la app
- App en INSTALLED_APPS: diario_viajes/settings.py
- Modelo con campos, tipos, __str__ y Meta.ordering: viajes/models.py, clase Viaje
- makemigrations / migrate: viajes/migrations/
- Vista con .all() y contexto: viajes/views.py, función lista_viajes()
- Template con {{ }}, {% for %}, {% if %}: viajes/templates/viajes/lista_viajes.html
- URLs con nombre: viajes/urls.py y diario_viajes/urls.py
- Admin registrado, superusuario, 5+ datos: viajes/admin.py, hay 6 viajes cargados de ejemplo

El modelo Viaje terminó con más de los 4 campos mínimos porque el Caso 4 pedía destino, país, fecha de inicio, estado y notas, y quise que cada uno tuviera el tipo correcto: CharField para texto, DateField para las fechas, y un CharField con choices para el estado.

## Lo que pedía el Caso 4

- Destino, país, fecha de inicio, estado y notas: son los campos del modelo Viaje.
- El estado se calcula solo, no se elige a mano: hay un método Viaje.calcular_estado() que se corre cada vez que se guarda un viaje, comparando fecha_inicio y fecha_fin con la fecha de hoy. El detalle es que el tiempo sigue pasando aunque nadie edite el viaje, así que cada vez que se carga la lista de viajes se recalculan todos los estados por si cambiaron solo por el paso de los días.
- Del más reciente al más antiguo: Meta.ordering = ['-fecha_inicio'] en el modelo, así que tanto el feed general como la línea de tiempo del perfil quedan ordenados así por defecto.
- Línea de tiempo por persona: el diseño de timeline vive solo en /perfil/<usuario>/. La página principal (/) es más bien un feed.
- Colores según el estado: gris para completado, azul para en progreso, verde para planificado, en viajes/static/viajes/css/style.css.
- Editar viaje, agregar notas, cambiar fechas: editar_viaje() en las vistas, usando ViajeForm.
- Crear viajes rápido desde la web: crear_viaje(), un formulario simple, sin tocar código.
- Que tu pareja pueda ver tus viajes pero no editarlos: lo resuelve el permiso puede_ver_otros, que da solo lectura. Sin puede_crear_viajes no aparecen los botones de crear ni editar, y la vista igual bloquea el acceso directo por URL.

## Cosas extra que agregué

No estaban pedidas en el mínimo del Caso 4, pero me parecieron necesarias para que el sistema tuviera sentido como algo real:

Permisos y superusuario: cualquier usuario con is_superuser=True recibe automáticamente los dos permisos activados, gracias a una señal en signals.py, y puede entrar al admin y al panel de gestión de usuarios.

Registro público: cualquiera puede crear una cuenta desde /registro/, pero queda sin ningún permiso hasta que un superusuario se lo dé.

Panel de permisos: en /usuarios/, el superusuario ve todos los usuarios y puede marcar, por cada uno, si puede crear viajes y/o ver los de los demás.

"Mg" tipo Instagram: un like simple (modelo Mg), sin comentarios. Un usuario solo puede darle mg a un viaje una vez.

Timeline por perfil: en /perfil/<usuario>/ se ve la línea de tiempo de esa persona, visible solo si es tu propio perfil o si tienes el permiso de ver otros.

Hasta 2 fotos por viaje: modelo FotoViaje, con el límite validado en las vistas de crear y editar, usando Pillow.

Alertas que se cierran solas: cuando alguien intenta hacer algo sin permiso, aparece una alerta que se cierra sola a los 4 segundos, en vez de un error en blanco.

El fondo del sitio: un mapa mundi real, fijo y difuminado, con un avioncito animado en puro CSS que respeta prefers-reduced-motion.

## Estructura

proyecto/
  manage.py
  requirements.txt
  crear_datos_demo.py        recrea los datos de ejemplo
  media/                     fotos subidas, se crea sola
  diario_viajes/             settings y urls del proyecto
  viajes/                    la app
    models.py                Viaje, PerfilUsuario, Mg, FotoViaje
    signals.py                crea el perfil al registrarse
    forms.py                  RegistroForm, ViajeForm
    views.py                  todas las vistas
    urls.py
    admin.py
    templatetags/viajes_extras.py   bandera, avatar, color
    static/viajes/             CSS propio + Bootstrap (vendorizado)
    templates/viajes/          los .html

## Para el día de la presentación

Orden que pienso seguir:

1. Arrancar el servidor y mostrar el admin (admin / admin12345) con los viajes ya cargados.
2. Entrar como viajero, mostrar la línea de tiempo, crear un viaje con fecha futura y otro con fecha pasada, y mostrar que el estado cambia solo.
3. Darle mg a un viaje y entrar a /perfil/viajero/.
4. Cerrar sesión, entrar como pareja (solo lectura) e intentar crear un viaje, para mostrar la alerta de "no tienes permiso".
5. Entrar como admin, ir a /usuarios/ y darle permiso al usuario nuevo en vivo.

### Las 4 preguntas técnicas

¿Qué es MVC? Es el patrón que separa la app en tres partes. El modelo es viajes/models.py, que define los datos; la vista (en el sentido de Django, la lógica) es viajes/views.py, que recibe la petición, le pide los datos al modelo y decide qué mostrar; y el template es el HTML en viajes/templates/, que solo dibuja lo que la vista le pasó. Por ejemplo, cuando alguien entra a /, la URL llama a lista_viajes(), esa función le pide los viajes al modelo con Viaje.objects.all(), y se los pasa a lista_viajes.html para que los muestre.

¿Qué hace .all()? Es un método del manager del modelo (Viaje.objects) que trae todos los registros de esa tabla desde la base de datos como una lista de objetos de Python. Se usa en lista_viajes() (y .filter() cuando hay que restringir por permisos) para traer los viajes y pasarlos al template.

Explica tu modelo: destino y pais son texto (CharField); fecha_inicio y fecha_fin son fechas (DateField); estado también es texto pero con opciones fijas (CharField con choices), y no se edita a mano, se recalcula solo en el save(); notas es texto largo (TextField). El Meta.ordering deja los viajes ordenados por -fecha_inicio, y el __str__ define cómo se ve el objeto como texto, por ejemplo en el admin.

¿Cómo funciona tu template? lista_viajes.html extiende base.html con {% extends %} para reusar el navbar y las alertas. Usa {{ viaje.destino }} para mostrar variables, {% for viaje in viajes %} para recorrer la lista que le llegó desde la vista, y {% if viaje.estado == 'completado' %} para decidir qué texto y color mostrar según el estado de cada viaje.
