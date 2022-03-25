from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import AnonymousUser
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import ListView

from schedule_app.models import Event, ActivityOnEvent


class EventsList(ListView):
    model = Event
    paginate_by = 10
    template_name = 'events.html'

    # context_object_name = 'travels'

    def get_queryset(self):
        if isinstance(self.request.user, AnonymousUser):
            return []
        events = Event.objects.all().order_by('-start_date', '-end_date')

        return events


def login(_):
    return redirect('/admin')


class BaseOperations(LoginRequiredMixin):
    login_url = reverse_lazy('login')


class EventDetail(BaseOperations, ListView):
    model = ActivityOnEvent
    template_name = 'event_detail.html'

    # TODO Вывод сводной таблицы с помощью Plotly
    def get_queryset(self):
        return ActivityOnEvent.objects.filter(event__pk=self.kwargs.get('pk')).order_by('start_dt', 'end_dt')
