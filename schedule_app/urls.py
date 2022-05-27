from django.urls import path

from . import views

urlpatterns = [
    path('', views.EventsList.as_view(), name='events'),
    path('login', views.login, name='login'),
    path('<int:pk>/volunteer_schedule', views.VolunteerSchedule.as_view(), name='volunteer_schedule'),
    path('<int:pk>/official_schedule', views.OfficialSchedule.as_view(), name='official_schedule'),
    path('<int:pk>/other_schedule', views.OtherSchedule.as_view(), name='other_schedule'),
    path('<int:pk>/download_schedule', views.download_all, name='download'),
    path('<int:event_pk>/<int:person_pk>/download_schedule', views.download_person, name='download_person_schedule'),
    path('<int:event_pk>/<int:person_pk>', views.PersonSchedule.as_view(), name='person'),
    path('person_replace', views.add_person, name='person_replace'),
    path('activity/<int:pk>', views.ActivityDetail.as_view(), name='activity_detail')
]
