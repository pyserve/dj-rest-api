from django.apps import apps
from django.db import models as models1
from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.serializers import ModelSerializer
from rest_framework.viewsets import ViewSet

from common.globals import ALLOWED_VIEWS
from common.mixins import PaginationMixin
from common.serializers import BaseSerializer
from common.views import BaseModelViewSet
from core import models, serializers


class ExportViewSet(BaseModelViewSet):
    queryset = models.Export.objects.all()
    serializer_class = serializers.ExportSerializers
    permission_classes = [IsAuthenticatedOrReadOnly]
    pagination_class = PaginationMixin
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["task_id"]


class ImportViewSet(BaseModelViewSet):
    queryset = models.Import.objects.all()
    serializer_class = serializers.ImportSerializers
    permission_classes = [IsAuthenticatedOrReadOnly]
    pagination_class = PaginationMixin
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["task_id"]


class GlobalSearchView(ViewSet):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def list(self, request):
        q = request.query_params.get("q")
        module = request.query_params.get("module", None)
        if not q:
            return Response(
                {"detail": "Query param `q` is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        results = {}
        all_models = apps.get_models()
        for model in all_models:

            if model.__name__ not in ALLOWED_VIEWS:
                continue

            if module is not None and model.__name__ != module:
                continue

            search_fields = [
                f.name
                for f in model._meta.fields
                if isinstance(
                    f,
                    (
                        models1.CharField,
                        models1.TextField,
                        models1.EmailField,
                        models1.URLField,
                        models1.SlugField,
                        models1.DateField,
                        models1.DateTimeField,
                        models1.TimeField,
                        models1.BigAutoField,
                    ),
                )
            ]

            if not search_fields:
                continue

            query = Q()
            for field in search_fields:
                query |= Q(**{f"{field}__icontains": q})

            qs = model.objects.filter(query)
            if qs.exists():
                TempSerializer = type(
                    f"{model.__name__}Serializer",
                    (BaseSerializer, ModelSerializer),
                    {
                        "Meta": type("Meta", (), {"model": model, "fields": "__all__"}),
                    },
                )
                serialized_data = TempSerializer(qs, many=True).data
                schema = [
                    {
                        "name": f.name,
                        "type": f.get_internal_type(),
                        "null": getattr(f, "null", False),
                        "primary_key": getattr(f, "primary_key", False),
                    }
                    for f in model._meta.fields
                ]
                results[model.__name__] = {
                    "data": serialized_data,
                    "schema": schema,
                }
        return Response(results, status=status.HTTP_200_OK)
