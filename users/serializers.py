from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.validators import FileExtensionValidator
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import (User, VIA_PHONE, VIA_EMAIL,
                     NEW, CODE_VERIFIED, DONE, PHOTO_DONE)
from rest_framework import serializers
from rest_framework.exceptions import ValidationError, PermissionDenied
from shared.utilitiy import check_email_or_phone, send_email, send_phone, check_user_type


class SignUpSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)

    def __init__(self, *args, **kwargs):
        super(SignUpSerializer, self).__init__(*args, **kwargs)
        self.fields['email_phone_number'] = serializers.CharField(required=False)

    class Meta:
        model = User
        fields = (
            'id',
            'auth_type',
            'auth_status'
        )
        extra_kwargs = {
            'auth_type': {'read_only': True, 'required': False},
            'auth_status': {'read_only': True, 'required': False},
        }

    def create(self, validated_data):
        email_phone_number = validated_data.pop('email_phone_number', None)
        user = super(SignUpSerializer, self).create(validated_data)
        if email_phone_number:
            if user.auth_type == VIA_EMAIL:
                user.email = email_phone_number
                code = user.create_verify_code(VIA_EMAIL)
                send_email(user.email, code)
            elif user.auth_type == VIA_PHONE:
                user.phone_number = email_phone_number
                code = user.create_verify_code(VIA_PHONE)
                send_phone(user.phone_number, code)
            user.save()

        return user

    def validate(self, data):
        super(SignUpSerializer, self).validate(data)
        self.auth_validate(data)
        return data

    @staticmethod
    def auth_validate(data):
        user_input = str(data.get('email_phone_number')).lower()
        input_type = check_email_or_phone(user_input)  # email or phone
        if input_type == "email":
            auth_type = VIA_EMAIL
        elif input_type == "phone":
            auth_type = VIA_PHONE
        else:
            data = {
                'success': False,
                'message': "You must send email or phone number"
            }
            raise ValidationError(data)

        data['auth_type'] = auth_type
        return data

    def validate_email_phone_number(self, value):
        if value and User.objects.filter(email=value).exists():
            res = {
                "status": False,
                "Message": "Email already exists"
            }
            raise ValidationError(res)
        elif value and User.objects.filter(phone_number=value).exists():
            res = {
                "status": False,
                "Message": "Phone number already exists"
            }
            raise ValidationError(res)
        return value

    def to_representation(self, instance):
        data = super(SignUpSerializer, self).to_representation(instance)
        data.update(instance.token())

        return data


class ChangeUserInformation(serializers.Serializer):
    first_name = serializers.CharField(write_only=True, required=True)
    last_name = serializers.CharField(write_only=True, required=True)
    username = serializers.CharField(write_only=True, required=True)
    password = serializers.CharField(write_only=True, required=True)
    confirm_password = serializers.CharField(write_only=True, required=True)

    def validate(self, data):
        password = data.get('password', None)
        confirm_password = data.get('confirm_password', None)

        if confirm_password != password:
            raise ValidationError(
                {
                    "success": False,
                    "message": "Passwords don't match"
                }
            )
        if password:
            validate_password(password)
            validate_password(confirm_password)

        return data

    def validate_username(self, username):
        if len(username) < 5 or len(username) > 30:
            raise ValidationError(
                {
                    "success": False,
                    "message": "Username must be between 5 and 30 characters"
                }
            )
        if username.isdigit():
            raise ValidationError(
                {
                    "success": False,
                    "message": "This username is entirely numeric"
                }
            )

        return username

    def update(self, instance, validated_data):
        instance.first_name = validated_data.get('first_name', instance.first_name)
        instance.last_name = validated_data.get('last_name', instance.last_name)
        instance.username = validated_data.get('username', instance.username)
        instance.password = validated_data.get('password', instance.password)

        if validated_data.get('password'):
            instance.set_password(validated_data.get('password'))
        if instance.auth_status == CODE_VERIFIED:
            instance.auth_status = DONE
        instance.save()
        return instance


class ChangeUserPhotoSerializer(serializers.Serializer):
    photo = serializers.ImageField(validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png'])])

    def update(self, instance, validated_data):
        photo = validated_data.get('photo')
        if photo:
            instance.photo = photo
            instance.auth_status = PHOTO_DONE
            instance.save()
        return instance


class LoginSerializer(TokenObtainPairSerializer):

    def __init__(self,*args, **kwargs):
        super(LoginSerializer, self).__init__(*args, **kwargs)
        self.fields['userinput'] = serializers.CharField(required=True)
        self.fields['username'] = serializers.CharField(required=False, read_only=True)

    def auth_validate(self, data):
        user_input = data.get('userinput') # email or phone number or username
        if check_user_type(user_input) == 'username':
            username = user_input
        elif check_user_type(user_input) == 'email':
            user = self.get_user(email__iexact=user_input) #Asadbek@gmail.com = asadbek@gmail.com
            username = user.username
        elif check_user_type(user_input) == 'phone':
            user = self.get_user(phone_number__iexact=user_input)
            username = user.username
        else:
            data = {
                "success": True,
                "message": "Siz email, username yoki telefon raqam jo'natishingiz kerak"
            }
            raise ValidationError(data)

        authentications_kwargs = {
            self.username_field: username,
            'password': data['password']
        }
        # user statusi tekshiramiz
        current_user = User.objects.filter(username__iexact=username).first()
        if current_user.auth_status in [NEW, CODE_VERIFIED]:
            raise ValidationError(
                {
                    "success": False,
                    "message": "Siz ro'yxatdan to'liq o'tmagansiz"
                }
            )
        user = authenticate(**authentications_kwargs)
        if user is not None:
            self.user = user
        else:
            raise ValidationError({
                "success": False,
                "message": "Sorry! Login or password you entered is incorrect. Please check and try again."
            })

    def validate(self, data):
        self.auth_validate(data)
        if self.user.auth_status not in [DONE, PHOTO_DONE]:
            raise PermissionDenied("Siz login qila olmaysiz. Ruxsastingiz yo'q")
        data = self.user.token()
        data['auth_status'] = self.user.auth_status
        return data

    def get_user(self, **kwargs):
        users = User.objects.filter(**kwargs)
        if not users.exists():
            raise ValidationError({
                "message": "No active account found"
            })
        return users.first()


