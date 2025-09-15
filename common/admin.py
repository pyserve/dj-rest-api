from django.contrib import admin

class BaseModelAdmin(admin.ModelAdmin):
    def get_list_display(self, request):
        field_names = [
            field.name for field in self.model._meta.fields if field.name != "password"
        ]
        if self.model._meta.pk.name in field_names:
            field_names.remove(self.model._meta.pk.name)
            field_names.insert(0, self.model._meta.pk.name)
        return field_names