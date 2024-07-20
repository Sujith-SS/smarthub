from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.utils import timezone
from django.core.mail import send_mail, BadHeaderError
from django.contrib.auth import get_backends
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






def account_view(request):
    return render(request, 'account.html')


def generate_otp():
    return str(random.randint(100000, 999999))
     

def send_otp_email(email, otp):
    subject = 'Your OTP for Verification'
    message = f'Your OTP is: {otp}'
    from_email = settings.DEFAULT_FROM_EMAIL
    recipient_list = [email]
    
    try:
        send_mail(subject, message, from_email, recipient_list)
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
                return redirect('home')  # Replace 'home' with your actual home URL name
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