from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from cartapp.models import Cart, CartItem
from .models import Order, OrderItem, PaymentMethod, ShippingMethod, OrderStatus, PaymentStatus
from users.models import Address
from decimal import Decimal



from django.http import JsonResponse
from decimal import Decimal



SHIPPING_CHARGE = Decimal('40.00')

@login_required(login_url="users:login")
def checkout(request):
    user = request.user
    cart = get_object_or_404(Cart, user=user)
    cart_items = CartItem.objects.filter(cart=cart)
    
    if not cart_items.exists():
        return JsonResponse({'error': 'Your cart is empty.'}, status=400)
    
    if request.method == 'POST':
        # Validate payment method
        payment_method_type = request.POST.get('payment_method')
        if not payment_method_type:
            return JsonResponse({'error': 'Payment method is required.'}, status=400)
        
        if payment_method_type == 'cod':
            payment_method = None  # COD doesn't require a payment method record
        else:
            payment_method = get_object_or_404(PaymentMethod, user=user, payment_type=payment_method_type)
        
        
        
        # Validate address
        address_id = request.POST.get('address')
        print(f"address{address_id}")
        if not address_id:
            return JsonResponse({'error': 'Address is required.'}, status=400)
        address = get_object_or_404(Address, id=address_id, user=user)
        
        # Calculate total price and quantity
        order_total = Decimal(0)
        total_quantity = 0
        for item in cart_items:
            order_total += item.get_total_price()
            total_quantity += item.quantity
        
        
        
        if order_total <= 0:
            return JsonResponse({'error': 'Order total must be greater than zero.'}, status=400)
        
        # Create Order
        order = Order.objects.create(
            user=user,
            payment_method=payment_method,
            shipping_address=address,
            order_total=order_total,
            order_status_id=1,  # assuming 1 is for 'Pending' status
            payment_status_id=1,  # assuming 1 is for 'Pending' status
        )
        
        # Create OrderItems
        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price=item.product.price,
                discounted_price=item.get_total_price(),  # Assuming you might have discounts later
            )
        
        # Clear cart after order is placed
        cart_items.delete()
        
        return JsonResponse({'success': 'Order placed successfully!'}, status=200)
    
    # Prepare context for rendering the checkout page
    total_quantity = sum(item.quantity for item in cart_items)
    cart_total = sum(item.get_total_price() for item in cart_items)
    subtotal = cart_total  # Subtotal is the cart total
    total_price = subtotal + SHIPPING_CHARGE
    

    context = {
        'cart_items': cart_items,
        'payment_methods': [
            {'payment_type': 'cod', 'display_name': 'Cash on Delivery'},
            {'payment_type': 'stripe', 'display_name': 'Stripe'},
            {'payment_type': 'wallet', 'display_name': 'Wallet'}
        ],
        'shipping_methods': ShippingMethod.objects.all(),
        'addresses': Address.objects.filter(user=user),
        'total_price': total_price, 
        'subtotal': subtotal, 
        'total_quantity': total_quantity,
        'shipping_charge': SHIPPING_CHARGE,
    }
    
    return render(request, 'checkout.html', context)



from django.db import transaction

@login_required(login_url="users:login")
def place_order(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method.'}, status=400)

    user = request.user
    cart = Cart.objects.get(user=user)
    cart_items = CartItem.objects.filter(cart=cart)

    if not cart_items.exists():
        return JsonResponse({'error': 'Your cart is empty.'}, status=400)

    address_id = request.POST.get('address')
    if not address_id:
        return JsonResponse({'error': 'Address is required.'}, status=400)
    address = get_object_or_404(Address, id=address_id, user=user)

    order_total = sum(item.get_total_price() for item in cart_items)
    total_quantity = sum(item.quantity for item in cart_items)

    if order_total <= 0:
        return JsonResponse({'error': 'Order total must be greater than zero.'}, status=400)

    order_status, _ = OrderStatus.objects.get_or_create(status='Pending')
    payment_status, _ = PaymentStatus.objects.get_or_create(status='Pending')

    try:
        with transaction.atomic():
            order = Order.objects.create(
                user=user,
                shipping_address=f"{address.address_line1}, {address.city}, {address.state}, {address.zip_code}",
                order_total=order_total,
                order_status=order_status,
                payment_status=payment_status
            )

            for item in cart_items:
                # Decrease the product stock
                product = item.product
                if product.stock < item.quantity:
                    return JsonResponse({'error': f"Not enough stock for {product.name}."}, status=400)
                
                product.stock -= item.quantity
                product.save()

                # Create order items
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=item.quantity,
                    price=item.product.price
                )

            # Clear the cart
            cart_items.delete()

            return JsonResponse({
                'success': 'Order placed successfully!',
                'order_id': order.id
            }, status=200)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

    
    
    
def order_success(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'order_success.html', {'order': order})



@login_required(login_url='users:login')
def my_orders(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'my_orders.html', {'orders': orders})

from django.utils import timezone


@login_required(login_url="users:login")
def cancel_order(request, order_id):
    try:
        order = Order.objects.get(id=order_id, user=request.user)
        if order.order_status.status != 'Cancelled':
            
            order.order_status = OrderStatus.objects.get(status='Cancelled')
            order.cancelled_at = timezone.now()
            order.save()

            
            order_items = OrderItem.objects.filter(order=order)
            for item in order_items:
                item.product.stock += item.quantity
                item.product.save()

            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'error': 'Order is already cancelled.'})
    except Order.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Order not found.'})

