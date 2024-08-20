from django import forms
from django.core.validators import MaxValueValidator

class AddToCartForm(forms.Form):
    quantity = forms.IntegerField(
        min_value=1,
        label='Quantity',
        validators=[MaxValueValidator(limit_value=1000, message="Quantity cannot exceed 1000")]
    )
