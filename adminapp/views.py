from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login,logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required,user_passes_test
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.models import User



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
@staff_member_required
def list_users(request):
    query = request.GET.get('search')
    if query: 
        users = User.objects.filter(username__icontains=query) | User.objects.filter(email__icontains=query)
        
    else:
        users = User.objects.all()
        users = users.order_by('username')
    return render(request, 'admin_usermanagement.html', {'users': users})

@staff_member_required
def block_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if user.is_superuser:
        messages.error(request, "You cannot block a superuser.")
        
    else:
        user.is_active = False
        user.save()
        messages.success(request, "User has been blocked successfully.")
    return redirect('admin_user_list')
@staff_member_required
def unblock_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    user.is_active = True
    user.save()
    messages.success(request, "User has been unblocked successfully.")
    return redirect('admin_user_list')







def admin_productManagement(request):
    return render(request,'admin_productmanagement.html')



def admin_categoryManagement(request):
    return render(request,'admin_categorymanagement.html')


def admin_orderManagement(request):
    return render (request, 'admin_ordermanagement.html')

def admin_salesRepot(request):
    return render (request, 'sales_report.html')


