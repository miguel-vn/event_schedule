import pandas as pd
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import AnonymousUser
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.generic import ListView

from schedule_app.models import Event, ActivityOnEvent


class EventsList(ListView):
    model = Event
    paginate_by = 10
    template_name = 'events.html'

    def get_queryset(self):
        if isinstance(self.request.user, AnonymousUser):
            return []
        events = Event.objects.all().order_by('-start_date', '-end_date')

        return events


def login(_):
    return redirect('/admin')


class BaseOperations(LoginRequiredMixin):
    login_url = reverse_lazy('login')


def show_schedule(request, pk):
    objs = ActivityOnEvent.objects.filter(event__pk=pk).order_by('start_dt', 'end_dt')

    data = []
    for obj in objs:
        for person in obj.person.all():
            data.append({'start_dt': obj.start_dt,
                         'end_dt': obj.end_dt,
                         'activity': obj.activity.name,
                         'full_name': f"{person.first_name} {person.last_name}"})

    data = pd.DataFrame(data).rename(columns={'activity': 'Активность',
                                              'start_dt': 'Время начала',
                                              'full_name': ' '})
    data['  '] = 1
    a = data.pivot_table(columns=['Активность', 'Время начала'],
                         index=[' '], values=['  '], fill_value=0).astype('int8')

    def highlight(s):
        return "background: red" if s == 1 else None

    a = a.style.applymap(highlight, '  ')
    return render(request, '../templates/event_detail.html',
                  {'table_content': a.set_table_attributes('class="table"').to_html()})
