from datetime import datetime

from rest_framework.response import Response
from rest_framework import permissions
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.views import TokenObtainPairView

from shared.utilitiy import send_email, send_phone
from .serializers import SignUpSerializer, ChangeUserInformation, ChangeUserPhotoSerializer, LoginSerializer
from .models import User, DONE, CODE_VERIFIED, VIA_EMAIL, VIA_PHONE
from rest_framework.generics import CreateAPIView, UpdateAPIView
from rest_framework.views import APIView


class CreateUserView(CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (permissions.AllowAny, )
    serializer_class = SignUpSerializer


class VerifyApiView(APIView):
    permission_classes = (permissions.IsAuthenticated, )

    def post(self, request, *args, **kwargs):
        user = self.request.user
        code = self.request.data.get('code')

        self.check_verify(user, code)
        data = {
            "status": True,
            "auth_status": user.auth_status,
            "access_token": user.token()['access'],
            "refresh_token": user.token()['refresh_token'],
        }
        return Response(data)

    @staticmethod
    def check_verify(user, code):
        verifies = user.verify_codes.filter(expiration_time__gte=datetime.now(), code=code, is_confirmed=False)
        if not verifies.exists():
            data = {
                "message": "Tasdiqlash kodingiz xato yoki eskirgan"
            }
            raise ValidationError(data)
        verifies.update(is_confirmed=True)
        if user.auth_status not in DONE:
            user.auth_status = CODE_VERIFIED
            user.save()

        return True


class GetNewVerification(APIView):
    permission_classes = (permissions.IsAuthenticated, )
    def get(self, request, *args, **kwargs):
        user = self.request.user
        self.check_verification(user)
        if user.auth_type == VIA_EMAIL:
            code = user.create_verify_code(VIA_EMAIL)
            send_email(user.email, code)
        elif user.auth_type == VIA_PHONE:
            code = user.create_verify_code(VIA_PHONE)
            send_phone(user.phone_number, code)
        else:
            data = {
                "Success": False,
                "message": "Email yoki telefon raqami noto'g'ri"
            }
            raise ValidationError(data)
        return Response(
            {
                "success": True,
                "message": "Tasdiqlash kodi qaytadan jo'natildi"
            }
        )

    @staticmethod
    def check_verification(user):
        verifies = user.verify_codes.filter(expiration_time__gte=datetime.now(), is_confirmed=False)
        if verifies.exists():
            data = {
                "success": False,
                "message": "Sizga kod yuborilgan iltimos biroz kuting... "
            }
            raise ValidationError(data)


class ChangeUserInformationView(UpdateAPIView):
    permission_classes = (permissions.IsAuthenticated, )
    serializer_class = ChangeUserInformation
    http_method_names = ['patch', 'put']

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        super(ChangeUserInformationView, self).update(request, *args, **kwargs)
        data = {
            "success": True,
            'message': "User updated successfully",
            'auth_status': self.request.user.auth_status
        }

        return Response(data, status=200)


class ChangeUserPhotoView(APIView):
    permission_classes = (permissions.IsAuthenticated, )
    def put(self, request, *args, **kwargs):
        serializer = ChangeUserPhotoSerializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            serializer.update(user, serializer.validated_data)
            return Response(
                {
                    "success": True,
                    "message": "Photo updated successfully",
                    "auth_status": self.request.user.auth_status
                }
            )
        return Response(
            serializer.errors, status=400
        )


class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer
