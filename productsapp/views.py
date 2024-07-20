from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
# from .models import Product, Category
from adminapp.models import Product, Category

def product_list(request):
    products = Product.objects.filter(is_active=True)
    print(products)
    print(f"Number of products: {products.count()}")
    
    # Add sorting functionality
    sort_by = request.GET.get('sort_by', 'name')
    if sort_by == 'price':
        products = products.order_by('price')
    elif sort_by == 'name':
        products = products.order_by('name')
        
    
    
    # Add category filter
    category = request.GET.get('category')
    if category:
        products = products.filter(category__name=category)
    
    #pagination
    paginator = Paginator(products, 12)  # Show 12 products per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    
    categories = Category.objects.filter(is_active=True)
    
    context = {
        'page_obj': page_obj,
        'sort_by': sort_by,
        'categories': categories,
        'selected_category': category
    }
    
    return render(request, 'products.html', context)
    

def product_detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    related_products = Product.objects.filter(category=product.category).exclude(id=product.id)[:4]
    context = {
        'product': product,
        'related_products': related_products
    }
    return render(request, 'product_details.html', context)