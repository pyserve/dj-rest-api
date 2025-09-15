from allauth.socialaccount.providers.facebook.views import \
    FacebookOAuth2Adapter
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from dj_rest_auth.registration.views import SocialLoginView
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.auth.tokens import default_token_generator
from django.contrib.contenttypes.models import ContentType
from django.core.mail import send_mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import AllowAny, IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from common.mixins import PaginationMixin
from common.views import BaseModelViewSet
from djauth import serializers

User = get_user_model()


class UserViewSet(BaseModelViewSet):
    queryset = User.objects.all()
    serializer_class = serializers.UserSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    pagination_class = PaginationMixin
    filter_backends = [DjangoFilterBackend, OrderingFilter]


class GroupViewSet(BaseModelViewSet):
    queryset = Group.objects.all()
    serializer_class = serializers.GroupSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    pagination_class = PaginationMixin
    filter_backends = [DjangoFilterBackend, OrderingFilter]


class ContentTypeViewSet(BaseModelViewSet):
    queryset = ContentType.objects.all()
    serializer_class = serializers.ContentTypeSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    pagination_class = PaginationMixin
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["model"]


class PermissionViewSet(BaseModelViewSet):
    queryset = Permission.objects.all()
    serializer_class = serializers.PermissionSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    pagination_class = PaginationMixin
    filter_backends = [DjangoFilterBackend, OrderingFilter]


class PasswordResetViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]

    @action(detail=False, methods=["post"], url_path="request")
    def request_password_reset(self, request):
        serializer = serializers.PasswordResetRequestSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data["email"]
            try:
                user = User.objects.get(email=email)
                uid = urlsafe_base64_encode(force_bytes(user.pk))
                token = default_token_generator.make_token(user)

                reset_link = (
                    f"{settings.FRONTEND_URL}/auth/reset-password/{uid}/{token}/"
                )

                send_mail(
                    subject="Password Reset Requested",
                    message=f"Click the link to reset your password: {reset_link}",
                    from_email=settings.EMAIL_HOST_USER,
                    recipient_list=[email],
                )
                return Response(
                    {"message": "Password reset email sent."}, status=status.HTTP_200_OK
                )
            except User.DoesNotExist:
                return Response(
                    {"error": "User not found."}, status=status.HTTP_404_NOT_FOUND
                )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(
        detail=False,
        methods=["post"],
        url_path="confirm/(?P<uidb64>[^/.]+)/(?P<token>[^/.]+)",
    )
    def confirm_password_reset(self, request, uidb64, token):
        serializer = serializers.PasswordResetConfirmSerializer(data=request.data)
        if serializer.is_valid():
            new_password = serializer.validated_data["new_password"]

            try:
                uid = urlsafe_base64_decode(uidb64).decode()
                user = User.objects.get(pk=uid)

                if default_token_generator.check_token(user, token):
                    user.set_password(new_password)
                    user.save()
                    return Response(
                        {"message": "Password has been reset."},
                        status=status.HTTP_200_OK,
                    )
                else:
                    return Response(
                        {"error": "Invalid token."}, status=status.HTTP_400_BAD_REQUEST
                    )

            except (TypeError, ValueError, OverflowError, User.DoesNotExist):
                return Response(
                    {"error": "Invalid user ID."}, status=status.HTTP_400_BAD_REQUEST
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GoogleLoginView(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter


class FacebookLoginView(SocialLoginView):
    adapter_class = FacebookOAuth2Adapter
