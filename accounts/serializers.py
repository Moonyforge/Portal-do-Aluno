from django.contrib.auth import authenticate
from django.contrib.auth.models import update_last_login
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.settings import api_settings

from .models import StudentProfile, User


class StudentProfileSerializer(serializers.ModelSerializer):

    class Meta:
        model = StudentProfile
        fields = ["registration_number", "course"]


class MeSerializer(serializers.ModelSerializer):
    student = StudentProfileSerializer(source="student_profile", read_only=True, allow_null=True)


    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "email", "role", "student"]
        read_only_fields = fields


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = "email"

    def validate(self, attrs):
        email = attrs["email"].strip().lower()
        user = User.objects.filter(email__iexact=email).first()

        authenticated_user = None
        if user:
            authenticated_user = authenticate(
                request=self.context.get("request"),
                username=user.get_username(),
                password=attrs["password"],
            )

        if authenticated_user is None or not api_settings.USER_AUTHENTICATION_RULE(authenticated_user):
            raise AuthenticationFailed(
                "E-mail ou senha inválidos.",
                code="no_active_account",
            )

        refresh = self.get_token(authenticated_user)
        data = {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }

        if api_settings.UPDATE_LAST_LOGIN:
            update_last_login(None, authenticated_user)

        return data


class AdminStudentSerializer(serializers.ModelSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password"].required = self.instance is None

    registration_number = serializers.CharField(source="student_profile.registration_number")
    course = serializers.CharField(source="student_profile.course", allow_blank=True, required=False)
    password = serializers.CharField(write_only=True, required=False, min_length=8)


    class Meta:
        model = User
        fields = [
            "id", "first_name", "last_name", "email",
            "registration_number", "course", "password", "is_active",
        ]
        read_only_fields = ["id"]

    def create(self, validated_data):
        from django.db import transaction

        profile = validated_data.pop("student_profile")
        password = validated_data.pop("password")
        registration = profile["registration_number"]

        with transaction.atomic():
            user = User.objects.create_user(
                username=registration,
                password=password,
                role=User.Role.STUDENT,
                **validated_data,
            )
            StudentProfile.objects.create(user=user, **profile)
        return user

    def update(self, instance, validated_data):
        profile = validated_data.pop("student_profile", {})
        password = validated_data.pop("password", None)

        for field, value in validated_data.items():
            setattr(instance, field, value)

        if password:
            instance.set_password(password)

        instance.save()

        student_profile = instance.student_profile
        for field, value in profile.items():
            setattr(student_profile, field, value)
        student_profile.save()

        return instance
