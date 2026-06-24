from rest_framework import viewsets
from rest_framework.response import Response

from apps.common.permissions import IsProducer, IsSeller
from .constants import PayeeType
from .models import Payout
from .serializers import PayoutSerializer


class SellerPayoutViewSet(viewsets.ReadOnlyModelViewSet):
    """US-60, US-63. Начисленная продавцу наценка и статусы выплат."""

    serializer_class = PayoutSerializer
    permission_classes = [IsSeller]
    filterset_fields = ["status"]

    def get_queryset(self):
        store = getattr(self.request.user, "store", None)
        if store is None:
            return Payout.objects.none()
        return Payout.objects.filter(store=store, payee_type=PayeeType.SELLER)


class ProducerPayoutViewSet(viewsets.ReadOnlyModelViewSet):
    """US-61, US-63. Причитающиеся производителю суммы и статусы."""

    serializer_class = PayoutSerializer
    permission_classes = [IsProducer]
    filterset_fields = ["status"]

    def get_queryset(self):
        producer = getattr(self.request.user, "producer", None)
        if producer is None:
            return Payout.objects.none()
        return Payout.objects.filter(producer=producer, payee_type=PayeeType.PRODUCER)
