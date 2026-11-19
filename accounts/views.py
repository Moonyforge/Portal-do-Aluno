from rest_framework.generics import RetrieveAPIView
from rest_framework.throttling import ScopedRateThrottle
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import EmailTokenObtainPairSerializer, MeSerializer


class LoginView(TokenObtainPairView):
    """Login por e-mail (RF01), com limite contra força bruta."""

    serializer_class = EmailTokenObtainPairSerializer
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"


class MeView(RetrieveAPIView):
    """Dados do usuário autenticado (RF04/RF05)."""

    serializer_class = MeSerializer

    def get_object(self):
        return self.request.user


from rest_framework import viewsets
from core.permissions import IsSecretary
from .models import User
from .serializers import AdminStudentSerializer


class AdminStudentViewSet(viewsets.ModelViewSet):
    permission_classes = [IsSecretary]
    serializer_class = AdminStudentSerializer
    queryset = User.objects.filter(
        role=User.Role.STUDENT
    ).select_related("student_profile")
    http_method_names = ["get", "post", "patch", "head", "options"]

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save(update_fields=["is_active"])
