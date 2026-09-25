"""
Migración de datos: carga el catálogo de países (193 miembros de la ONU y
algunos territorios muy visitados) con su código ISO y su continente.
Es reversible: «migrate viajes 0001» los elimina.
"""

from django.db import migrations

PAISES = {
    "africa": [
        ("DZ", "Argelia"), ("AO", "Angola"), ("BJ", "Benín"), ("BW", "Botsuana"),
        ("BF", "Burkina Faso"), ("BI", "Burundi"), ("CV", "Cabo Verde"), ("CM", "Camerún"),
        ("CF", "República Centroafricana"), ("TD", "Chad"), ("KM", "Comoras"),
        ("CG", "República del Congo"), ("CD", "República Democrática del Congo"),
        ("CI", "Costa de Marfil"), ("DJ", "Yibuti"), ("EG", "Egipto"), ("GQ", "Guinea Ecuatorial"),
        ("ER", "Eritrea"), ("SZ", "Esuatini"), ("ET", "Etiopía"), ("GA", "Gabón"), ("GM", "Gambia"),
        ("GH", "Ghana"), ("GN", "Guinea"), ("GW", "Guinea-Bisáu"), ("KE", "Kenia"), ("LS", "Lesoto"),
        ("LR", "Liberia"), ("LY", "Libia"), ("MG", "Madagascar"), ("MW", "Malaui"), ("ML", "Malí"),
        ("MR", "Mauritania"), ("MU", "Mauricio"), ("MA", "Marruecos"), ("MZ", "Mozambique"),
        ("NA", "Namibia"), ("NE", "Níger"), ("NG", "Nigeria"), ("RW", "Ruanda"),
        ("ST", "Santo Tomé y Príncipe"), ("SN", "Senegal"), ("SC", "Seychelles"),
        ("SL", "Sierra Leona"), ("SO", "Somalia"), ("ZA", "Sudáfrica"), ("SS", "Sudán del Sur"),
        ("SD", "Sudán"), ("TZ", "Tanzania"), ("TG", "Togo"), ("TN", "Túnez"), ("UG", "Uganda"),
        ("ZM", "Zambia"), ("ZW", "Zimbabue"),
    ],
    "america_norte": [
        ("CA", "Canadá"), ("US", "Estados Unidos"), ("MX", "México"), ("GL", "Groenlandia"),
    ],
    "america_central": [
        ("BZ", "Belice"), ("CR", "Costa Rica"), ("SV", "El Salvador"), ("GT", "Guatemala"),
        ("HN", "Honduras"), ("NI", "Nicaragua"), ("PA", "Panamá"), ("AG", "Antigua y Barbuda"),
        ("BS", "Bahamas"), ("BB", "Barbados"), ("CU", "Cuba"), ("DM", "Dominica"),
        ("DO", "República Dominicana"), ("GD", "Granada"), ("HT", "Haití"), ("JM", "Jamaica"),
        ("KN", "San Cristóbal y Nieves"), ("LC", "Santa Lucía"),
        ("VC", "San Vicente y las Granadinas"), ("TT", "Trinidad y Tobago"),
        ("PR", "Puerto Rico"), ("AW", "Aruba"), ("CW", "Curazao"),
    ],
    "america_sur": [
        ("AR", "Argentina"), ("BO", "Bolivia"), ("BR", "Brasil"), ("CL", "Chile"),
        ("CO", "Colombia"), ("EC", "Ecuador"), ("GY", "Guyana"), ("PY", "Paraguay"),
        ("PE", "Perú"), ("SR", "Surinam"), ("UY", "Uruguay"), ("VE", "Venezuela"),
    ],
    "asia": [
        ("AF", "Afganistán"), ("SA", "Arabia Saudita"), ("AM", "Armenia"), ("AZ", "Azerbaiyán"),
        ("BH", "Baréin"), ("BD", "Bangladés"), ("BT", "Bután"), ("BN", "Brunéi"), ("KH", "Camboya"),
        ("QA", "Catar"), ("CN", "China"), ("KP", "Corea del Norte"), ("KR", "Corea del Sur"),
        ("AE", "Emiratos Árabes Unidos"), ("PH", "Filipinas"), ("GE", "Georgia"), ("IN", "India"),
        ("ID", "Indonesia"), ("IQ", "Irak"), ("IR", "Irán"), ("IL", "Israel"), ("JP", "Japón"),
        ("JO", "Jordania"), ("KZ", "Kazajistán"), ("KG", "Kirguistán"), ("KW", "Kuwait"),
        ("LA", "Laos"), ("LB", "Líbano"), ("MY", "Malasia"), ("MV", "Maldivas"), ("MN", "Mongolia"),
        ("MM", "Myanmar"), ("NP", "Nepal"), ("OM", "Omán"), ("PK", "Pakistán"), ("SG", "Singapur"),
        ("SY", "Siria"), ("LK", "Sri Lanka"), ("TJ", "Tayikistán"), ("TH", "Tailandia"),
        ("TL", "Timor Oriental"), ("TM", "Turkmenistán"), ("TR", "Turquía"), ("UZ", "Uzbekistán"),
        ("VN", "Vietnam"), ("YE", "Yemen"), ("TW", "Taiwán"), ("HK", "Hong Kong"), ("MO", "Macao"),
        ("PS", "Palestina"),
    ],
    "europa": [
        ("AL", "Albania"), ("DE", "Alemania"), ("AD", "Andorra"), ("AT", "Austria"), ("BE", "Bélgica"),
        ("BY", "Bielorrusia"), ("BA", "Bosnia y Herzegovina"), ("BG", "Bulgaria"), ("CY", "Chipre"),
        ("HR", "Croacia"), ("DK", "Dinamarca"), ("SK", "Eslovaquia"), ("SI", "Eslovenia"),
        ("ES", "España"), ("EE", "Estonia"), ("FI", "Finlandia"), ("FR", "Francia"), ("GR", "Grecia"),
        ("HU", "Hungría"), ("IE", "Irlanda"), ("IS", "Islandia"), ("IT", "Italia"), ("LV", "Letonia"),
        ("LI", "Liechtenstein"), ("LT", "Lituania"), ("LU", "Luxemburgo"), ("MK", "Macedonia del Norte"),
        ("MT", "Malta"), ("MD", "Moldavia"), ("MC", "Mónaco"), ("ME", "Montenegro"), ("NO", "Noruega"),
        ("NL", "Países Bajos"), ("PL", "Polonia"), ("PT", "Portugal"), ("GB", "Reino Unido"),
        ("CZ", "Chequia"), ("RO", "Rumania"), ("RU", "Rusia"), ("SM", "San Marino"), ("RS", "Serbia"),
        ("SE", "Suecia"), ("CH", "Suiza"), ("UA", "Ucrania"), ("VA", "Ciudad del Vaticano"),
    ],
    "oceania": [
        ("AU", "Australia"), ("FJ", "Fiyi"), ("MH", "Islas Marshall"), ("SB", "Islas Salomón"),
        ("KI", "Kiribati"), ("FM", "Micronesia"), ("NR", "Nauru"), ("NZ", "Nueva Zelanda"),
        ("PW", "Palaos"), ("PG", "Papúa Nueva Guinea"), ("WS", "Samoa"), ("TO", "Tonga"),
        ("TV", "Tuvalu"), ("VU", "Vanuatu"), ("PF", "Polinesia Francesa"),
    ],
}


def cargar_paises(apps, schema_editor):
    Pais = apps.get_model("viajes", "Pais")
    nuevos = [
        Pais(codigo_iso=codigo, nombre=nombre, continente=continente)
        for continente, paises in PAISES.items()
        for codigo, nombre in paises
    ]
    Pais.objects.bulk_create(nuevos, ignore_conflicts=True)


def eliminar_paises(apps, schema_editor):
    Pais = apps.get_model("viajes", "Pais")
    codigos = [codigo for paises in PAISES.values() for codigo, _ in paises]
    Pais.objects.filter(codigo_iso__in=codigos, viajes__isnull=True).delete()


class Migration(migrations.Migration):
    dependencies = [("viajes", "0001_initial")]

    operations = [migrations.RunPython(cargar_paises, eliminar_paises)]
