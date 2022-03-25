from django.urls import path

from . import views

urlpatterns = [
    path('', views.EventsList.as_view(), name='events'),
    path('login', views.login, name='login'),
    path('<int:pk>', views.show_schedule, name='event_detail'),
]
