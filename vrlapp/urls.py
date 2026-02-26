from django.urls import path
from . import views

urlpatterns = [
    # Public pages
    path('', views.home, name='home'),
    
    # Authentication
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='user_login'),
    path('logout/', views.user_logout, name='logout'),
    
    # Pickup requests
    path('pickup/request/', views.pickup_request, name='pickup_request'),
    path('pickup/history/', views.pickup_history, name='pickup_history'),
    path('pickup/<int:pickup_id>/', views.pickup_detail, name='pickup_detail'),
    
    # Admin
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/request/<int:pickup_id>/accept/', views.accept_request, name='accept_request'),
    path('admin/request/<int:pickup_id>/reject/', views.reject_request, name='reject_request'),
    path('admin/request/<int:pickup_id>/complete/', views.complete_request, name='complete_request'),
    
    # Admin panel actions
    path('admin/pickup/<int:pickup_id>/accept_request/', views.admin_accept_request, name='admin_accept_request'),
    path('admin/pickup/<int:pickup_id>/reject_request/', views.admin_reject_request, name='admin_reject_request'),
    path('admin/pickup/<int:pickup_id>/complete_request/', views.admin_complete_request, name='admin_complete_request'),
]
