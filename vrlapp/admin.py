from django.contrib import admin
from django.utils.html import format_html
from django.contrib import messages
from .models import CustomerProfile, PickupRequest, RequestStatusHistory, Invoice, EmailVerification
from .views import send_acceptance_email, send_rejection_email


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    """Admin interface for Customer Profiles"""
    
    list_display = ['get_customer_name', 'phone_number', 'city', 'created_at']
    list_filter = ['state', 'city', 'created_at']
    search_fields = ['user__first_name', 'user__last_name', 'user__email', 'phone_number']
    readonly_fields = ['user', 'created_at', 'updated_at']
    
    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Contact Details', {
            'fields': ('phone_number', )
        }),
        ('Address', {
            'fields': ('address', 'city', 'state', 'pincode')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_customer_name(self, obj):
        """Display customer name"""
        return f"{obj.user.first_name} {obj.user.last_name}"
    get_customer_name.short_description = 'Customer Name'


@admin.register(PickupRequest)
class PickupRequestAdmin(admin.ModelAdmin):
    """Admin interface for Pickup Requests"""
    
    list_display = ['request_id', 'get_customer_name', 'get_status_colored', 'preferred_pickup_date', 'requested_at']
    list_filter = ['status', 'requested_at', 'preferred_pickup_date', 'city', 'state']
    search_fields = ['full_name', 'email', 'phone_number', 'address']
    readonly_fields = ['customer', 'requested_at', 'reviewed_at', 'completed_at', 'updated_at', 'id']
    date_hierarchy = 'requested_at'
    actions = ['mark_as_accepted', 'mark_as_rejected', 'mark_as_completed']
    
    fieldsets = (
        ('Request Information', {
            'fields': ('id', 'customer', 'status', 'requested_at', 'reviewed_at')
        }),
        ('Customer Details', {
            'fields': ('full_name', 'email', 'phone_number')
        }),
        ('Pickup Address', {
            'fields': ('address', 'city', 'state', 'pincode')
        }),
        ('Parcel Details', {
            'fields': ('parcel_description', 'parcel_weight', 'estimated_price')
        }),
        ('Scheduled Pickup', {
            'fields': ('preferred_pickup_date', 'preferred_pickup_time')
        }),
        ('Admin Notes', {
            'fields': ('admin_notes',),
            'classes': ('wide',)
        }),
        ('Timestamps', {
            'fields': ('completed_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def request_id(self, obj):
        """Display request ID"""
        return f"#{obj.id}"
    request_id.short_description = "Request ID"
    
    def get_customer_name(self, obj):
        """Display customer name"""
        return obj.full_name
    get_customer_name.short_description = "Customer"
    
    def get_status_colored(self, obj):
        """Display status with color coding"""
        colors = {
            'pending': '#FFA500',     # Orange
            'accepted': '#008000',    # Green
            'rejected': '#FF0000',    # Red
            'completed': '#4169E1',   # Blue
        }
        color = colors.get(obj.status, '#000000')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    get_status_colored.short_description = "Status"
    
    def mark_as_accepted(self, request, queryset):
        """Admin action to mark requests as accepted and send acceptance emails"""
        count = 0
        email_count = 0
        for pickup in queryset:
            old_status = pickup.status
            pickup.status = 'accepted'
            pickup.reviewed_at = __import__('django.utils.timezone', fromlist=['now']).now()
            pickup.save()
            
            # Create status history
            RequestStatusHistory.objects.create(
                pickup_request=pickup,
                old_status=old_status,
                new_status='accepted',
                changed_by=request.user,
                notes='Accepted via admin bulk action'
            )
            
            # Try to send acceptance email with invoice
            try:
                if send_acceptance_email(pickup):
                    email_count += 1
            except Exception as e:
                print(f"Error sending acceptance email for {pickup.id}: {str(e)}")
            
            count += 1
        
        self.message_user(request, f'✅ {count} request(s) marked as accepted. Acceptance emails sent to {email_count} customer(s).')
    mark_as_accepted.short_description = "Mark selected as Accepted (with email notification)"
    
    def mark_as_rejected(self, request, queryset):
        """Admin action to mark requests as rejected and send rejection emails"""
        count = 0
        email_count = 0
        for pickup in queryset:
            old_status = pickup.status
            pickup.status = 'rejected'
            pickup.reviewed_at = __import__('django.utils.timezone', fromlist=['now']).now()
            pickup.admin_notes = 'Rejected via admin bulk action'
            pickup.save()
            
            # Create status history
            RequestStatusHistory.objects.create(
                pickup_request=pickup,
                old_status=old_status,
                new_status='rejected',
                changed_by=request.user,
                notes='Rejected via admin bulk action'
            )
            
            # Send rejection email
            try:
                send_rejection_email(pickup)
                email_count += 1
            except Exception as e:
                print(f"Error sending rejection email for {pickup.id}: {str(e)}")
            
            count += 1
        
        self.message_user(request, f'❌ {count} request(s) marked as rejected. Rejection emails sent to {email_count} customer(s).')
    mark_as_rejected.short_description = "Mark selected as Rejected (with email notification)"
    
    def mark_as_completed(self, request, queryset):
        """Admin action to mark requests as completed"""
        count = 0
        for pickup in queryset:
            old_status = pickup.status
            pickup.status = 'completed'
            pickup.completed_at = __import__('django.utils.timezone', fromlist=['now']).now()
            pickup.save()
            
            # Create status history
            RequestStatusHistory.objects.create(
                pickup_request=pickup,
                old_status=old_status,
                new_status='completed',
                changed_by=request.user,
                notes='Marked as completed via admin bulk action'
            )
            
            count += 1
        
        self.message_user(request, f'🎉 {count} request(s) marked as completed.')
    mark_as_completed.short_description = "Mark selected as Completed"


@admin.register(RequestStatusHistory)
class RequestStatusHistoryAdmin(admin.ModelAdmin):
    """Admin interface for Request Status History"""
    
    list_display = ['pickup_request', 'old_status_display', 'new_status_display', 'changed_at', 'changed_by']
    list_filter = ['new_status', 'changed_at', 'changed_by']
    search_fields = ['pickup_request__full_name', 'pickup_request__email', 'notes']
    readonly_fields = ['pickup_request', 'changed_at', 'old_status', 'new_status', 'changed_by', 'notes']
    date_hierarchy = 'changed_at'
    
    fieldsets = (
        ('Status Change', {
            'fields': ('pickup_request', 'old_status', 'new_status')
        }),
        ('Change Details', {
            'fields': ('changed_by', 'notes')
        }),
        ('Timestamp', {
            'fields': ('changed_at',)
        }),
    )
    
    def old_status_display(self, obj):
        """Display old status"""
        if not obj.old_status:
            return "—"
        return obj.get_old_status_display() if hasattr(obj, 'get_old_status_display') else obj.old_status
    old_status_display.short_description = "From"
    
    def new_status_display(self, obj):
        """Display new status"""
        return obj.get_new_status_display() if hasattr(obj, 'get_new_status_display') else obj.new_status
    new_status_display.short_description = "To"

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    """Admin interface for Invoices"""
    
    list_display = ['invoice_number', 'get_customer_name', 'total_amount', 'generated_at']
    list_filter = ['generated_at', 'tax_percentage']
    search_fields = ['invoice_number', 'pickup_request__full_name', 'pickup_request__email']
    readonly_fields = ['pickup_request', 'invoice_number', 'tax_amount', 'total_amount', 'generated_at', 'updated_at']
    date_hierarchy = 'generated_at'
    
    fieldsets = (
        ('Invoice Information', {
            'fields': ('invoice_number', 'pickup_request', 'generated_at')
        }),
        ('Charges', {
            'fields': ('base_charge', 'weight_charge')
        }),
        ('Taxes', {
            'fields': ('tax_percentage', 'tax_amount')
        }),
        ('Total', {
            'fields': ('total_amount',),
            'classes': ('wide',)
        }),
    )
    
    def get_customer_name(self, obj):
        """Display customer name"""
        return obj.pickup_request.full_name
    get_customer_name.short_description = 'Customer'
    
    def has_add_permission(self, request):
        """Disable manual invoice creation - they are auto-generated"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Prevent invoice deletion"""
        return False


@admin.register(EmailVerification)
class EmailVerificationAdmin(admin.ModelAdmin):
    """Admin interface for Email Verifications"""
    
    list_display = ['email', 'get_user_name', 'get_status', 'created_at', 'verified_at']
    list_filter = ['is_verified', 'created_at', 'verified_at']
    search_fields = ['email', 'user__email', 'user__first_name', 'user__last_name']
    readonly_fields = ['token', 'created_at', 'verified_at', 'user', 'email']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Email Information', {
            'fields': ('user', 'email')
        }),
        ('Verification', {
            'fields': ('token', 'is_verified')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'verified_at')
        }),
    )
    
    def get_user_name(self, obj):
        """Display user name"""
        return f"{obj.user.first_name} {obj.user.last_name}"
    get_user_name.short_description = 'User'
    
    def get_status(self, obj):
        """Display verification status with color"""
        if obj.is_verified:
            color = '#008000'  # Green
            status = '✅ Verified'
        else:
            if obj.is_token_expired():
                color = '#FF0000'  # Red
                status = '❌ Expired'
            else:
                color = '#FFA500'  # Orange
                status = '⏳ Pending'
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 5px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            status
        )
    get_status.short_description = 'Status'
    
    def has_add_permission(self, request):
        """Disable manual creation"""
        return False


# Customize Django Admin Site
admin.site.site_header = "VRL Logistics Administration"
admin.site.site_title = "VRL Logistics Admin"
admin.site.index_title = "Welcome to VRL Logistics Admin Panel"

