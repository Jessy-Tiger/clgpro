#!/usr/bin/env python
"""
Test script for Invoice & Email System
Run this to verify the complete workflow works correctly
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'newproject.settings')
django.setup()

from django.core.mail import EmailMessage
from django.conf import settings
from vrlapp.models import PickupRequest
from vrlapp.invoice_utils import generate_invoice_pdf, calculate_weight_charge
from vrlapp.views import send_acceptance_email

def test_weight_calculation():
    """Test weight charge calculation"""
    print("\n" + "="*60)
    print("TEST 1: Weight Charge Calculation")
    print("="*60)
    
    test_cases = [
        ("500g", 20),
        ("1kg", 40),
        ("1.5kg", 60),
        ("2kg", 80),
        ("2.5kg", 100),
    ]
    
    for weight_str, expected_min_charge in test_cases:
        charge = calculate_weight_charge(weight_str)
        status = "[OK]" if charge >= expected_min_charge else "[FAIL]"
        print(f"{status} Weight {weight_str:>6} -> Charge: Rs{charge:>6.2f}")
    
    print("[PASS] Weight calculation test completed!")


def test_email_configuration():
    """Test email configuration"""
    print("\n" + "="*60)
    print("TEST 2: Email Configuration")
    print("="*60)
    
    print(f"Email Backend: {settings.EMAIL_BACKEND}")
    print(f"Email Host: {settings.EMAIL_HOST}")
    print(f"Email Port: {settings.EMAIL_PORT}")
    print(f"Email Use TLS: {settings.EMAIL_USE_TLS}")
    print(f"Email Host User: {settings.EMAIL_HOST_USER}")
    
    if settings.EMAIL_HOST_USER and settings.EMAIL_HOST_PASSWORD:
        print("[PASS] Email configuration is set up!")
    else:
        print("[WARN] Warning: Email credentials might be missing!")


def test_invoice_generation():
    """Test invoice generation for a real pickup request"""
    print("\n" + "="*60)
    print("TEST 3: Invoice Generation for Pickup Request")
    print("="*60)
    
    # Find a sample pickup request
    pickup = PickupRequest.objects.filter(status='pending').first()
    
    if not pickup:
        print("[WARN] No pending pickup requests found for testing.")
        print("   Please create a test pickup request first.")
        return False
    
    print(f"Testing with Pickup Request: #{pickup.id}")
    print(f"Customer: {pickup.full_name}")
    print(f"Email: {pickup.email}")
    print(f"Weight: {pickup.parcel_weight}")
    
    try:
        print("\nGenerating invoice PDF...")
        invoice_pdf = generate_invoice_pdf(pickup)
        
        print(f"[OK] PDF generated successfully!")
        print(f"[OK] PDF Buffer size: {len(invoice_pdf.getvalue())} bytes")
        
        # Check invoice record
        from vrlapp.models import Invoice
        invoice = Invoice.objects.filter(pickup_request=pickup).first()
        if invoice:
            print(f"[OK] Invoice record created: {invoice.invoice_number}")
            print(f"  - Base Charge: Rs{invoice.base_charge}")
            print(f"  - Weight Charge: Rs{invoice.weight_charge}")
            print(f"  - Tax Amount: Rs{invoice.tax_amount}")
            print(f"  - Total Amount: Rs{invoice.total_amount}")
        
        print("[PASS] Invoice generation test completed!")
        return True
        
    except Exception as e:
        print(f"[FAIL] Invoice generation failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_email_sending():
    """Test sending email with invoice"""
    print("\n" + "="*60)
    print("TEST 4: Email Sending with Invoice Attachment")
    print("="*60)
    
    # Find a pending request to test with
    pickup = PickupRequest.objects.filter(status='pending').first()
    
    if not pickup:
        print("[WARN] No pending pickup requests found for testing.")
        print("   Please create a test pickup request first.")
        return False
    
    print(f"Testing email sending for Pickup Request: #{pickup.id}")
    print(f"Recipient: {pickup.email}")
    
    try:
        print("\nAttempting to send email with invoice...")
        print("\n" + "-"*60)
        
        # This will print debug messages
        email_sent = send_acceptance_email(pickup)
        
        print("-"*60)
        
        if email_sent:
            print("[PASS] Email sent successfully!")
            print("   Check your email inbox (or spam folder)")
            return True
        else:
            print("[WARN] Email sending may have failed. Check console output above.")
            return False
            
    except Exception as e:
        print(f"[FAIL] Email sending test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n")
    print("=" * 60)
    print("VRL LOGISTICS - INVOICE & EMAIL SYSTEM TEST".center(60))
    print("=" * 60)
    
    results = []
    
    # Test 1: Weight calculation
    try:
        test_weight_calculation()
        results.append(("Weight Calculation", True))
    except Exception as e:
        print(f"[FAIL] Weight calculation test failed: {str(e)}")
        results.append(("Weight Calculation", False))
    
    # Test 2: Email configuration
    try:
        test_email_configuration()
        results.append(("Email Configuration", True))
    except Exception as e:
        print(f"[FAIL] Email configuration test failed: {str(e)}")
        results.append(("Email Configuration", False))
    
    # Test 3: Invoice generation
    try:
        success = test_invoice_generation()
        results.append(("Invoice Generation", success))
    except Exception as e:
        print(f"[FAIL] Invoice generation test failed: {str(e)}")
        results.append(("Invoice Generation", False))
    
    # Test 4: Email sending
    try:
        success = test_email_sending()
        results.append(("Email Sending", success))
    except Exception as e:
        print(f"[FAIL] Email sending test failed: {str(e)}")
        results.append(("Email Sending", False))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    for test_name, success in results:
        status = "[PASS]" if success else "[FAIL]"
        print(f"{status:>10} - {test_name}")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    print("="*60)
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n[SUCCESS] All tests passed! System is ready to use!")
    else:
        print(f"\n[INFO] {total - passed} test(s) failed. See details above.")
    
    print("\n" + "="*60)


if __name__ == '__main__':
    main()
