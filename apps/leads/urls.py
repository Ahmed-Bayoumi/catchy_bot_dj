from django.urls import path
from . import views

app_name = 'leads'

urlpatterns = [
    path('', views.lead_list_view, name='lead_list'),
    path('kanban/', views.lead_kanban_view, name='lead_kanban'),
    path('create/', views.lead_create_view, name='lead_create'),
    path('<int:pk>/', views.lead_detail_view, name='lead_detail'),
    path('<int:pk>/edit/', views.lead_edit_view, name='lead_edit'),
    path('<int:pk>/delete/', views.lead_delete_view, name='lead_delete'),
    path('<int:pk>/assign/', views.lead_assign_view, name='lead_assign'),
    path('<int:pk>/change-status/', views.lead_change_status_view, name='lead_change_status'),
    path('<int:pk>/change-stage/', views.lead_change_stage_view, name='lead_change_stage'),
    path('<int:pk>/set-follow-up/', views.lead_set_follow_up_view, name='lead_set_follow_up'),
    path('<int:pk>/add-note/', views.lead_add_note_view, name='lead_add_note'),
    path('note/<int:note_id>/delete/', views.note_delete_view, name='note_delete'),
    path('<int:pk>/activities/', views.lead_activities_view, name='lead_activities'),
    path('bulk-actions/', views.lead_bulk_actions_view, name='lead_bulk_actions'),
    path('export/', views.lead_export_view, name='lead_export'),
    path('import/', views.lead_import_view, name='lead_import'),
    path('<int:pk>/json/', views.lead_json_view, name='lead_json'),
    path('<int:pk>/quick-update/', views.lead_quick_update_view, name='lead_quick_update'),
]