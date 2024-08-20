from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm,AuthenticationForm,PasswordResetForm
from .models import Address
from django.contrib.auth import get_user_model


User = get_user_model()

class SignUpForm(UserCreationForm):
    email = forms.EmailField(max_length=200, help_text='Required')
    name = forms.CharField(max_length=200, help_text='Required')

    class Meta:
        model = User
        fields = ('name', 'email', 'password1', 'password2')

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with that email already exists.")
        return email

    def save(self, commit=True):
        user = super(SignUpForm, self).save(commit=False)
        user.email = self.cleaned_data['email']
        user.username = self.cleaned_data['email']  # Set username to email
        if commit:
            user.save()
        return user
    
    
class OTPForm(forms.Form):
    otp = forms.CharField(max_length=6)


class LoginForm(AuthenticationForm):
    username = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'}))
    



class PasswordResetRequestForm(forms.Form):
    email = forms.EmailField(max_length=254, required=True)
    
    

class SetNewPasswordForm(forms.Form):
    new_password = forms.CharField(widget=forms.PasswordInput, required=True)
    confirm_password = forms.CharField(widget=forms.PasswordInput, required=True)

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get("new_password")
        confirm_password = cleaned_data.get("confirm_password")

        if new_password and confirm_password:
            if new_password != confirm_password:
                raise forms.ValidationError("Passwords do not match.")
        return cleaned_data
    
    

class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = ['address_line1', 'address_line2', 'city', 'state', 'zip_code', 'phone_number', 'label']

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        if Address.objects.filter(user=self.user).count() >= 4 and not self.instance.pk:
            raise forms.ValidationError("You can only add up to 4 addresses.")
        return cleaned_data