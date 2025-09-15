from rest_framework.routers import DefaultRouter

from meta import views

router = DefaultRouter()
router.register("modules", views.ModuleViewset, basename="module")
router.register("fields", views.FieldViewset, basename="field")
