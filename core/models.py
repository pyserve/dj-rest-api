from django.contrib.auth import get_user_model
from django.db import models

from common.models import BaseModel

User = get_user_model()

class Export(BaseModel):
    name = models.CharField(max_length=255, blank=True, null=True)
    model = models.CharField(max_length=100)
    app_label = models.CharField(max_length=100)
    columns = models.JSONField()
    conditions = models.JSONField()
    file = models.FileField(upload_to="exports", blank=True, null=True)
    task_id = models.UUIDField(blank=True, null=True, unique=True)


class Import(BaseModel):
    name = models.CharField(max_length=255, blank=True, null=True)
    model = models.CharField(max_length=100)
    app_label = models.CharField(max_length=100)
    action = models.CharField(max_length=100, default="create")
    columns = models.JSONField()
    mappings = models.JSONField()
    default_values = models.JSONField(blank=True, null=True)
    conditions = models.JSONField(blank=True, null=True)
    rows = models.JSONField(blank=True, null=True)
    file = models.FileField(upload_to="imports", blank=True, null=True)
    results = models.FileField(upload_to="imports/results", blank=True, null=True)
    task_id = models.UUIDField(blank=True, null=True, unique=True)
