from django.contrib import admin

# Register your models here.
from .models import Address,Profile,UserProfile

admin.site.register([Address,Profile,UserProfile])