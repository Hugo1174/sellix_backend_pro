import django_filters as df

from .models import Product
from .constants import ProductStatus


class PoolProductFilter(df.FilterSet):
    """Фильтры общего пула для продавца (US-11): категория, производитель, цена."""

    category = df.UUIDFilter(field_name="category_id")
    producer = df.UUIDFilter(field_name="producer_id")
    price_min = df.NumberFilter(field_name="base_price", lookup_expr="gte")
    price_max = df.NumberFilter(field_name="base_price", lookup_expr="lte")

    class Meta:
        model = Product
        fields = ["category", "producer", "price_min", "price_max"]
