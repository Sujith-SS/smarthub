from django.urls import path
from . import views

urlpatterns = [
    path('administration', views.admin_dashboard, name='administration'),
    path('admin_login/', views.admin_login, name='admin_login'),
    path('admin_logout/',views.admin_logout , name='admin_logout'),
    
    path('userslist/', views.list_users, name='admin_user_list'),
    path('users/block/<int:user_id>/', views.block_user, name='block_user'),
    path('unblock_user/<int:user_id>/', views.unblock_user, name='unblock_user'),
    
    path('categories/', views.list_categories, name='list_categories'),
    path('add_category/', views.add_category, name='add_category'),
    path('edit_category/<int:category_id>/', views.edit_category, name='edit_category'),
    path('toggle_category_status/<int:category_id>/', views.toggle_category_status, name='toggle_category_status'),
    
    path('products/', views.list_products, name='list_products'),
    path('add_product/', views.add_product, name='add_product'),
    path('product_status/<int:product_id>/', views.product_status, name='product_status'),
    path('edit_product/<int:product_id>/', views.edit_product, name='edit_product'),
    
    
    
    # path('productmanagement/',views.admin_productManagement, name='productmanagement'),
    path('ordermanagement/',views.admin_orderManagement, name='ordermanagement'),
    path('salesreport/',views.admin_salesRepot, name='salesreport'),
    
]
