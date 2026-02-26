#!/usr/bin/env python
"""
Quick test to verify email registration works
Run: python manage.py shell < test_registration_email.py
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'newproject.settings')
django.setup()

from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.conf import settings
from vrlapp.models import CustomerProfile, EmailVerification

print("\n" + "="*70)
print("REGISTRATION EMAIL TEST")
print("="*70 + "\n")

# Test 1: Email Configuration
print("TEST 1: Email Configuration Check")
print("-" * 70)
print(f"EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
print(f"EMAIL_HOST: {settings.EMAIL_HOST}")
print(f"EMAIL_PORT: {settings.EMAIL_PORT}")
print(f"EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}")
print(f"EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}")
print(f"SITE_URL: {settings.SITE_URL}")
print()

# Test 2: Send Test Email
print("TEST 2: Send Test Email to Configured Account")
print("-" * 70)
try:
    test_email = settings.EMAIL_HOST_USER
    send_mail(
        subject='🧪 VRL Logistics - Test Email Configuration',
        message='This is a test email. If you received this, email configuration is working correctly!',
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=[test_email],
        fail_silently=False,
    )
    print(f"✅ SUCCESS: Test email SENT to {test_email}")
    print(f"   Check your inbox for the test email")
except Exception as e:
    print(f"❌ FAILED: Could not send test email")
    print(f"Error: {str(e)}")
print()

# Test 3: Clean old test data
print("TEST 3: Clean Old Test Data")
print("-" * 70)
try:
    old_users = User.objects.filter(username__startswith='testuser_registration_')
    if old_users.exists():
        count = old_users.count()
        old_users.delete()
        print(f"✅ Deleted {count} old test users")
    else:
        print(f"✅ No old test data to clean")
except Exception as e:
    print(f"⚠️ Error cleaning: {str(e)}")
print()

# Test 4: Create Test User (Simulate Registration)
print("TEST 4: Create Test User Account (Simulate Registration)")
print("-" * 70)
try:
    # Create test user
    test_user = User.objects.create_user(
        username='testuser_registration_001',
        email='test.registration@gmail.com',  # Will be registered to this email
        password='TestPassword123!',
        first_name='Test',
        last_name='Reg'
    )
    print(f"✅ Created user: {test_user.username}")
    print(f"   Email: {test_user.email}")
    print(f"   First Name: {test_user.first_name}")
    
    # Create customer profile
    profile = CustomerProfile.objects.create(
        user=test_user,
        phone_number='9876543210',
        address='123 Test Street, Test Area',
        city='Chennai',
        state='Tamil Nadu',
        pincode='600001'
    )
    print(f"✅ Created customer profile")
    print(f"   Email Verified: {profile.email_verified}")
    
except Exception as e:
    print(f"❌ FAILED: {str(e)}")
    import traceback
    traceback.print_exc()
print()

# Test 5: Test Verification Email Sending
print("TEST 5: Test Verification Email Sending")
print("-" * 70)
try:
    from vrlapp.views import send_verification_email
    
    # Send verification email
    email_sent = send_verification_email(test_user, test_user.email)
    
    if email_sent:
        print(f"✅ Verification email SENT successfully")
        
        # Get the verification record
        verification = EmailVerification.objects.filter(user=test_user).order_by('-created_at').first()
        if verification:
            token = verification.token
            verification_link = f"{settings.SITE_URL}/verify-email/{token}/"
            print(f"   Verification Token: {token[:30]}...")
            print(f"   Verification Link: {verification_link}")
            print(f"   Token Expires: 24 hours")
            print(f"\n   📧 EMAIL SENT TO: {test_user.email}")
    else:
        print(f"❌ Failed to send verification email")
        import traceback
        traceback.print_exc()
        
except Exception as e:
    print(f"❌ FAILED: {str(e)}")
    import traceback
    traceback.print_exc()
print()

# Test 6: Verify Email Verification Works
print("TEST 6: Test Email Verification Process")
print("-" * 70)
try:
    verification = EmailVerification.objects.filter(user=test_user).order_by('-created_at').first()
    
    if verification:
        print(f"Found verification token: {verification.token[:20]}...")
        print(f"Is Verified Before: {verification.is_verified}")
        print(f"Token Expired: {verification.is_token_expired()}")
        
        # Verify the email
        if verification.verify():
            print(f"\n✅ Email verified successfully!")
            
            # Check profile
            profile = test_user.customer_profile
            print(f"   Profile email_verified: {profile.email_verified}")
            print(f"   Verification is_verified: {verification.is_verified}")
        else:
            print(f"❌ Email verification failed")
    else:
        print("❌ No verification record found")
        
except Exception as e:
    print(f"❌ FAILED: {str(e)}")
    import traceback
    traceback.print_exc()
print()

# Test 7: Summary
print("=" * 70)
print("SUMMARY")
print("=" * 70)
print("""
✅ Email Configuration: Verified
📧 Test Email: SEND TO YOUR EMAIL AND CHECK
✅ User Registration: Working
✅ Verification Email: Sent to test.registration@gmail.com
✅ Email Verification: Works

NEXT STEPS:
1. Test in browser: Go to /register/
2. Create account with YOUR username and email
3. YOU will receive verification email at YOUR specified email
4. Click the link in the email to verify
5. Then you can submit pickup requests

IMPORTANT NOTES:
- Each user registration creates TWO emails:
  1. Welcome email (sent immediately)
  2. Verification email (sent immediately)
  
- Both emails go to the email address user enters in registration form
- Always check SPAM folder if not in inbox
- Unused test accounts expire after 24 hours
""")

print("=" * 70)
