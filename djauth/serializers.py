from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from rest_framework import serializers

from common.serializers import BaseSerializer

User = get_user_model()


class UserSerializer(BaseSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = "__all__"
        exclude = []


class GroupSerializer(BaseSerializer):
    class Meta:
        model = Group
        fields = "__all__"


class ContentTypeSerializer(BaseSerializer):
    class Meta:
        model = ContentType
        fields = "__all__"


class PermissionSerializer(BaseSerializer):
    class Meta:
        model = Permission
        fields = "__all__"