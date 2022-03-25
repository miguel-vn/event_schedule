from django.urls import path

from . import views

urlpatterns = [
    path('', views.EventsList.as_view(), name='events'),
    path('login', views.login, name='login'),
    path('<int:pk>', views.EventDetail.as_view(), name='event_detail'),
    # path('new_person', views.NewPerson.as_view(), name='new_person'),
    # path('travel_detail/<int:pk>/', views.TravelDetail.as_view(), name='travel_detail'),
    # path('travel_detail/<int:pk>/delete', views.DeleteTravel.as_view(), name='travel_delete'),
    # path('travel_detail/<int:pk>/update', views.UpdateTravel.as_view(), name='travel_update'),
    # path('travel_detail/<int:travel_pk>/new_payment', views.AddPayment.as_view(), name='new_payment'),
    # path('travel_detail/<int:pk>/summary', views.SummaryPaymentsAndDebts.as_view(), name='summaries'),
]
