from django.shortcuts import render, redirect, get_object_or_404
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
from .utils import generate_and_send_otp
from django.contrib.auth.hashers import make_password
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.backends import ModelBackend 
from django.core.mail import send_mail
from django.conf import settings
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import Profile,Address
from django.contrib.auth.hashers import check_password, make_password




from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os


# Path to the email template
template_path = os.path.join(os.path.dirname(__file__), 'email.html')

# Read the HTML template once at the start
with open(template_path, 'r', encoding='utf-8') as file:
    html_template = file.read()
    





def account_view(request):
    return render(request, 'account.html')


def generate_otp():
    return str(random.randint(100000, 999999))
     

def send_otp_email(email, otp):
    html_content = html_template.replace("123456", otp)
    subject = 'Your OTP for Verification'
    from_email = settings.DEFAULT_FROM_EMAIL
    recipient_list = [email]
    
    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = ", ".join(recipient_list)
    msg['Subject'] = subject
    msg.attach(MIMEText(html_content, 'html'))
    
    try:
        send_mail(subject, '', from_email, recipient_list, html_message=html_content)
        return True
    except Exception as e:
        return False
    
        

def signup(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            request.session['signup_data'] = {
                'name': form.cleaned_data.get('name'),
                'email': form.cleaned_data.get('email'),
                'password1': form.cleaned_data.get('password1'),
                'password2': form.cleaned_data.get('password2'),
            }
            otp = generate_otp()
            expires_at = timezone.now() + timedelta(minutes=5)
            request.session['otp'] = otp
            request.session['otp_expires_at'] = expires_at.isoformat()
            
            if send_otp_email(form.cleaned_data.get('email'), otp):
                return redirect('verify_otp')
            else:
                form.add_error(None, 'Failed to send OTP email. Please try again later.')
    else:
        form = SignUpForm()
        print(f"Generated OTP: {otp}")
    return render(request, 'account.html', {'form': form})

    

    

@csrf_exempt
def verify_otp(request):
    if request.method == 'POST':
        form = OTPForm(request.POST)
        if form.is_valid():
            otp_code = form.cleaned_data.get('otp')
            
            otp = request.session.get('otp')
            otp_expires_at = request.session.get('otp_expires_at')
            if otp and otp_expires_at:
                expires_at = timezone.datetime.fromisoformat(otp_expires_at)
                if timezone.now() > expires_at:
                    form.add_error('otp', 'OTP has expired')
                elif otp_code == otp:
                    signup_data = request.session.get('signup_data')
                    if signup_data:
                        user = User.objects.create_user(
                            username=signup_data['email'],
                            email=signup_data['email'],
                            password=signup_data['password1'],
                            first_name=signup_data['name'],
                            is_active=True
                        )
                        messages.success(request, 'Signup successful! Please log in.')
                        return redirect('account')
                else:
                    form.add_error('otp', 'Invalid OTP')
    else:
        form = OTPForm()
        
    return render(request, 'verify_otp.html', {'form': form})

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
    
    print(f"otp{otp}")
    expires_at = timezone.now() + timedelta(minutes=5)
    request.session['otp'] = otp
    request.session['otp_expires_at'] = expires_at.isoformat()
    signup_data = request.session.get('signup_data')
    if signup_data:
        send_mail(
            'Your New OTP Code',
            f'Your new OTP code is {otp}',
            'smarthubcart@gmail.com',
            [signup_data['email']],
            fail_silently=False,
        )
    return redirect('verify_otp')


def login_view(request):
    print("inside")
    if request.method == 'POST':
        print("inside post")
        form = LoginForm(request=request, data=request.POST)
        if form.is_valid():
            print("inside form")
            email = form.cleaned_data['username']
            password = form.cleaned_data['password']
            print("email:",email,"password:",password)
            user = authenticate(request, username=email, password=password)
            if user is not None:
                print("here")
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




@login_required
def address_list(request):
    addresses = Address.objects.filter(user=request.user)
    return render(request, 'address_list.html', {'addresses': addresses})

@login_required
def address_create(request):
    if request.method == 'POST':
        address_line1 = request.POST.get('address_line1')
        city = request.POST.get('city')
        zipcode = request.POST.get('zipcode')
        country = request.POST.get('country')

        address = Address(user=request.user, address_line1=address_line1, city=city, zipcode=zipcode, country=country)
        address.save()
        messages.success(request, 'Address added successfully!')
        return JsonResponse({'message': 'Address added successfully!'}, status=200)
    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
def address_update(request, pk):
    address = get_object_or_404(Address, pk=pk, user=request.user)
    if request.method == 'POST':
        address.address_line1 = request.POST.get('address_line1')
        address.city = request.POST.get('city')
        address.zipcode = request.POST.get('zipcode')
        address.country = request.POST.get('country')
        address.save()
        messages.success(request, 'Address updated successfully!')
        return JsonResponse({'message': 'Address updated successfully!'}, status=200)
    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
def address_delete(request, pk):
    address = get_object_or_404(Address, pk=pk, user=request.user)
    if request.method == 'POST':
        address.delete()
        messages.success(request, 'Address deleted successfully!')
        return JsonResponse({'message': 'Address deleted successfully!'}, status=200)
    return JsonResponse({'error': 'Invalid request'}, status=400)



@login_required
def address_set_active(request, pk):
    address = get_object_or_404(Address, pk=pk, user=request.user)
    Address.objects.filter(user=request.user).update(is_active=False)
    address.is_active = True
    address.save()
    messages.success(request, 'Address set as active successfully!')
    return JsonResponse({'message': 'Address set as active successfully!'}, status=200)
