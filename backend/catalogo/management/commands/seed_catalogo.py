from datetime import date

from django.core.management.base import BaseCommand

from catalogo.models import Categoria, Genero, OfertaVideojuego, Plataforma, Videojuego
from cuentas.models import Rol


class Command(BaseCommand):
    help = "Pobla la base de datos con datos de prueba para Arkane Zone."

    def handle(self, *args, **kwargs):
        roles_creados = self._seed_roles()
        cats_creadas = self._seed_categorias()
        plats_creadas = self._seed_plataformas()
        gens_creados = self._seed_generos()
        juegos_creados, ofertas_creadas = self._seed_catalogo_comercial()

        self.stdout.write(self.style.SUCCESS("\n=== Seed completado ==="))
        self.stdout.write(f"  Roles:        {roles_creados} creados")
        self.stdout.write(f"  Categorías:   {cats_creadas} creadas")
        self.stdout.write(f"  Plataformas:  {plats_creadas} creadas")
        self.stdout.write(f"  Géneros:      {gens_creados} creados")
        self.stdout.write(f"  Videojuegos:  {juegos_creados} creados")
        self.stdout.write(f"  Ofertas:      {ofertas_creadas} creadas")

    # ------------------------------------------------------------------
    def _seed_roles(self):
        creados = 0
        for nombre in ["cliente", "administrador"]:
            _, nuevo = Rol.objects.get_or_create(nombre=nombre)
            if nuevo:
                creados += 1
        return creados

    def _seed_categorias(self):
        datos = [
            ("Acción", "Juegos de ritmo rápido con combate y reflejos."),
            ("Deportes", "Simulaciones de deportes reales o fantásticos."),
            ("Aventura", "Exploración, narrativa y resolución de acertijos."),
            ("Carreras", "Competencias de velocidad en circuitos y mundo abierto."),
            ("Estrategia", "Planificación táctica y gestión de recursos."),
            ("RPG", "Desarrollo de personaje y narrativa profunda."),
        ]
        creados = 0
        for nombre, desc in datos:
            _, nuevo = Categoria.objects.get_or_create(nombre=nombre, defaults={"descripcion": desc})
            if nuevo:
                creados += 1
        return creados

    def _seed_plataformas(self):
        datos = [
            ("PC", "Computadores personales con Windows/Linux/Mac."),
            ("PlayStation 5", "Consola de Sony de novena generación."),
            ("Xbox Series X", "Consola de Microsoft de novena generación."),
            ("Nintendo Switch", "Consola híbrida portátil/sobremesa de Nintendo."),
        ]
        creados = 0
        for nombre, desc in datos:
            _, nuevo = Plataforma.objects.get_or_create(nombre=nombre, defaults={"descripcion": desc})
            if nuevo:
                creados += 1
        return creados

    def _seed_generos(self):
        datos = [
            ("Shooter", "Juegos de disparos en primera o tercera persona."),
            ("Mundo abierto", "Exploración libre en mapas extensos."),
            ("Deportivo", "Mecánicas basadas en deportes reales."),
            ("Plataformas", "Saltos y obstáculos en escenarios variados."),
            ("Rol", "Progresión de personaje con habilidades y equipo."),
            ("Simulación", "Recreación realista de actividades o entornos."),
        ]
        creados = 0
        for nombre, desc in datos:
            _, nuevo = Genero.objects.get_or_create(nombre=nombre, defaults={"descripcion": desc})
            if nuevo:
                creados += 1
        return creados

    def _seed_catalogo_comercial(self):
        """
        Pobla la identidad de los videojuegos y sus ofertas por plataforma.
        Un mismo título puede venderse en varias plataformas con precio,
        SKU y stock propios.
        """
        cat = {c.nombre: c for c in Categoria.objects.all()}
        plt = {p.nombre: p for p in Plataforma.objects.all()}
        gen = {g.nombre: g for g in Genero.objects.all()}

        juegos = [
            {
                "titulo": "God of War Ragnarök",
                "descripcion": "Kratos y Atreus enfrentan el Ragnarök nórdico en una épica aventura de acción.",
                "fecha_lanzamiento": date(2022, 11, 9),
                "categoria": cat["Acción"],
                "genero": gen["Mundo abierto"],
                "ofertas": [
                    {"plataforma": "PlayStation 5", "precio": 219900, "stock": 10},
                    {"plataforma": "PC", "precio": 199900, "stock": 6},
                ],
            },
            {
                "titulo": "The Legend of Zelda: Tears of the Kingdom",
                "descripcion": "Link explora Hyrule y los cielos en una nueva aventura de mundo abierto.",
                "fecha_lanzamiento": date(2023, 5, 12),
                "categoria": cat["Aventura"],
                "genero": gen["Mundo abierto"],
                "ofertas": [
                    {"plataforma": "Nintendo Switch", "precio": 249900, "stock": 8},
                ],
            },
            {
                "titulo": "Elden Ring",
                "descripcion": "RPG de acción oscura en el vasto mundo entre-tierras, creado con George R.R. Martin.",
                "fecha_lanzamiento": date(2022, 2, 25),
                "categoria": cat["RPG"],
                "genero": gen["Rol"],
                "ofertas": [
                    {"plataforma": "PC", "precio": 199900, "stock": 15},
                    {"plataforma": "PlayStation 5", "precio": 209900, "stock": 7},
                    {"plataforma": "Xbox Series X", "precio": 209900, "stock": 4},
                ],
            },
            {
                "titulo": "FIFA 24",
                "descripcion": "La entrega anual de fútbol con licencias oficiales de ligas y selecciones.",
                "fecha_lanzamiento": date(2023, 9, 29),
                "categoria": cat["Deportes"],
                "genero": gen["Deportivo"],
                "ofertas": [
                    {"plataforma": "PlayStation 5", "precio": 189900, "stock": 20},
                    {"plataforma": "Xbox Series X", "precio": 189900, "stock": 12},
                    {"plataforma": "PC", "precio": 149900, "stock": 9},
                ],
            },
            {
                "titulo": "Forza Horizon 5",
                "descripcion": "Carreras en mundo abierto ambientadas en los coloridos paisajes de México.",
                "fecha_lanzamiento": date(2021, 11, 9),
                "categoria": cat["Carreras"],
                "genero": gen["Mundo abierto"],
                "ofertas": [
                    {"plataforma": "Xbox Series X", "precio": 179900, "stock": 12},
                    {"plataforma": "PC", "precio": 169900, "stock": 5},
                ],
            },
            {
                "titulo": "Halo Infinite",
                "descripcion": "El Jefe Maestro regresa en un shooter de ciencia ficción épico y multijugador.",
                "fecha_lanzamiento": date(2021, 12, 8),
                "categoria": cat["Acción"],
                "genero": gen["Shooter"],
                "ofertas": [
                    {"plataforma": "Xbox Series X", "precio": 159900, "stock": 9},
                ],
            },
            {
                "titulo": "Hogwarts Legacy",
                "descripcion": "Vive tu propia historia en el mundo mágico del siglo XIX del universo Harry Potter.",
                "fecha_lanzamiento": date(2023, 2, 10),
                "categoria": cat["RPG"],
                "genero": gen["Rol"],
                "ofertas": [
                    {"plataforma": "PlayStation 5", "precio": 209900, "stock": 7},
                    {"plataforma": "PC", "precio": 189900, "stock": 0},
                ],
            },
            {
                "titulo": "Super Mario Bros. Wonder",
                "descripcion": "Mario y sus amigos exploran el Reino de las Flores con nuevas mecánicas Wonder.",
                "fecha_lanzamiento": date(2023, 10, 20),
                "categoria": cat["Acción"],
                "genero": gen["Plataformas"],
                "ofertas": [
                    {"plataforma": "Nintendo Switch", "precio": 229900, "stock": 14},
                ],
            },
            {
                "titulo": "Cyberpunk 2077",
                "descripcion": "RPG de mundo abierto en Night City, una megalópolis del futuro obsesionada con el poder.",
                "fecha_lanzamiento": date(2020, 12, 10),
                "categoria": cat["RPG"],
                "genero": gen["Mundo abierto"],
                "ofertas": [
                    {"plataforma": "PC", "precio": 149900, "stock": 18},
                    {"plataforma": "PlayStation 5", "precio": 159900, "stock": 5},
                ],
            },
            {
                "titulo": "NBA 2K24",
                "descripcion": "La simulación de baloncesto más completa con modos carrera, MyTeam y online.",
                "fecha_lanzamiento": date(2023, 9, 8),
                "categoria": cat["Deportes"],
                "genero": gen["Deportivo"],
                "ofertas": [
                    {"plataforma": "Xbox Series X", "precio": 189900, "stock": 11},
                ],
            },
            {
                "titulo": "Age of Empires IV",
                "descripcion": "Estrategia en tiempo real con civilizaciones históricas de la Edad Media.",
                "fecha_lanzamiento": date(2021, 10, 28),
                "categoria": cat["Estrategia"],
                "genero": gen["Simulación"],
                "ofertas": [
                    {"plataforma": "PC", "precio": 139900, "stock": 6},
                ],
            },
            {
                "titulo": "Gran Turismo 7",
                "descripcion": "Simulador de carreras con más de 400 autos licenciados y físicas ultra realistas.",
                "fecha_lanzamiento": date(2022, 3, 4),
                "categoria": cat["Carreras"],
                "genero": gen["Simulación"],
                "ofertas": [
                    {"plataforma": "PlayStation 5", "precio": 219900, "stock": 0},
                ],
            },
            {
                "titulo": "Baldur's Gate 3",
                "descripcion": "RPG por turnos basado en D&D con decisiones que moldean cada aspecto de la historia.",
                "fecha_lanzamiento": date(2023, 8, 3),
                "categoria": cat["RPG"],
                "genero": gen["Rol"],
                "ofertas": [
                    {"plataforma": "PC", "precio": 199900, "stock": 5},
                    {"plataforma": "PlayStation 5", "precio": 219900, "stock": 2},
                ],
            },
            {
                "titulo": "Mortal Kombat 1",
                "descripcion": "Reinicio de la saga con nuevos Kameos, historia épica y brutal combate en HD.",
                "fecha_lanzamiento": date(2023, 9, 19),
                "categoria": cat["Acción"],
                "genero": gen["Shooter"],
                "ofertas": [
                    {"plataforma": "PlayStation 5", "precio": 209900, "stock": 0},
                ],
            },
            {
                "titulo": "Starfield",
                "descripcion": "RPG espacial de Bethesda con más de 1000 planetas explorables y libertad total.",
                "fecha_lanzamiento": date(2023, 9, 6),
                "categoria": cat["Aventura"],
                "genero": gen["Mundo abierto"],
                "ofertas": [
                    {"plataforma": "Xbox Series X", "precio": 219900, "stock": 13},
                    {"plataforma": "PC", "precio": 209900, "stock": 3},
                ],
            },
        ]

        juegos_creados = 0
        ofertas_creadas = 0
        for datos in juegos:
            videojuego, nuevo = Videojuego.objects.get_or_create(
                titulo=datos["titulo"],
                defaults={
                    "descripcion": datos["descripcion"],
                    "fecha_lanzamiento": datos["fecha_lanzamiento"],
                    "categoria": datos["categoria"],
                    "genero": datos["genero"],
                },
            )
            if nuevo:
                juegos_creados += 1

            for oferta in datos["ofertas"]:
                plataforma = plt[oferta["plataforma"]]
                _, nueva = OfertaVideojuego.objects.get_or_create(
                    videojuego=videojuego,
                    plataforma=plataforma,
                    defaults={
                        "sku": f"AZ-{videojuego.pk:04d}-{plataforma.pk:03d}",
                        "precio_vigente": oferta["precio"],
                        "stock": oferta["stock"],
                    },
                )
                if nueva:
                    ofertas_creadas += 1

        return juegos_creados, ofertas_creadas
