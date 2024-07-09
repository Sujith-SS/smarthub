from django.urls import path
from . import views



urlpatterns = [
    path('account/', views.account_view, name='account'),
    path('signup/', views.signup, name='signup'),
    path('verify_otp/', views.verify_otp, name='verify_otp'),
    path('resend_otp/', views.resend_otp, name='resend_otp'),
    path('login/', views.login_view, name='login'),
    
]


