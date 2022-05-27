import datetime
import os
from zipfile import ZipFile

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import AnonymousUser
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView

import schedule_app.constants as const
import schedule_app.utils as utils
from adentro_schedule import settings
from schedule_app.models import Event, Person, ActivityOnEvent, Activity


def login(_):
    return redirect('/admin')


class LoginMixin(LoginRequiredMixin):
    login_url = reverse_lazy('login')


class EventsList(ListView):
    model = Event
    paginate_by = 10
    template_name = 'events.html'

    def get_queryset(self):
        if isinstance(self.request.user, AnonymousUser):
            return []
        events = Event.objects.all().order_by('-start_date', '-end_date')

        return events


def add_person(request):
    # TODO need free_time_limit validation here

    pk = int(request.GET.get('aoe'))
    event_pk = int(request.GET.get('event'))
    person_pk = int(request.GET.get('person'))

    action_type = request.GET.get('action_type')
    act = ActivityOnEvent.objects.get(pk=pk)

    person = Person.objects.get(pk=person_pk)
    if action_type == 'del':
        act.person.remove(person)
        act.save()

    elif action_type == 'add':
        act.person.add(person)
        act.save()

    return redirect('volunteer_schedule', pk=event_pk)


@login_required
def download_all(_, pk):
    files_to_zip = {}
    event = get_object_or_404(Event, pk=pk)

    for person in event.get_schedule().exclude(person__isnull=True).values('person').distinct():
        person = Person.objects.get(pk=person['person'])

        activities = person.get_schedule(pk).order_by('start_dt', 'end_dt')

        filename = f'{person.last_name} {person.first_name}.csv'
        files_to_zip[filename] = utils.create_google_calendar_format_schedule(activities)

    archive_path = os.path.join(settings.MEDIA_ROOT, f'{event.title}_расписание.zip')

    with ZipFile(archive_path, 'w') as zip_file:
        for file in files_to_zip:
            zip_file.writestr(file, files_to_zip[file].to_csv(index=False, header=True))

    if os.path.exists(archive_path):
        response = FileResponse(open(archive_path, 'rb'))
        return response
    raise Http404


@login_required
def download_person(_, event_pk, person_pk):
    person = get_object_or_404(Person, pk=person_pk)

    activities = person.get_schedule(event_pk).order_by('start_dt', 'end_dt')

    formatted_schedule = utils.create_google_calendar_format_schedule(activities)

    filename = f'{person.last_name} {person.first_name}.csv'
    file_path = os.path.join(settings.MEDIA_ROOT, filename)

    formatted_schedule.to_csv(file_path, header=True, index=False)

    if os.path.exists(file_path):
        response = FileResponse(open(file_path, 'rb'))
        return response
    raise Http404


class ActivityDetail(LoginMixin, DetailView):
    model = Activity
    template_name = 'activity_detail.html'


class PersonSchedule(LoginMixin, ListView):
    model = Person
    template_name = 'person_detail.html'

    def get_context_data(self, **kwargs):
        person = get_object_or_404(Person, pk=self.kwargs['person_pk'])

        object_list = person.get_schedule(self.kwargs['event_pk'], const.VOLUNTEER).order_by('start_dt', 'end_dt')
        context = super(PersonSchedule, self).get_context_data(object_list=object_list)
        context['event_pk'] = self.kwargs['event_pk']
        context['person'] = person
        return context


class OfficialSchedule(LoginMixin, ListView):
    model = Event
    template_name = 'other_schedule.html'

    def get_context_data(self, **kwargs):
        event = get_object_or_404(Event, pk=self.kwargs['pk'])

        object_list = event.get_schedule(const.OFFICIAL).order_by('start_dt', 'end_dt')
        context = super(OfficialSchedule, self).get_context_data(object_list=object_list)
        context['event'] = event
        context['current_page'] = const.OFFICIAL
        return context


class OtherSchedule(LoginMixin, ListView):
    model = Event
    template_name = 'other_schedule.html'

    def get_context_data(self, **kwargs):
        event = get_object_or_404(Event, pk=self.kwargs['pk'])

        object_list = event.get_schedule(const.OTHER).order_by('start_dt', 'end_dt')
        context = super(OtherSchedule, self).get_context_data(object_list=object_list)
        context['event'] = event
        context['current_page'] = const.OTHER
        return context


class VolunteerSchedule(LoginMixin, ListView):
    model = Event
    template_name = 'event_detail.html'

    def get_context_data(self, **kwargs):
        event = get_object_or_404(Event, pk=self.kwargs['pk'])
        objs = event.get_schedule()
        headers = {'activity_dt': list(),
                   'activity_name': list(),
                   'need_peoples': list()}
        persons = Person.objects.all()
        names = {person: {'status': list(),
                          'duration_full': datetime.timedelta(seconds=0)} for person in persons}
        volunteer_objs = objs.filter(activity__category__activity_type__name=const.VOLUNTEER).order_by('start_dt',
                                                                                                       'end_dt')
        context = super(VolunteerSchedule, self).get_context_data(object_list=list())
        context['event'] = event
        context['current_page'] = const.VOLUNTEER

        if not volunteer_objs:
            context['table_headers'] = headers
            context['persons'] = names

            return context

        for activity in volunteer_objs:
            row_data = self.extract_activity_data(activity)

            another_acts = objs.filter(~Q(pk=activity.pk))
            for another_act in another_acts:
                if activity.is_intersects(another_act):
                    row_data['unavailable'] += [person for person in another_act.person.all()]

            duration = activity.duration()
            duration_with_coef = activity.duration_with_coef()

            headers['activity_dt'].append(utils.date_transform(row_data, duration, duration_with_coef))
            headers['activity_name'].append(row_data['activity'])
            headers['need_peoples'].append(utils.need_peoples_transform(row_data))

            filled = row_data['need_peoples'] == len(row_data['persons'])
            for person in persons:
                if person in row_data['persons']:
                    names[person]['duration_full'] += duration_with_coef
                    names[person]['status'].append(('Участвует', activity.pk, filled))

                elif person in row_data['unavailable']:
                    names[person]['status'].append('Недоступен')
                elif not person.arrive_and_depart_filled():
                    names[person]['status'].append('?')
                else:
                    names[person]['status'].append(('Доступен', activity.pk))

        for person in list(names.keys()):
            names[person]['duration_full'] = utils.human_readable_time(
                int(names[person]['duration_full'].total_seconds()) // 60)

        context['table_headers'] = headers
        context['persons'] = names

        return context

    @staticmethod
    def extract_activity_data(activity):
        row_data = {'start_dt': activity.start_dt,
                    'end_dt': activity.end_dt,
                    'time_coef': activity.activity.category.time_coefficient,
                    'additional_time': activity.activity.category.additional_time,
                    'activity': activity.activity,
                    'persons': [person for person in activity.person.all()],
                    'need_peoples': activity.activity.need_peoples,
                    'activity_pk': activity.pk}

        unavailable = Person.objects.filter(Q(arrival_datetime__gte=activity.start_dt) |
                                            Q(departure_datetime__lte=activity.end_dt) |
                                            Q(excluded_categories=activity.activity.category))
        row_data['unavailable'] = [person for person in unavailable]

        return row_data
