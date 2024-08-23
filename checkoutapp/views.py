from django.shortcuts import render, get_object_or_404,redirect,HttpResponse
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from cartapp.models import Cart, CartItem
from .models import Order, OrderItem, PaymentMethod, ShippingMethod, OrderStatus, PaymentStatus
from users.models import Address
from decimal import Decimal
from django.views.decorators.cache import never_cache




from django.http import JsonResponse
from decimal import Decimal



SHIPPING_CHARGE = Decimal('40.00')

@login_required(login_url="users:login")
def checkout(request):
    print("check out called")
    
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
        elif payment_method_type == 'razorpay':
            # Get Razorpay API keys from settings
            razorpay_key_id = settings.RAZORPAY_KEY_ID
            razorpay_key_secret = settings.RAZORPAY_SECRET_KEY
            
            # Initialize Razorpay client
            client = razorpay.Client(auth=(razorpay_key_id, razorpay_key_secret))
            
            # Calculate the total amount
            total_amount = sum(item.get_total_price() for item in cart_items)
            shipping_charge = settings.SHIPPING_CHARGE
            total_amount_with_shipping = total_amount + shipping_charge
            total_amount_paise = int(total_amount_with_shipping * 100)  # Convert to paisa
            
            # Create Razorpay order
            razorpay_order = client.order.create({
                "amount": total_amount_paise,
                "currency": "INR",
                "payment_capture": "1"  # Auto capture the payment
            })
            
            payment_method = {
                'razorpay_order_id': razorpay_order['id'],
                'razorpay_key_id': razorpay_key_id
            }
        else:
            payment_method = get_object_or_404(PaymentMethod, user=user, payment_type=payment_method_type)
        
        # Validate address
        address_id = request.POST.get('address')
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
            shipping_address=f"{address.address_line1}, {address.city}, {address.state}, {address.zip_code}",
            order_total=order_total,
            order_status_id=1,  # assuming 1 is for 'Pending' status
            payment_status_id=1,  # assuming 1 is for 'Pending' status
            razorpay_payment_id=payment_method.get('razorpay_order_id', '') if payment_method_type == 'razorpay' else ''
        )
        
        # Create OrderItems
        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=item.product,
                quantity=item.quantity,
                price=item.product.price
            )
        
        # Clear cart after order is placed
        cart_items.delete()
        
        if payment_method_type == 'razorpay':
            return JsonResponse({
                'success': 'Order placed successfully!',
                'order_id': order.id,
                'razorpay_order_id': payment_method['razorpay_order_id'],
                'razorpay_key_id': payment_method['razorpay_key_id'],
                'amount': total_amount_paise
            }, status=200)
        else:
            return JsonResponse({'success': 'Order placed successfully!', 'order_id': order.id}, status=200)
    
    # Prepare context for rendering the checkout page
    total_quantity = sum(item.quantity for item in cart_items)
    cart_total = sum(item.get_total_price() for item in cart_items)
    subtotal = cart_total  # Subtotal is the cart total
    total_price = subtotal + SHIPPING_CHARGE
    
    context = {
        'cart_items': cart_items,
        'payment_methods': [
            {'payment_type': 'cod', 'display_name': 'Cash on Delivery'},
            {'payment_type': 'razorpay', 'display_name': 'Razorpay'},
            {'payment_type': 'wallet', 'display_name': 'Wallet'}
        ],
        'shipping_methods': ShippingMethod.objects.all(),
        'addresses': Address.objects.filter(user=user),
        'total_price': total_price,
        'subtotal': subtotal,
        'total_quantity': total_quantity,
        'shipping_charge': settings.SHIPPING_CHARGE,
    }
    
    return render(request, 'checkout.html', context)





from django.db import transaction

import razorpay
from django.conf import settings

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

    if order_total <= 0:
        return JsonResponse({'error': 'Order total must be greater than zero.'}, status=400)

    try:
        payment_method_type = request.POST.get('payment_method')
        if payment_method_type == 'razorpay':
            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_SECRET_KEY))
            data = {
                "amount": int(order_total * 100),  # amount in paise
                "currency": "INR",
                "receipt": "receipt_" + str(user.id),
                "payment_capture": 1  # Auto-capture
            }
            razorpay_order = client.order.create(data=data)

            # Create the order in the database
            order_status, _ = OrderStatus.objects.get_or_create(status='Pending')
            payment_status, _ = PaymentStatus.objects.get_or_create(status='Pending')

            with transaction.atomic():
                order = Order.objects.create(
                    user=user,
                    shipping_address=f"{address.address_line1}, {address.city}, {address.state}, {address.zip_code}",
                    order_total=order_total,
                    order_status=order_status,
                    payment_status=payment_status,
                    razorpay_payment_id=razorpay_order['id']  # Save Razorpay order ID
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
                'success': 'Razorpay order created successfully!',
                'razorpay_order_id': razorpay_order['id'],
                'razorpay_key_id': settings.RAZORPAY_KEY_ID,
                'order_total': order_total
            }, status=200)

        elif payment_method_type == 'cod':
            # Handle Cash on Delivery (COD) orders
            order_status, _ = OrderStatus.objects.get_or_create(status='Confirmed')
            payment_status, _ = PaymentStatus.objects.get_or_create(status='COD Pending')

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
                'success': 'Order placed successfully with Cash on Delivery!',
                'order_id': order.id
            }, status=200)

        else:
            return JsonResponse({'error': 'Invalid payment method.'}, status=400)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


    
 
@login_required(login_url="users:login")
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
    order = get_object_or_404(Order, id=order_id, user=request.user)

    if order.payment_status.status == 'Paid':
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_SECRET_KEY))
        
        try:
            # Refund the payment
            refund_response = client.payment.refund(order.razorpay_payment_id)
            # Log the refund response or handle it as needed
            order.payment_attempts += 1  # Increment payment attempt count
            order.save()
        except Exception as e:
            # Handle any exceptions or errors during refund
            print(f"Error during refund: {e}")
            return JsonResponse({'error': 'Failed to process refund. Please try again later.'}, status=500)

    # Cancel the order
    order.cancel_order()
    
    return redirect('checkoutapp:my_orders')



# Razorpay

import razorpay
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import json


@csrf_exempt
def razorpay_webhook(request):
    if request.method == 'POST':
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_SECRET_KEY))
        
        try:
            data = request.body.decode('utf-8')
            signature = request.META.get('HTTP_X_RAZORPAY_SIGNATURE', '')
            
            # Validate webhook signature
            client.utility.verify_webhook_signature(data, signature, settings.RAZORPAY_WEBHOOK_SECRET)
            
            webhook_data = json.loads(data)
            event_type = webhook_data.get('event')
            payload = webhook_data.get('payload', {}).get('payment', {}).get('entity', {})
            
            if event_type == 'payment.captured':
                razorpay_order_id = payload.get('order_id')
                payment_id = payload.get('id')

                if not razorpay_order_id or not payment_id:
                    return HttpResponse('Order ID or Payment ID missing', status=400)
                
                try:
                    order = Order.objects.get(razorpay_payment_id=razorpay_order_id)
                except Order.DoesNotExist:
                    return HttpResponse('Order not found', status=404)

                # Update payment and order status
                paid_status, _ = PaymentStatus.objects.get_or_create(status='Paid')
                confirmed_status, _ = OrderStatus.objects.get_or_create(status='Confirmed')
                
                order.payment_status = paid_status
                order.order_status = confirmed_status
                order.save()

                # Update stock only after payment is confirmed
                order_items = OrderItem.objects.filter(order=order)
                for item in order_items:
                    product = item.product
                    if product.stock < item.quantity:
                        return HttpResponse('Insufficient stock for ordered items', status=400)
                    product.stock -= item.quantity
                    product.save()
                
            elif event_type == 'payment.failed':
                # Handle payment failure case
                razorpay_order_id = payload.get('order_id')
                try:
                    order = Order.objects.get(razorpay_payment_id=razorpay_order_id)
                    failed_status, _ = PaymentStatus.objects.get_or_create(status='Failed')
                    order.payment_status = failed_status
                    order.save()
                except Order.DoesNotExist:
                    return HttpResponse('Order not found', status=404)

            return HttpResponse(status=200)
        
        except razorpay.errors.SignatureVerificationError:
            return HttpResponse('Webhook signature verification failed', status=400)
        except Exception as e:
            return HttpResponse(f'Unexpected error: {str(e)}', status=500)
    
    else:
        return HttpResponse('Invalid request method', status=405)

    
    
    
@csrf_exempt
def verify_payment(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method.'}, status=400)

    try:
        data = json.loads(request.body)
        razorpay_order_id = data.get('razorpay_order_id')
        razorpay_payment_id = data.get('razorpay_payment_id')
        razorpay_signature = data.get('razorpay_signature')

        if not all([razorpay_order_id, razorpay_payment_id, razorpay_signature]):
            return JsonResponse({'error': 'Missing payment details.'}, status=400)

        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_SECRET_KEY))

        # Verify the payment signature
        client.utility.verify_payment_signature({
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature
        })

        # If verification is successful, update order status and payment status
        order = get_object_or_404(Order, razorpay_payment_id=razorpay_order_id)
        
        # Retrieve or create the 'Paid' PaymentStatus
        paid_status, _ = PaymentStatus.objects.get_or_create(status='Paid')
        order.payment_status = paid_status
        order.save()

        return JsonResponse({'success': True, 'order_id': order.id})

    except razorpay.errors.SignatureVerificationError:
        return JsonResponse({'error': 'Payment signature verification failed.'}, status=400)
    except Order.DoesNotExist:
        return JsonResponse({'error': 'Order not found.'}, status=404)
    except PaymentStatus.DoesNotExist:
        return JsonResponse({'error': 'Payment status does not exist.'}, status=400)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data.'}, status=400)
    except Exception as e:
        # Log unexpected exceptions for debugging
        return JsonResponse({'error': f'Unexpected error: {str(e)}'}, status=500)