from .models import (User, UserConfirmation, VIA_PHONE, VIA_EMAIL,
                     NEW, CODE_VERIFIED, DONE, PHOTO_DONE)
from rest_framework import exceptions
from django.db.models import Q
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from shared.utilitiy import check_email_or_phone, send_email, send_phone


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

