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
    
    
    path('profile/', views.user_profile, name='user_profile'),
    path('profile/update/', views.update_profile, name='update_profile'),
    path('change_password/', views.change_password, name='change_password'),
    
    
    path('addresses/', views.address_list, name='address_list'),
    path('addresses/new/', views.address_create, name='address_create'),
    path('addresses/<int:pk>/edit/', views.address_update, name='address_update'),
    path('addresses/<int:pk>/delete/', views.address_delete, name='address_delete'),
    path('addresses/set_active/<int:pk>/', views.address_set_active, name='address_set_active'),
    
    
    
    
    
    path('userprofile/',views.user_profile, name='userprofile')
]


