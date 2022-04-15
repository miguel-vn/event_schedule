import os
from zipfile import ZipFile

import pandas as pd
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import AnonymousUser
from django.http import FileResponse, Http404
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.generic import ListView

from adentro_schedule import settings
from schedule_app.models import Event, ActivityOnEvent, Person
from schedule_app.utils import (highlight,
                                date_transform,
                                need_peoples_transform,
                                Act, is_intersects,
                                replace_person_status)


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


def download(request, pk):
    files_to_zip = {}
    date_format = '%Y-%m-%d'
    time_format = '%H:%M:%S'
    for person in ActivityOnEvent.objects.filter(event__pk=pk).values('person').distinct():
        person = Person.objects.get(pk=person['person'])

        activities = ActivityOnEvent.objects.filter(event__pk=pk,
                                                    person__pk=person.pk) \
            .order_by('start_dt', 'end_dt')
        data = []
        for activity in activities:
            data.append({'Subject': activity.activity.name,
                         'Start Date': activity.start_dt.strftime(date_format),
                         'Start Time': activity.start_dt.strftime(time_format),
                         'End Date': activity.end_dt.strftime(date_format),
                         'End Time': activity.end_dt.strftime(time_format),
                         'Description': activity.activity.description})

        filename = f'{person.last_name} {person.first_name}.csv'
        files_to_zip[filename] = pd.DataFrame(data, dtype=str)
        data.clear()

    archive_path = os.path.join(settings.MEDIA_ROOT, f'{Event.objects.get(pk=pk).title}_расписание.zip')

    with ZipFile(archive_path, 'w') as zip_file:
        for file in files_to_zip:
            zip_file.writestr(file, files_to_zip[file].to_csv(index=False, header=True))

    if os.path.exists(archive_path):
        response = FileResponse(open(archive_path, 'rb'))
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
    objs = ActivityOnEvent.objects.filter(event__pk=pk,
                                          activity__activity_type__name='volunteer_schedule') \
        .order_by('start_dt', 'end_dt')

    response = ScheduleResponse(current_page_name='volunteer_schedule', event_pk=pk)

    if not objs:
        return render(request, '../templates/event_detail.html', response.as_dict())

    data = []
    activity_pk = {}
    for activity in objs:
        row_data = {'start_dt': activity.start_dt,
                    'end_dt': activity.end_dt,
                    'time_coef': activity.activity.category.time_coefficient,
                    'additional_time': activity.activity.category.additional_time,
                    'activity': activity.activity.name,
                    'persons': [f"{person.last_name} {person.first_name}" for person in activity.person.all()],
                    'need_peoples': activity.activity.need_peoples,
                    'activity_pk': activity.pk}

        activity_pk[activity.activity.name] = activity.pk

        data.append(row_data)

    for i in range(len(data)):
        row_data = data[i]
        act = Act(row_data['start_dt'], row_data['end_dt'], row_data['activity_pk'])
        for j in range(i + 1, len(data)):
            checking_act = Act(data[j]['start_dt'], data[j]['end_dt'], data[j]['activity_pk'])

            if is_intersects(start_dt=checking_act.start_dt, end_dt=checking_act.end_dt, activity=act,
                             checked_activity=checking_act):
                data[j]['unavailable'] = data[i]['persons']
            else:
                data[j]['unavailable'] = list()

    df = pd.DataFrame(data)

    df['num_peoples'] = df['persons'].apply(len)

    df['need_peoples'] = df[['need_peoples', 'num_peoples', 'activity_pk']].apply(need_peoples_transform, axis=1)
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
    df['start_dt'] = df[['start_dt', 'end_dt', 'time_coef', 'additional_time']].apply(date_transform, axis=1)

    df = df.pivot_table(values='available', index='persons', columns=['start_dt', 'activity', 'need_peoples'],
                        fill_value=0).astype('int8')
    df = df.applymap(replace_person_status)

    table_styles = [{'selector': 'th.col_heading', 'props': 'text-align: center;'},
                    {'selector': 'th.col_heading.level1', 'props': 'font-size: 1.5em;'}]

    for i, col in enumerate(df.columns):
        if 'Требуется еще' in col[2]:
            table_styles.append({'selector': f'th.col_heading.level2.col{i}', 'props': 'background: #FFD700;'})

    df.columns.set_names(['Время', 'Активность', 'Наполнение'], inplace=True)
    df.index.set_names([''], inplace=True)
    df = df.style.applymap(highlight)

    out = df.set_table_attributes('class="table"').set_table_styles(table_styles, overwrite=False).to_html()

    response.content = out
    return render(request, '../templates/event_detail.html', response.as_dict())
