import re
import threading

from decouple import config
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from twilio.rest import Client
from rest_framework.exceptions import ValidationError

email_regex = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b")
phone_regex = re.compile(r"^\+998([- ])?(90|91|93|94|95|98|99|33|97|71)([- ])?(\d{3})([- ])?(\d{2})([- ])?(\d{2})$")


def check_email_or_phone(email_or_phone):
    if re.fullmatch(email_regex, email_or_phone):
        email_or_phone = "email"

    elif re.fullmatch(phone_regex, email_or_phone):
        email_or_phone = 'phone'

    else:
        data = {
            "success": False,
            "message": "Email yoki telefon raqam xato"
        }
        raise ValidationError(data)

    return email_or_phone

# Emailga asinxron jo'natish
class EmailThreading(threading.Thread):

    def __init__(self, email):
        self.email = email
        threading.Thread.__init__(self)

    def run(self):
        self.email.send()


class Email:
    @staticmethod
    def send_email(data):
        email = EmailMessage(
            subject=data['subject'],
            body=data['body'],
            to=[data['to_email']]
        )
        if data.get('content_type') == 'html':
            email.content_subtype = 'html'
        EmailThreading(email).start()


def send_email(email, code):
    html_content = render_to_string(
        'email/authentication/activate_account.html',
        {'code': code}
    )
    Email.send_email(
        {
            "subject": "Ro'yxatdan o'tish",
            "to_email": email,
            "body": html_content,
            "content_type": "html"
        }
    )


def send_phone(phone, code):
    account_sid = 'AC043f6aadea3f2bccee5378954a96dcd2'
    auth_token = '4a92d0d6de916635168559ce2a80b118'
    client = Client(account_sid, auth_token)
    client.messages.create(
        body=f"Salom foydalanuvchi! Sizning instagramdagi tasdiqlash kodingiz: {code}\n",
        from_='+14248887173',
        to=f"{phone}"
    )
