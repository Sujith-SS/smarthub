from django.shortcuts import render, redirect, get_object_or_404,HttpResponse
from django.contrib.auth import login, authenticate
from django.utils import timezone
from django.core.mail import send_mail, BadHeaderError
import random
from .forms import SignUpForm, OTPForm, LoginForm,PasswordResetRequestForm,SetNewPasswordForm
from django.contrib.auth.models import User
from datetime import timedelta
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import logout
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.hashers import make_password
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.backends import ModelBackend 
from django.core.mail import send_mail
from django.conf import settings
from rest_framework import status
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import Profile,UserProfile
from django.contrib.auth.hashers import check_password, make_password
from django.views.decorators.http import require_http_methods
from django.contrib.auth import get_user_model
from .utils import generate_otp,send_otp_email  



from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os


# Path to the email template
template_path = os.path.join(os.path.dirname(__file__), 'email.html')

# Read the HTML template once at the start
with open(template_path, 'r', encoding='utf-8') as file:
    html_template = file.read()
    

User = get_user_model()

def account_view(request):
    return render(request, 'account.html')


def verify_otp(request):
    if request.method == 'POST':
        form = OTPForm(request.POST)
        if form.is_valid():
            otp_code = form.cleaned_data.get('otp')
            signup_data = request.session.get('signup_data')

            if signup_data:
                try:
                    user = User.objects.get(id=signup_data['user_id'], email=signup_data['email'])
                    try:
                        profile = user.userprofile
                        if profile.is_otp_valid(otp_code):
                            user.is_active = True
                            profile.otp = None
                            profile.otp_expires_at = None
                            user.save()
                            profile.save()
                            messages.success(request, 'Signup successful! Please log in.')
                            return redirect('login')
                        else:
                            form.add_error('otp', 'Invalid or expired OTP')
                    except UserProfile.DoesNotExist:
                        form.add_error(None, 'User profile does not exist')
                except User.DoesNotExist:
                    form.add_error(None, 'User does not exist')
            else:
                form.add_error(None, 'Session data not found')
    else:
        form = OTPForm()

    return render(request, 'verify_otp.html', {'form': form})


def signup(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False  # Create user as inactive
            user.save()
            
            # Save additional data in session for OTP verification
            request.session['signup_data'] = {
                'user_id': user.id,
                'email': user.email,
            }
            return redirect('verify_otp')
    else:
        form = SignUpForm()
    return render(request, 'signup.html', {'form': form})



class EmailBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            user = User.objects.get(email=username)
        except User.DoesNotExist:
            return None
        else:
            if user.check_password(password):
                return user
        return None
    

def resend_otp(request):
    otp = generate_otp()
    expires_at = timezone.now() + timedelta(minutes=5)
    request.session['otp'] = otp
    request.session['otp_expires_at'] = expires_at.isoformat()
    signup_data = request.session.get('signup_data')
    if signup_data:
        send_otp_email(signup_data['email'], otp)
    return redirect('verify_otp')


def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request=request, data=request.POST)
        if form.is_valid():
            email = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=email, password=password)
            if user is not None:
                login(request, user)
                return redirect(reverse('home') + '?message=You have been logged in successfully&action=login')
            else:
                form.add_error(None, 'Invalid email or password.')
    else:
        form = LoginForm()

    return render(request, 'account.html', {'form': form})


@login_required
def logout_view(request):
    logout(request)
    return redirect(reverse('login'))



def password_reset_request(request):
    if request.method == "POST":
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                user = User.objects.get(email=email)
                otp = random.randint(100000, 999999)
                request.session['reset_email'] = email
                request.session['reset_otp'] = otp
                send_mail(
                    'Password Reset OTP',
                    f'Your OTP for password reset is {otp}',
                    'from@example.com',
                    [email],
                    fail_silently=False,
                )
                messages.success(request, 'OTP has been sent to your email.')
                return redirect('password_reset_verify')
            except User.DoesNotExist:
                messages.error(request, 'Email does not exist.')
    else:
        form = PasswordResetRequestForm()
    return render(request, 'password_reset_request.html', {'form': form})


def password_reset_verify(request):
    if request.method == "POST":
        form = OTPForm(request.POST)
        if form.is_valid():
            otp = form.cleaned_data['otp']
            session_otp = request.session.get('reset_otp')
            email = request.session.get('reset_email')

            if otp == str(session_otp):
                return redirect('password_reset_complete')
            else:
                messages.error(request, 'Invalid OTP.')
    else:
        form = OTPForm()
    return render(request, 'password_reset_verify.html', {'form': form})


def password_reset_complete(request):
    if request.method == "POST":
        form = SetNewPasswordForm(request.POST)
        if form.is_valid():
            new_password = form.cleaned_data['new_password']
            email = request.session.get('reset_email')
            try:
                user = User.objects.get(email=email)
                user.password = make_password(new_password)
                user.save()
                messages.success(request, 'Password has been reset successfully.')
                return redirect('login')
            except User.DoesNotExist:
                messages.error(request, 'User does not exist.')
    else:
        form = SetNewPasswordForm()
    return render(request, 'password_reset_complete.html', {'form': form})


def user_profile(request):
    return render(request,'user_profile.html')



# User Profile section



@login_required
def user_profile(request):
    try:
        profile = request.user.profile
    except Profile.DoesNotExist:
        profile = Profile.objects.create(user=request.user)
    
    context = {
        'user': request.user,
        'profile': profile
    }
    return render(request, 'user_profile.html', context)

@login_required
@require_POST
def update_profile(request):
    user = request.user
    profile = user.profile

    user.first_name = request.POST.get('username', user.first_name)
    user.email = request.POST.get('email', user.email)
    profile.phone_number = request.POST.get('phone', profile.phone_number)

    if 'profile_picture' in request.FILES:
        if profile.profile_picture:
            profile.profile_picture.delete(save=False)
        profile.profile_picture = request.FILES['profile_picture']

    user.save()
    profile.save()

    return JsonResponse({
        'status': 'success',
        'username': user.first_name,
        'email': user.email,
        'phone': str(profile.phone_number),
        'profile_picture_url': profile.profile_picture.url if profile.profile_picture else None
    })

    

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.shortcuts import redirect, render
from django.urls import reverse

@login_required(login_url='login')
def change_password(request):
    if request.method == "POST":
        action = request.POST.get('action')
        
        if action == 'send_otp':
            otp = generate_otp()  # Generate a new OTP
            if send_otp_email(request.user.email, otp):
                request.session['password_change_otp'] = otp
                messages.success(request, "OTP has been sent to your email.")
            else:
                messages.error(request, "Failed to send OTP. Please try again.")
            return redirect('change_password')
        
        elif action == 'verify_otp':
            entered_otp = request.POST.get('otp')
            stored_otp = request.session.get('password_change_otp')
            
            if entered_otp == stored_otp:
                request.session['otp_verified'] = True
                return redirect('change_password')
            else:
                messages.error(request, "Invalid OTP.")
                return redirect('change_password')
        
        elif action == 'change_password':
            if not request.session.get('otp_verified'):
                messages.error(request, "Please verify OTP first.")
                return redirect('change_password')

            new_password = request.POST.get("new_password")
            confirm_password = request.POST.get("confirm_password")
            
            if new_password != confirm_password:
                messages.error(request, "New passwords do not match.")
                return redirect('change_password')
            
            if len(new_password) < 8:
                messages.error(request, "Password must be at least 8 characters long.")
                return redirect('change_password')
            
            request.user.set_password(new_password)
            request.user.save()
            update_session_auth_hash(request, request.user)
            messages.success(request, "Password changed successfully.")
            
            # Clear session variables
            del request.session['password_change_otp']
            del request.session['otp_verified']
            
            # Set a context variable to trigger the SweetAlert
            return render(request, 'change_password.html', {'otp_verified': False, 'password_changed': True})
    
    otp_verified = request.session.get('otp_verified', False)
    return render(request, 'change_password.html', {'otp_verified': otp_verified})




from .models import Address
from .forms import AddressForm

def address_list(request):
    addresses = Address.objects.filter(user=request.user)
    can_add_address = addresses.count() < 4

    if request.method == 'POST':
        form = AddressForm(request.POST, user=request.user)
        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user
            if address.is_default:
                Address.objects.filter(user=request.user).update(is_default=False)
            address.save()
            return redirect('address_list')
    else:
        form = AddressForm(user=request.user)

    return render(request, 'address_list.html', {
        'addresses': addresses,
        'form': form,
        'can_add_address': can_add_address
    })

def address_edit(request, pk):
    address = get_object_or_404(Address, pk=pk, user=request.user)
    if request.method == 'POST':
        form = AddressForm(request.POST, instance=address, user=request.user)
        if form.is_valid():
            form.save()
            return redirect('address_list')
    else:
        form = AddressForm(instance=address, user=request.user)
    return render(request, 'address_edit.html', {'form': form})

def address_delete(request, pk):
    address = get_object_or_404(Address, pk=pk, user=request.user)
    if request.method == 'POST':
        address.delete()
        return redirect('address_list')
    return render(request, 'address_delete.html', {'address': address})

def set_default_address(request, pk):
    address = get_object_or_404(Address, pk=pk, user=request.user)
    Address.objects.filter(user=request.user).update(is_default=False)
    address.is_default = True
    address.save()
    return redirect('address_list')