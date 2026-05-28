from django.urls import path
from .views import LoginView, RegisterView, MeView

urlpatterns = [
    path('login/', LoginView.as_view()),
    path('register/', RegisterView.as_view()),
    path('me/', MeView.as_view()),
]
