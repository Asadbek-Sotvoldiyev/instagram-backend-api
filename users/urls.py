from django.urls import path
from .views import (CreateUserView, VerifyApiView, GetNewVerification,
                    ChangeUserInformationView, ChangeUserPhotoView, LoginView)


urlpatterns = [
    path('login/', LoginView.as_view()),
    path('signup/', CreateUserView.as_view()),
    path('verify/', VerifyApiView.as_view()),
    path('new-verify/', GetNewVerification.as_view()),
    path('full-register/', ChangeUserInformationView.as_view()),
    path('change-photo/', ChangeUserPhotoView.as_view()),
]