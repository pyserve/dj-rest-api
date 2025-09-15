import importlib

from django.apps import apps
from rest_framework import viewsets
from rest_framework.response import Response


class ModuleViewset(viewsets.ViewSet):
    def get_router_views(self, router):
        endpoints = {}
        for prefix, viewset, _ in router.registry:
            model = getattr(getattr(viewset, "queryset", None), "model", None)
            if model:
                endpoints[model.__name__] = f"/{prefix}/"
            else:
                endpoints[prefix] = f"/{prefix}/"
        return endpoints

    def list(self, request):
        data = {}
        for app in apps.get_app_configs():
            endpoints = {}
            try:
                urls_module = importlib.import_module(f"{app.name}.urls")
                router = getattr(urls_module, "router", None)
                if router:
                    endpoints = self.get_router_views(router)
            except ModuleNotFoundError:
                pass

            data[app.name] = {
                "name": app.name,
                "label": app.label,
                "views": endpoints,
            }
        return Response({"results": data})


class FieldViewset(viewsets.ViewSet):
    def list(self, request):
        app_name = request.query_params.get("app_name")
        model_name = request.query_params.get("model_name")
        response = []

        for model in apps.get_models():
            if app_name and model._meta.app_label != app_name:
                continue
            if model_name and model.__name__ != model_name:
                continue

            fields = []
            for field in model._meta.get_fields():
                if field.auto_created and (field.is_relation or field.many_to_many):
                    continue
                fields.append(
                    {
                        "api_name": field.name,
                        "data_type": type(field).__name__,
                        "picklists": (
                            [str(choice[0]) for choice in getattr(field, "choices", [])]
                            if getattr(field, "choices", None)
                            else None
                        ),
                        "lookup": (
                            {
                                "model": (
                                    field.related_model.__name__
                                    if field.related_model
                                    else None
                                ),
                                "id": (
                                    field.related_model._meta.pk.name
                                    if field.related_model
                                    else None
                                ),
                            }
                            if getattr(field, "is_relation", False)
                            else None
                        ),
                        "primary_key": getattr(field, "primary_key", False),
                        "max_length": getattr(field, "max_length", None),
                        "null": getattr(field, "null", False),
                        "blank": getattr(field, "blank", False),
                        "default": (
                            str(getattr(field, "default", None))
                            if not callable(getattr(field, "default", None))
                            else None
                        ),
                        "unique": getattr(field, "unique", False),
                        "help_text": getattr(field, "help_text", None),
                        "verbose_name": getattr(field, "verbose_name", None),
                    }
                )

            response.append(
                {
                    "app_name": model._meta.app_label,
                    "model": model.__name__,
                    "fields": fields,
                }
            )

        return Response({"results": response}, status=200)
