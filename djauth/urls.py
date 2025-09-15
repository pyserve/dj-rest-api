from rest_framework.routers import DefaultRouter

from djauth import views

router = DefaultRouter()
router.register("users", views.UserViewSet, basename="user")
router.register("groups", views.GroupViewSet, basename="group")
router.register("permissions", views.PermissionViewSet, basename="permission")
router.register("content_types", views.ContentTypeViewSet, basename="content_type")
