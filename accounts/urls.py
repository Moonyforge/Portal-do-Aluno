from django.urls import include, path
from rest_framework.routers import SimpleRouter

from .views import AdminStudentViewSet, MeView

router = SimpleRouter()
router.register("admin/alunos", AdminStudentViewSet, basename="admin-students")

urlpatterns = [
    path("me/", MeView.as_view(), name="me"),
]

urlpatterns += router.urls
