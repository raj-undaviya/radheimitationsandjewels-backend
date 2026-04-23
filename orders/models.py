from django.utils import timezone

from django.db import models
from django.conf import settings
from decimal import Decimal

User = settings.AUTH_USER_MODEL


class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="cart")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Cart - {self.user}"

    @property
    def total_price(self):
        return sum(item.total_price for item in self.items.all())


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("products.Product", on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)  # snapshot price

    def save(self, *args, **kwargs):
        if self._state.adding:   # only when creating
            self.price = self.product.price
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product} ({self.quantity})"

    @property
    def total_price(self):
        return self.price * self.quantity
    
class Wishlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="wishlist")
    product = models.ForeignKey("products.Product", on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'product']

    def __str__(self):
        return f"{self.user} - {self.product}"
    
# models.py
class Order(models.Model):

    STATUS_CHOICES = [
        ("pending",   "Pending"),
        ("confirmed", "Confirmed"),
        ("shipped",   "Shipped"),
        ("delivered", "Delivered"),
        ("cancelled", "Cancelled"),
    ]

    PAYMENT_METHOD_CHOICES = [
        ("cod",    "Cash on Delivery"),
        ("online", "Online Payment"),
    ]

    PAYMENT_STATUS_CHOICES = [
        ("pending",  "Pending"),
        ("paid",     "Paid"),
        ("failed",   "Failed"),
        ("refunded", "Refunded"),
    ]

    user           = models.ForeignKey(User, on_delete=models.CASCADE, related_name="orders")
    total_amount   = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status         = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    # ✅ Payment fields
    payment_method  = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default="cod")
    payment_status  = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default="pending")
    razorpay_order_id   = models.CharField(max_length=255, blank=True, null=True)  # from Razorpay
    razorpay_payment_id = models.CharField(max_length=255, blank=True, null=True)  # after payment
    razorpay_signature  = models.CharField(max_length=255, blank=True, null=True)  # for verification
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    address  = models.TextField()
    city     = models.CharField(max_length=100)
    pincode  = models.CharField(max_length=10)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order #{self.id} - {self.user}"

    def calculate_total(self):
        total            = sum(item.total_price for item in self.items.all())
        self.total_amount = total
        self.save()

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("products.Product", on_delete=models.SET_NULL, null=True)

    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)  # snapshot price

    def __str__(self):
        return f"{self.product} ({self.quantity})"

    @property
    def total_price(self):
        return self.price * self.quantity

class Coupon(models.Model):

    TYPE_CHOICES = [
        ('percentage', 'Percentage'),
        ('fixed',      'Fixed'),
    ]

    STATUS_CHOICES = [
        ('active',   'Active'),
        ('inactive', 'Inactive'),
    ]

    code            = models.CharField(max_length=50, unique=True)
    type            = models.CharField(max_length=20, choices=TYPE_CHOICES)
    value           = models.DecimalField(max_digits=10, decimal_places=2)  # % or fixed amount
    max_usage       = models.PositiveIntegerField(default=100)              # max times usable
    used_count      = models.PositiveIntegerField(default=0)                # times used so far
    min_order_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # min cart value
    expiry_date     = models.DateField(blank=True, null=True)               # null = no expiry
    status          = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.code

    @property
    def is_valid(self):
        if self.status != 'active':
            return False
        if self.used_count >= self.max_usage:
            return False
        if self.expiry_date and self.expiry_date < timezone.now().date():
            return False
        return True
    