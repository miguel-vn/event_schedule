import os
from zipfile import ZipFile

import pandas as pd
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import AnonymousUser
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.generic import ListView

import schedule_app.utils as utils
from adentro_schedule import settings
from schedule_app.models import Event, ActivityOnEvent, Person


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


def download_all(_, pk):
    files_to_zip = {}

    for person in ActivityOnEvent.objects.filter(event__pk=pk).values('person').distinct():
        person = Person.objects.get(pk=person['person'])

        activities = ActivityOnEvent.objects.filter(event__pk=pk,
                                                    person__pk=person.pk) \
            .order_by('start_dt', 'end_dt')

        filename = f'{person.last_name} {person.first_name}.csv'
        files_to_zip[filename] = utils.create_google_calendar_format_schedule(activities)

    archive_path = os.path.join(settings.MEDIA_ROOT, f'{Event.objects.get(pk=pk).title}_расписание.zip')

    with ZipFile(archive_path, 'w') as zip_file:
        for file in files_to_zip:
            zip_file.writestr(file, files_to_zip[file].to_csv(index=False, header=True))

    if os.path.exists(archive_path):
        response = FileResponse(open(archive_path, 'rb'))
        return response
    raise Http404


def download_person(_, event_pk, person_pk):
    person = Person.objects.get(pk=person_pk)

    activities = ActivityOnEvent.objects.filter(event__pk=event_pk,
                                                person__pk=person_pk,
                                                activity__activity_type__name='volunteer_schedule') \
        .order_by('start_dt', 'end_dt')

    formatted_schedule = utils.create_google_calendar_format_schedule(activities)

    filename = f'{person.last_name} {person.first_name}.csv'
    file_path = os.path.join(settings.MEDIA_ROOT, filename)

    formatted_schedule.to_csv(file_path, header=True, index=False)

    if os.path.exists(file_path):
        response = FileResponse(open(file_path, 'rb'))
        return response
    raise Http404


class ScheduleResponse:
    empty_schedule_message = '<div class="container"><h2>Расписание отсутствует</h2></div>'

    def __init__(self, current_page_name, event_pk, content=None):
        assert current_page_name in ('official_schedule', 'other_schedule', 'volunteer_schedule')

        self.current_page_name = current_page_name
        self.event = Event.objects.get(pk=event_pk)
        self.__content = content

    @property
    def content(self):
        return self.__content if self.__content else self.empty_schedule_message

    @content.setter
    def content(self, value):
        self.__content = value

    def as_dict(self):
        return {'table_content': self.content,
                'current_page': self.current_page_name,
                'event': self.event}


def show_person_schedule(request, event_pk, person_pk):
    person = Person.objects.get(pk=person_pk)
    objs = ActivityOnEvent.objects.filter(event__pk=event_pk,
                                          person__pk=person_pk,
                                          activity__activity_type__name='volunteer_schedule') \
        .order_by('start_dt', 'end_dt')

    return render(request, '../templates/person_detail.html', {'event_pk': event_pk,
                                                               'person': person,
                                                               'table_content': objs if objs else None})


def show_official_schedule(request, pk):
    objs = ActivityOnEvent.objects.filter(event__pk=pk,
                                          activity__activity_type__name='official_schedule') \
        .order_by('start_dt', 'end_dt')

    response = ScheduleResponse(current_page_name='official_schedule', event_pk=pk)
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


def show_other_schedule(request, pk):
    objs = ActivityOnEvent.objects.filter(event__pk=pk,
                                          activity__activity_type__name='other_schedule') \
        .order_by('start_dt', 'end_dt')
    response = ScheduleResponse(current_page_name='other_schedule', event_pk=pk)

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


def show_volunteer_schedule(request, pk):
    objs = ActivityOnEvent.objects.filter(event__pk=pk)

    response = ScheduleResponse(current_page_name='volunteer_schedule', event_pk=pk)

    if not objs.filter(activity__activity_type__name='volunteer_schedule'):
        return render(request, '../templates/event_detail.html', response.as_dict())

    data = []
    for activity in objs.filter(activity__activity_type__name='volunteer_schedule').order_by('start_dt', 'end_dt'):
        row_data = {'start_dt': activity.start_dt,
                    'end_dt': activity.end_dt,
                    'time_coef': activity.activity.category.time_coefficient,
                    'additional_time': activity.activity.category.additional_time,
                    'activity': activity.activity.name,
                    'persons': [utils.create_url_for_person(activity.event,
                                                            person) for person in activity.person.all()],
                    'need_peoples': activity.activity.need_peoples,
                    'activity_pk': activity.pk}

        not_arrived_persons = Person.objects.filter(Q(arrival_datetime__gte=activity.start_dt) |
                                                    Q(departure_datetime__lte=activity.end_dt))
        row_data['unavailable'] = [utils.create_url_for_person(activity.event,
                                                               person) for person in not_arrived_persons]

        another_acts = objs.filter(~Q(pk=activity.pk))
        for another_act in another_acts:
            if utils.is_intersects(start_dt=another_act.start_dt, end_dt=another_act.end_dt, activity=activity,
                                   checked_activity=another_act):
                row_data['unavailable'] += [utils.create_url_for_person(activity.event,
                                                                        person) for person in another_act.person.all()]

        data.append(row_data)

    df = pd.DataFrame(data)

    df['num_peoples'] = df['persons'].apply(len)

    df['need_peoples'] = df[['need_peoples', 'num_peoples', 'activity_pk']].apply(utils.need_peoples_transform, axis=1)
    df.drop(columns=['num_peoples'], inplace=True)
    df = df.explode('persons').reset_index(drop=True)

    unavailables = df.explode('unavailable') \
        .dropna(subset=['unavailable']) \
        .drop(columns=['persons']) \
        .rename(columns={'unavailable': 'persons'}) \
        .drop_duplicates() \
        .reset_index(drop=True)

    unavailables['available'] = -1

    df = df.drop(columns=['unavailable'])

    df = pd.concat([df, unavailables]).fillna(1).astype({'available': 'int8'})

    df['duration'] = df[['start_dt', 'end_dt']].apply(utils.get_duration, axis=1)
    df['duration_with_coef'] = df[['duration', 'time_coef', 'additional_time']] \
        .apply(utils.get_duration_with_coef, axis=1)

    new_df = df.groupby('persons') \
        .agg({'duration_with_coef': 'sum'}) \
        .rename(columns={'duration_with_coef': 'duration_with_coef_full'})

    new_df['duration_full'] = new_df['duration_with_coef_full'].apply(utils.total_person_load)

    df['start_dt'] = df[['start_dt', 'end_dt', 'duration', 'duration_with_coef']].apply(utils.date_transform, axis=1)

    df = df.merge(new_df, left_on='persons', right_index=True, how='inner')

    df = df.pivot_table(values='available', index=['persons', 'duration_full'],
                        columns=['start_dt', 'activity', 'need_peoples'],
                        fill_value=0).astype('int8')
    df = df.applymap(utils.replace_person_status)

    table_styles = [{'selector': 'th.col_heading', 'props': 'text-align: center;'}]

    for i, col in enumerate(df.columns):
        if 'Требуется еще' in col[2]:
            table_styles.append({'selector': f'th.col_heading.level2.col{i}', 'props': 'background: #FFD700;'})

    df.columns.set_names(['Время', 'Активность', 'Наполнение'], inplace=True)
    df.index.set_names(['', '   '], inplace=True)
    df = df.style.applymap(utils.highlight)

    out = df.set_table_attributes('class="table"').set_table_styles(table_styles, overwrite=False).to_html()

    response.content = out
    return render(request, '../templates/event_detail.html', response.as_dict())
