from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from .models import Cart, CartItem
from productsapp.models import Product,Category

class CartAppTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='password')
        self.category = Category.objects.create(name='Test Category')
        self.product = Product.objects.create(
            name='Test Product',
            stock=10,
            price=100,
            is_available=True,
            category=self.category  
        )
        
        self.cart = Cart.objects.create(user=self.user)
        self.cart_item = CartItem.objects.create(cart=self.cart, product=self.product, quantity=2)

        self.client.login(username='testuser', password='password')
        
        
        


    def test_add_to_cart(self):
        url = reverse('cartapp:add_to_cart', args=[self.product.id])
        response = self.client.post(url, {'quantity': 1})
        self.assertEqual(response.status_code, 302)  # Check for redirect
        self.assertTrue(CartItem.objects.filter(cart=self.cart, product=self.product).exists())
