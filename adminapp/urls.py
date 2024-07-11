from django.urls import path
from . import views

urlpatterns = [
    path('administration', views.admin_dashboard, name='administration'),
    path('admin_login/', views.admin_login, name='admin_login'),
    path('admin_logout/',views.admin_logout , name='admin_logout'),
    
    path('userslist/', views.list_users, name='admin_user_list'),
    path('users/block/<int:user_id>/', views.block_user, name='block_user'),
    path('unblock_user/<int:user_id>/', views.unblock_user, name='unblock_user'),
    
    
    
    path('productmanagement/',views.admin_productManagement, name='productmanagement'),
    path('categorymanagement/',views.admin_categoryManagement, name='categorymanagement'),
    path('ordermanagement/',views.admin_orderManagement, name='ordermanagement'),
    path('salesreport/',views.admin_salesRepot, name='salesreport'),
    
]
