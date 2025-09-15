from common.serializers import BaseSerializer
from core import models


class ExportSerializers(BaseSerializer):
    class Meta:
        model = models.Export
        fields = "__all__"


class ImportSerializers(BaseSerializer):
    class Meta:
        model = models.Import
        fields = "__all__"
