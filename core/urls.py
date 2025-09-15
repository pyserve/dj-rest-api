from rest_framework.routers import DefaultRouter

from core import views

router = DefaultRouter()

router.register(r"exports", views.ExportViewSet, basename="export")
router.register(r"imports", views.ImportViewSet, basename="import")
router.register(r"search", views.GlobalSearchView, basename="search")
