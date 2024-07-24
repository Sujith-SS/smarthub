from django.contrib import admin
from productsapp.models import Category, Product

class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'created_at')
    search_fields = ('name',)
    list_filter = ('created_at',)

admin.site.register(Product, ProductAdmin)
admin.site.register(Category)
