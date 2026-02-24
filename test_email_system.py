#!/usr/bin/env python
"""
Test Email System for VRL Logistics
Tests all email functionality including admin notifications and acceptance emails with invoices
"""

import os
import sys
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'newproject.settings')
django.setup()

from django.core.mail import send_mail, EmailMessage
from django.contrib.auth.models import User
from vrlapp.models import PickupRequest, Invoice
from vrlapp.views import send_acceptance_email, send_admin_notification_email, send_rejection_email
from vrlapp.invoice_utils import generate_invoice_pdf
from datetime import datetime, timedelta, date
import traceback

print("=" * 80)
print("VRL LOGISTICS - EMAIL SYSTEM TEST")
print("=" * 80)

def test_email_configuration():
    """Test basic email configuration"""
    print("\n[TEST 1] Checking Email Configuration...")
    print(f"  EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
    print(f"  EMAIL_HOST: {settings.EMAIL_HOST}")
    print(f"  EMAIL_PORT: {settings.EMAIL_PORT}")
    print(f"  EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}")
    print(f"  EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}")
    print(f"  ✅ Email configuration loaded successfully")

def test_admin_users():
    """Test admin user retrieval"""
    print("\n[TEST 2] Checking Admin Users...")
    admin_users = User.objects.filter(is_staff=True, is_active=True).exclude(email='')
    print(f"  Found {len(admin_users)} active admin user(s)")
    for admin in admin_users:
        print(f"    - {admin.username}: {admin.email}")
    if len(admin_users) == 0:
        print("  ⚠️  WARNING: No active admin users with email found!")
        print("  Please create an admin user with email address")
    else:
        print(f"  ✅ Found {len(admin_users)} admin user(s)")

def test_simple_email():
    """Test sending a simple test email"""
    print("\n[TEST 3] Sending Test Email...")
    test_email = settings.EMAIL_HOST_USER
    try:
        send_mail(
            'VRL Logistics - Email System Test',
            'This is a test email from VRL Logistics email system.\nIf you receive this, email configuration is working correctly!',
            settings.EMAIL_HOST_USER,
            [test_email],
            fail_silently=False,
        )
        print(f"  ✅ Test email sent successfully to {test_email}")
    except Exception as e:
        print(f"  ❌ Failed to send test email: {str(e)}")
        traceback.print_exc()

def test_pickup_data():
    """Check if there's test pickup data"""
    print("\n[TEST 4] Checking Test Data...")
    pickups = PickupRequest.objects.all()
    print(f"  Total pickup requests: {len(pickups)}")
    
    if len(pickups) > 0:
        latest = pickups.first()
        print(f"  Latest pickup: Request #{latest.id} - {latest.full_name}")
        print(f"  Status: {latest.status}")
        print(f"  Email: {latest.email}")
        return latest
    else:
        print("  ℹ️  No pickup requests in database yet")
        return None

def test_invoice_generation():
    """Test invoice PDF generation"""
    print("\n[TEST 5] Testing Invoice PDF Generation...")
    
    # Get or create a test pickup
    pickup = PickupRequest.objects.filter(status='pending').first()
    
    if not pickup:
        print("  ⚠️  No pending pickup request found for testing")
        print("  Please create a pickup request first through the web interface")
        return None
    
    try:
        print(f"  Generating invoice for pickup #{pickup.id}...")
        invoice_pdf = generate_invoice_pdf(pickup)
        invoice_pdf.seek(0)
        pdf_content = invoice_pdf.read()
        pdf_size_kb = len(pdf_content) / 1024
        print(f"  ✅ Invoice PDF generated successfully ({pdf_size_kb:.2f} KB)")
        
        # Check invoice record
        invoice = Invoice.objects.get(pickup_request=pickup)
        print(f"  Invoice Number: {invoice.invoice_number}")
        print(f"  Base Charge: ₹{invoice.base_charge}")
        print(f"  Weight Charge: ₹{invoice.weight_charge}")
        print(f"  Tax ({invoice.tax_percentage}%): ₹{invoice.tax_amount}")
        print(f"  Total Amount: ₹{invoice.total_amount}")
        
        return pickup
    except Exception as e:
        print(f"  ❌ Failed to generate invoice: {str(e)}")
        traceback.print_exc()
        return None

def test_acceptance_email_with_invoice():
    """Test sending acceptance email with invoice"""
    print("\n[TEST 6] Testing Acceptance Email with Invoice...")
    
    # Get a pending or accepted request
    pickup = PickupRequest.objects.filter(status__in=['pending', 'accepted']).first()
    
    if not pickup:
        print("  ⚠️  No pending/accepted pickup request found for testing")
        return False
    
    try:
        print(f"  Sending acceptance email for request #{pickup.id}...")
        print(f"  Customer: {pickup.full_name} ({pickup.email})")
        
        success = send_acceptance_email(pickup)
        
        if success:
            print(f"  ✅ Acceptance email with invoice sent successfully")
            return True
        else:
            print(f"  ⚠️  Acceptance email sending returned False but no exception")
            return False
    except Exception as e:
        print(f"  ❌ Failed to send acceptance email: {str(e)}")
        traceback.print_exc()
        return False

def test_admin_notification_email():
    """Test sending admin notification email"""
    print("\n[TEST 7] Testing Admin Notification Email...")
    
    # Get a pending request
    pickup = PickupRequest.objects.filter(status='pending').first()
    
    if not pickup:
        print("  ⚠️  No pending pickup request found for testing")
        return False
    
    try:
        print(f"  Sending admin notification for request #{pickup.id}...")
        print(f"  Customer: {pickup.full_name}")
        
        send_admin_notification_email(pickup)
        print(f"  ✅ Admin notification email sent successfully")
        return True
    except Exception as e:
        print(f"  ❌ Failed to send admin notification: {str(e)}")
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    try:
        test_email_configuration()
        test_admin_users()
        test_simple_email()
        test_pickup_data()
        test_invoice_generation()
        test_acceptance_email_with_invoice()
        test_admin_notification_email()
        
        print("\n" + "=" * 80)
        print("✅ EMAIL SYSTEM TEST COMPLETED")
        print("=" * 80)
        print("\nNote: Check your email inbox/spam folder to verify emails were received")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        traceback.print_exc()

if __name__ == '__main__':
    main()
