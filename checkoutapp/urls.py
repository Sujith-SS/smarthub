from django.urls import path
from . import views

urlpatterns = [
    path('checkout/', views.checkout, name='checkout'),
    path('add_address/', views.add_address, name='add_address'),
    path('edit_address/', views.edit_address, name='edit_address'),
    path('delete_address/', views.delete_address, name='delete_address'),
    # path('order_history/', views.order_history, name='order_history'),
]
