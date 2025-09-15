from django.db import models
from django.db.models import Q
from django_filters import CharFilter, FilterSet


class DynamicSearchFilterSet(FilterSet):
    search = CharFilter(method="filter_search", label="Search")

    def __init__(self, *args, **kwargs):
        queryset = kwargs.get("queryset", None)

        if queryset is not None:
            model = queryset.model
        else:
            model = getattr(self._meta, "model", None)

        if model is None:
            raise ValueError(
                "DynamicSearchFilterSet requires a model or queryset to infer fields."
            )

        self._search_fields = getattr(self._meta, "filterset_search_fields", [])
        exclude_fields = getattr(self._meta, "search_exclude_fields", [])

        if not self._search_fields:
            self._search_fields = [
                field.name
                for field in model._meta.fields
                if isinstance(
                    field,
                    (
                        models.CharField,
                        models.TextField,
                        models.EmailField,
                        models.URLField,
                        models.SlugField,
                        models.DateField,
                        models.DateTimeField,
                        models.TimeField,
                        models.BigAutoField,
                    ),
                )
            ]

        self._search_fields = [
            field for field in self._search_fields if field not in exclude_fields
        ]

        super().__init__(*args, **kwargs)

    def filter_search(self, queryset, name, value):
        if not value:
            return queryset

        query = Q()
        for field in self._search_fields:
            query |= Q(**{f"{field}__icontains": value})

        return queryset.filter(query)
