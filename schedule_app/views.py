import datetime
import os
from zipfile import ZipFile

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import AnonymousUser
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.generic import ListView

import schedule_app.common as common
import schedule_app.utils as utils
from adentro_schedule import settings
from schedule_app.models import Event, Person


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


@login_required
def download_all(_, pk):
    files_to_zip = {}
    event = Event.objects.get(pk=pk)

    for person in common.get_full_schedule(pk).exclude(person__isnull=True).values('person').distinct():
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
    person = Person.objects.get(pk=person_pk)

    activities = person.get_schedule(event_pk).order_by('start_dt', 'end_dt')

    formatted_schedule = utils.create_google_calendar_format_schedule(activities)

    filename = f'{person.last_name} {person.first_name}.csv'
    file_path = os.path.join(settings.MEDIA_ROOT, filename)

    formatted_schedule.to_csv(file_path, header=True, index=False)

    if os.path.exists(file_path):
        response = FileResponse(open(file_path, 'rb'))
        return response
    raise Http404


@login_required
def show_person_schedule(request, event_pk, person_pk):
    person = Person.objects.get(pk=person_pk)
    objs = person.get_schedule(event_pk, 'volunteer_schedule').order_by('start_dt', 'end_dt')

    return render(request, '../templates/person_detail.html', {'event_pk': event_pk,
                                                               'person': person,
                                                               'table_content': objs if objs else None})


@login_required
def show_official_schedule(request, pk):
    objs = common.get_official_schedule(pk).order_by('start_dt', 'end_dt')
    response = utils.ScheduleResponse(current_page_name='official_schedule', event_pk=pk)
    if not objs:
        return render(request, '../templates/event_detail.html', response.as_dict())

    data = []
    for activity in objs:
        row_data = {'start_dt': activity.start_dt,
                    'end_dt': activity.end_dt,
                    'activity': activity.activity.name,
                    'persons': [f"{person.last_name} {person.first_name}" for person in activity.person.all()]}

        data.append(row_data)

    response.content = data
    return render(request, '../templates/other_schedule.html', response.as_dict())


@login_required
def show_other_schedule(request, pk):
    objs = common.get_other_schedule(pk).order_by('start_dt', 'end_dt')
    response = utils.ScheduleResponse(current_page_name='other_schedule', event_pk=pk)

    if not objs:
        return render(request, '../templates/event_detail.html', response.as_dict())

    data = []
    for activity in objs:
        row_data = {'start_dt': activity.start_dt,
                    'end_dt': activity.end_dt,
                    'activity': activity.activity.name,
                    'persons': [f"{person.last_name} {person.first_name}" for person in activity.person.all()]}

        data.append(row_data)

    response.content = data
    return render(request, '../templates/other_schedule.html', response.as_dict())


@login_required
def show_volunteer_schedule(request, pk):
    objs = common.get_full_schedule(pk)

    response = utils.ScheduleResponse(current_page_name='volunteer_schedule', event_pk=pk)

    if not objs.filter(activity__activity_type__name='volunteer_schedule'):
        return render(request, '../templates/event_detail.html', response.as_dict())

    headers = {'activity_dt': list(),
               'activity_name': list(),
               'need_peoples': list()}
    persons = Person.objects.all()
    event = response.event
    names = {person: {'status': list(),
                      'duration_full': datetime.timedelta(seconds=0)} for person in persons}

    for activity in objs.filter(activity__activity_type__name='volunteer_schedule').order_by('start_dt', 'end_dt'):
        row_data = {'start_dt': activity.start_dt,
                    'end_dt': activity.end_dt,
                    'time_coef': activity.activity.category.time_coefficient,
                    'additional_time': activity.activity.category.additional_time,
                    'activity': activity.activity.name,
                    'persons': [person for person in activity.person.all()],
                    'need_peoples': activity.activity.need_peoples,
                    'activity_pk': activity.pk}

        not_arrived_persons = Person.objects.filter(Q(arrival_datetime__gte=activity.start_dt) |
                                                    Q(departure_datetime__lte=activity.end_dt))
        row_data['unavailable'] = [person for person in not_arrived_persons]

        another_acts = objs.filter(~Q(pk=activity.pk))
        for another_act in another_acts:
            if utils.is_intersects(start_dt=another_act.start_dt, end_dt=another_act.end_dt, activity=activity,
                                   checked_activity=another_act):
                row_data['unavailable'] += [person for person in another_act.person.all()]

        duration = utils.get_duration(row_data)
        duration_with_coef = utils.get_duration_with_coef(duration, row_data['additional_time'], row_data['time_coef'])

        headers['activity_dt'].append(utils.date_transform(row_data, duration, duration_with_coef))
        headers['activity_name'].append(row_data['activity'])
        headers['need_peoples'].append(utils.need_peoples_transform(row_data))

        for person in persons:
            if person in row_data['persons']:
                names[person]['duration_full'] += duration_with_coef
                names[person]['status'].append('Участвует')
            elif person in row_data['unavailable']:
                names[person]['status'].append('Недоступен')
            else:
                names[person]['status'].append('Доступен')

    for person in list(names.keys()):
        names[person]['duration_full'] = utils.human_readable_time(
            int(names[person]['duration_full'].total_seconds()) // 60)
        names[utils.create_url_for_person(event, person)] = names.pop(person)

    response.content = {'table_headers': headers,
                        'persons': names}

    return render(request, '../templates/event_detail.html', {'table_headers': headers,
                                                              'persons': names,
                                                              'current_page': 'volunteer_schedule',
                                                              'event': event})
