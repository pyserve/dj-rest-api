from django.contrib import admin

from common.admin import BaseModelAdmin
from djauth import models

admin.site.register(models.User, BaseModelAdmin)
