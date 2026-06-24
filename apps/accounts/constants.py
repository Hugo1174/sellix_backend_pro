from django.db import models


class Role(models.TextChoices):
    BUYER = "buyer", "Покупатель"
    SELLER = "seller", "Продавец"
    PRODUCER = "producer", "Производитель"
    ADMIN = "admin", "Суперадмин"


class AuthProvider(models.TextChoices):
    YANDEX = "yandex", "Яндекс ID"
    VK = "vk", "VK ID"
    LOCAL = "local", "Локальный (админ)"
