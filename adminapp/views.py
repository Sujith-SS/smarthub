from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login,logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required,user_passes_test
from django.contrib.admin.views.decorators import staff_member_required



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


@staff_member_required(login_url='admin_login')
@login_required(login_url='admin_login')
def admin_userManagement(request):
    return render(request, 'admin_usermanagement.html')



def admin_productManagement(request):
    return render(request,'admin_productmanagement.html')



def admin_categoryManagement(request):
    return render(request,'admin_categorymanagement.html')


def admin_orderManagement(request):
    return render (request, 'admin_ordermanagement.html')

def admin_salesRepot(request):
    return render (request, 'sales_report.html')


