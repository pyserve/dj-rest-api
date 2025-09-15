from common.mixins import (
    DisplayNameMixin,
    M2MValidationMixin,
    NestedRelationDisplayMixin,
    PrevNextMixin,
    UserStampMixin,
)
from django.db import models
from rest_framework import serializers


class BaseSerializer(
    NestedRelationDisplayMixin,
    M2MValidationMixin,
    UserStampMixin,
    serializers.ModelSerializer,
    DisplayNameMixin,
    PrevNextMixin,
):
    display_name = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()
    module = serializers.SerializerMethodField()
    previous_id = serializers.SerializerMethodField()
    next_id = serializers.SerializerMethodField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.m2m_fields = [f for f in self.Meta.model._meta.many_to_many]
        self.fk_fields = [
            f
            for f in self.Meta.model._meta.fields
            if (isinstance(f, models.ForeignKey) or isinstance(f, models.OneToOneField))
        ]
        for field in self.m2m_fields + self.fk_fields:
            serializer_cls = self.get_nested_serializer(field)
            self.fields[field.name] = serializer_cls(
                many=field.many_to_many, read_only=True
            )

    def validate(self, attrs):
        self.validate_many_to_many_fields(self.initial_data)

        for field in self.Meta.model._meta.get_fields():
            if field.is_relation and (field.many_to_one or field.one_to_one):
                if field.name in self.initial_data:
                    try:
                        attrs[field.name] = field.related_model.objects.get(
                            id=self.initial_data[field.name]
                        )
                    except field.related_model.DoesNotExist:
                        raise serializers.ValidationError(
                            {field.name: f"Invalid {field.related_model.__name__} ID."}
                        )

        return super().validate(attrs)

    def create(self, validated_data):
        validated_data = self.set_user_stamps(validated_data)
        instance = super().create(validated_data)

        for field_name, related_ids in self._validated_m2m_data.items():
            getattr(instance, field_name).set(related_ids)

        return instance

    def update(self, instance, validated_data):
        validated_data = self.set_user_stamps(validated_data)

        for field_name, related_ids in self._validated_m2m_data.items():
            getattr(instance, field_name).set(related_ids)

        return super().update(instance, validated_data)

    class Meta:
        abstract = True
