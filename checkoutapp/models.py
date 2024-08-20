from django.db import models
from django.contrib.auth.models import User
from cartapp.models import Cart
from productsapp.models import Product
from django.utils import timezone


class ShippingMethod(models.Model):
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return self.name


class OrderStatus(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Shipped', 'Shipped'),
        ('Delivered', 'Delivered'),
        ('Returned', 'Returned'),
        ('Cancelled', 'Cancelled'),
    ]

    status = models.CharField(max_length=255, choices=STATUS_CHOICES)

    def __str__(self):
        return self.status


class PaymentStatus(models.Model):
    status = models.CharField(max_length=255)

    def __str__(self):
        return self.status


class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    shipping_address = models.TextField()
    shipping_method = models.ForeignKey(ShippingMethod, on_delete=models.SET_NULL, null=True)
    order_total = models.DecimalField(max_digits=10, decimal_places=2)
    order_status = models.ForeignKey(OrderStatus, on_delete=models.SET_NULL, null=True)
    payment_status = models.ForeignKey(PaymentStatus, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Order {self.id} for {self.user.username}"

    def calculate_total(self):
        # Calculate the total order amount from cart items and shipping
        items_total = sum(item.get_total_price() for item in self.items.all())
        return items_total + self.shipping_method.price if self.shipping_method else items_total

    def apply_coupon(self, coupon):
        # Method to apply a coupon to the order
        if coupon.discount_type == 'percentage':
            discount = (self.order_total * coupon.discount_value) / 100
        else:  # fixed discount
            discount = coupon.discount_value
        return max(self.order_total - discount, 0)  # Ensure total doesn't go below zero

    def cancel_order(self):
        # Method to cancel the order
        self.order_status = OrderStatus.objects.get(status='Cancelled')
        self.cancelled_at = timezone.now()
        self.save()


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"

    def get_total_price(self):
        return self.price * self.quantity


class PaymentMethod(models.Model):
    PAYMENT_CHOICES = [
        ('cod', 'Cash on Delivery'),
        ('stripe', 'Stripe'),
        ('wallet', 'Wallet'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    payment_type = models.CharField(max_length=255, choices=PAYMENT_CHOICES)
    provider = models.CharField(max_length=255, blank=True, null=True)  # Optional field for providers like Stripe
    account_number = models.CharField(max_length=255, blank=True, null=True)  # Optional field for account details
    expiry_date = models.DateField(blank=True, null=True)  # Optional, relevant for card payments
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.get_payment_type_display()} - {self.account_number if self.account_number else 'N/A'}"
    
    


class Coupon(models.Model):
    code = models.CharField(max_length=50, unique=True)
    discount_type = models.CharField(max_length=50, choices=[('percentage', 'Percentage'), ('fixed', 'Fixed')])
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    usage_limit = models.PositiveIntegerField(default=1)

    def __str__(self):
        return self.code
