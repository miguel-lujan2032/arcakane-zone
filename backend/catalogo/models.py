from django.db import models
from django.db.models.functions import Lower


def normalizar_nombre_catalogo(valor: str) -> str:
    """Recorta extremos y colapsa espacios internos (regla de carga AZ-S1-20).

    La unicidad de ``nombre`` en los catálogos maestros no distingue
    mayúsculas/minúsculas; esta función homogeneiza los espacios antes de
    insertar datos de referencia para que dos variantes visuales no convivan.
    """
    return " ".join(valor.split())


class Categoria(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"

    def __str__(self):
        return self.nombre


class Plataforma(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Plataforma"
        verbose_name_plural = "Plataformas"

    def __str__(self):
        return self.nombre


class Genero(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Género"
        verbose_name_plural = "Géneros"

    def __str__(self):
        return self.nombre


class Desarrolladora(models.Model):
    """
    Catálogo maestro de estudios que desarrollan videojuegos (AZ-S1-20).

    ``codigo`` es el identificador estable (slug) y ``nombre`` la etiqueta
    visible. La unicidad de ``nombre`` no distingue mayúsculas/minúsculas.
    """

    codigo = models.CharField(
        max_length=100,
        help_text="Identificador estable (slug); no es la etiqueta visible.",
    )
    nombre = models.CharField(max_length=150)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Desarrolladora"
        verbose_name_plural = "Desarrolladoras"
        ordering = ["nombre"]
        constraints = [
            models.UniqueConstraint(
                fields=["codigo"],
                name="catalogo_desarrolladora_codigo_unico",
            ),
            models.UniqueConstraint(
                Lower("nombre"),
                name="catalogo_desarrolladora_nombre_unico",
            ),
        ]

    def __str__(self):
        return self.nombre


class Distribuidora(models.Model):
    """
    Catálogo maestro de distribuidoras de videojuegos (AZ-S1-20).

    ``codigo`` es el identificador estable (slug) y ``nombre`` la etiqueta
    visible. La unicidad de ``nombre`` no distingue mayúsculas/minúsculas.
    """

    codigo = models.CharField(
        max_length=100,
        help_text="Identificador estable (slug); no es la etiqueta visible.",
    )
    nombre = models.CharField(max_length=150)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Distribuidora"
        verbose_name_plural = "Distribuidoras"
        ordering = ["nombre"]
        constraints = [
            models.UniqueConstraint(
                fields=["codigo"],
                name="catalogo_distribuidora_codigo_unico",
            ),
            models.UniqueConstraint(
                Lower("nombre"),
                name="catalogo_distribuidora_nombre_unico",
            ),
        ]

    def __str__(self):
        return self.nombre


class ClasificacionEdad(models.Model):
    """
    Catálogo único de clasificación por edad (PEGI) (AZ-S1-20).

    ``codigo`` es el identificador estable (3, 7, 12, 16, 18) y ``orden``
    define la presentación de menor a mayor. No se almacena una edad numérica
    libre en ``Videojuego``.
    """

    codigo = models.CharField(
        max_length=20,
        help_text="Código PEGI: 3, 7, 12, 16 o 18.",
    )
    nombre = models.CharField(max_length=50)
    orden = models.PositiveSmallIntegerField(
        help_text="Orden de presentación; menor primero."
    )

    class Meta:
        verbose_name = "Clasificación por edad"
        verbose_name_plural = "Clasificaciones por edad"
        ordering = ["orden", "codigo"]
        constraints = [
            models.UniqueConstraint(
                fields=["codigo"],
                name="catalogo_clasificacionedad_codigo_unico",
            ),
            models.UniqueConstraint(
                fields=["nombre"],
                name="catalogo_clasificacionedad_nombre_unico",
            ),
        ]

    def __str__(self):
        return self.nombre


class Idioma(models.Model):
    """
    Catálogo de idiomas con código ISO 639-1 (AZ-S1-20).

    ``codigo`` es el identificador estable de dos letras y ``nombre`` la
    etiqueta visible. La unicidad de ``nombre`` no distingue mayúsculas.
    """

    codigo = models.CharField(
        max_length=2,
        help_text="Código ISO 639-1 de dos letras (es, en, fr...).",
    )
    nombre = models.CharField(max_length=100)

    class Meta:
        verbose_name = "Idioma"
        verbose_name_plural = "Idiomas"
        ordering = ["nombre"]
        constraints = [
            models.UniqueConstraint(
                fields=["codigo"],
                name="catalogo_idioma_codigo_unico",
            ),
            models.UniqueConstraint(
                Lower("nombre"),
                name="catalogo_idioma_nombre_unico",
            ),
        ]

    def __str__(self):
        return self.nombre


class TipoIdioma(models.TextChoices):
    """Tipo de presencia de un idioma en un título (AZ-S1-20)."""

    AUDIO = "audio", "Audio"
    INTERFAZ = "interfaz", "Interfaz"
    SUBTITULOS = "subtitulos", "Subtítulos"


class Videojuego(models.Model):
    """
    Identidad e información común de un título.

    El videojuego NO conoce precio, stock ni plataforma: esos atributos
    dependen de la presentación comercial vendible (``OfertaVideojuego``),
    que combina este título con una plataforma concreta.
    """

    titulo = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    portada = models.ImageField(upload_to="portadas/", null=True, blank=True)
    fecha_lanzamiento = models.DateField(null=True, blank=True)
    # Un título puede pertenecer a varias categorías y géneros. El vínculo se
    # materializa en las tablas puente VideojuegoCategoria / VideojuegoGenero.
    categorias = models.ManyToManyField(
        Categoria,
        through="VideojuegoCategoria",
        related_name="videojuegos",
        blank=True,
    )
    generos = models.ManyToManyField(
        Genero,
        through="VideojuegoGenero",
        related_name="videojuegos",
        blank=True,
    )
    # Catálogos maestros del videojuego (AZ-S1-20). Desarrolladora y
    # distribuidora son M:N porque un título puede tener varios estudios y
    # varias distribuidoras por región. El idioma lleva el tipo de presencia
    # en la tabla puente.
    desarrolladoras = models.ManyToManyField(
        Desarrolladora,
        through="VideojuegoDesarrolladora",
        related_name="videojuegos",
        blank=True,
    )
    distribuidoras = models.ManyToManyField(
        Distribuidora,
        through="VideojuegoDistribuidora",
        related_name="videojuegos",
        blank=True,
    )
    idiomas = models.ManyToManyField(
        Idioma,
        through="VideojuegoIdioma",
        related_name="videojuegos",
        blank=True,
    )
    clasificacion_edad = models.ForeignKey(
        ClasificacionEdad,
        to_field="codigo",
        db_column="clasificacion_edad",
        db_index=False,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="videojuegos",
        help_text="Clasificación PEGI; NULL si se desconoce.",
    )
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Videojuego"
        verbose_name_plural = "Videojuegos"
        ordering = ["titulo"]
        indexes = [
            # La FK usa db_index=False; este índice cubre el filtro por
            # clasificación (listados por edad recomendada).
            models.Index(
                fields=["clasificacion_edad"],
                name="catalogo_vj_clasificacion_idx",
            ),
        ]

    def __str__(self):
        return self.titulo

    @property
    def disponible(self) -> bool:
        """Un título es vendible si alguna de sus ofertas está publicada y con stock."""
        return self.ofertas.vendibles().exists()


class VideojuegoCategoria(models.Model):
    """
    Asociación explícita entre un videojuego y una categoría del catálogo.

    Regla de negocio: un videojuego puede tener varias categorías y una
    categoría agrupa varios videojuegos, pero la pareja
    (videojuego, categoría) no puede repetirse. La base de datos lo garantiza
    con un UniqueConstraint, no solo la aplicación.
    """

    videojuego = models.ForeignKey(
        Videojuego, on_delete=models.CASCADE, related_name="vinculos_categoria"
    )
    categoria = models.ForeignKey(
        Categoria, on_delete=models.PROTECT, related_name="vinculos_videojuego"
    )

    class Meta:
        verbose_name = "Categoría del videojuego"
        verbose_name_plural = "Categorías del videojuego"
        constraints = [
            models.UniqueConstraint(
                fields=["videojuego", "categoria"],
                name="catalogo_videojuegocategoria_videojuego_categoria_unicos",
            ),
        ]
        indexes = [
            # Listado de videojuegos por categoría (consulta inversa del M2M).
            models.Index(
                fields=["categoria", "videojuego"],
                name="catalogo_vjc_categoria_idx",
            ),
        ]

    def __str__(self):
        return f"{self.videojuego.titulo} · {self.categoria.nombre}"


class VideojuegoGenero(models.Model):
    """
    Asociación explícita entre un videojuego y un género del catálogo.

    Regla de negocio: un videojuego puede tener varios géneros y un género
    agrupa varios videojuegos, pero la pareja (videojuego, género) no puede
    repetirse. La base de datos lo garantiza con un UniqueConstraint.
    """

    videojuego = models.ForeignKey(
        Videojuego, on_delete=models.CASCADE, related_name="vinculos_genero"
    )
    genero = models.ForeignKey(
        Genero, on_delete=models.PROTECT, related_name="vinculos_videojuego"
    )

    class Meta:
        verbose_name = "Género del videojuego"
        verbose_name_plural = "Géneros del videojuego"
        constraints = [
            models.UniqueConstraint(
                fields=["videojuego", "genero"],
                name="catalogo_videojuegogenero_videojuego_genero_unicos",
            ),
        ]
        indexes = [
            # Listado de videojuegos por género (consulta inversa del M2M).
            models.Index(
                fields=["genero", "videojuego"],
                name="catalogo_vjg_genero_idx",
            ),
        ]

    def __str__(self):
        return f"{self.videojuego.titulo} · {self.genero.nombre}"


class VideojuegoDesarrolladora(models.Model):
    """
    Tabla puente explícita entre un título y una desarrolladora (AZ-S1-20).

    La pareja ``(videojuego, desarrolladora)`` no se repite. El lado
    ``videojuego`` es ``CASCADE`` (consistente con las puentes de AZ-S1-16) y
    el lado catálogo es ``PROTECT``.
    """

    videojuego = models.ForeignKey(
        Videojuego, on_delete=models.CASCADE, related_name="vinculos_desarrolladora"
    )
    desarrolladora = models.ForeignKey(
        Desarrolladora,
        on_delete=models.PROTECT,
        related_name="vinculos_videojuego",
    )

    class Meta:
        verbose_name = "Desarrolladora del videojuego"
        verbose_name_plural = "Desarrolladoras del videojuego"
        constraints = [
            models.UniqueConstraint(
                fields=["videojuego", "desarrolladora"],
                name="catalogo_vjdesarrolladora_unicos",
            ),
        ]
        indexes = [
            models.Index(
                fields=["desarrolladora", "videojuego"],
                name="catalogo_vjd_desarroll_idx",
            ),
        ]

    def __str__(self):
        return f"{self.videojuego.titulo} · {self.desarrolladora.nombre}"


class VideojuegoDistribuidora(models.Model):
    """
    Tabla puente explícita entre un título y una distribuidora (AZ-S1-20).

    La pareja ``(videojuego, distribuidora)`` no se repite. El lado
    ``videojuego`` es ``CASCADE`` y el lado catálogo es ``PROTECT``.
    """

    videojuego = models.ForeignKey(
        Videojuego, on_delete=models.CASCADE, related_name="vinculos_distribuidora"
    )
    distribuidora = models.ForeignKey(
        Distribuidora,
        on_delete=models.PROTECT,
        related_name="vinculos_videojuego",
    )

    class Meta:
        verbose_name = "Distribuidora del videojuego"
        verbose_name_plural = "Distribuidoras del videojuego"
        constraints = [
            models.UniqueConstraint(
                fields=["videojuego", "distribuidora"],
                name="catalogo_vjdistribuidora_unicos",
            ),
        ]
        indexes = [
            models.Index(
                fields=["distribuidora", "videojuego"],
                name="catalogo_vjd_distrib_idx",
            ),
        ]

    def __str__(self):
        return f"{self.videojuego.titulo} · {self.distribuidora.nombre}"


class VideojuegoIdioma(models.Model):
    """
    Presencia de un idioma en un título, con su tipo (AZ-S1-20).

    ``tipo`` se restringe en la base de datos a ``audio``, ``interfaz`` o
    ``subtitulos``. La terna ``(videojuego, idioma, tipo)`` no se repite: un
    mismo idioma puede aparecer con tipos distintos en el mismo título.
    """

    videojuego = models.ForeignKey(
        Videojuego, on_delete=models.CASCADE, related_name="vinculos_idioma"
    )
    idioma = models.ForeignKey(
        Idioma, on_delete=models.PROTECT, related_name="vinculos_videojuego"
    )
    tipo = models.CharField(max_length=10, choices=TipoIdioma.choices)

    class Meta:
        verbose_name = "Idioma del videojuego"
        verbose_name_plural = "Idiomas del videojuego"
        constraints = [
            models.UniqueConstraint(
                fields=["videojuego", "idioma", "tipo"],
                name="catalogo_vjidioma_tipo_unicos",
            ),
            models.CheckConstraint(
                condition=models.Q(tipo__in=TipoIdioma.values),
                name="catalogo_vji_tipo_valido",
            ),
        ]
        indexes = [
            models.Index(
                fields=["idioma", "tipo", "videojuego"],
                name="catalogo_vji_idioma_tipo_idx",
            ),
        ]

    def __str__(self):
        return f"{self.videojuego.titulo} · {self.idioma.nombre} ({self.tipo})"


class EstadoPublicacion(models.Model):
    """
    Catálogo de estados de publicación de una oferta.

    ``codigo`` es el identificador estable referenciado por las ofertas;
    ``nombre`` es la etiqueta visible y editable. Regla de negocio: el estado
    editorial no se almacena como enum en código (AZ-S1-17).
    """

    codigo = models.CharField(
        max_length=50,
        help_text="Identificador estable del estado; no es la etiqueta visible.",
    )
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)

    class Meta:
        verbose_name = "Estado de publicación"
        verbose_name_plural = "Estados de publicación"
        ordering = ["codigo"]
        constraints = [
            models.UniqueConstraint(
                fields=["codigo"],
                name="catalogo_estadopublicacion_codigo_unico",
            ),
        ]

    def __str__(self):
        return self.nombre


class OfertaVideojuegoQuerySet(models.QuerySet):
    """Consultas de dominio sobre el catálogo comercial."""

    def publicadas(self):
        """Ofertas visibles en la tienda (estado de publicación = publicado)."""
        return self.filter(estado_publicacion_id="publicado")

    def vendibles(self):
        """Ofertas publicadas, de títulos activos y con stock disponible."""
        return self.publicadas().filter(stock__gt=0, videojuego__activo=True)


class OfertaVideojuego(models.Model):
    """
    Unidad comercial vendible: la combinación videojuego + plataforma.

    Concentra los atributos que dependen de la edición/plataforma:
    precio vigente, SKU, estado de publicación y stock (residencia
    provisional del inventario hasta AZ-S1-14).
    """

    videojuego = models.ForeignKey(
        Videojuego, on_delete=models.PROTECT, related_name="ofertas"
    )
    plataforma = models.ForeignKey(
        Plataforma, on_delete=models.PROTECT, related_name="ofertas"
    )
    precio_vigente = models.DecimalField(max_digits=10, decimal_places=2)
    sku = models.CharField(max_length=50, unique=True)
    stock = models.PositiveIntegerField(default=0)
    estado_publicacion = models.ForeignKey(
        EstadoPublicacion,
        to_field="codigo",
        db_column="estado_publicacion",
        db_index=False,
        on_delete=models.PROTECT,
        related_name="ofertas",
        default="publicado",
        help_text="Estado editorial de la oferta (catálogo catalogo.EstadoPublicacion).",
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    objects = OfertaVideojuegoQuerySet.as_manager()

    class Meta:
        verbose_name = "Oferta de videojuego"
        verbose_name_plural = "Ofertas de videojuegos"
        ordering = ["videojuego__titulo", "plataforma__nombre"]
        constraints = [
            models.UniqueConstraint(
                fields=["videojuego", "plataforma"],
                name="%(app_label)s_%(class)s_videojuego_plataforma_unicos",
            ),
            models.CheckConstraint(
                condition=models.Q(precio_vigente__gte=0),
                name="%(app_label)s_%(class)s_precio_vigente_no_negativo",
            ),
        ]
        indexes = [
            # Storefront: ofertas publicadas con stock disponible. Sustituye
            # al índice de una sola columna, que exigía leer la tabla para
            # resolver el filtro de stock.
            models.Index(
                fields=["estado_publicacion", "stock"],
                name="catalogo_oferta_est_stock_idx",
            ),
            # Catálogo por plataforma: ofertas publicadas de cada plataforma.
            models.Index(
                fields=["plataforma", "estado_publicacion"],
                name="catalogo_oferta_plat_est_idx",
            ),
        ]

    def __str__(self):
        return f"{self.videojuego.titulo} — {self.plataforma.nombre} [{self.sku}]"

    @property
    def esta_publicada(self) -> bool:
        return self.estado_publicacion_id == "publicado"

    @property
    def disponible(self) -> bool:
        """La oferta es vendible: está publicada y tiene stock."""
        return self.esta_publicada and self.stock > 0
