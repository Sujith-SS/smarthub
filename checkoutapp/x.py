import json
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.shortcuts import render, redirect,get_object_or_404
from .form import UserRegistrationForm
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.db.models import Count,Avg,Sum
import re
from .utils import generate_otp, send_otp
from datetime import datetime, timedelta
from django.db.models import Avg, Min, Max,Q
from django.conf import settings
import razorpay
from razorpay import Client as RazorpayClient
from django.utils import timezone
from django.urls import reverse
from django.db import transaction
from django.contrib.auth.decorators import user_passes_test
from Admin_side.models import (
    User,
    Address,
    PaymentType,
    PaymentMethod,
    Category,
    SubCategory,
    Variation,
    VariationOption,
    Product,
    ProductConfiguration,
    Cart,
    CartItem,
    ShippingMethod,
    OrderStatus,
    Order,
    OrderLine,
    Review,
    Promotion,
    PromotionCategory,
    ProductImage,
    Coupon,
    CouponUsage,
    Wishlist,
    WishlistItem,
    Wallet,
    Transaction,
    CarouselBanner,
    OfferBanner,
    PaymentStatus,
    OrderReturn,
    OrderReturnStatus,
    PermanentAddress
)


# from django.core.validators import validate_email,EmailValidator


########################## function for login & singUp ###############################
@never_cache
def userLogin(request):
    # print("Submit value:", request.POST.get('submit'))

    if request.user.is_authenticated:
        return redirect('userHome')

    active_form = "login"  # Default active form
    print("Initial active_form:", active_form)

    def clean_email(email):
        mail_regex = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b"
        if re.fullmatch(mail_regex, email):
            return email
        else:
            raise ValidationError("Invalid email format")

    def clean_password(password):
        if len(password) < 8:
            raise ValidationError("Password should contain at least 8 characters.")
        if not re.search("[A-Z]", password):
            raise ValidationError(
                "Password should contain at least one uppercase letter."
            )
        if not re.search("[a-z]", password):
            raise ValidationError(
                "Password should contain at least one lowercase letter."
            )
        if not re.search("[0-9]", password):
            raise ValidationError("Password should contain at least one digit.")
        if not re.search('[@#$%^&*(),.?":{}|<>]', password):
            raise ValidationError(
                "Password should contain at least one special character."
            )
        return password

    if request.method == "POST":
        if request.POST.get("submit") == "login_form":
            ## login the user

            username = request.POST.get("loginUsername")
            password = request.POST.get("loginPassword")
            active_form = "login"

            if not username:
                messages.error(request, "Enter the Email")
            elif not password:
                messages.error(request, "Enter the Password")
            else:
                user = authenticate(username=username, password=password)
                if user is None:
                    messages.error(request, "Invalid Email Id or Password")
                elif user.is_active is False:
                    messages.error(request, f"{username} was temporarily blocked to access this site")
                else:
                    auth_login(request, user)
                    return redirect("userHome")

        elif request.POST.get("submit") == "signup_form":
            ## signUp new user

            signUp_username = request.POST["signupUsername"]
            signUp_email = request.POST["signupEmail"]
            signUp_password1 = request.POST["signupPassword"]
            signUp_password2 = request.POST["signupConfirmationPassword"]
            active_form = "signup"

            if User.objects.filter(username=signUp_username).exists():
                messages.error(
                    request, f"User name '{signUp_username}' is already taken"
                )
            elif User.objects.filter(email=signUp_email).exists():
                messages.error(
                    request, f"Mail Id '{signUp_email}' already has an account"
                )
            elif signUp_password1 != signUp_password2:
                messages.error(request, "Passwords do not match")
            else:
                if not signUp_username:
                    messages.error(request, "Enter the username")
                elif not signUp_email:
                    messages.error(request, "Enter the email")
                elif not signUp_password1:
                    messages.error(request, "Enter the Password")
                elif not signUp_password2:
                    messages.error(request, "Enter the Confirmation Password")
                else:

                    try:
                        clean_email(signUp_email)
                        clean_password(signUp_password1)
                    except ValidationError as e:
                        messages.error(request, e.message)
                    else:
                        # Save user data to session
                        request.session["username"] = signUp_username
                        request.session["email"] = signUp_email
                        request.session["password"] = signUp_password1

                        # Generate OTP and send it via email
                        otp = generate_otp()
                        send_otp(signUp_email, otp)
                        request.session["otp"] = otp
                        request.session["otp_creation_time"] = datetime.now().strftime(
                            "%Y-%m-%d %H:%M:%S"
                        )
                        return redirect("otp")
                        messages.success(
                            request, f"New user '{signUp_username}' is created"
                        )
                        return redirect("userLogin")

    print("Final active_form:", active_form)
    return render(request, "login.html", {"active_form": active_form})

def ajax_login_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'success': False, 'error': 'Authentication required'}, status=401)
        return view_func(request, *args, **kwargs)
    return wrapper

def otp(request):
    # Retrieve user data from session
    username = request.session.get("username")
    email = request.session.get("email")
    password = request.session.get("password")
    otp_creation_time_str = request.session.get("otp_creation_time")

    # Check if user data is present in session
    if not (username and email and password):
        return redirect("userLogin")

    otp_creation_time = datetime.strptime(otp_creation_time_str, "%Y-%m-%d %H:%M:%S")
    otp_expiry_time = otp_creation_time + timedelta(minutes=5)

    if datetime.now() > otp_expiry_time:
        messages.error(request, "OTP has expired. Please sign up again.")
        return redirect("userLogin")

    if request.method == "POST":
        # Assuming your OTP fields are named 'ist', 'sec', 'third', 'fourth', and 'fifth'
        otp_digits = [
            request.POST.get("ist", ""),
            request.POST.get("sec", ""),
            request.POST.get("third", ""),
            request.POST.get("fourth", ""),
            request.POST.get("fifth", ""),
        ]

        # Concatenate OTP digits into a single OTP string
        otp = "".join(otp_digits)
        print("otp", otp)
        # Retrieve OTP from session
        session_otp = request.session.get("otp")
        print("session", otp)
        if otp == session_otp:
            # OTP is correct, create user and log in
            user = User.objects.create_user(
                username=username, email=email, password=password
            )
            user.is_active = True
            user.save()
            # auth_login(request, user)
            return redirect("userLogin")
        else:
            # Invalid OTP, display error message
            messages.error(request, "Ivalid otp")
            return render(request, "otp.html")

    return render(request, "otp.html")


def resend_otp(request):
    if request.method == "GET":
        # Retrieve user email from session
        email = request.session.get("email")

        # Generate new OTP and update session
        new_otp = generate_otp()
        request.session["otp"] = new_otp
        request.session["otp_creation_time"] = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        # Resend OTP via email (assuming send_otp function sends the OTP)
        send_otp(email, new_otp)

        # Display success message
        messages.success(request, "OTP has been resent.")

        # Redirect back to OTP page
        return redirect("otp")


########################## function for home page ############################
def common(request):
    categories = Category.objects.filter(is_active=True)
    context = {"categories":categories}
    return redirect(request,'common.html',context)

# @login_required(login_url='userLogin')
@never_cache
def userHome(request):
    categories = Category.objects.filter(is_active=True)
    featured_products = Product.objects.filter(is_featured=True)
    recent_products = Product.objects.order_by('-created_at')[:10]
    carousel_banners = CarouselBanner.objects.filter(is_active=True)
    offer_banners = OfferBanner.objects.filter(is_active=True)
    for product in featured_products:
        configs = ProductConfiguration.objects.filter(product=product).order_by('price')
        if configs:
            first_config = configs.first()
            product.starting_price = first_config.price
            product.discounted_price = first_config.get_discounted_price()
            # print(product.discounted_price)
        else:
            product.starting_price = 0
            product.discounted_price = 0

    for product in recent_products:
        configs = ProductConfiguration.objects.filter(product=product).order_by('price')
        if configs:
            first_config = configs.first()
            product.starting_price = first_config.price
            product.discounted_price = first_config.get_discounted_price()
        else:
            product.starting_price = 0
            product.discounted_price = 0

    context = {
        "categories": categories,
        "featured_products": featured_products,
        "recent_products": recent_products,
        'carousel_banners': carousel_banners,
        'offer_banners': offer_banners,        
    }
    return render(request, "home.html", context)

@never_cache
def productDetails(request, pk):
    product = get_object_or_404(Product, pk=pk)
    related_products = Product.objects.filter(
        Q(subcategory=product.subcategory), 
        is_active=True
    ).exclude(id=product.id)
    
    configurations = []
    for config in product.configurations.all():
        option_ids = list(config.variation_options.values_list('id', flat=True))
        configurations.append({
                'id': config.id,
                'price': float(config.price),
                'discounted_price': float(config.get_discounted_price()),
                'qty_in_stock': config.qty_in_stock,
                'options': option_ids
        })
    
    # Calculate prices for the main product
    product_configs = ProductConfiguration.objects.filter(product=product)
    product.min_price = product_configs.aggregate(Min('price'))['price__min']
    product.min_discounted_price = min((config.get_discounted_price() for config in product_configs), default=product.min_price)

    # Calculate prices for related products
    for related_product in related_products:
        related_configs = ProductConfiguration.objects.filter(product=related_product)
        related_product.min_price = related_configs.aggregate(Min('price'))['price__min']
        related_product.min_discounted_price = min((config.get_discounted_price() for config in related_configs), default=related_product.min_price)

    if not product.is_active:
        return redirect("userHome")

    context = {
        'product': product,
        'related_products': related_products,
        'configurations': configurations,
    }
    return render(request, "productDetails.html", context)

from django.db.models import Min, Max, Avg
from decimal import Decimal
@never_cache
def shop(request):
    products = Product.objects.filter(is_active=True)
    categories = Category.objects.filter(is_active=True)
    sort = request.GET.get('sort', 'default')
    
    if sort == 'price_low_high':
        products = products.annotate(min_price=Min('configurations__price')).order_by('min_price')
    elif sort == 'price_high_low':
        products = products.annotate(max_price=Max('configurations__price')).order_by('-max_price')
    elif sort == 'featured':
        products = products.order_by('-is_featured')
    elif sort == 'new_arrivals':
        products = products.order_by('-created_at')
    elif sort == 'a_z':
        products = products.order_by('name')
    elif sort == 'z_a':
        products = products.order_by('-name')
    
    for product in products:
        configs = product.configurations.all()
        product.min_price = configs.aggregate(Min('price'))['price__min']
        product.max_price = configs.aggregate(Max('price'))['price__max']
        product.min_discounted_price = min((config.get_discounted_price() for config in configs), default=Decimal(product.min_price or 0))

        if sort == 'price_low_high':
            product.display_price = product.min_price
        elif sort == 'price_high_low':
            product.display_price = product.max_price
        else:
            product.display_price = product.min_price  # Changed from avg_price to min_price
    
    context = {
        "products": products,
        "sort": sort,
        "categories": categories,
    }
    return render(request, "shop.html", context)

from django.db.models import Min, Max, Avg
from decimal import Decimal
@never_cache
def categoryProduct(request, pk):
    products = Product.objects.filter(category_id=pk,is_active=True)
    sort = request.GET.get('sort', 'default')
    categories = Category.objects.filter(is_active=True)

    if sort == 'price_low_high':
        products = products.annotate(min_price=Min('configurations__price')).order_by('min_price')
    elif sort == 'price_high_low':
        products = products.annotate(max_price=Max('configurations__price')).order_by('-max_price')
    elif sort == 'featured':
        products = products.order_by('-is_featured')
    elif sort == 'new_arrivals':
        products = products.order_by('-created_at')
    elif sort == 'a_z':
        products = products.order_by('name')
    elif sort == 'z_a':
        products = products.order_by('-name')

    for product in products:
        configs = product.configurations.all()
        product.min_price = configs.aggregate(Min('price'))['price__min']
        product.max_price = configs.aggregate(Max('price'))['price__max']
        product.min_discounted_price = min((config.get_discounted_price() for config in configs), default=Decimal(product.min_price or 0))

        if sort == 'price_low_high':
            product.display_price = product.min_price
        elif sort == 'price_high_low':
            product.display_price = product.max_price
        else:
            product.display_price = product.min_price  # You can change this to avg_price if you prefer

    context = {
        "products": products,
        "sort": sort,
        "categories": categories,
    }
    return render(request, "categoryProduct.html", context)

@never_cache
def subcategoryProduct(request, pk):
    products = Product.objects.filter(subcategory_id=pk)
    sort = request.GET.get('sort', 'default')
    categories = Category.objects.filter(is_active=True)

    if sort == 'price_low_high':
        products = products.annotate(min_price=Min('configurations__price')).order_by('min_price')
    elif sort == 'price_high_low':
        products = products.annotate(max_price=Max('configurations__price')).order_by('-max_price')
    elif sort == 'featured':
        products = products.order_by('-is_featured')
    elif sort == 'new_arrivals':
        products = products.order_by('-created_at')
    elif sort == 'a_z':
        products = products.order_by('name')
    elif sort == 'z_a':
        products = products.order_by('-name')

    for product in products:
        configs = product.configurations.all()
        product.min_price = configs.aggregate(Min('price'))['price__min']
        product.max_price = configs.aggregate(Max('price'))['price__max']
        product.min_discounted_price = min((config.get_discounted_price() for config in configs), default=Decimal(product.min_price or 0))

        if sort == 'price_low_high':
            product.display_price = product.min_price
        elif sort == 'price_high_low':
            product.display_price = product.max_price
        else:
            product.display_price = product.min_price  # You can change this to avg_price if you prefer

    context = {
        "products": products,
        "sort": sort,
        "categories": categories
    }
    
    return render(request, "subcategoryProduct.html", context)

@login_required(login_url='userLogin')
@never_cache
def profile(request, pk):
    user = get_object_or_404(User, pk=pk)
    addresses = Address.objects.filter(user=user)
    context = {"user": user, "addresses": addresses}
    return render(request, "profile.html", context)

@login_required(login_url='userLogin')
def editProfile(request,pk):
    user = get_object_or_404(User, pk=pk)
    context = {"user":user}
    return render(request,"editProfile.html",context)

@login_required(login_url='userLogin')
def addAddress(request,pk):
    user = get_object_or_404(User, pk=pk)

    if request.method == 'POST':
        unit_number = request.POST.get('unit_number')
        street_number = request.POST.get('street_number')
        address_line1 = request.POST.get('address_line1')
        address_line2 = request.POST.get('address_line2')
        city = request.POST.get('city')
        region = request.POST.get('region')
        postal_code = request.POST.get('postal_code')
        country = request.POST.get('country')
        is_default = request.POST.get('is_default') == 'on'

        # Validate required fields
        if not street_number or not address_line1 or not city or not region or not postal_code or not country:
            messages.error(request, "Please fill in all required fields.")
            return redirect('addAddress', pk=user.pk)
        else:
            if is_default:
                # Unset the default flag for all other addresses of the user
                Address.objects.filter(user=user, is_default=True).update(is_default=False)
        # Create the address
        Address.objects.create(
            user=user,
            unit_number=unit_number,
            street_number=street_number,
            address_line1=address_line1,
            address_line2=address_line2,
            city=city,
            region=region,
            postal_code=postal_code,
            country=country,
            is_default=is_default
        )
        messages.success(request, "Address added successfully.")
        return redirect('profile', pk=user.pk)  # Change to the appropriate success URL

    return render(request, 'addAddress.html', {'user': user})

def set_default_address(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        address_id = data.get('address_id')
        user_id = data.get('user_id')

        try:
            user = User.objects.get(pk=user_id)
            Address.objects.filter(user=user, is_default=True).update(is_default=False)
            Address.objects.filter(pk=address_id).update(is_default=True)
            return JsonResponse({'success': True})
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'User does not exist'})
        except Address.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Address does not exist'})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required(login_url='userLogin')
def editAddress(request, pk):
    try:
        address = get_object_or_404(Address, pk=pk, user=request.user)
        addresses = list(Address.objects.filter(user=request.user))
        address_number = addresses.index(address) + 1
        context = {"address": address, "edit": True,"address_number":address_number}
    except Address.DoesNotExist:
        messages.error(request, "The address you are trying to edit does not exist.")
        return redirect("profile", pk=request.user.pk) 
    if request.method == "POST":
        address.unit_number = request.POST.get('unit_number')
        address.street_number = request.POST.get('street_number')
        address.address_line1 = request.POST.get('address_line1')
        address.address_line2 = request.POST.get('address_line2')
        address.city = request.POST.get('city')
        address.region = request.POST.get('region')
        address.postal_code = request.POST.get('postal_code')
        address.country = request.POST.get('country')
        address.is_default = 'is_default' in request.POST
        address.save()
        messages.success(request, "Address updated successfully.")
        return redirect('profile', pk=request.user.pk)
    return render(request, "editAddress.html", context)

def deleteAddress(request, pk):
    address = get_object_or_404(Address, pk=pk, user=request.user)
    if address.is_default:
        messages.error(request, "Default address cannot be deleted.")
        return redirect('profile', pk=request.user.id)
    if request.method == "POST":
        address.delete()
        messages.success(request, "Address deleted successfully.")
    return redirect('profile', pk=request.user.id)


@login_required(login_url='userLogin')
@never_cache
def cart_view(request):
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_items = CartItem.objects.filter(cart=cart)
    categories = Category.objects.filter(is_active=True)

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        cart_items_data = []
        for item in cart_items:
            original_price = float(item.product_configuration.price)
            discounted_price = float(item.product_configuration.get_discounted_price())
            discount_percentage = ((original_price - discounted_price) / original_price) * 100 if original_price > discounted_price else 0
            
            item_data = {
                'id': item.id,
                'product_name': item.product_configuration.product.name,
                'product_image': item.product_configuration.product.images.first().image.url,
                'original_price': original_price,
                'discounted_price': discounted_price,
                'discount_percentage': round(discount_percentage, 2),
                'quantity': item.qty
            }
            cart_items_data.append(item_data)
        
        return JsonResponse({'cart_items': cart_items_data})

    context = {
        'cart_items': cart_items,
        "categories": categories
    }
    return render(request, 'cart.html', context)

@require_POST
@ajax_login_required
def add_to_cart(request):
    try:
        data = json.loads(request.body)
        product_id = data.get('product_id')
        configuration_id = data.get('configuration_id')
        quantity = data.get('quantity', 1)

        if not product_id or not configuration_id:
            raise ValueError('Product ID and configuration ID are required')

        product = get_object_or_404(Product, id=product_id)
        configuration = get_object_or_404(ProductConfiguration, id=configuration_id,product=product)

        cart, created = Cart.objects.get_or_create(user=request.user)

        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product_configuration=configuration
        )

        if created:
            cart_item.qty = int(quantity)
        else:
            cart_item.qty += int(quantity)
        
        cart_item.save()

        return JsonResponse({'success': True}, status=200)
    
    except ValueError as ve:
        return JsonResponse({'success': False, 'error': str(ve)}, status=400)
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    

@require_POST
def get_configuration_id(request):
    try:
        data = json.loads(request.body)
        product_id = data.get('product_id')
        selected_options = data.get('selected_options', [])
        print("data", data)
        print("product id", product_id)
        print("selected options", selected_options)
        
        if not product_id or not selected_options:
            raise ValueError('Product ID and selected options are required')

        product = get_object_or_404(Product, id=product_id)
        print("product", product)
        
        # Convert selected options to VariationOption objects
        selected_options_objects = VariationOption.objects.filter(id__in=selected_options)
        print("selected option objects", selected_options_objects)
        
        # Ensure the number of selected options matches the expected number
        if len(selected_options_objects) != len(selected_options):
            raise ValueError('Mismatch in the number of selected options and the variation options found')

        # Fetch the configuration that exactly matches all selected options
        configurations = ProductConfiguration.objects.filter(
            product=product
        ).annotate(
            num_options=Count('variation_options')
        ).filter(
            num_options=len(selected_options)
        ).distinct()

        # Ensure the configuration matches the selected options exactly
        matching_configurations = []
        for config in configurations:
            config_option_ids = set(config.variation_options.values_list('id', flat=True))
            selected_option_ids = set(selected_options_objects.values_list('id', flat=True))
            if config_option_ids == selected_option_ids:
                matching_configurations.append(config)
        
        print("matching configurations", matching_configurations)
        
        if len(matching_configurations) == 1:
            configuration = matching_configurations[0]
            return JsonResponse({
                'success': True, 
                'configuration_id': configuration.id,
                'price': configuration.price,
                'qty_in_stock': configuration.qty_in_stock
            }, status=200)
        else:
            raise ValueError('No matching configuration found or multiple configurations found')

    except ValueError as ve:
        return JsonResponse({'success': False, 'error': str(ve)}, status=400)
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


def contact(request):
    return render(request, "contact.html")


@csrf_exempt
def increment_quantity(request, item_id):
    try:
        cart_item = CartItem.objects.get(id=item_id)
        if cart_item.product_configuration.qty_in_stock > cart_item.qty:
            cart_item.qty += 1
            cart_item.save()
            response_data = {
                'status': 'success',
                'quantity': cart_item.qty,
                'price': cart_item.product_configuration.price,
                'total': cart_item.qty * cart_item.product_configuration.price,
                'subtotal': calculate_subtotal(cart_item.cart),
                'total_cart': calculate_total(cart_item.cart)
            }
        else:
            response_data = {'status': 'error', 'message': 'Insufficient stock'}
        return JsonResponse(response_data)
    except CartItem.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Item not found'}, status=404)


@csrf_exempt
def decrement_quantity(request, item_id):
    try:
        cart_item = CartItem.objects.get(id=item_id)
        if cart_item.qty > 1:
            cart_item.qty -= 1
            cart_item.save()
        response_data = {
            'status': 'success',
            'quantity': cart_item.qty,
            'price': cart_item.product_configuration.price,
            'total': cart_item.qty * cart_item.product_configuration.price,
            'subtotal': calculate_subtotal(cart_item.cart),
            'total_cart': calculate_total(cart_item.cart)
        }
        return JsonResponse(response_data)
    except CartItem.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Item not found'}, status=404)

@csrf_exempt
def remove_cart_item(request, item_id):
    try:
        cart_item = CartItem.objects.get(id=item_id)
        cart_item.delete()
        response_data = {
            'status': 'success',
            'subtotal': calculate_subtotal(cart_item.cart),
            'total_cart': calculate_total(cart_item.cart)
        }
        return JsonResponse(response_data)
    except CartItem.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Item not found'}, status=404)

def calculate_subtotal(cart):
    cart_items = CartItem.objects.filter(cart=cart)
    return sum(item.qty * item.product_configuration.price for item in cart_items)

def calculate_total(cart):
    # Assuming shipping cost is fixed at $10
    return calculate_subtotal(cart) + 10


@require_POST
def check_cart_quantity(request):
    try:
        data = json.loads(request.body)
        product_id = data.get('product_id')
        configuration_id = data.get('configuration_id')
        quantity = data.get('quantity')

        if not product_id or not configuration_id or quantity is None:
            return JsonResponse({'success': False, 'message': 'Product ID, Configuration ID, and quantity are required'}, status=400)

        # Fetch product configuration
        product_configuration = get_object_or_404(ProductConfiguration, id=configuration_id)
        
        # Calculate the total quantity in the cart for this configuration
        total_quantity_in_cart = CartItem.objects.filter(
            product_configuration_id=configuration_id
        ).aggregate(total=Sum('qty'))['total'] or 0

        # Check if adding the requested quantity exceeds the available stock
        if total_quantity_in_cart + quantity > product_configuration.qty_in_stock:
            return JsonResponse({
                'success': False,
                'message': f'Only {product_configuration.qty_in_stock - total_quantity_in_cart} items available.'
            }, status=200)
        
        return JsonResponse({'success': True}, status=200)

    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)

@login_required(login_url='userLogin')
@never_cache
def order_success(request):
    return render(request, 'order_success.html')

@csrf_exempt
def razorpay_checkout(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            amount = data.get('amount')
            
            if amount is None:
                return JsonResponse({'error': 'Amount is required'}, status=400)
            
            # Convert amount to paise
            order_amount = int(float(amount) * 100)
            
            client = razorpay.Client(auth=(settings.RAZORPAY_KEY, settings.RAZORPAY_SECRET))
            
            order_currency = 'INR'
            order_receipt = 'order_rcptid_11'
            notes = {'Shipping address': 'TVM, Kerala'}

            razorpay_order = client.order.create(
                {
                    'amount': order_amount,
                    'currency': order_currency,
                    'receipt': order_receipt,
                    'notes': notes,
                }
            )

            print('Razorpay order created:', razorpay_order) 
            return JsonResponse({
                'razorpay_order_id': razorpay_order['id'],
                'amount': order_amount
            })
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            print(f"Error in razorpay_checkout: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=400)

from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from decimal import Decimal

@login_required(login_url='userLogin')
@never_cache
def checkOut(request):
    categories = Category.objects.filter(is_active=True)
    user = request.user

    if request.method == 'POST':
        payment_method = request.POST.get('payment')
        try:
            if payment_method == 'directcheck':
                payment_method_instance = PaymentMethod.objects.get(name='Cash On Delivery')
            elif payment_method == 'paypal':
                payment_method_instance = PaymentMethod.objects.get(name='Paypal')
            elif payment_method == 'banktransfer':
                payment_method_instance = PaymentMethod.objects.get(name='Bank Transfer')
            else:
                return JsonResponse({'status': 'error', 'message': 'Invalid payment method.'})
        except PaymentMethod.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Payment method not found.'})

        addresses = Address.objects.filter(user=user)
        default_address = addresses.filter(is_default=True).first() or addresses.first()
        if not default_address:
            return JsonResponse({'status': 'error', 'message': 'No address found for user.'})

        cart, created = Cart.objects.get_or_create(user=user)
        cart_items = CartItem.objects.filter(cart=cart)

        order_total = sum(Decimal(item.qty) * Decimal(item.product_configuration.price) for item in cart_items)
        shipping_cost = Decimal('10.00')
        total_discount = Decimal('0.00')
        
        for item in cart_items:
            if item.product_configuration.get_discounted_price:
                discount_price = Decimal(item.product_configuration.get_discounted_price())
                original_price = Decimal(item.product_configuration.price)
                discount = original_price - discount_price
                total_discount += discount * Decimal(item.qty)

        order_total -= total_discount
        order_total += shipping_cost

        order_status, created = OrderStatus.objects.get_or_create(status='Pending')

        order = Order.objects.create(
            user=user,
            payment_method=payment_method_instance,
            shipping_address=default_address,
            shipping_method=ShippingMethod.objects.get(name='Standard'),
            order_total=order_total,
            order_status=order_status
        )

        for item in cart_items:
            OrderLine.objects.create(
                order=order,
                product_configuration=item.product_configuration,
                qty=item.qty,
                price=item.product_configuration.price
            )

        cart_items.delete()
        return redirect('order_success')

    addresses = Address.objects.filter(user=user)
    default_address = addresses.filter(is_default=True).first() or addresses.first()
    show_modal = not default_address

    cart, created = Cart.objects.get_or_create(user=user)
    cart_items = CartItem.objects.filter(cart=cart)

    order_total = sum(Decimal(item.qty) * Decimal(item.product_configuration.price) for item in cart_items)
    shipping_cost = Decimal('10.00')
    total_discount = Decimal('0.00')
    
    for item in cart_items:
        if item.product_configuration.get_discounted_price:
            discount_price = Decimal(item.product_configuration.get_discounted_price())
            original_price = Decimal(item.product_configuration.price)
            discount = original_price - discount_price
            total_discount += discount * Decimal(item.qty)

    discounted_total = order_total - total_discount
    final_total = discounted_total + shipping_cost

    context = {
        "addresses": addresses,
        "default_address": default_address,
        "cart_items": cart_items,
        "categories": categories,
        "edit": True,
        'show_modal': show_modal,
        'razorpay_key': settings.RAZORPAY_KEY,
        'total_discount': total_discount,
        'discounted_total': discounted_total,
        'final_total': final_total
    }
    return render(request, "checkOut.html", context)

from django.urls import reverse

@csrf_exempt
@login_required(login_url='userLogin')
@never_cache
def place_order(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user = request.user
            payment_method_value = data.get('payment')
            confirmation = data.get('confirmation', False)
            coupon_code = data.get('coupon_code', None)
            razorpay_payment_id = data.get('razorpay_payment_id')
            razorpay_order_id = data.get('razorpay_order_id')
            razorpay_signature = data.get('razorpay_signature')
            print("coupon:", coupon_code)
            print("Received data:", data)
            print("the pay method: ", payment_method_value)
            
                        # Print statements for debugging
            print("Permanent Address Line 1:", data.get('permanent_address_line1'))
            print("Permanent Address Line 2:", data.get('permanent_address_line2'))
            print("Permanent City:", data.get('permanent_city'))
            print("Permanent State:", data.get('permanent_state'))
            print("Permanent Country:", data.get('permanent_country'))
            print("Permanent Postal Code:", data.get('permanent_postal_code'))

            if not payment_method_value:
                return JsonResponse({'status': 'error', 'message': 'Payment method is required.', 'redirect_url': reverse('my_orders')})

            payment_status = None  # Initialize payment_status
            if payment_method_value == 'razorpay':
                print("Verifying Razorpay payment")
                expiry_date = datetime.now().date() + timedelta(days=365)

                try:
                    if verify_razorpay_payment(razorpay_payment_id, razorpay_order_id, razorpay_signature):
                        payment_status = PaymentStatus.objects.get(status='Payment Completed')
                    else:
                        payment_status = PaymentStatus.objects.get(status='Payment Failed')
                        print("Razorpay Signature Verification Failed. Setting payment status to Failed.")
                except Exception as e:
                    print(f"Razorpay verification error: {str(e)}")
                    payment_status = PaymentStatus.objects.get(status='Payment Failed')
                    print("Exception in Razorpay verification. Setting payment status to Failed.")

                payment_method = PaymentMethod.objects.create(
                    user=user,
                    payment_type=PaymentType.objects.get(value="razorpay"),
                    provider="Razorpay",
                    expiry_date=expiry_date,
                    account_number=razorpay_payment_id or "Failed",
                    is_default=False
                )
                
            elif payment_method_value == 'cod':
                payment_status = PaymentStatus.objects.get(status='Payment Pending')
                payment_method = create_cod_payment_method(user)
            elif payment_method_value == 'Wallet':
                try:
                    wallet = Wallet.objects.get(user=user)
                except Wallet.DoesNotExist:
                    return JsonResponse({'status': 'error', 'message': 'Wallet not found for this user.', 'redirect_url': reverse('my_orders')})

                order_total = calculate_order_total(user, coupon_code)
                expiry_date = datetime.now().date() + timedelta(days=365)
                if wallet.balance >= order_total:
                    wallet.balance -= order_total
                    wallet.save()
                    
                    payment_method = PaymentMethod.objects.create(
                        user=user,
                        payment_type=PaymentType.objects.get(value="Wallet"),
                        provider="Wallet",
                        expiry_date=expiry_date,
                        is_default=False
                    )
                    payment_status = PaymentStatus.objects.get(status='Payment Completed')
                else:
                    payment_status = PaymentStatus.objects.get(status='Payment Failed')
                    payment_method = PaymentMethod.objects.create(
                        user=user,
                        payment_type=PaymentType.objects.get(value="Wallet"),
                        provider="Wallet",
                        expiry_date=expiry_date,
                        is_default=False
                    )
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Insufficient wallet balance. Choose another payment method.',
                        'redirect_url': reverse('my_orders')
                    })
            else:
                try:
                    payment_method = PaymentMethod.objects.get(id=payment_method_value)
                    payment_status = PaymentStatus.objects.get(status='Payment Pending')
                except PaymentMethod.DoesNotExist:
                    return JsonResponse({'status': 'error', 'message': 'Invalid payment method.', 'redirect_url': reverse('my_orders')})

            shipping_address_id = data.get('shipping_address_id')
            if not shipping_address_id:
                return JsonResponse({'status': 'error', 'message': 'Shipping address ID is required.', 'redirect_url': reverse('my_orders')})

            try:
                shipping_address = Address.objects.get(id=shipping_address_id, user=user)
            except Address.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Invalid shipping address.', 'redirect_url': reverse('my_orders')})

            cart = Cart.objects.get(user=user)
            cart_items = CartItem.objects.filter(cart=cart)
            error_messages = []
            confirmation_required = False

            for item in cart_items:
                product_config = item.product_configuration
                requested_qty = item.qty

                if product_config.qty_in_stock == 0:
                    variation_options = ', '.join(option.value for option in product_config.variation_options.all())
                    error_messages.append(f'Out of stock for {product_config.product.name} ({variation_options}).')
                elif product_config.qty_in_stock < requested_qty:
                    variation_options = ', '.join(option.value for option in product_config.variation_options.all())
                    error_messages.append(f'Insufficient stock for {product_config.product.name} ({variation_options}). Requested: {requested_qty}, Available: {product_config.qty_in_stock}')
                    confirmation_required = True
                    item.qty = product_config.qty_in_stock
                    item.save()

            order_total = Decimal('0.00')
            for item in cart_items:
                product_config = item.product_configuration
                discounted_price = Decimal(product_config.get_discounted_price())
                item_total = discounted_price * Decimal(item.qty)
                order_total += item_total
            
            shipping_cost = Decimal('10.00')
            order_total += shipping_cost

            discount_value = Decimal('0.00')
            if coupon_code:
                try:
                    coupon = Coupon.objects.get(code=coupon_code)
                    if coupon.is_valid(order_total, request.user):
                        discount_value = Decimal(coupon.discount_value)
                        if coupon.discount_type == 'percentage':
                            discount_value = (discount_value / Decimal('100')) * order_total
                        order_total -= discount_value
                        logger.info(f"Coupon applied. Discount: {discount_value}, New total: {order_total}")
                except Coupon.DoesNotExist:
                    logger.warning(f"Non-existent coupon code attempted: {coupon_code}")
                    return JsonResponse({'status': 'error', 'message': 'Invalid coupon code.', 'redirect_url': reverse('my_orders')})
                except Exception as e:
                    logger.error(f"Error processing coupon {coupon_code}: {str(e)}")
                    return JsonResponse({'status': 'error', 'message': f'Error processing coupon: {str(e)}', 'redirect_url': reverse('my_orders')})

            if error_messages:
                if any("Out of stock" in msg for msg in error_messages):
                    return JsonResponse({'status': 'error', 'messages': error_messages, 'redirect_url': reverse('my_orders')})
                else:
                    if confirmation_required and not confirmation:
                        adjusted_messages = [f"Available stock for {item.product_configuration.product.name}: {item.qty}" for item in cart_items if item.product_configuration.qty_in_stock < item.qty]
                        return JsonResponse({
                            'status': 'error', 
                            'messages': error_messages + adjusted_messages, 
                            'confirmation_required': True,
                            'redirect_url': reverse('my_orders')
                        })

            with transaction.atomic():
                order_status, created = OrderStatus.objects.get_or_create(status='Pending')
                
                order = Order.objects.create(
                    user=user,
                    payment_method=payment_method,
                    shipping_address=shipping_address,
                    shipping_method=ShippingMethod.objects.first(),
                    order_total=order_total,
                    order_status=order_status,
                    payment_status=payment_status,
                    discount_amount=discount_value,
                    permanent_address_line1=data.get('permanent_address_line1'),
                    permanent_address_line2=data.get('permanent_address_line2'),
                    permanent_city=data.get('permanent_city'),
                    permanent_state=data.get('permanent_state'),
                    permanent_country=data.get('permanent_country'),
                    permanent_postal_code=data.get('permanent_postal_code')
                )
                
                if payment_method_value == 'Wallet' and order.payment_status.status == 'Payment Completed':
                    Transaction.objects.create(
                        wallet=wallet,
                        amount=order_total,
                        transaction_type='PURCHASE',
                        order=order
                    )

                for item in cart_items:
                    product_config = item.product_configuration
                    OrderLine.objects.create(
                        order=order,
                        product_configuration=product_config,
                        qty=item.qty,
                        price=product_config.price,
                        discounted_price=Decimal(product_config.get_discounted_price())
                    )

                    if payment_status.status in ['Payment Completed', 'Payment Pending']:
                        product_config.qty_in_stock -= item.qty
                        product_config.save()

                cart_items.delete()

                if order.payment_status.status in ['Payment Completed', 'Payment Pending']:
                    return JsonResponse({
                        'status': 'success',
                        'message': 'Order placed successfully.',
                        'order_id': order.id,
                        'payment_status': order.payment_status.status,
                        'redirect_url': reverse('order_success')
                    })
                else:
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Payment failed. Please try again.',
                        'order_id': order.id,
                        'payment_status': order.payment_status.status,
                        'redirect_url': reverse('my_orders')
                    })
        except Exception as e:
            transaction.set_rollback(True)
            print(f"Error placing order: {str(e)}")
            return JsonResponse({'status': 'error', 'message': str(e), 'redirect_url': reverse('my_orders')})

    return JsonResponse({'status': 'error', 'message': 'Invalid request method.', 'redirect_url': reverse('my_orders')})

def calculate_order_total(user, coupon_code):
    cart = Cart.objects.get(user=user)
    cart_items = CartItem.objects.filter(cart=cart)
    subtotal = sum(Decimal(str(item.qty)) * Decimal(str(item.product_configuration.price)) for item in cart_items)
    shipping_cost = Decimal('10')

    total = subtotal + shipping_cost

    if coupon_code:
        try:
            coupon = Coupon.objects.get(code=coupon_code)
            if coupon.is_valid(Decimal(str(total)), user):
                discount = Decimal(str(coupon.discount_value))
                if coupon.discount_type == 'percentage':
                    discount = (discount / Decimal('100')) * Decimal(str(total))
                total -= discount
        except Coupon.DoesNotExist:
            pass

    return total

def verify_razorpay_payment(payment_id, order_id, signature):
    client = RazorpayClient(auth=(settings.RAZORPAY_KEY, settings.RAZORPAY_SECRET))
    try:
        return client.utility.verify_payment_signature({
            'razorpay_order_id': order_id,
            'razorpay_payment_id': payment_id,
            'razorpay_signature': signature
        })
    except Exception as e:
        print(f"Razorpay verification error: {str(e)}")
        return False
    
def create_cod_payment_method(user):
    cod_payment_type = PaymentType.objects.get(value="Cash on Delivery")

    # Calculate expiry date as 365 days from today
    expiry_date = datetime.now().date() + timedelta(days=365)

    payment_method, created = PaymentMethod.objects.get_or_create(
        user=user,
        payment_type=cod_payment_type,
        defaults={
            'provider': "N/A",  # or any default value  
            'account_number': "N/A",  # or any default value
            'expiry_date': expiry_date,  # dynamically calculated expiry date
            'is_default': False
        }
    )
    return payment_method

@never_cache
def view_coupons(request):
    now = timezone.now()
    all_coupons = Coupon.objects.all()
    for coupon in all_coupons:
        coupon.is_expired = now > coupon.valid_to or not coupon.active
    return render(request, 'viewCoupon.html', {'coupons': all_coupons})

def test_view(request):
    return JsonResponse({'message': 'Test successful'})

@login_required(login_url='userLogin')
@never_cache
def wishlist(request):
    try:
        user_wishlist = Wishlist.objects.get(user=request.user)
        wishlist_items = WishlistItem.objects.filter(wishlist=user_wishlist)
    except Wishlist.DoesNotExist:
        wishlist_items = []

    context = {
        'wishlist_items': wishlist_items
    }
    return render(request, "wishlist.html", context)

@ajax_login_required
@require_POST
def add_to_wishlist(request):
    data = json.loads(request.body)
    product_id = data.get('product_id')
    configuration_id = data.get('configuration_id')

    try:
        wishlist, created = Wishlist.objects.get_or_create(user=request.user)
        product_config = ProductConfiguration.objects.get(id=configuration_id)
        
        wishlist_item, created = WishlistItem.objects.get_or_create(
            wishlist=wishlist,
            product_configuration=product_config
        )
        
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
    
@require_POST
@login_required(login_url='userLogin')
def remove_from_wishlist(request, item_id):
    try:
        logger.info(f"Attempting to remove item {item_id} for user {request.user}")
        item = WishlistItem.objects.get(id=item_id,  wishlist__user=request.user)
        item.delete()
        logger.info(f"Successfully removed item {item_id}")
        return JsonResponse({'success': True})
    except WishlistItem.DoesNotExist:
        logger.warning(f"Item {item_id} not found in wishlist for user {request.user}")
        return JsonResponse({'success': False, 'error': 'Item not found in wishlist'}, status=404)
    except Exception as e:
        logger.error(f"Error removing item {item_id}: {str(e)}", exc_info=True)
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
from decimal import Decimal
import logging
from django.core.exceptions import ObjectDoesNotExist
logger = logging.getLogger(_name_)

@csrf_exempt
@login_required(login_url='userLogin')
def apply_coupon(request):
    try:
        data = json.loads(request.body)
        code = data.get('code')
        order_total = Decimal(data.get('order_total', '0'))

        logger.info(f"Received data: {data}")
        logger.info(f"Coupon code: {code}")
        logger.info(f"Order total: {order_total}")

        if not code or order_total <= 0:
            return JsonResponse({'success': False, 'message': 'Invalid coupon code or order total'}, status=400)

        try:
            coupon = Coupon.objects.get(code=code)
        except ObjectDoesNotExist:
            return JsonResponse({'success': False, 'message': 'Coupon not found'}, status=404)

        logger.info(f"Coupon found: {coupon}")

        # Check if the order total meets the minimum purchase amount
        if order_total < coupon.min_purchase_amount:
            return JsonResponse({
                'success': False, 
                'message': f'This coupon requires a minimum purchase of ${coupon.min_purchase_amount:.2f}'
            })

        if not coupon.is_valid(order_total,request.user):

            user_coupon_usage = CouponUsage.objects.filter(coupon=coupon, user=request.user).count()
            if user_coupon_usage >= coupon.usage_limit:
                return JsonResponse({'success': False, 'message': 'You have already used this coupon the maximum number of times.'})
            return JsonResponse({'success': False, 'message': 'This coupon is not valid.'})

        discount_value = Decimal(coupon.discount_value)
        if coupon.discount_type == 'percentage':
            print(discount_value)
            discount_value = (discount_value / Decimal('100')) * Decimal(order_total)
            print(discount_value)
        new_total = Decimal(order_total) - discount_value


        # new_total = order_total - discount_value

        logger.info(f"Discount value: {discount_value}")
        logger.info(f"New total: {new_total}")

        # Update coupon usage count
        coupon.usage_limit += 1
        coupon.save()

        # Create a CouponUsage record
        CouponUsage.objects.create(coupon=coupon, user=request.user)

        return JsonResponse({
            'success': True, 
            'message': f'Coupon applied! You saved ₹{discount_value:.2f}. New total is ₹{new_total:.2f}', 
            'new_total': str(new_total),
            'discount_value': str(discount_value)
        })

    except json.JSONDecodeError:
        logger.error("Invalid JSON data received")
        return JsonResponse({'success': False, 'message': 'Invalid JSON data'}, status=400)
    except Exception as e:
        logger.exception(f"Error in apply_coupon: {str(e)}")
        return JsonResponse({'success': False, 'message': f'An error occurred: {str(e)}'}, status=500)


@login_required(login_url='userLogin')
@never_cache
def my_orders(request):
    categories = Category.objects.filter(is_active=True)
    orders = Order.objects.filter(user=request.user).prefetch_related(
        'orderline_set_product_configurationproduct_images',
        'orderline_set_product_configuration_variation_options',
        'orderreturn_set'  # Add this line to prefetch return information
    ).order_by('-id')
    
    payment_status = request.GET.get('payment_status')
    order_status = request.GET.get('order_status')
    
    if payment_status:
        orders = orders.filter(payment_status__status=payment_status)
    if order_status:
        orders = orders.filter(order_status__status=order_status)
    
    for order in orders:
        for line in order.orderline_set.all():
            line.price = Decimal(line.price) if line.price is not None else Decimal(0)
            line.discounted_price = Decimal(line.discounted_price) if line.discounted_price is not None else Decimal(line.price)
            line.discount_amount = line.price - line.discounted_price
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        # If it's an AJAX request, return JSON data
        order_data = [{
            'id': order.id,
            'order_date': order.order_date,
            'order_total': str(order.order_total),
            'payment_status': order.payment_status.status if order.payment_status is not None else 'Unknown',
            'order_status': order.order_status.status if order.order_status is not None else 'Unknown',
            'lines': [{
                'product_name': line.product_configuration.product.name,
                'price': str(line.price),
                'discounted_price': str(line.discounted_price),
                'discount_amount': str(line.discount_amount),
                'qty': line.qty,
                'image_url': line.product_configuration.product.images.first().image.url if line.product_configuration.product.images.exists() else 'https://via.placeholder.com/60',
                'variation_options': [{
                    'variation_name': option.variation.name,
                    'value': option.value
                } for option in line.product_configuration.variation_options.all()]
            } for line in order.orderline_set.all()],
            'shipping_address': {
                'address_line1': order.shipping_address.address_line1,
                'city': order.shipping_address.city,
                'region': order.shipping_address.region,
                'country': order.shipping_address.country
            },
            'permanent_address': {
                'address_line1': order.permanent_address_line1,
                'address_line2': order.permanent_address_line2,
                'city': order.permanent_city,
                'state': order.permanent_state,
                'country': order.permanent_country,
                'postal_code': order.permanent_postal_code
            },
            'return_status': order.orderreturn_set.first().return_status.status if order.orderreturn_set.exists() else None,
            'return_reason': order.orderreturn_set.first().return_reason if order.orderreturn_set.exists() else None,
        } for order in orders]
        return JsonResponse({'orders': order_data})
    
    return render(request, "myOrders.html", {'orders': orders, 'categories': categories})
    
@csrf_exempt
@login_required(login_url='userLogin')
def request_order_return(request, order_id):
    if request.method == 'POST':
        try:
            order = get_object_or_404(Order, id=order_id, user=request.user)
            
            # Parse JSON data from request body
            data = json.loads(request.body)
            reason = data.get('reason')

            if not reason:
                return JsonResponse({'message': 'Return reason is required.'}, status=400)

            if order.order_status.status == 'Delivered' and not order.orderreturn_set.exists():
                return_status = OrderReturnStatus.objects.get(status='Pending')
                OrderReturn.objects.create(
                    order=order,
                    return_reason=reason,
                    return_status=return_status
                )
                return JsonResponse({'message': 'Return request submitted successfully.'})
            else:
                return JsonResponse({'message': 'Return request cannot be submitted.'}, status=400)
        except Order.DoesNotExist:
            return JsonResponse({'message': 'Order not found.'}, status=404)
        except json.JSONDecodeError:
            return JsonResponse({'message': 'Invalid JSON data.'}, status=400)
        except Exception as e:
            logger.error(f"Error submitting return request for order {order_id} for user {request.user.id}: {e}")
            return JsonResponse({'message': f'Error: {str(e)}'}, status=500)
    else:
        return JsonResponse({'message': 'Invalid request method.'}, status=405)
    
from django.contrib.auth.decorators import user_passes_test

@login_required(login_url='userLogin')
@user_passes_test(lambda u: u.is_staff)
def update_return_status(request, return_id):
    if request.method == 'POST':
        try:
            return_request = get_object_or_404(OrderReturn, id=return_id)
            new_status = request.POST.get('status')
            
            if new_status in ['Accepted', 'Rejected']:
                return_request.return_status = OrderReturnStatus.objects.get(status=new_status)
                return_request.save()
                return JsonResponse({'message': f'Return status updated to {new_status}'})
            else:
                return JsonResponse({'message': 'Invalid status'}, status=400)
        except Exception as e:
            return JsonResponse({'message': str(e)}, status=500)
    return JsonResponse({'message': 'Invalid request method'}, status=405)

import logging

# Get an instance of a logger
logger = logging.getLogger(_name_)

@csrf_exempt
@login_required(login_url='userLogin')
def cancel_order(request, order_id):
    try:
        order = get_object_or_404(Order, id=order_id, user=request.user)

        if order.order_status.status == 'Pending':
            cancel_status, created = OrderStatus.objects.get_or_create(status='Cancelled')
            with transaction.atomic():
                for order_line in order.orderline_set.all():
                    product_config = order_line.product_configuration

                    if product_config:
                        product_config.qty_in_stock += order_line.qty
                        product_config.save()
                    else: