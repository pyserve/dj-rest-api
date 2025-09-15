import json

from celery.result import AsyncResult
from django.apps import apps
from django.conf import settings
from django.db import models
from django.db.models import ProtectedError, Q
from django.db.models.fields import NOT_PROVIDED
from django.urls import reverse
from rest_framework import serializers, status
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from api.celery import app
from common.tasks import start_import
from core.models import Import

OPERATOR_MAP = {
    "is": "exact",
    "is not": "exact",
    "contains": "icontains",
    "doesn't contain": "icontains",
    "is empty": "isnull",
    "not empty": "isnull",
    "starts_with": "istartswith",
    "ends_with": "iendswith",
    "<": "lt",
    "<=": "lte",
    ">": "gt",
    ">=": "gte",
    "between": "range",
    "not between": "range",
}
NEGATE_OPERATORS = {"is not", "doesn't contain", "not empty", "not between"}


class MetadataMixin:
    def to_representation(self, instance):
        model = self.Meta.model
        data = super().to_representation(instance)

        field_metadata = []
        for field in self.Meta.model._meta.get_fields():
            if isinstance(field, (models.ManyToOneRel, models.ManyToManyRel)):
                continue

            field_info = {
                "name": field.name,
                "null": getattr(field, "null", None),
                "primary_key": getattr(field, "primary_key", False),
            }
            field_metadata.append(field_info)

        metadata = {
            "total_records": self.Meta.model.objects.count(),
            "fields": field_metadata,
            "author": "Eco Home Group Team",
            "app_label": model._meta.app_label,
            "model": model.__name__,
        }

        return {
            "metadata": metadata,
            "data": data,
        }


class PaginationMixin(PageNumberPagination):
    page_size = 100
    page_size_query_param = "page_size"
    max_page_size = 200

    def get_paginated_response(self, data):
        model = self.page.paginator.object_list.model
        model_schema = self.get_model_schema()
        return Response(
            {
                "count": self.page.paginator.count,
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
                "results": data,
                "metadata": {
                    "total_records": self.page.paginator.count,
                    "page_size": self.page.paginator.per_page,
                    "current_page": self.page.number,
                    "total_pages": self.page.paginator.num_pages,
                    "model": model.__name__,
                    "app_label": model._meta.app_label,
                    "schema": model_schema,
                },
            }
        )

    def get_model_schema(self):
        model = self.page.paginator.object_list.model
        field_metadata = []
        for field in model._meta.get_fields():
            if not field.is_relation or (field.is_relation and not field.auto_created):
                related_model = (
                    getattr(field.related_model, "__name__", None)
                    if hasattr(field, "related_model")
                    else None
                )
                field_info = {
                    "name": field.name,
                    "type": type(field).__name__,
                    "null": getattr(field, "null", None),
                    "primary_key": getattr(field, "primary_key", False),
                    "related_model": related_model,
                }
                field_metadata.append(field_info)
        return field_metadata


class MassActionMixin:
    @action(detail=False, methods=["put"], url_path="mass-update")
    def mass_update(self, request):
        ids = request.data.get("ids", [])
        update_data = request.data.get("data", {})

        if not ids or not update_data:
            return Response(
                {"error": "Please provide 'ids' and 'data' for the update."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        instances = self.queryset.filter(id__in=ids)
        if not instances.exists():
            return Response(
                {"error": "No records found for the provided ids."},
                status=status.HTTP_404_NOT_FOUND,
            )

        for instance in instances:
            for attr, value in update_data.items():
                setattr(instance, attr, value)
            instance.save()

        return Response({"message": "Updated successfully"}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["delete"], url_path="mass-delete")
    def mass_delete(self, request):
        ids = request.data.get("ids", [])

        if not ids:
            return Response(
                {"error": "Please provide 'ids' for the delete."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        instances = self.queryset.filter(id__in=ids)
        if not instances.exists():
            return Response(
                {"error": "No records found for the provided ids."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            instances.delete()
        except ProtectedError as e:
            protected_ids = [str(obj) for obj in e.protected_objects]
            return Response(
                {
                    "error": "Cannot delete some records because they are protected.",
                    "protected_objects": protected_ids,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        return Response(
            {"message": "Deleted successfully"}, status=status.HTTP_204_NO_CONTENT
        )

    @action(detail=False, methods=["post"], url_path="export")
    def export_data(self, request):
        payload = request.data.get("data", {})
        app_label = payload.get("app_label")
        model = payload.get("model")
        columns = payload.get("columns", [])
        conditions = payload.get("conditions", [])

        if not model:
            return Response(
                {"error": "Model name is required."}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            Model = apps.get_model(app_label, model)
        except LookupError:
            return Response(
                {"error": f"Model '{model}' not found."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        q_objects = Q()
        for cond in conditions:
            field = cond.get("field")
            operator = cond.get("operator")
            value = cond.get("value")
            connector = cond.get("connector", "AND").upper()
            app_label = payload.get("app_label")
            model = payload.get("model")

            if not field or not operator:
                continue

            lookup = OPERATOR_MAP.get(operator)
            if not lookup:
                continue

            if operator in {"is empty", "not empty"}:
                q = Q(**{f"{field}__{lookup}": operator == "is empty"})
            elif operator in {"between", "not between"}:
                q = Q(**{f"{field}__{lookup}": value})
            else:
                q = Q(**{f"{field}__{lookup}": value})

            if operator in NEGATE_OPERATORS:
                q = ~q

            q_objects = q_objects & q if connector == "AND" else q_objects | q

        qs = (
            Model.objects.filter(q_objects).values(*columns)
            if columns
            else Model.objects.filter(q_objects).values()
        )
        results = [{k: str(v) for k, v in row.items()} for row in qs]
        return Response({"results": results}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="import")
    def import_data(self, request):
        uploaded_file = request.FILES.get("file")
        action_type = request.data.get("action")
        mappings = json.loads(request.data.get("mappings", "{}"))
        default_values = json.loads(request.data.get("defaultValues", "{}"))
        columns = json.loads(request.data.get("columns", "[]"))
        rows = json.loads(request.data.get("rows", "[]"))
        app_label = request.data.get("app_label")
        model = request.data.get("model")

        if not model:
            return Response(
                {"error": "Model name is required."}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            Model = apps.get_model(app_label, model)
        except LookupError:
            return Response(
                {"error": f"Model '{model}' not found."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        fields = Model._meta.get_fields()
        required_fields = [
            f.name
            for f in Model._meta.get_fields()
            if (
                (
                    getattr(f, "editable", False)
                    and hasattr(f, "blank")
                    and hasattr(f, "null")
                    and not f.blank
                    and not f.null
                    and not getattr(f, "auto_created", False)
                    and (not hasattr(f, "default") or f.default is NOT_PROVIDED)
                )
                or (action_type == "update" and f.name == Model._meta.pk.name)
            )
        ]
        missing_required_fields = [
            field for field in required_fields if not mappings.get(field)
        ]
        if missing_required_fields:
            return Response(
                {
                    "error": f"Missing required fields: {', '.join(missing_required_fields)}."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if action_type == "create":
            try:
                record = Import.objects.create(
                    app_label=app_label,
                    model=model,
                    file=uploaded_file,
                    name=uploaded_file.name,
                    columns=columns,
                    mappings=mappings,
                    default_values=default_values,
                    action=action_type,
                )
                task = start_import.delay(app_label, model, record.id, required_fields)
                record.task_id = task.id
                record.save()
                return Response(
                    {
                        "status": "started",
                        "task_id": task.id,
                        "name": f"Importing {model}",
                    },
                    status=status.HTTP_202_ACCEPTED,
                )
            except Exception as e:
                return Response(
                    {"error": f"Error: {str(e)}."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        if action_type == "update":
            pass
        if action_type == "both":
            pass

        return Response(
            {
                "file_name": uploaded_file.name if uploaded_file else None,
                "action": action_type,
                "mappings": mappings,
                "default_values": default_values,
                "columns": columns,
                "row": rows,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"], url_path="status/(?P<task_id>[^/.]+)")
    def status(self, request, task_id=None):
        res = AsyncResult(task_id, app=app)
        data = {
            "task_id": task_id,
            "status": res.status,
            "result": res.result,
        }
        if res.state == "PENDING":
            info = res.info or {}
            data["progress"] = round(
                info.get("current", 0) / info.get("total", 1) * 100, 2
            )

        return Response(data)


class UserStampMixin:
    def set_user_stamps(self, validated_data):
        request = self.context.get("request", None)
        if request and hasattr(request, "user"):
            model_fields = [f.name for f in self.Meta.model._meta.get_fields()]
            if "created_by" in model_fields:
                validated_data["created_by"] = request.user
            if "updated_by" in model_fields:
                validated_data["updated_by"] = request.user
        return validated_data


class M2MValidationMixin:
    def __init__(self, *args, **kwargs):
        self._validated_m2m_data = {}
        super().__init__(*args, **kwargs)

    def validate_many_to_many_fields(self, initial_data):
        for field in self.Meta.model._meta.get_fields():
            if field.is_relation and field.many_to_many and field.name in initial_data:
                self._validated_m2m_data[field.name] = (
                    self._validate_many_to_many_field(field, initial_data[field.name])
                )

    def _validate_many_to_many_field(self, field, input_data):
        related_ids = []
        model = field.related_model

        for record in input_data:
            if isinstance(record, dict):
                obj = model.objects.create(**record)
                related_ids.append(obj.id)
            elif isinstance(record, (int, str)) and str(record).isdigit():
                related_ids.append(record)

        return list(
            model.objects.filter(id__in=related_ids).values_list("id", flat=True)
        )


class NestedRelationDisplayMixin:
    def get_nested_serializer(self, field):
        related_model = field.related_model
        all_fields = [f.name for f in related_model._meta.fields]
        exclude_fields = {"password", "secret_key", "token"}
        safe_fields = [f for f in all_fields if f not in exclude_fields]

        class serializer_class(serializers.ModelSerializer, DisplayNameMixin):
            display_name = serializers.SerializerMethodField()
            module = serializers.SerializerMethodField()
            url = serializers.SerializerMethodField()

            class Meta:
                model = related_model
                fields = safe_fields + ["display_name", "module", "url"]
                depth = 0
                ref_name = f"{related_model.__name__}NestedSerializer"

        return serializer_class


class DisplayNameMixin:
    def get_display_name(self, obj):
        return str(obj)

    def get_module(self, obj):
        return obj.__class__.__name__

    def get_url(self, obj):
        try:
            url_name = f"{(obj._meta.model_name)}-detail"
            endpoint = str(reverse(url_name, kwargs={"pk": obj.pk}))
            return settings.FRONTEND_URL + endpoint
        except Exception:
            return ""


class PrevNextMixin:
    def get_previous_id(self, obj):
        model = obj.__class__
        prev_record = model.objects.filter(id__lt=obj.id).order_by("-id").first()
        return prev_record.id if prev_record else None

    def get_next_id(self, obj):
        model = obj.__class__
        next_record = model.objects.filter(id__gt=obj.id).order_by("id").first()
        return next_record.id if next_record else None


class FiltersetMixin:
    allowed_field_types = (
        models.CharField,
        models.TextField,
        models.EmailField,
        models.SlugField,
        models.URLField,
        models.ForeignKey,
        models.OneToOneField,
        models.AutoField,
        models.BigAutoField,
    )

    def get_filterset_fields(self):
        model = self.queryset.model
        return [
            f.name
            for f in model._meta.get_fields()
            if isinstance(getattr(f, "related_model", f), self.allowed_field_types)
        ]

    def get_ordering_fields(self, view):
        return self.get_filterset_fields()
