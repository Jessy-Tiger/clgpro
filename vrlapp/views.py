from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.core.mail import send_mail, EmailMessage
from django.conf import settings
from django.contrib import messages
from django.utils.timezone import now
from django.core.paginator import Paginator
from datetime import datetime, timedelta

from .models import PickupRequest, CustomerProfile, RequestStatusHistory, EmailVerification
from .forms import CustomerRegistrationForm, PickupRequestForm, LoginForm
from .invoice_utils import generate_invoice_pdf


def home(request):
    """Home page with hero section and overview"""
    context = {
        'page_title': 'VRL Logistics - Doorstep Parcel Pickup',
        'is_authenticated': request.user.is_authenticated,
    }
    return render(request, 'home.html', context)


@require_http_methods(["GET", "POST"])
def register(request):
    """Customer registration page"""
    if request.user.is_authenticated:
        return redirect('pickup_request')
    
    if request.method == 'POST':
        form = CustomerRegistrationForm(request.POST)
        if form.is_valid():
            try:
                user = form.save()
                # Load the user again to ensure password is properly set
                user = User.objects.get(pk=user.pk)
                
                # Log the user in
                login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                
                # Send welcome email
                try:
                    send_welcome_email(user)
                except Exception as e:
                    print(f"Error sending welcome email: {str(e)}")
                
                messages.success(request, f'Welcome {user.first_name}! You can now submit pickup requests.')
                return redirect('pickup_request')
            except Exception as e:
                messages.error(request, f'Registration failed: {str(e)}')
        else:
            # Display form errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = CustomerRegistrationForm()
    
    context = {
        'form': form,
        'page_title': 'Register - VRL Logistics',
    }
    return render(request, 'register.html', context)


@require_http_methods(["GET", "POST"])
def user_login(request):
    """Customer login page"""
    if request.user.is_authenticated:
        return redirect('pickup_request')
    
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            
            # Try to login with username first, then email
            user = authenticate(request, username=username, password=password)
            if user is None:
                # Try with email as username
                try:
                    user_obj = User.objects.get(email=username)
                    user = authenticate(request, username=user_obj.username, password=password)
                except User.DoesNotExist:
                    user = None
            
            if user is not None:
                login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                messages.success(request, f'Welcome back, {user.first_name}!')
                
                # Redirect to next page if available
                next_page = request.GET.get('next', 'pickup_request')
                return redirect(next_page)
            else:
                messages.error(request, 'Invalid username or password.')
    else:
        form = LoginForm()
    
    context = {
        'form': form,
        'page_title': 'Login - VRL Logistics',
    }
    return render(request, 'login.html', context)


@login_required(login_url='user_login')
def user_logout(request):
    """Logout user"""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('home')


@login_required(login_url='user_login')
@require_http_methods(["GET", "POST"])
def pickup_request(request):
    """Pickup request submission form"""
    
    # Check if authenticated
    if not request.user.is_authenticated:
        return redirect('user_login')
    
    try:
        profile = request.user.customer_profile
    except CustomerProfile.DoesNotExist:
        messages.error(request, 'Please register first to submit pickup requests.')
        return redirect('register')
    
    if request.method == 'POST':
        form = PickupRequestForm(request.POST)
        if form.is_valid():
            try:
                # Create pickup request
                pickup = form.save(commit=False)
                pickup.customer = request.user
                pickup.save()
                
                # Send email to customer
                try:
                    send_customer_request_email(pickup)
                except Exception as e:
                    print(f"Error sending customer email: {str(e)}")
                
                # Send email to admin
                try:
                    send_admin_notification_email(pickup)
                except Exception as e:
                    print(f"Error sending admin email: {str(e)}")
                
                messages.success(
                    request,
                    f'Your pickup request #{pickup.id} has been submitted successfully! '
                    f'You will receive a confirmation email shortly.'
                )
                return redirect('pickup_history')
            except Exception as e:
                messages.error(request, f'Error submitting request: {str(e)}')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        # Pre-fill form with user's profile data
        customer_data = {}
        try:
            profile = request.user.customer_profile
            customer_data = {
                'full_name': f"{request.user.first_name} {request.user.last_name}",
                'email': request.user.email,
                'phone_number': profile.phone_number,
                'address': profile.address,
                'city': profile.city,
                'state': profile.state,
                'pincode': profile.pincode,
            }
        except CustomerProfile.DoesNotExist:
            customer_data = {
                'full_name': f"{request.user.first_name} {request.user.last_name}",
                'email': request.user.email,
            }
        
        form = PickupRequestForm(initial=customer_data)
    
    context = {
        'form': form,
        'page_title': 'Submit Pickup Request - VRL Logistics',
        'user': request.user,
        'is_authenticated': request.user.is_authenticated,
    }
    return render(request, 'pickup.html', context)


@login_required(login_url='user_login')
def pickup_history(request):
    """View pickup request history"""
    requests = request.user.pickup_requests.all().order_by('-requested_at')
    
    # Pagination
    paginator = Paginator(requests, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'requests': page_obj,
        'page_title': 'My Pickup Requests - VRL Logistics',
        'user': request.user,
    }
    return render(request, 'pickup_history.html', context)


@login_required(login_url='user_login')
def pickup_detail(request, pickup_id):
    """View detailed information about a pickup request"""
    pickup = get_object_or_404(PickupRequest, id=pickup_id, customer=request.user)
    status_history = pickup.status_history.all()
    
    context = {
        'pickup': pickup,
        'status_history': status_history,
        'page_title': f'Request #{pickup.id} Details - VRL Logistics',
        'user': request.user,
        'is_authenticated': request.user.is_authenticated,
    }
    return render(request, 'pickup_detail.html', context)


@login_required(login_url='user_login')
def admin_dashboard(request):
    """Admin dashboard to view and manage pickup requests"""
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('home')
    
    # Get filter options
    status_filter = request.GET.get('status', '')
    search_query = request.GET.get('search', '')
    
    # Base queryset
    all_requests = PickupRequest.objects.all().order_by('-requested_at')
    
    # Apply filters
    if status_filter:
        all_requests = all_requests.filter(status=status_filter)
    
    if search_query:
        all_requests = all_requests.filter(
            full_name__icontains=search_query
        ) | all_requests.filter(
            email__icontains=search_query
        ) | all_requests.filter(
            phone_number__icontains=search_query
        )
    
    # Get statistics
    stats = {
        'total': PickupRequest.objects.count(),
        'pending': PickupRequest.objects.filter(status='pending').count(),
        'accepted': PickupRequest.objects.filter(status='accepted').count(),
        'rejected': PickupRequest.objects.filter(status='rejected').count(),
        'completed': PickupRequest.objects.filter(status='completed').count(),
    }
    
    # Pagination
    paginator = Paginator(all_requests, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'requests': page_obj,
        'status_filter': status_filter,
        'search_query': search_query,
        'stats': stats,
        'status_choices': PickupRequest.STATUS_CHOICES,
        'page_title': 'Admin Dashboard - VRL Logistics',
    }
    return render(request, 'admin_dashboard.html', context)


@login_required(login_url='user_login')
@require_http_methods(["POST"])
def accept_request(request, pickup_id):
    """Admin accepts a pickup request"""
    if not request.user.is_staff:
        return redirect('home')
    
    pickup = get_object_or_404(PickupRequest, id=pickup_id)
    admin_notes = request.POST.get('admin_notes', '')
    
    try:
        # Store old status
        old_status = pickup.status
        
        # Update pickup request
        pickup.status = 'accepted'
        pickup.reviewed_at = now()
        if admin_notes:
            pickup.admin_notes = admin_notes
        pickup.save()
        
        # Create status history
        RequestStatusHistory.objects.create(
            pickup_request=pickup,
            old_status=old_status,
            new_status='accepted',
            changed_by=request.user,
            notes=admin_notes
        )
        
        # Send acceptance email to customer
        print(f"\n{'='*60}")
        print(f"[INFO] Accepting pickup request #{pickup_id}")
        print(f"[INFO] Customer Email: {pickup.email}")
        print(f"[INFO] Customer Name: {pickup.full_name}")
        print(f"{'='*60}")
        
        email_sent = False
        try:
            email_sent = send_acceptance_email(pickup)
        except Exception as e:
            print(f"[ERROR] Exception in send_acceptance_email: {str(e)}")
            import traceback
            print(traceback.format_exc())
        
        if email_sent:
            messages.success(request, f'✅ Pickup request #{pickup_id} has been accepted and customer notified via email.')
        else:
            messages.warning(request, f'⚠️ Pickup request #{pickup_id} has been accepted but email notification failed. Check console logs.')
        
        print(f"[INFO] Redirecting to admin dashboard")
        return redirect('admin_dashboard')
    
    except Exception as e:
        print(f"[ERROR] Exception in accept_request: {str(e)}")
        import traceback
        print(traceback.format_exc())
        messages.error(request, f'Error accepting request: {str(e)}')
        return redirect('admin_dashboard')


@login_required(login_url='user_login')
@require_http_methods(["POST"])
def reject_request(request, pickup_id):
    """Admin rejects a pickup request"""
    if not request.user.is_staff:
        return redirect('home')
    
    pickup = get_object_or_404(PickupRequest, id=pickup_id)
    rejection_reason = request.POST.get('rejection_reason', 'Not specified')
    
    try:
        # Store old status
        old_status = pickup.status
        
        # Update pickup request
        pickup.status = 'rejected'
        pickup.reviewed_at = now()
        pickup.admin_notes = rejection_reason
        pickup.save()
        
        # Create status history
        RequestStatusHistory.objects.create(
            pickup_request=pickup,
            old_status=old_status,
            new_status='rejected',
            changed_by=request.user,
            notes=rejection_reason
        )
        
        # Send rejection email to customer
        try:
            send_rejection_email(pickup)
        except Exception as e:
            print(f"Error sending rejection email: {str(e)}")
        
        messages.success(request, f'Pickup request #{pickup_id} has been rejected.')
        return redirect('admin_dashboard')
    
    except Exception as e:
        messages.error(request, f'Error rejecting request: {str(e)}')
        return redirect('admin_dashboard')


@login_required(login_url='user_login')
@require_http_methods(["POST"])
def complete_request(request, pickup_id):
    """Mark a pickup request as completed"""
    if not request.user.is_staff:
        return redirect('home')
    
    pickup = get_object_or_404(PickupRequest, id=pickup_id)
    
    try:
        old_status = pickup.status
        pickup.status = 'completed'
        pickup.completed_at = now()
        pickup.save()
        
        # Create status history
        RequestStatusHistory.objects.create(
            pickup_request=pickup,
            old_status=old_status,
            new_status='completed',
            changed_by=request.user,
            notes='Marked as completed'
        )
        
        messages.success(request, f'Pickup request #{pickup_id} has been completed.')
        return redirect('admin_dashboard')
    
    except Exception as e:
        messages.error(request, f'Error completing request: {str(e)}')
        return redirect('admin_dashboard')


@login_required(login_url='user_login')
@require_http_methods(["GET"])
def admin_accept_request(request, pickup_id):
    """Admin panel button to accept a pickup request"""
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to perform this action.')
        return redirect('home')
    
    pickup = get_object_or_404(PickupRequest, id=pickup_id)
    
    try:
        old_status = pickup.status
        pickup.status = 'accepted'
        pickup.reviewed_at = now()
        pickup.save()
        
        # Create status history
        RequestStatusHistory.objects.create(
            pickup_request=pickup,
            old_status=old_status,
            new_status='accepted',
            changed_by=request.user,
            notes='Accepted via admin panel button'
        )
        
        # Send acceptance email
        try:
            if send_acceptance_email(pickup):
                messages.success(request, f'✅ Request #{pickup_id} accepted and email sent to customer.')
            else:
                messages.warning(request, f'✅ Request #{pickup_id} accepted but email sending failed.')
        except Exception as e:
            messages.warning(request, f'✅ Request #{pickup_id} accepted but email error: {str(e)}')
        
        # Redirect back to admin change form
        return redirect(f'/admin/vrlapp/pickuprequest/{pickup_id}/change/')
    
    except Exception as e:
        messages.error(request, f'Error accepting request: {str(e)}')
        return redirect(f'/admin/vrlapp/pickuprequest/{pickup_id}/change/')


@login_required(login_url='user_login')
@require_http_methods(["GET"])
def admin_reject_request(request, pickup_id):
    """Admin panel button to reject a pickup request"""
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to perform this action.')
        return redirect('home')
    
    pickup = get_object_or_404(PickupRequest, id=pickup_id)
    
    try:
        old_status = pickup.status
        pickup.status = 'rejected'
        pickup.reviewed_at = now()
        pickup.admin_notes = 'Rejected via admin panel button'
        pickup.save()
        
        # Create status history
        RequestStatusHistory.objects.create(
            pickup_request=pickup,
            old_status=old_status,
            new_status='rejected',
            changed_by=request.user,
            notes='Rejected via admin panel button'
        )
        
        # Send rejection email
        try:
            if send_rejection_email(pickup):
                messages.success(request, f'❌ Request #{pickup_id} rejected and email sent to customer.')
            else:
                messages.warning(request, f'❌ Request #{pickup_id} rejected but email sending failed.')
        except Exception as e:
            messages.warning(request, f'❌ Request #{pickup_id} rejected but email error: {str(e)}')
        
        return redirect(f'/admin/vrlapp/pickuprequest/{pickup_id}/change/')
    
    except Exception as e:
        messages.error(request, f'Error rejecting request: {str(e)}')
        return redirect(f'/admin/vrlapp/pickuprequest/{pickup_id}/change/')


@login_required(login_url='user_login')
@require_http_methods(["GET"])
def admin_complete_request(request, pickup_id):
    """Admin panel button to mark pickup request as completed"""
    if not request.user.is_staff:
        messages.error(request, 'You do not have permission to perform this action.')
        return redirect('home')
    
    pickup = get_object_or_404(PickupRequest, id=pickup_id)
    
    try:
        old_status = pickup.status
        pickup.status = 'completed'
        pickup.completed_at = now()
        pickup.save()
        
        # Create status history
        RequestStatusHistory.objects.create(
            pickup_request=pickup,
            old_status=old_status,
            new_status='completed',
            changed_by=request.user,
            notes='Marked as completed via admin panel button'
        )
        
        messages.success(request, f'🎉 Request #{pickup_id} marked as completed.')
        return redirect(f'/admin/vrlapp/pickuprequest/{pickup_id}/change/')
    
    except Exception as e:
        messages.error(request, f'Error completing request: {str(e)}')
        return redirect(f'/admin/vrlapp/pickuprequest/{pickup_id}/change/')


# Email Helper Functions

def send_welcome_email(user):
    """Send welcome email to new customer"""
    subject = 'Welcome to VRL Logistics Pickup Service'
    email_body = f"""
Dear {user.first_name},

Welcome to VRL Logistics Doorstep Parcel Pickup Service!

Your account has been created successfully. You can now submit parcel pickup requests through our online platform.

Our features:
- Easy parcel pickup request submission
- Real-time status tracking
- Email notifications at every step
- Professional pickup service

To submit your first pickup request, please log in to your account and navigate to the pickup request form.

Best regards,
VRL Logistics Team
"""
    
    try:
        send_mail(
            subject,
            email_body,
            settings.EMAIL_HOST_USER,
            [user.email],
            fail_silently=False,
        )
        print(f"[SUCCESS] Welcome email sent to {user.email}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to send welcome email: {str(e)}")
        return False


def send_customer_request_email(pickup):
    """Send confirmation email to customer when request is submitted"""
    subject = f'Pickup Request Received - Request #{pickup.id} - VRL Logistics'
    status_display = dict(PickupRequest.STATUS_CHOICES).get(pickup.status, pickup.status)
    
    email_body = f"""Dear {pickup.full_name},

Thank you for submitting your parcel pickup request with VRL Logistics!

📋 REQUEST CONFIRMATION:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Request ID: #{pickup.id}
Submitted: {pickup.requested_at.strftime('%d-%m-%Y at %H:%M')}
Status: ⏳ {status_display}

📦 PICKUP INFORMATION:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Pickup Address: {pickup.address}, {pickup.city}, {pickup.state} {pickup.pincode}
Preferred Date: {pickup.preferred_pickup_date.strftime('%d-%m-%Y')}
Preferred Time: {pickup.preferred_pickup_time.strftime('%H:%M')}
Parcel Weight: {pickup.parcel_weight}

📝 DESCRIPTION:
{pickup.parcel_description}

⏱️ NEXT STEPS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Our admin team will review your request
2. You'll receive an acceptance or rejection email
3. If accepted, we'll confirm the exact pickup time
4. Keep your contact information handy

❓ QUESTIONS?
Contact us at: support@vrllogistics.com

Best regards,
VRL Logistics Team"""
    
    try:
        send_mail(
            subject,
            email_body,
            settings.EMAIL_HOST_USER,
            [pickup.email],
            fail_silently=False,
        )
        print(f"[SUCCESS] Customer request email sent to {pickup.email}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to send customer request email: {str(e)}")
        print(f"[ERROR] Email config - Host: {settings.EMAIL_HOST}, Port: {settings.EMAIL_PORT}")
        return False


def send_admin_notification_email(pickup):
    """Send notification email to admin when new request is received"""
    subject = f'New Pickup Request - {pickup.full_name}'
    email_body = f"""
ADMIN NOTIFICATION: New Pickup Request Received

REQUEST DETAILS:
Request ID: {pickup.id}
Customer: {pickup.full_name}
Email: {pickup.email}
Phone: {pickup.phone_number}

PICKUP INFORMATION:
Address: {pickup.address}, {pickup.city}, {pickup.state} {pickup.pincode}
Preferred Date: {pickup.preferred_pickup_date}
Preferred Time: {pickup.preferred_pickup_time}
Weight: {pickup.parcel_weight}

PARCEL DESCRIPTION:
{pickup.parcel_description}

Please review this request and take appropriate action in the admin dashboard.

Best regards,
VRL Logistics System
"""
    
    try:
        # Get all active admin/staff users
        admin_users = User.objects.filter(is_staff=True, is_active=True).exclude(email='')
        admin_emails = [user.email for user in admin_users]
        
        if admin_emails:
            send_mail(
                subject,
                email_body,
                settings.EMAIL_HOST_USER,
                admin_emails,
                fail_silently=False,
            )
            print(f"[SUCCESS] Admin notification email sent to {len(admin_emails)} admin(s): {admin_emails}")
            return True
        else:
            print("[WARNING] No active admin users with email addresses found")
            return False
    except Exception as e:
        print(f"[ERROR] Failed to send admin notification email: {str(e)}")
        return False


def send_acceptance_email(pickup):
    """Send acceptance email to customer with generated invoice"""
    subject = f'Your Pickup Request Accepted - Request #{pickup.id} - Invoice Enclosed'
    
    # Professional HTML email body
    email_body = f"""
Dear {pickup.full_name},

We are delighted to inform you that your parcel pickup request has been ACCEPTED and APPROVED! ✅

REQUEST CONFIRMATION:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Request ID: {pickup.id}
Status: ACCEPTED
Approval Date: {now().strftime("%d-%m-%Y")}

PICKUP SCHEDULE:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Pickup Date: {pickup.preferred_pickup_date.strftime("%d-%m-%Y")}
Pickup Time: {pickup.preferred_pickup_time.strftime("%H:%M to %H:%M")} (Approximate)
Location: {pickup.address}, {pickup.city}, {pickup.state} {pickup.pincode}

PARCEL DETAILS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Description: {pickup.parcel_description}
Weight: {pickup.parcel_weight}
Estimated Value: ₹ {pickup.estimated_price if pickup.estimated_price else 'Not Declared'}

IMPORTANT INSTRUCTIONS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Please ensure the parcel is properly packed and ready for pickup.
2. Our delivery representative will call you 30 minutes before arrival.
3. Please ensure someone is available at the given address to hand over the parcel.
4. Have your mobile number ready for communication with our delivery executive.
5. Please verify the condition of parcel before handing it to our representative.

YOUR INVOICE:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
A detailed invoice has been attached to this email. It shows all charges and applicable taxes.

PAYMENT OPTIONS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Cash on Pickup (COD)
• Online Payment via our website
• Bank Transfer (Details available upon request)

NEED HELP?
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
For any questions or concerns, please contact us:
📧 Email: support@vrllogistics.com
📞 Phone: +91-XXXXXXXXXX
🌐 Website: www.vrllogistics.com

Thank you for choosing VRL Logistics. We appreciate your business!

Best regards,
VRL Logistics Team
Doorstep Parcel Pickup Service

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
This is an automated email. Please do not reply to this address.
Invoice attached: See attachment below
"""
    
    email_sent = False
    
    try:
        # Generate invoice PDF
        print(f"[DEBUG] Generating invoice for pickup #{pickup.id}...")
        invoice_pdf = generate_invoice_pdf(pickup)
        
        # Seek to the beginning of the buffer
        invoice_pdf.seek(0)
        pdf_content = invoice_pdf.read()
        
        print(f"[DEBUG] Invoice PDF generated successfully. Size: {len(pdf_content)} bytes")
        
        # Create email with attachment
        email_message = EmailMessage(
            subject=subject,
            body=email_body,
            from_email=settings.EMAIL_HOST_USER,
            to=[pickup.email],
        )
        
        # Attach invoice PDF
        email_message.attach(
            f'Invoice_Request_{pickup.id}.pdf',
            pdf_content,
            'application/pdf'
        )
        
        # Send email
        print(f"[DEBUG] Sending acceptance email to {pickup.email}...")
        email_message.send(fail_silently=False)
        email_sent = True
        
        print(f"[SUCCESS] Acceptance email with invoice sent successfully to {pickup.email}")
        return email_sent
        
    except Exception as e:
        print(f"[ERROR] Error sending acceptance email with invoice: {str(e)}")
        print(f"[ERROR] Exception type: {type(e).__name__}")
        import traceback
        print(f"[ERROR] Traceback: {traceback.format_exc()}")
        
        # Fallback: send simple email without invoice
        try:
            print(f"[DEBUG] Attempting fallback - sending email without PDF...")
            send_mail(
                subject,
                email_body,
                settings.EMAIL_HOST_USER,
                [pickup.email],
                fail_silently=False,
            )
            email_sent = True
            print(f"[SUCCESS] Fallback acceptance email sent to {pickup.email} (without PDF)")
        except Exception as e2:
            print(f"[ERROR] Failed to send fallback acceptance email: {str(e2)}")
            print(f"[ERROR] Exception type: {type(e2).__name__}")
            import traceback
            print(f"[ERROR] Traceback: {traceback.format_exc()}")
    
    return email_sent


def send_rejection_email(pickup):
    """Send rejection email to customer"""
    subject = f'Your Pickup Request Status Update - Request #{pickup.id}'
    email_body = f"""
Dear {pickup.full_name},

We regret to inform you that your parcel pickup request has been declined.

REQUEST DETAILS:
Request ID: {pickup.id}
Status: REJECTED

REASON:
{pickup.admin_notes}

If you believe this is an error or would like to provide additional information, please contact us at support@vrllogistics.com

You can also submit a new pickup request with any necessary adjustments.

Best regards,
VRL Logistics Team
"""
    
    try:
        send_mail(
            subject,
            email_body,
            settings.EMAIL_HOST_USER,
            [pickup.email],
            fail_silently=False,
        )
        print(f"[SUCCESS] Rejection email sent to {pickup.email}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to send rejection email: {str(e)}")
        return False





