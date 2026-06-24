from django.db import models


class ProductStatus(models.TextChoices):
    DRAFT = "draft", "Черновик"
    PUBLISHED = "published", "Опубликован"
    OUT_OF_STOCK = "out_of_stock", "Нет в наличии"
    ARCHIVED = "archived", "Снят с публикации"
