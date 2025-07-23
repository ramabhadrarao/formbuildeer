# apps/users/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.custom_login, name='login'),
    path('logout/', views.custom_logout, name='logout'),
    path('signup/', views.SignUpView.as_view(), name='signup'),
]