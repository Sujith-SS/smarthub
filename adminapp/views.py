from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login,logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required,user_passes_test
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.models import User
from productsapp.models import Category, ProductImage, Product
from django.http import JsonResponse
import logging
from django.db import transaction
from django.views.decorators.http import require_http_methods


def admin_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request,user)
            if user.is_superuser:
                return redirect('administration')
        else:
            messages.error(request, 'Invalid username or password.')
    return render(request, 'admin_signin.html')




def admin_logout(request):
    if request.user.is_authenticated:
        logout(request)
    return redirect('admin_login')

 

def admin_dashboard(request):
    if request.user.is_authenticated:
        if request.user.is_superuser:
            return render(request, 'admin_dashboard.html')
    return render(request, 'admin_signin.html')



# User management section

@staff_member_required(login_url='admin_login')
@login_required(login_url='admin_login')
def list_users(request):
    query = request.GET.get('search')
    if query: 
        users = User.objects.filter(username__icontains=query) | User.objects.filter(email__icontains=query)
        
    else:
        users = User.objects.all()
        users = users.order_by('username')
    return render(request, 'admin_usermanagement.html', {'users': users})



@staff_member_required(login_url='admin_login')
def block_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if user.is_superuser:
        messages.error(request, "You cannot block a superuser.")
        
    else:
        user.is_active = False
        user.save()
        messages.success(request, "User has been blocked successfully.")
    return redirect('admin_user_list')



@staff_member_required(login_url='admin_login')
def unblock_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    user.is_active = True
    user.save()
    messages.success(request, "User has been unblocked successfully.")
    return redirect('admin_user_list')



#Category management section

# List categories
@staff_member_required(login_url='admin_login')
def list_categories(request):
    query = request.GET.get('search')
    if query:
        categories = Category.objects.filter(name__icontains=query)
    else:
        categories = Category.objects.all().order_by('name')
    return render(request, 'admin_categorymanagement.html', {'categories': categories})

# Add category
@staff_member_required(login_url='admin_login')
def add_category(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        if name:
            Category.objects.create(name=name)
            return redirect('list_categories')
    categories = Category.objects.all()
    return render(request, 'admin_categorymanagement.html', {'categories': categories})

# Edit category
@staff_member_required(login_url='admin_login')
def edit_category(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    if request.method == 'POST':
        name = request.POST.get('name')
        if name:
            category.name = name
            category.save()
            return redirect('list_categories')
    categories = Category.objects.all()
    return render(request, 'admin_categorymanagement.html', {'category': category, 'categories': categories})


# status category
@staff_member_required(login_url='admin_login')
def toggle_category_status(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    if request.method == 'POST':
        category.is_active = not category.is_active
        category.save()
        status = 'listed' if category.is_active else 'unlisted'
        messages.success(request, f'Category {status} successfully.')
        return redirect('list_categories')
    categories = Category.objects.all()
    return render(request, 'admin_categorymanagement.html', {'category': category, 'categories': categories})


# List products
@staff_member_required(login_url='admin_login')
def list_products(request):
    query = request.GET.get('search')
    if query:
        products = Product.objects.filter(name__icontains=query)
    else:
        products = Product.objects.all().order_by('name')
    categories = Category.objects.filter(is_active=True)
    return render(request, 'admin_productmanagement.html', {'products': products, 'categories': categories})

# Add product

logger = logging.getLogger(__name__)

@staff_member_required(login_url='admin_login')
def add_product(request):
    if request.method == 'POST':
        try:
            with transaction.atomic():
                name = request.POST.get('name')
                description = request.POST.get('description')
                price = request.POST.get('price')
                stock = request.POST.get('stock')
                category_id = request.POST.get('category')

                # Check for missing fields
                if not all([name, description, price, stock, category_id]):
                    missing_fields = [field for field in ['name', 'description', 'price', 'stock', 'category'] if not request.POST.get(field)]
                    error_msg = f"Missing required fields: {', '.join(missing_fields)}"
                    return JsonResponse({'success': False, 'error': error_msg})

                # Convert and validate price and stock
                try:
                    price = float(price)
                    stock = int(stock)
                except ValueError:
                    return JsonResponse({'success': False, 'error': 'Invalid price or stock value.'})

                if price <= 0:
                    return JsonResponse({'success': False, 'error': 'Price must be positive.'})

                if stock < 0:
                    return JsonResponse({'success': False, 'error': 'Stock must be non-negative.'})

                # Check if category exists and is active
                try:
                    category = Category.objects.get(id=category_id, is_active=True)
                except Category.DoesNotExist:
                    error_msg = f"Category with id {category_id} does not exist or is not active"
                    return JsonResponse({'success': False, 'error': error_msg})

                # Create product
                product = Product.objects.create(
                    name=name,
                    description=description,
                    price=price,
                    stock=stock,
                    category=category
                )

                # Validate and add images
                images = request.FILES.getlist('images')
                if len(images) < 3:
                    error_msg = f"Not enough images. Received {len(images)}, need at least 3."
                    raise ValueError(error_msg)

                for image in images:
                    product_image = ProductImage.objects.create(image=image)
                    product.images.add(product_image)

                return JsonResponse({'success': True, 'message': 'Product added successfully.'})

        except ValueError as ve:
            return JsonResponse({'success': False, 'error': str(ve)})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'error': 'Invalid request method.'})


# Edit product

@require_http_methods(["GET", "PATCH"])
def edit_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    
    if request.method == 'PATCH':
        product.name = request.POST.get('name', product.name)
        product.description = request.POST.get('description', product.description)
        product.price = request.POST.get('price', product.price)
        product.stock = request.POST.get('stock', product.stock)
        category_id = request.POST.get('category')
        if category_id:
            product.category = get_object_or_404(Category, id=category_id, is_active=True)
        
        images = request.FILES.getlist('images')
        if images:
            for image in images:
                product_image = ProductImage.objects.create(image=image)
                product.images.add(product_image)
        
        product.save()
        return JsonResponse({'success': True, 'message': 'Product updated successfully.'})
    
    # GET request - return product data including image URLs
    categories = Category.objects.filter(is_active=True)
    image_urls = [image.image.url for image in product.images.all()]
    return JsonResponse({
        'product': {
            'id': product.id,
            'name': product.name,
            'description': product.description,
            'price': str(product.price),
            'stock': product.stock,
            'category_id': product.category.id,
            'image_urls': image_urls
        },
        'categories': list(categories.values('id', 'name'))
    })

@require_http_methods(["POST"])
def remove_product_image(request, product_id, image_index):
    product = get_object_or_404(Product, id=product_id)
    try:
        image = product.images.all()[image_index]
        product.images.remove(image)
        image.delete()
        return JsonResponse({'success': True})
    except IndexError:
        return JsonResponse({'success': False, 'error': 'Image not found'})
    
    
# Toggle product status
@staff_member_required(login_url='admin_login')
def product_status(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    product.is_active = not product.is_active
    product.save()
    return redirect('list_products')





def admin_categoryManagement(request):
    return render(request,'admin_categorymanagement.html')


def admin_orderManagement(request):
    return render (request, 'admin_ordermanagement.html')

def admin_salesRepot(request):
    return render (request, 'sales_report.html')


