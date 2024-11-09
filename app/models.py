from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal
from datetime import datetime


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    phone = models.CharField(max_length=15, blank=True)
    location = models.CharField(max_length=100, blank=True)
    wallet = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __str__(self):
        return self.user.username

    def full_name(self):
        return f"{self.user.first_name} {self.user.last_name}"

    def is_provider(self):
        return hasattr(self, 'provider')


class Provider(models.Model):
    profile = models.OneToOneField(Profile, on_delete=models.CASCADE)
    about = models.TextField(blank=True, null=True)
    linkedin = models.URLField(blank=True, null=True)
    twitter = models.URLField(blank=True, null=True)
    facebook = models.URLField(blank=True, null=True)
    contact_email = models.EmailField(blank=True, null=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def completed_services_count(self):
        return self.services.filter(booking__status='completed').count()

    def total_reviews(self):
        return self.reviews.count()

    def average_rating(self):
        if self.reviews.exists():
            return self.reviews.aggregate(models.Avg('rating'))['rating__avg']
        return None

    def __str__(self):
        return self.profile.user.username



class Chat(models.Model):
    service = models.ForeignKey('Service', on_delete=models.CASCADE, related_name='chats')
    client = models.ForeignKey('Profile', on_delete=models.CASCADE, related_name='client_chats')
    provider = models.ForeignKey('Provider', on_delete=models.CASCADE, related_name='provider_chats')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Chat between {self.client.user.username} and {self.provider.profile.user.username} for {self.service.title}"

class Message(models.Model):
    chat = models.ForeignKey('Chat', on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message from {self.sender.username} at {self.timestamp}"

class Review(models.Model):
    provider = models.ForeignKey(Provider, related_name='reviews', on_delete=models.CASCADE)
    reviewer = models.ForeignKey(Profile, related_name='written_reviews', on_delete=models.CASCADE)
    rating = models.DecimalField(max_digits=2, decimal_places=1)
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, editable=False)

    class Meta:
        ordering = ['-created_at']  # Default ordering by most recent

    def clean(self):
        if not (0 <= self.rating <= 5.0):
            raise ValidationError("Rating must be between 0 and 5.0")

    def __str__(self):
        return f"{self.provider.profile.user.username} - {self.rating}"

class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()

    def __str__(self):
        return self.name

class Service(models.Model):
    provider = models.ForeignKey(Provider, on_delete=models.CASCADE, related_name='services')
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    duration = models.DurationField()
    is_active  = models.BooleanField(default=True)
    approval = models.CharField(choices=[('pending approval', 'Pending Approval'), ('approved', 'Approved'), ('not approved', 'Not Approved')],max_length=16, default='pending approval')
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    image = models.ImageField(upload_to='service_images/', blank=True, null=True)

    def __str__(self):
        return self.title

class Booking(models.Model):
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    customer = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name='bookings')
    date = models.DateTimeField()
    status = models.CharField(max_length=10, choices=[('pending', 'Pending'), ('completed', 'Completed'), ('cancelled', 'Cancelled')])

    def __str__(self):
        return f"{self.service.title} - {self.customer.user.username} - {self.status}"