from django.urls import path
from . import views
from . import views_simulator
app_name = 'whatsapp'

urlpatterns = [
    path('webhook/woztell/<str:webhook_secret>/',views.webhook_receiver,name='webhook_receiver'),
    path('webhook/woztell/<str:webhook_secret>/',views.webhook_test, name='webhook_test'),
    path('send-message/', views.send_message_api, name='send_message'),
    path('messages/<int:lead_id>/',views.get_messages_api,name='get_messages'),

    path('webhook-simulator/',views_simulator.webhook_simulator_page,name='webhook_simulator'),
    path('simulate-incoming-message/',views_simulator.simulate_incoming_message,name='simulate_incoming_message'),
    path('quick-test-webhook/',views_simulator.quick_test_webhook,name='quick_test_webhook'),
    path('simulator/lead/<int:lead_id>/messages/',views_simulator.get_lead_messages,name='simulator_lead_messages'),
]
