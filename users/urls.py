from django.urls import path
from .views import CreateUserView, VerifyApiView


urlpatterns = [
    path('signup/', CreateUserView.as_view()),
    path('verify/', VerifyApiView.as_view()),
]