from django.shortcuts import render, redirect
from .models import Order, OrderItem
from cartapp.models import CartItem
from users.models import Address
from users.forms import AddressForm

def checkout(request):
    if request.method == 'POST':
        address_id = request.POST.get('address_id')
        payment_option = request.POST.get('payment_option')
        address = Address.objects.get(id=address_id)
        cart_items = CartItem.objects.filter(cart__user=request.user)

        # Create order
        order = Order.objects.create(
            user=request.user,
            address=address,
            payment_option=payment_option
        )
        
        # Add cart items to the order
        for item in cart_items:
            OrderItem.objects.create(order=order, product=item.product, quantity=item.quantity)

        return redirect('order_success')

    addresses = Address.objects.filter(user=request.user)
    cart_items = CartItem.objects.filter(cart__user=request.user)
    total_price = sum(item.get_total_price() for item in cart_items)

    return render(request, 'checkout.html', {
        'addresses': addresses,
        'cart_items': cart_items,
        'total_price': total_price
    })

def add_address(request):
    if request.method == 'POST':
        form = AddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user
            address.save()
            return redirect('checkout')
    return redirect('checkout')

def edit_address(request):
    if request.method == 'POST':
        address_id = request.POST.get('address_id')
        address = Address.objects.get(id=address_id)
        form = AddressForm(request.POST, instance=address)
        if form.is_valid():
            form.save()
            return redirect('checkout')
    return redirect('checkout')

def delete_address(request):
    if request.method == 'POST':
        address_id = request.POST.get('address_id')
        address = Address.objects.get(id=address_id)
        address.delete()
        return redirect('checkout')
    return redirect('checkout')

def order_history(request):
    orders = Order.objects.filter(user=request.user)
    return render(request, 'order_history.html', {'orders': orders})
