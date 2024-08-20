from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from productsapp.models import Category, ProductImage, Product

def product_list(request):
    products = Product.objects.filter(is_active=True)
    
    # Sorting
    sort_by = request.GET.get('sort_by', 'name')
    if sort_by == 'price':
        products = products.order_by('price')
    elif sort_by == 'name':
        products = products.order_by('name')
    

    category = request.GET.get('category')
    if category:
        products = products.filter(category__name=category)
    
    
    price_range = request.GET.get('price_range')
    if price_range:
        if price_range == '0-1000':
            products = products.filter(price__gte=0, price__lte=1000)
        elif price_range == '1000-2000':
            products = products.filter(price__gte=1000, price__lte=2000)
        elif price_range == '2000-5000':
            products = products.filter(price__gte=2000, price__lte=5000)
        elif price_range == '5000-10000':
            products = products.filter(price__gte=5000, price__lte=10000)
        elif price_range == '10000-above':
            products = products.filter(price__gte=10000)
    
    # Pagination
    paginator = Paginator(products, 12)  # Show 12 products per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    categories = Category.objects.filter(is_active=True)
    
    context = {
        'page_obj': page_obj,
        'sort_by': sort_by,
        'categories': categories,
        'selected_category': category,
        'price_range': price_range,
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