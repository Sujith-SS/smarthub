from django.contrib import admin

from .models import Order,OrderItem,PaymentMethod,Coupon,OrderStatus,PaymentStatus
# Register your models here.
admin.site.register ([Order,OrderItem,PaymentMethod,Coupon,OrderStatus,PaymentStatus])


