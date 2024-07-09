from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate
from django.utils import timezone
from django.core.mail import send_mail, BadHeaderError
from django.contrib.auth import get_backends
import random
from .forms import SignUpForm, OTPForm, LoginForm
from django.contrib.auth.models import User
from datetime import timedelta
from django.views.decorators.csrf import csrf_exempt



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
            expires_at = timezone.now() + timedelta(minutes=5)  # OTP expires in 5 minutes
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
