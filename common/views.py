from common.mixins import FiltersetMixin, MassActionMixin
from django.contrib.contenttypes.fields import GenericForeignKey
from django.db import models
from rest_framework import viewsets
from rest_framework.response import Response


class BaseModelViewSet(viewsets.ModelViewSet, MassActionMixin, FiltersetMixin):
    # filterset_fields = "__all__"
    ordering_fields = "__all__"

    def retrieve(self, request, *args, **kwargs):
        response = super().retrieve(request, *args, **kwargs)
        metadata = self.get_model_schema()
        return Response(
            {
                "data": response.data,
                "schema": metadata,
            }
        )

    def get_model_schema(self):
        model = self.queryset.model
        schema = {
            "title": f"{model.__name__} schema",
            "description": f"Schema for {model.__name__}",
            "type": "object",
            "properties": {},
            "required": [],
        }
        for field in model._meta.get_fields():
            if isinstance(field, (models.ManyToOneRel, models.ManyToManyRel)):
                continue

            if isinstance(field, GenericForeignKey):
                continue

            field_info = {
                "title": field.verbose_name.title(),
                "type": field.get_internal_type(),
                "nullable": getattr(field, "null", False),
                "blank": getattr(field, "blank", False),
            }

            if not field.null and not field.blank and not field.primary_key:
                schema["required"].append(field.name)

            if field.primary_key:
                field_info["type"] = "string"

            schema["properties"][field.name] = field_info

        return schema
        return schema
        return schema
