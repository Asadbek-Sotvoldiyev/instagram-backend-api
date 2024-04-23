from datetime import datetime

from rest_framework.response import Response
from rest_framework import permissions
from rest_framework.exceptions import ValidationError

from .serializers import SignUpSerializer
from .models import User, DONE, CODE_VERIFIED
from rest_framework.generics import CreateAPIView
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
