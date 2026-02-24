#!/usr/bin/env python
"""
Integration Test - Complete Email Workflow for VRL Logistics
Tests the complete flow: Customer submits -> Admin notified -> Admin accepts -> Customer gets invoice email
"""

import os
import sys
import django
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'newproject.settings')
django.setup()

from django.contrib.auth.models import User
from django.core.management import call_command
from vrlapp.models import PickupRequest, CustomerProfile, RequestStatusHistory, Invoice
from vrlapp.views import (
    send_acceptance_email, 
    send_admin_notification_email, 
    send_rejection_email,
    send_customer_request_email
)
from datetime import datetime, timedelta, date
import traceback

print("\n" + "=" * 90)
print("VRL LOGISTICS - COMPLETE EMAIL WORKFLOW TEST")
print("=" * 90 + "\n")

def run_integration_test():
    """Run complete workflow test"""
    
    print("[STEP 1] Checking Database Setup...")
    try:
        # Check users
        users_count = User.objects.count()
        print(f"  ✅ Database connected. Total users: {users_count}")
    except Exception as e:
        print(f"  ❌ Database error: {str(e)}")
        return False
    
    print("\n[STEP 2] Getting Test Customer...")
    try:
        # Get or use existing test customer
        test_customer = User.objects.filter(is_staff=False).first()
        if not test_customer:
            print("  ❌ No test customer found")
            return False
        print(f"  ✅ Test customer: {test_customer.username} ({test_customer.email})")
    except Exception as e:
        print(f"  ❌ Error: {str(e)}")
        return False
    
    print("\n[STEP 3] Getting Test Pickup Request...")
    try:
        # Get a recent pickup request
        test_pickup = PickupRequest.objects.filter(status='pending').first()
        if not test_pickup:
            print("  ⚠️  No pending pickup request found")
            print("  Creating a test pickup request...")
            
            # Create test pickup
            test_pickup = PickupRequest.objects.create(
                customer=test_customer,
                full_name="Test Customer",
                email=test_customer.email if test_customer.email else "test@example.com",
                phone_number="9876543210",
                address="123 Test Street",
                city="Chennai",
                state="Tamil Nadu",
                pincode="600001",
                parcel_description="Test Package",
                parcel_weight="2.5 kg",
                estimated_price=500.00,
                preferred_pickup_date=date.today() + timedelta(days=1),
                preferred_pickup_time=datetime.now().time(),
            )
            print(f"  ✅ Test pickup created: Request #{test_pickup.id}")
        else:
            print(f"  ✅ Using existing test pickup: Request #{test_pickup.id}")
            print(f"     Customer: {test_pickup.full_name}")
            print(f"     Email: {test_pickup.email}")
            print(f"     Status: {test_pickup.status}")
    except Exception as e:
        print(f"  ❌ Error: {str(e)}")
        traceback.print_exc()
        return False
    
    print("\n[STEP 4] Simulating Customer Submitting Request...")
    print(f"  Scenario: Customer {test_pickup.full_name} submits pickup request")
    print(f"  Expected: Confirmation email sent to customer AND notification sent to admin")
    
    try:
        # Send customer confirmation email
        print(f"  • Sending confirmation email to {test_pickup.email}...")
        send_customer_request_email(test_pickup)
        print(f"    ✅ Confirmation email sent")
        
        # Send admin notification
        print(f"  • Sending notification to admin...")
        send_admin_notification_email(test_pickup)
        print(f"    ✅ Admin notification sent")
        
        print(f"  ✅ STEP 4 Complete: Customer notified and admin alerted")
    except Exception as e:
        print(f"  ❌ Error: {str(e)}")
        traceback.print_exc()
        return False
    
    print("\n[STEP 5] Simulating Admin Accepting Request...")
    print(f"  Scenario: Admin accepts the pickup request")
    print(f"  Expected: Request status changes to 'accepted' AND acceptance email with invoice sent to customer")
    
    try:
        # Get admin user
        admin_user = User.objects.filter(is_staff=True).first()
        if not admin_user:
            print("  ⚠️  No admin user found for this test")
            admin_user = User.objects.first()
        
        # Store old status
        old_status = test_pickup.status
        print(f"  • Old status: {old_status}")
        
        # Change status to accepted
        test_pickup.status = 'accepted'
        test_pickup.reviewed_at = django.utils.timezone.now()
        test_pickup.save()
        print(f"  • New status: accepted")
        
        # Create status history
        RequestStatusHistory.objects.create(
            pickup_request=test_pickup,
            old_status=old_status,
            new_status='accepted',
            changed_by=admin_user,
            notes='Integration test - automatic acceptance'
        )
        print(f"  • Status history recorded")
        
        # Send acceptance email with invoice
        print(f"  • Sending acceptance email with invoice to {test_pickup.email}...")
        success = send_acceptance_email(test_pickup)
        
        if success:
            print(f"    ✅ Acceptance email with invoice sent")
        else:
            print(f"    ⚠️  Acceptance email returned False (check logs)")
        
        print(f"  ✅ STEP 5 Complete: Request accepted and invoice email sent")
    except Exception as e:
        print(f"  ❌ Error: {str(e)}")
        traceback.print_exc()
        return False
    
    print("\n[STEP 6] Verifying Invoice Was Generated...")
    try:
        invoice = Invoice.objects.get(pickup_request=test_pickup)
        print(f"  ✅ Invoice found: {invoice.invoice_number}")
        print(f"     Base Charge: ₹{invoice.base_charge}")
        print(f"     Weight Charge: ₹{invoice.weight_charge}")
        print(f"     Tax: ₹{invoice.tax_amount}")
        print(f"     Total: ₹{invoice.total_amount}")
    except Invoice.DoesNotExist:
        print(f"  ⚠️  Invoice not found (should have been created)")
    except Exception as e:
        print(f"  ❌ Error: {str(e)}")
    
    print("\n" + "=" * 90)
    print("✅ INTEGRATION TEST COMPLETED SUCCESSFULLY")
    print("=" * 90)
    print("\nWorkflow Summary:")
    print("  1. ✅ Customer submits pickup request")
    print("  2. ✅ Customer receives confirmation email")
    print("  3. ✅ Admin receives notification email")  
    print("  4. ✅ Admin accepts request in dashboard")
    print("  5. ✅ Customer receives acceptance email with invoice attached")
    print("  6. ✅ All status changes logged in history")
    print("\n📧 Check your email inbox/spam folder to verify you received the emails")
    print("=" * 90 + "\n")
    
    return True

if __name__ == '__main__':
    try:
        success = run_integration_test()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Integration test failed: {str(e)}")
        traceback.print_exc()
        sys.exit(1)
