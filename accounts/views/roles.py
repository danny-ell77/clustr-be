from typing import cast

from django.db import IntegrityError, transaction
from django.db.models import QuerySet
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from accounts.models import AccountUser, Role
from accounts.permissions import IsOwnerOrReadOnly
from accounts.serializers import RoleSerializer
from core.common.exceptions import UnprocessedEntityException
from core.common.responses import duplicate_entity_response
from core.common.decorators import audit_viewset
from core.common.error_utils import exception_to_response_mapper

DEFAULT_DUPLICATE_DETAIL_MESSAGE = "A role with this name already exists"


@audit_viewset(resource_type='role')
class RoleViewSet(viewsets.ModelViewSet):
    serializer_class = RoleSerializer
    permission_classes = [IsAuthenticated & IsOwnerOrReadOnly]

    def get_queryset(self) -> QuerySet:
        user = cast(AccountUser, self.request.user)
        return Role.objects.filter(owner=user.get_owner())

    def create(self, request: Request, *args, **kwargs) -> Response:
        try:
            with transaction.atomic():
                return super().create(request, *args, **kwargs)
        except IntegrityError:
            return duplicate_entity_response(detail=DEFAULT_DUPLICATE_DETAIL_MESSAGE)

    def update(self, request: Request, *args, **kwargs) -> Response:
        try:
            with transaction.atomic():
                return super().update(request, *args, **kwargs)
        except IntegrityError:
            return duplicate_entity_response(detail=DEFAULT_DUPLICATE_DETAIL_MESSAGE)

    def destroy(self, request: Request, *args, **kwargs) -> Response:
        role: Role = self.get_object()
        if role.is_owner:
            raise UnprocessedEntityException(detail="Primary role may not be deleted")
        return super().destroy(request, *args, **kwargs)
