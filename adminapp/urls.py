from django.urls import path
from . import views

urlpatterns = [
    path('administration', views.admin_login, name='administration'),
]
