import os
from zipfile import ZipFile

import pandas as pd
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import AnonymousUser
from django.http import FileResponse, Http404
from django.shortcuts import redirect, render, reverse
from django.urls import reverse_lazy
from django.views.generic import ListView

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


def show_schedule(request, pk):
    objs = ActivityOnEvent.objects.filter(event__pk=pk,
                                          activity__activity_type__name='volunteer_schedule')\
        .order_by('start_dt', 'end_dt')

    data = []
    activity_pk = {}
    for activity in objs:
        row_data = {'start_dt': activity.start_dt,
                    'end_dt': activity.end_dt,
                    'time_coef': activity.activity.category.time_coefficient,
                    'activity': activity.activity.name,
                    'persons': [f"{person.last_name} {person.first_name}" for person in activity.person.all()],
                    'need_peoples': activity.activity.need_peoples,
                    'activity_pk': activity.pk}

        activity_pk[activity.activity.name] = activity.pk

        data.append(row_data)

    df = pd.DataFrame(data)

    df['num_peoples'] = df['persons'].apply(len)

    def need_peoples_transform(value):
        need = value['need_peoples']
        current = value['num_peoples']
        msg = f'{current}/{need}'

        if need == current:
            return f'Заполнено ({msg})'
        diff = need - current
        admin_url = reverse('admin:schedule_app_activityonevent_change', args=(value['activity_pk'],))

        return f'<a href="{admin_url}" target="_blank">Требуется еще {diff} ({msg})</a>'

    def date_transform(value):
        start = value['start_dt']
        end = value['end_dt']
        coef = value['time_coef']
        duration = (end - start).seconds // 60
        duration_with_coef = int(duration * coef)

        duration = human_readable_time(duration)
        duration_with_coef = human_readable_time(duration_with_coef)
        return f"{start.strftime('%d.%m %H:%M')} - {end.strftime('%H:%M')} ({duration} - {duration_with_coef})"

    def human_readable_time(value):
        if value > 60:
            h = value // 60
            m = value % 60
            value = f"{h} ч. {m} мин."
        else:
            value = f"{value} мин."
        return value

    def highlight(s):
        return "background: #00FF00" if s == 'Участвует' else None

    df['need_peoples'] = df[['need_peoples', 'num_peoples', 'activity_pk']].apply(need_peoples_transform, axis=1)
    df['start_dt'] = df[['start_dt', 'end_dt', 'time_coef']].apply(date_transform, axis=1)

    df.drop(columns=['num_peoples'], inplace=True)
    df = df.explode('persons').reset_index(drop=True)
    df['values'] = 1
    df = df.pivot_table(values='values', index='persons', columns=['start_dt', 'activity','need_peoples'],
                        fill_value=0).astype('int8')
    df = df.applymap(lambda elem: 'Участвует' if elem == 1 else 'Доступен')

    table_styles = [{'selector': 'th.col_heading', 'props': 'text-align: center;'},
                    {'selector': 'th.col_heading.level1', 'props': 'font-size: 1.5em;'}]

    for i, col in enumerate(df.columns):
        if 'Требуется еще' in col[2]:
            table_styles.append({'selector': f'th.col_heading.level2.col{i}', 'props': 'background: #FFD700;'})

    df.columns.set_names(['Время', 'Активность','Наполнение'], inplace=True)
    df.index.set_names([''], inplace=True)
    df = df.style.applymap(highlight)

    out = df.set_table_attributes('class="table"').set_table_styles(table_styles, overwrite=False).to_html()

    return render(request, '../templates/event_detail.html',
                  {'table_content': out,
                   'event': Event.objects.get(pk=pk)})
