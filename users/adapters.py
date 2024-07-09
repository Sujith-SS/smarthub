from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.exceptions import ImmediateHttpResponse
from django.shortcuts import redirect
from django.http import HttpResponseRedirect
from django.contrib.auth import get_user_model

User = get_user_model()

class MyAccountAdapter(DefaultAccountAdapter):
    def is_open_for_signup(self, request):
        return False

class MySocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        if sociallogin.is_existing:
            return
        try:
            email_address = sociallogin.account.extra_data['email']
            user = User.objects.filter(email=email_address).first()
            if user:
                sociallogin.connect(request, user)
                raise ImmediateHttpResponse(HttpResponseRedirect('/accounts/login/?message=Email is already associated with an account. Please login using your credentials.'))
        except User.DoesNotExist:
            pass
