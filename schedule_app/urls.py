from django.urls import path

from . import views

urlpatterns = [
    path('', views.EventsList.as_view(), name='events'),
    path('login', views.login, name='login'),
    path('<int:pk>/volunteer_schedule', views.show_volunteer_schedule, name='volunteer_schedule'),
    path('<int:pk>/official_schedule', views.show_official_schedule, name='official_schedule'),
    path('<int:pk>/other_schedule', views.show_other_schedule, name='other_schedule'),
    path('<int:pk>/download_schedule', views.download_all, name='download'),
    path('<int:event_pk>/<int:person_pk>/download_schedule', views.download_person, name='download_person_schedule'),
    path('<int:event_pk>/<int:person_pk>', views.show_person_schedule, name='person')
]
