from django.urls import path
from . import views


app_name="checkoutapp"

urlpatterns = [
    path('checkout/', views.checkout, name='checkout'),
    path('place-order/', views.place_order, name='place_order'),
    path('order-success/<int:order_id>/', views.order_success, name='order_success'),
    
    path('my-orders/', views.my_orders, name='my_orders'),
    path('cancel-order/<int:order_id>/', views.cancel_order, name='cancel_order'),
    path('razorpay-webhook/', views.razorpay_webhook, name='razorpay_webhook'),
    path('verify-payment/', views.verify_payment, name='verify_payment'),
    

]
