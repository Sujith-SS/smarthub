from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Cart, CartItem
from productsapp.models import Product
from .forms import AddToCartForm
from django.http import JsonResponse


@login_required(login_url="users:login")
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    
    if not product.is_available:
        return JsonResponse({'success': False, 'message': 'This product is out of stock and cannot be added to the cart.'})
    
    cart, created = Cart.objects.get_or_create(user=request.user)
    form = AddToCartForm(request.POST)
    
    if form.is_valid():
        quantity = form.cleaned_data['quantity']
        if quantity > product.stock:
            return JsonResponse({'success': False, 'message': f'Only {product.stock} items available in stock.'})
        
        cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
        if not created:
            cart_item.quantity += quantity
            cart_item.save()
            message = 'Product quantity updated in the cart!'
            success = True
        else:
            cart_item.quantity = quantity
            cart_item.save()
            message = 'Product added to cart successfully!'
            success = True
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': success, 'message': message})
        else:
            return redirect('cartapp:cart_detail')
    
    return JsonResponse({'success': False, 'message': 'Failed to add product to cart.'})



@login_required(login_url="users:login")
def cart_detail(request):
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_items = cart.items.all()
    
    print(f"User: {request.user.username}")
    print(f"Cart ID: {cart.id}")
    print(f"Cart items: {list(cart_items)}")
    
    total_price = sum(item.get_total_price() for item in cart_items)
    
    print(f"Total price: {total_price}")
    
    context = {
        'cart': cart,
        'cart_items': cart_items,
        'total_price': total_price,
    }
    return render(request, 'cart.html', context)



@login_required(login_url="users:login")
def remove_from_cart(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    cart_item.delete()
    return redirect('cartapp:cart_detail')


@login_required(login_url="users:login")
def update_cart(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    if request.method == 'POST':
        try:
            quantity = int(request.POST.get('quantity', 0))
            if quantity > 0 and quantity <= cart_item.product.stock:
                cart_item.quantity = quantity
                cart_item.save()
            elif quantity == 0:
                cart_item.delete()
            else:
                
                pass
        except ValueError:
            pass
    return redirect('cartapp:cart_detail')

