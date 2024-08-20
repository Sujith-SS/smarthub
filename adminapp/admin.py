from django.contrib import admin
from productsapp.models import Category, Product

class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'created_at')
    search_fields = ('name','category__name')
    list_filter = ('created_at','is_active')
    fields = ('name', 'description', 'price', 'category', 'stock_quantity', 'is_active', 'images')

admin.site.register(Product, ProductAdmin)
admin.site.register(Category)
