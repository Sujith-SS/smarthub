from django import forms
from .models import Category
from .models import Product

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name']
        

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'description', 'price', 'category', 'image','stock']    
        



