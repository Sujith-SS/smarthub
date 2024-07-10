from django.urls import path
from . import views



urlpatterns = [
    path('account/', views.account_view, name='account'),
    path('signup/', views.signup, name='signup'),
    path('verify_otp/', views.verify_otp, name='verify_otp'),
    path('resend_otp/', views.resend_otp, name='resend_otp'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    path('password_reset/', views.password_reset_request, name='password_reset_request'),
    path('password_reset/verify/', views.password_reset_verify, name='password_reset_verify'),
    path('password_reset/complete/', views.password_reset_complete, name='password_reset_complete'),
]


