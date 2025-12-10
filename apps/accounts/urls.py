from django.urls import path
from . import views

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
