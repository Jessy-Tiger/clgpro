from django.urls import path
from . import views

urlpatterns = [
    # Public pages
    path('', views.home, name='home'),
    
    # Authentication
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='user_login'),
    path('logout/', views.user_logout, name='logout'),
    
    # Email Verification
    path('verify-email/', views.verify_email_page, name='verify_email_page'),
    path('verify-email/<str:token>/', views.verify_email, name='verify_email'),
    
    # Pickup requests
    path('pickup/request/', views.pickup_request, name='pickup_request'),
    path('pickup/history/', views.pickup_history, name='pickup_history'),
    path('pickup/<int:pickup_id>/', views.pickup_detail, name='pickup_detail'),
    
    # Admin
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/request/<int:pickup_id>/accept/', views.accept_request, name='accept_request'),
    path('admin/request/<int:pickup_id>/reject/', views.reject_request, name='reject_request'),
]
