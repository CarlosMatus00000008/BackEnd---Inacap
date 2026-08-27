# Diario de Viajes — Crear Viajes

Parte del CASO 4 (Persona 2): formulario para registrar un viaje nuevo.

## Instalación

```bash
python -m venv venv
venv\Scripts\activate        # Mac/Linux: source venv/bin/activate

pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Abrir: `http://127.0.0.1:8000/viajes/nuevo/`

## Estructura

```
diario_viajes/
├── manage.py
├── requirements.txt
├── diario_viajes/        # configuración del proyecto
└── viajes/                # app: Crear Viajes
    ├── models.py          # modelo Viaje
    ├── forms.py           # formulario + validaciones
    ├── views.py            # vista crear_viaje
    ├── urls.py              # ruta /viajes/nuevo/
    └── templates/viajes/crear_viaje.html
```

Solo incluye mi parte (Crear Viajes). El resto del equipo agrega sus partes por su lado.
