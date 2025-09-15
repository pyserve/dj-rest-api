from django.contrib import admin

from common.admin import BaseModelAdmin
from core import models

admin.site.register(models.Export, BaseModelAdmin)
admin.site.register(models.Import, BaseModelAdmin)
