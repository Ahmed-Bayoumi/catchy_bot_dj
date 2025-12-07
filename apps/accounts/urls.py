# URLs in this file:
# - /accounts/login/          → Login page
# - /accounts/logout/         → Logout action
# - /accounts/profile/        → User profile page
# - /accounts/profile/edit/   → Edit profile
# - /accounts/password/change → Change password

# Namespace: 'accounts'
# Usage in templates: {% url 'accounts:login' %}
# ==============================================================================

from django.urls import path
from . import views

# Namespace for this app's URLs
# Allows referring to URLs as 'accounts:login' instead of just 'login'
# Prevents conflicts if multiple apps have 'login' URL
app_name = 'accounts'

urlpatterns = [

    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.profile_edit_view, name='profile_edit'),
    path('password/change/', views.password_change_view, name='password_change'),
    path('password/reset/', views.password_reset_request_view, name='password_reset'),
    path(
        'password/reset/<uidb64>/<token>/',
        views.password_reset_confirm_view,
        name='password_reset_confirm'
    ),
    path('users/', views.user_list_view, name='user_list'),
    path('users/<int:pk>/toggle-status/', views.toggle_user_status, name='user_toggle_status'),
    path('users/<int:pk>/', views.user_detail_view, name='user_detail'),
    path('users/create/', views.user_create_view, name='user_create'),
    path('users/<int:pk>/edit/', views.user_edit_view, name='user_edit'),

    path('users/<int:pk>/delete/', views.user_delete_view, name='user_delete'),
]



# ==============================================================================
# TESTING URLS
# ==============================================================================
#
# Test URL resolution:
# from django.urls import reverse
#
# # Test login URL
# url = reverse('accounts:login')
# assert url == '/accounts/login/'
#
# # Test user detail URL
# url = reverse('accounts:user_detail', kwargs={'pk': 5})
# assert url == '/accounts/users/5/'
#
# # Test in Django shell
# python manage.py shell
# >>> from django.urls import reverse
# >>> reverse('accounts:profile')
# '/accounts/profile/'
#
# ==============================================================================