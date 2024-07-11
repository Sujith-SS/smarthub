from django.urls import path
from . import views

urlpatterns = [
    path('administration', views.admin_dashboard, name='administration'),
    path('admin_login/', views.admin_login, name='admin_login'),
    path('admin_logout/',views.admin_logout , name='admin_logout'),
    
    
    path('usermanagement/',views.admin_userManagement, name='user_management'),
    path('productmanagement/',views.admin_productManagement, name='productmanagement'),
    path('categorymanagement/',views.admin_categoryManagement, name='categorymanagement'),
    path('ordermanagement/',views.admin_orderManagement, name='ordermanagement'),
    path('salesreport/',views.admin_salesRepot, name='salesreport'),
    
]
