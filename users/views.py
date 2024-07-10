from django.shortcuts import render, redirect, get_object_or_404
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



def account_view(request):
    return render(request, 'account.html')

def generate_otp():
    return str(random.randint(100000, 999999))

def signup(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            request.session['signup_data'] = {
                'username': form.cleaned_data.get('username'),
                'password1': form.cleaned_data.get('password1'),
                'password2': form.cleaned_data.get('password2'),
                'email': form.cleaned_data.get('email')
            }
            otp = generate_otp()
            expires_at = timezone.now() + timedelta(minutes=5) 
            request.session['otp'] = otp
            request.session['otp_expires_at'] = expires_at.isoformat()
            try:
                send_mail(
                    'Your OTP Code',
                    f'Your OTP code is {otp}',
                    'smarthubcart@gmail.com',
                    [form.cleaned_data.get('email')],
                    fail_silently=False,
                )
            except BadHeaderError:
                form.add_error(None, 'Failed to send OTP email. Please try again later.')
                return render(request, 'account.html', {'form': form})
            return redirect('verify_otp')

    else:
        form = SignUpForm()
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
                            username=signup_data['username'],
                            email=signup_data['email'],
                            password=signup_data['password1'],
                            is_active=True
                        )
                        backend = get_backends()[0]
                        user.backend = f'{backend.__module__}.{backend.__class__.__name__}'
                        login(request, user, backend=user.backend)
                        # Clear session data
                        del request.session['signup_data']
                        del request.session['otp']
                        del request.session['otp_expires_at']
                        return redirect('home')
                else:
                    form.add_error('otp', 'Invalid OTP')
    else:
        form = OTPForm()
    return render(request, 'verify_otp.html', {'form': form})

def resend_otp(request):
    otp = generate_otp()
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
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('home')
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