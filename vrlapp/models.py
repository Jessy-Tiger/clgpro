from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils.timezone import now
import re
import secrets
from django.utils import timezone

def validate_phone_number(value):
    """Validate Indian phone number format"""
    pattern = r'^[6-9]\d{9}$'
    if not re.match(pattern, value):
        raise ValidationError('Please enter a valid 10-digit phone number starting with 6-9.')

class CustomerProfile(models.Model):
    """Extended User Profile for Customers"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customer_profile')
    phone_number = models.CharField(
        max_length=10,
        validators=[validate_phone_number],
        help_text="10-digit mobile number"
    )
    address = models.TextField(help_text="Complete address including door number, street, area")
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100, default="Tamil Nadu")
    pincode = models.CharField(max_length=6)
    email_verified = models.BooleanField(default=True, help_text="Email verification status")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Customer Profiles"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name} - {self.phone_number}"

class PickupRequest(models.Model):
    """Pickup Request Model"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('completed', 'Completed'),
    ]
    
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pickup_requests')
    
    # Customer Information
    full_name = models.CharField(max_length=200)
    email = models.EmailField()
    phone_number = models.CharField(max_length=10, validators=[validate_phone_number])
    address = models.TextField(help_text="Complete pickup address")
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100, default="Tamil Nadu")
    pincode = models.CharField(max_length=6)
    
    # Parcel Information
    parcel_description = models.TextField(help_text="Description of items in parcel")
    parcel_weight = models.CharField(
        max_length=50,
        help_text="Weight (e.g., 2.5 kg, 500g, etc.)"
    )
    estimated_price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Estimated value of parcel (optional)"
    )
    
    # Pickup Scheduling
    preferred_pickup_date = models.DateField(help_text="Date of pickup")
    preferred_pickup_time = models.TimeField(help_text="Preferred time slot")
    
    # Request Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    
    # Admin Notes
    admin_notes = models.TextField(blank=True, null=True, help_text="Admin remarks")
    
    # Timestamps
    requested_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Pickup Requests"
        ordering = ['-requested_at']
        indexes = [
            models.Index(fields=['status', '-requested_at']),
            models.Index(fields=['customer', '-requested_at']),
        ]

    def __str__(self):
        return f"#{self.id} - {self.full_name} - {self.status.upper()}"

    def get_status_display_fancy(self):
        """Return a fancy display of status"""
        status_map = {
            'pending': '⏳ Pending',
            'accepted': '✅ Accepted',
            'rejected': '❌ Rejected',
            'completed': '🎉 Completed',
        }
        return status_map.get(self.status, self.status)

class RequestStatusHistory(models.Model):
    """Track status changes for audit trail"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('completed', 'Completed'),
    ]
    
    pickup_request = models.ForeignKey(
        PickupRequest,
        on_delete=models.CASCADE,
        related_name='status_history'
    )
    old_status = models.CharField(max_length=20, null=True, blank=True, choices=STATUS_CHOICES)
    new_status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    changed_at = models.DateTimeField(auto_now_add=True)
    changed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        help_text="Admin who changed the status"
    )
    notes = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name_plural = "Request Status History"
        ordering = ['-changed_at']

    def __str__(self):
        return f"{self.pickup_request} - {self.old_status} → {self.new_status}"


class Invoice(models.Model):
    """Invoice Model for tracking generated invoices"""
    
    pickup_request = models.OneToOneField(
        PickupRequest,
        on_delete=models.CASCADE,
        related_name='invoice'
    )
    invoice_number = models.CharField(max_length=50, unique=True, editable=False)
    base_charge = models.DecimalField(max_digits=8, decimal_places=2, default=100.00)
    weight_charge = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    tax_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=18.00)
    tax_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    total_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    generated_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Invoices"
        ordering = ['-generated_at']
    
    def __str__(self):
        return f"Invoice {self.invoice_number}"
    
    def calculate_totals(self):
        """Calculate tax and total amount"""
        subtotal = self.base_charge + self.weight_charge
        self.tax_amount = (subtotal * self.tax_percentage) / 100
        self.total_amount = subtotal + self.tax_amount
        return self.total_amount
    
    def save(self, *args, **kwargs):
        """Generate invoice number if not exists"""
        if not self.invoice_number:
            # Generate invoice number: INV-20260223-001
            from datetime import date
            today = date.today().strftime('%Y%m%d')
            count = Invoice.objects.filter(invoice_number__startswith=f'INV-{today}').count()
            self.invoice_number = f'INV-{today}-{count + 1:03d}'
        
        # Calculate totals
        self.calculate_totals()
        super().save(*args, **kwargs)


class EmailVerification(models.Model):
    """Email Verification Token Model"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='email_verifications')
    email = models.EmailField()
    token = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    
    class Meta:
        verbose_name_plural = "Email Verifications"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.email} - {'Verified' if self.is_verified else 'Pending'}"
    
    @staticmethod
    def generate_token():
        """Generate secure verification token"""
        return secrets.token_urlsafe(48)
    
    def is_token_expired(self, hours=24):
        """Check if token has expired (default 24 hours)"""
        expiry_time = self.created_at + timezone.timedelta(hours=hours)
        return timezone.now() > expiry_time
    
    def verify(self):
        """Mark email as verified"""
        if not self.is_token_expired():
            self.is_verified = True
            self.verified_at = timezone.now()
            self.save()
            
            # Update customer profile email_verified status
            try:
                profile = self.user.customer_profile
                profile.email_verified = True
                profile.save()
            except:
                pass
            
            return True
        return False
