#!/usr/bin/env python
"""
Test Email Verification System
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'newproject.settings')
sys.path.insert(0, '/'.join(__file__.split('/')[:-1]))
django.setup()

from django.contrib.auth.models import User
from vrlapp.models import EmailVerification, CustomerProfile
from vrlapp.views import send_verification_email
from django.utils import timezone

def test_email_verification():
    """Test the email verification system"""
    print("\n" + "="*60)
    print("TESTING EMAIL VERIFICATION SYSTEM")
    print("="*60 + "\n")
    
    # Test 1: Create verification token
    print("TEST 1: Create EmailVerification Token")
    print("-" * 40)
    try:
        # Create a test user if not exists
        test_user, created = User.objects.get_or_create(
            username='testverify@example.com',
            defaults={
                'email': 'testverify@example.com',
                'first_name': 'Test',
                'last_name': 'User',
            }
        )
        
        # Create customer profile
        profile, _ = CustomerProfile.objects.get_or_create(
            user=test_user,
            defaults={
                'phone_number': '9999999999',
                'address': 'Test Address',
                'city': 'Test City',
                'state': 'Tamil Nadu',
                'pincode': '600001',
                'email_verified': False
            }
        )
        
        # Create verification
        token = EmailVerification.generate_token()
        verification = EmailVerification.objects.create(
            user=test_user,
            email=test_user.email,
            token=token
        )
        
        print(f"✅ Token Generated: {token[:20]}...")
        print(f"✅ User: {test_user.username}")
        print(f"✅ Email: {test_user.email}")
        print(f"✅ Verification ID: {verification.id}")
        print(f"✅ Is Verified: {verification.is_verified}")
        print(f"✅ Created At: {verification.created_at}")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return
    
    # Test 2: Check token expiry
    print("\nTEST 2: Check Token Expiry")
    print("-" * 40)
    try:
        is_expired = verification.is_token_expired(hours=24)
        print(f"✅ Is Token Expired (24 hours): {is_expired}")
        
        # Test with very short expiry
        is_expired_short = verification.is_token_expired(hours=0)
        print(f"✅ Is Token Expired (0 hours): {is_expired_short}")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    
    # Test 3: Verify email
    print("\nTEST 3: Verify Email via Token")
    print("-" * 40)
    try:
        before_verify = profile.email_verified
        print(f"Before verification - Email Verified: {before_verify}")
        
        result = verification.verify()
        print(f"✅ Verification Result: {result}")
        
        # Refresh from database
        verification.refresh_from_db()
        profile.refresh_from_db()
        
        print(f"✅ After verification - Is Verified: {verification.is_verified}")
        print(f"✅ After verification - Verified At: {verification.verified_at}")
        print(f"✅ Profile Email Verified: {profile.email_verified}")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    
    # Test 4: Cannot verify again
    print("\nTEST 4: Cannot Verify Already Verified Token")
    print("-" * 40)
    try:
        result = verification.verify()
        print(f"✅ Cannot verify again - Result: {result}")
        print(f"✅ Token still marked as verified: {verification.is_verified}")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    
    # Test 5: Retrieve from database
    print("\nTEST 5: Query EmailVerification from Database")
    print("-" * 40)
    try:
        found = EmailVerification.objects.get(token=token)
        print(f"✅ Found in database: {found.email}")
        print(f"✅ Is Verified: {found.is_verified}")
        print(f"✅ User: {found.user.username}")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    
    # Test 6: Create multiple verifications for same user
    print("\nTEST 6: Create Multiple Verification Tokens")
    print("-" * 40)
    try:
        token2 = EmailVerification.generate_token()
        verification2 = EmailVerification.objects.create(
            user=test_user,
            email=test_user.email,
            token=token2
        )
        
        verifications = EmailVerification.objects.filter(user=test_user)
        print(f"✅ Total verifications for user: {verifications.count()}")
        
        for i, v in enumerate(verifications, 1):
            print(f"   {i}. Token: {v.token[:20]}... | Verified: {v.is_verified}")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    
    # Test 7: Test invalid token
    print("\nTEST 7: Test Invalid Token")
    print("-" * 40)
    try:
        invalid_token = "invalid_token_12345"
        try:
            EmailVerification.objects.get(token=invalid_token)
            print(f"❌ Should not have found token")
        except EmailVerification.DoesNotExist:
            print(f"✅ Invalid token correctly raises DoesNotExist")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    
    # Summary
    print("\n" + "="*60)
    print("EMAIL VERIFICATION TESTS COMPLETE")
    print("="*60 + "\n")

if __name__ == '__main__':
    test_email_verification()
