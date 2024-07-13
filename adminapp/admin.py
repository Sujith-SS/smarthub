from django.contrib import admin

# Register your models here.
from .models import Category,Product

class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'created_at')
    search_fields = ('name',)
    list_filter = ('created_at',)


admin.site.register(Product,ProductAdmin)
admin.site.register(Category)
