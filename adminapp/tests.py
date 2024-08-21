from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from adminapp.models import Category, Product, ProductImage

class AdminAppTestCase(TestCase):
    def setUp(self):
        # Create a test user with staff privileges
        self.user = User.objects.create_user(username='admin', password='adminpass', is_staff=True)
        
        # Create a test category
        self.category = Category.objects.create(name='Electronics', is_active=True)

        # Initialize the Django test client
        self.client = Client()

    def test_add_product_missing_fields(self):
        # Log in as the admin user
        self.client.login(username='admin', password='adminpass')

        # Attempt to add a product with missing fields
        response = self.client.post(reverse('adminapp:add_product'), {
            'name': 'Test Product',
            'price': '100.00',
            # Missing description, stock, and category
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['success'])
        self.assertIn('Missing required fields', response.json()['error'])

    def test_add_product_invalid_price_stock(self):
        self.client.login(username='admin', password='adminpass')

        response = self.client.post(reverse('adminapp:add_product'), {
            'name': 'Test Product',
            'description': 'Test Description',
            'price': 'invalid_price',
            'stock': 'invalid_stock',
            'category': self.category.id,
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['success'])
        self.assertIn('Invalid price or stock value.', response.json()['error'])

    def test_add_product_success(self):
        self.client.login(username='admin', password='adminpass')

        # Create a list of images
        image1 = SimpleUploadedFile(name='test_image1.jpg', content=b'', content_type='image/jpeg')
        image2 = SimpleUploadedFile(name='test_image2.jpg', content=b'', content_type='image/jpeg')
        image3 = SimpleUploadedFile(name='test_image3.jpg', content=b'', content_type='image/jpeg')

        response = self.client.post(reverse('adminapp:add_product'), {
            'name': 'Test Product',
            'description': 'Test Description',
            'price': '100.00',
            'stock': '10',
            'category': self.category.id,
            'images': [image1, image2, image3],  # Include three images
        })

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])
        self.assertEqual(Product.objects.count(), 1)
        self.assertEqual(ProductImage.objects.count(), 3)

    def test_add_product_not_enough_images(self):
        self.client.login(username='admin', password='adminpass')

        # Create a list of images
        image1 = SimpleUploadedFile(name='test_image1.jpg', content=b'', content_type='image/jpeg')

        response = self.client.post(reverse('adminapp:add_product'), {
            'name': 'Test Product',
            'description': 'Test Description',
            'price': '100.00',
            'stock': '10',
            'category': self.category.id,
            'images': [image1],  # Include only one image
        })

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['success'])
        self.assertIn('Not enough images', response.json()['error'])

